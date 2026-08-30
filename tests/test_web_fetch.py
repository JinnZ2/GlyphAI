import sys
import os
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_fetch import PoliteFetcher, FetchError, RobotsDenied

ALLOW_ALL = "User-agent: *\nDisallow:\n"
DENY_ALL = "User-agent: *\nDisallow: /\n"
DENY_PRICES = "User-agent: *\nDisallow: /prices\n"
DELAYED = "User-agent: *\nDisallow:\nCrawl-delay: 5\n"


class FakeTransport:
    """Stands in for the network. Records every request it receives."""

    def __init__(self, pages, robots=ALLOW_ALL, status=200):
        self.pages = pages
        self.robots = robots
        self.status = status
        self.calls = []

    def __call__(self, url, headers, timeout, max_bytes):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        if url.endswith("/robots.txt"):
            if self.robots is None:
                return 404, "", url
            return 200, self.robots, url
        if url in self.pages:
            return self.status, self.pages[url], url
        return 404, "", url


def make_fetcher(transport, **kwargs):
    """A fetcher with a controllable clock, so tests never actually sleep."""
    state = {"now": 1000.0, "slept": []}

    def clock():
        return state["now"]

    def sleep(seconds):
        state["slept"].append(seconds)
        state["now"] += seconds

    kwargs.setdefault("min_interval", 0)
    fetcher = PoliteFetcher(transport=transport, sleep=sleep, clock=clock, **kwargs)
    fetcher._test_state = state
    return fetcher


def test_fetches_an_allowed_page():
    transport = FakeTransport({"https://shop.test/p": "<html>hi</html>"})
    fetcher = make_fetcher(transport)
    assert fetcher.fetch("https://shop.test/p") == "<html>hi</html>", \
        "Should return the page body"


def test_robots_disallow_blocks_the_fetch():
    transport = FakeTransport({"https://shop.test/p": "<html>hi</html>"},
                              robots=DENY_ALL)
    fetcher = make_fetcher(transport)
    try:
        fetcher.fetch("https://shop.test/p")
    except RobotsDenied:
        pass
    else:
        raise AssertionError("A disallowed URL must raise RobotsDenied")
    fetched = [c["url"] for c in transport.calls if not c["url"].endswith("robots.txt")]
    assert fetched == [], "A denied page must never be requested"


def test_robots_path_rules_are_respected():
    pages = {"https://shop.test/prices/x": "<html>a</html>",
             "https://shop.test/ok": "<html>b</html>"}
    transport = FakeTransport(pages, robots=DENY_PRICES)
    fetcher = make_fetcher(transport)
    assert fetcher.fetch("https://shop.test/ok"), "Allowed path should fetch"
    try:
        fetcher.fetch("https://shop.test/prices/x")
    except RobotsDenied:
        pass
    else:
        raise AssertionError("Disallowed path should raise")


def test_missing_robots_txt_allows_fetching():
    transport = FakeTransport({"https://shop.test/p": "<html>hi</html>"}, robots=None)
    fetcher = make_fetcher(transport)
    assert fetcher.fetch("https://shop.test/p"), "404 robots.txt means no restrictions"


def test_identifies_itself_in_user_agent():
    transport = FakeTransport({"https://shop.test/p": "<html>hi</html>"})
    fetcher = make_fetcher(transport)
    fetcher.fetch("https://shop.test/p")
    agents = {c["headers"].get("User-Agent") for c in transport.calls}
    assert all("GlyphAI" in a for a in agents), "Every request must identify GlyphAI"


def test_crawl_delay_is_honoured():
    pages = {"https://shop.test/a": "a", "https://shop.test/b": "b"}
    transport = FakeTransport(pages, robots=DELAYED)
    fetcher = make_fetcher(transport)
    fetcher.fetch("https://shop.test/a")
    fetcher.fetch("https://shop.test/b")
    assert fetcher._test_state["slept"], "Second request should wait"
    assert max(fetcher._test_state["slept"]) >= 5, "Should honour Crawl-delay: 5"


def test_rate_limit_applies_between_requests():
    pages = {"https://shop.test/a": "a", "https://shop.test/b": "b"}
    transport = FakeTransport(pages)
    fetcher = make_fetcher(transport, min_interval=2.0)
    fetcher.fetch("https://shop.test/a")
    fetcher.fetch("https://shop.test/b")
    assert sum(fetcher._test_state["slept"]) >= 2.0, "Should rate-limit per host"


def test_http_error_raises_fetch_error():
    transport = FakeTransport({}, status=500)
    fetcher = make_fetcher(transport)
    try:
        fetcher.fetch("https://shop.test/missing")
    except FetchError:
        pass
    else:
        raise AssertionError("A non-200 response should raise FetchError")


def test_rejects_non_http_schemes():
    fetcher = make_fetcher(FakeTransport({}))
    for url in ("file:///etc/passwd", "ftp://shop.test/p"):
        try:
            fetcher.fetch(url)
        except FetchError:
            pass
        else:
            raise AssertionError(f"{url} should be rejected")


def test_cache_prevents_a_second_request():
    cache_dir = tempfile.mkdtemp()
    try:
        transport = FakeTransport({"https://shop.test/p": "<html>hi</html>"})
        fetcher = make_fetcher(transport, cache_dir=cache_dir)
        first = fetcher.fetch("https://shop.test/p")
        before = len(transport.calls)
        second = fetcher.fetch("https://shop.test/p")
        assert first == second, "Cached body should match"
        assert len(transport.calls) == before, "Cache hit must not re-request"
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)


def test_expired_cache_refetches():
    cache_dir = tempfile.mkdtemp()
    try:
        transport = FakeTransport({"https://shop.test/p": "<html>hi</html>"})
        fetcher = make_fetcher(transport, cache_dir=cache_dir, cache_ttl=10)
        fetcher.fetch("https://shop.test/p")
        before = len(transport.calls)
        fetcher._test_state["now"] += 100  # past the TTL
        fetcher.fetch("https://shop.test/p")
        assert len(transport.calls) > before, "Expired cache should refetch"
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)


def test_server_error_on_robots_is_treated_as_denial():
    """A 5xx on robots.txt is not permission to crawl."""
    class ErroringRobots(FakeTransport):
        def __call__(self, url, headers, timeout, max_bytes):
            if url.endswith("/robots.txt"):
                self.calls.append({"url": url, "headers": headers, "timeout": timeout})
                return 503, "", url
            return FakeTransport.__call__(self, url, headers, timeout, max_bytes)

    transport = ErroringRobots({"https://shop.test/p": "<html>hi</html>"})
    fetcher = make_fetcher(transport)
    try:
        fetcher.fetch("https://shop.test/p")
    except RobotsDenied:
        pass
    else:
        raise AssertionError("robots.txt 503 should block, not allow")


def test_timeout_is_always_passed():
    transport = FakeTransport({"https://shop.test/p": "<html>hi</html>"})
    fetcher = make_fetcher(transport, timeout=3.0)
    fetcher.fetch("https://shop.test/p")
    assert all(c["timeout"] == 3.0 for c in transport.calls), \
        "Every request must carry a timeout"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"All {len(tests)} tests passed.")
