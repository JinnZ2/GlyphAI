"""A deliberately well-behaved HTTP fetcher.

GlyphAI exists to resist exploitative behaviour, so its own crawler does not
get to be exploitative. This fetcher:

  * obeys robots.txt, including Crawl-delay
  * rate-limits itself per host
  * identifies itself honestly in the User-Agent
  * caches responses on disk so re-runs do not re-hit a site
  * caps response size and always sets a timeout

Explicit non-goals: rotating user agents, proxy pools, CAPTCHA solving, or any
other means of evading a site that has said no. If a site disallows automated
access, the correct outcome is to stop, and `RobotsDenied` is that outcome.

Standard library only. The network call is injectable, so tests never touch
the network.
"""

import gzip
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import urlparse, urlunparse

DEFAULT_USER_AGENT = (
    "GlyphAI/0.1 (personal shopping agent; "
    "+https://github.com/JinnZ2/GlyphAI)"
)
DEFAULT_TIMEOUT = 10.0
DEFAULT_MIN_INTERVAL = 1.0      # seconds between requests to the same host
DEFAULT_MAX_BYTES = 2_000_000   # 2 MB is plenty for a product page
DEFAULT_CACHE_TTL = 3600        # 1 hour


class FetchError(Exception):
    """A page could not be retrieved."""


class RobotsDenied(FetchError):
    """The site's robots.txt disallows this URL for our user agent."""


def urllib_transport(url, headers, timeout, max_bytes):
    """Default network transport. Returns (status, text, final_url)."""
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise FetchError(f"Response from {url} exceeded {max_bytes} bytes")
            if response.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            charset = response.headers.get_content_charset() or "utf-8"
            status = getattr(response, "status", 200)
            final_url = response.geturl()
    except urllib.error.HTTPError as e:
        return e.code, "", url
    except FetchError:
        raise
    except Exception as e:
        raise FetchError(f"Could not fetch {url}: {e}")
    return status, raw.decode(charset, errors="replace"), final_url


class PoliteFetcher:
    def __init__(self, user_agent=DEFAULT_USER_AGENT, timeout=DEFAULT_TIMEOUT,
                 min_interval=DEFAULT_MIN_INTERVAL, max_bytes=DEFAULT_MAX_BYTES,
                 cache_dir=None, cache_ttl=DEFAULT_CACHE_TTL,
                 respect_robots=True, transport=None,
                 sleep=time.sleep, clock=time.time):
        self.user_agent = user_agent
        self.timeout = timeout
        self.min_interval = min_interval
        self.max_bytes = max_bytes
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self.respect_robots = respect_robots
        self.transport = transport or urllib_transport
        self._sleep = sleep
        self._clock = clock
        self._last_request = {}   # host -> timestamp
        self._robots = {}         # host -> (RobotFileParser or None)

    # -- robots.txt ------------------------------------------------------

    def _robots_for(self, url):
        parts = urlparse(url)
        host = parts.netloc
        if host in self._robots:
            return self._robots[host]

        robots_url = urlunparse((parts.scheme, host, "/robots.txt", "", "", ""))
        parser = urllib.robotparser.RobotFileParser()
        try:
            status, text, _ = self.transport(
                robots_url, {"User-Agent": self.user_agent},
                self.timeout, self.max_bytes)
        except FetchError:
            parser = None  # Unreachable robots.txt: fail open, as crawlers do.
        else:
            if status == 200 and text:
                parser.parse(text.splitlines())
            elif 500 <= status < 600:
                # A server error is not permission; refuse rather than assume.
                parser.disallow_all = True
            else:
                parser = None  # 404 and friends mean "no restrictions".
        self._robots[host] = parser
        return parser

    def can_fetch(self, url):
        if not self.respect_robots:
            return True
        parser = self._robots_for(url)
        if parser is None:
            return True
        return parser.can_fetch(self.user_agent, url)

    def crawl_delay(self, url):
        parser = self._robots_for(url) if self.respect_robots else None
        if parser is None:
            return self.min_interval
        try:
            delay = parser.crawl_delay(self.user_agent)
        except AttributeError:
            delay = None
        return max(self.min_interval, float(delay)) if delay else self.min_interval

    # -- cache -----------------------------------------------------------

    def _cache_path(self, url):
        if not self.cache_dir:
            return None
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, digest + ".json")

    def _read_cache(self, url):
        path = self._cache_path(url)
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r") as handle:
                entry = json.load(handle)
        except Exception:
            return None
        if self._clock() - entry.get("fetched_at", 0) > self.cache_ttl:
            return None
        return entry.get("body")

    def _write_cache(self, url, body):
        path = self._cache_path(url)
        if not path:
            return
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(path, "w") as handle:
                json.dump({"url": url, "fetched_at": self._clock(), "body": body},
                          handle)
        except Exception:
            pass  # A cache failure must never break a fetch.

    # -- fetching --------------------------------------------------------

    def _throttle(self, url):
        host = urlparse(url).netloc
        last = self._last_request.get(host)
        delay = self.crawl_delay(url)
        if last is not None:
            elapsed = self._clock() - last
            if elapsed < delay:
                self._sleep(delay - elapsed)
        self._last_request[host] = self._clock()

    def fetch(self, url):
        """Return the page text, or raise FetchError / RobotsDenied."""
        parts = urlparse(url)
        if parts.scheme not in ("http", "https"):
            raise FetchError(f"Unsupported URL scheme: {url!r}")

        cached = self._read_cache(url)
        if cached is not None:
            return cached

        if not self.can_fetch(url):
            raise RobotsDenied(
                f"robots.txt at {parts.netloc} disallows {url} for {self.user_agent}")

        self._throttle(url)
        status, text, _ = self.transport(
            url,
            {"User-Agent": self.user_agent,
             "Accept": "text/html,application/xhtml+xml"},
            self.timeout, self.max_bytes)

        if status != 200:
            raise FetchError(f"{url} returned HTTP {status}")
        self._write_cache(url, text)
        return text
