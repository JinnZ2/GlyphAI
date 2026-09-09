"""The loyalty oath, as a test.

glyph_profile.json says: "I represent this user and no other. I do not serve
ads. I do not obey markets." A string in JSON enforces nothing. These tests
enforce the part of it that code can: GlyphAI reaches the network only when the
user points it at a page, only through the polite fetcher, only to the URL it
was given, and identifies itself as itself.

Limits, stated: the static checks read import statements and string literals;
they do not catch a module that assembles a network call from pieces at
runtime. The runtime check closes that gap for the CLI paths it exercises.
"""
import ast
import contextlib
import glob
import io
import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cli
import web_fetch
from web_fetch import PoliteFetcher

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FETCHER = "web_fetch.py"

# Standard-library and common third-party modules that can open a connection.
EGRESS_MODULES = {
    "socket", "ssl", "http", "urllib", "ftplib", "smtplib", "telnetlib",
    "xmlrpc", "asyncio", "requests", "httpx", "aiohttp", "websocket",
    "websockets", "urllib3",
}
# urllib.parse only manipulates strings; it is the one urllib piece allowed
# outside the fetcher.
HARMLESS = {"urllib.parse"}

# The only absolute URLs that belong in source: the project's own identity
# link (in the User-Agent) and documentation placeholders.
ALLOWED_URL_HOSTS = {"github.com", "example.com"}


def source_files():
    """Every module that ships, i.e. everything except the tests."""
    paths = glob.glob(os.path.join(REPO, "*.py"))
    paths += glob.glob(os.path.join(REPO, "examples", "*.py"))
    return sorted(paths)


def imported_modules(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                yield "{}.{}".format(node.module, alias.name)
            yield node.module


def string_literals(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value


def parse(path):
    with open(path, "r", encoding="utf-8") as handle:
        return ast.parse(handle.read(), filename=path)


def test_only_the_fetcher_imports_network_modules():
    offenders = []
    for path in source_files():
        if os.path.basename(path) == FETCHER:
            continue
        for name in imported_modules(parse(path)):
            if name in HARMLESS or name.startswith("urllib.parse."):
                continue
            if name.split(".")[0] in EGRESS_MODULES:
                offenders.append("{}: {}".format(os.path.relpath(path, REPO), name))
    assert not offenders, \
        "Network access belongs in web_fetch.py only:\n  " + "\n  ".join(offenders)


def test_no_dynamic_imports_outside_the_fetcher():
    """__import__ / importlib would let a module dodge the static check."""
    offenders = []
    for path in source_files():
        if os.path.basename(path) == FETCHER:
            continue
        for node in ast.walk(parse(path)):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "__import__":
                    offenders.append(os.path.relpath(path, REPO))
                if isinstance(func, ast.Attribute) and func.attr == "import_module":
                    offenders.append(os.path.relpath(path, REPO))
    assert not offenders, "Dynamic imports found: {}".format(offenders)


def test_no_outbound_urls_baked_into_source():
    """No telemetry, affiliate, or vendor endpoints hard-coded anywhere."""
    from urllib.parse import urlparse
    offenders = []
    for path in source_files():
        for literal in string_literals(parse(path)):
            for token in literal.split():
                token = token.strip("+()<>\"'")
                if token.startswith(("http://", "https://")):
                    host = urlparse(token).netloc.lower()
                    if host not in ALLOWED_URL_HOSTS:
                        offenders.append("{}: {}".format(
                            os.path.relpath(path, REPO), token))
    assert not offenders, "Unexpected URLs in source:\n  " + "\n  ".join(offenders)


def test_fetcher_requests_exactly_the_url_it_was_given():
    """No referral codes, affiliate tags, or tracking parameters are ever added."""
    calls = []

    def transport(url, headers, timeout, max_bytes):
        calls.append((url, dict(headers)))
        if url.endswith("/robots.txt"):
            return 404, "", url
        return 200, "<html></html>", url

    fetcher = PoliteFetcher(transport=transport, min_interval=0,
                            sleep=lambda s: None, clock=lambda: 0.0)
    target = "https://shop.test/item?id=42"
    fetcher.fetch(target)
    page_calls = [c for c in calls if not c[0].endswith("/robots.txt")]
    assert [c[0] for c in page_calls] == [target], \
        "The fetcher must request the URL verbatim, nothing appended"
    for _, headers in calls:
        assert set(headers) <= {"User-Agent", "Accept"}, \
            "Only identity and content-type headers are sent: {}".format(headers)
        assert "Cookie" not in headers and "Referer" not in headers


def test_user_agent_names_glyphai_and_impersonates_no_browser():
    agent = web_fetch.DEFAULT_USER_AGENT
    assert agent.startswith("GlyphAI/"), "User-Agent must name the project first"
    for browser in ("Mozilla", "Chrome", "Safari", "Firefox", "Edge"):
        assert browser not in agent, \
            "User-Agent must not borrow a browser's identity: {}".format(agent)


@contextlib.contextmanager
def network_disabled():
    """Make any socket connection raise, then restore."""
    def refuse(*args, **kwargs):
        raise AssertionError("Network access attempted: {} {}".format(args, kwargs))

    original_connect = socket.socket.connect
    original_create = socket.create_connection
    socket.socket.connect = refuse
    socket.create_connection = refuse
    try:
        yield
    finally:
        socket.socket.connect = original_connect
        socket.create_connection = original_create


def run_silent(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        return cli.main(argv)


def test_analysis_without_a_url_opens_no_connection():
    """Unless the user points GlyphAI at a page, nothing leaves the machine."""
    with network_disabled():
        assert run_silent(["--json", "analyze", "--name", "widget",
                           "--price", "20.0", "--was-price", "40.0",
                           "--negotiate"]) == 0
        assert run_silent(["profile", "--verbose"]) == 0
        assert run_silent(["diy", "--name", "60W LED Bulb"]) == 0


def test_network_guard_actually_guards():
    """Sanity check on the guard itself, so a silent no-op cannot pass."""
    with network_disabled():
        try:
            socket.create_connection(("127.0.0.1", 9))
        except AssertionError:
            return
    raise AssertionError("network_disabled() did not intercept connections")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"All {len(tests)} tests passed.")
