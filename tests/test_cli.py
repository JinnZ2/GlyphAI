import sys
import os
import io
import json
import contextlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cli


def run(argv):
    """Run the CLI, capturing stdout. Returns (exit_code, stdout)."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = cli.main(argv)
    return code, buffer.getvalue()


def test_analyze_produces_a_verdict():
    code, out = run(["analyze", "--name", "60W LED Bulb", "--price", "12.99",
                     "--was-price", "24.99",
                     "--description", "LIMITED TIME! Only 3 left in stock!"])
    assert code == 0, "analyze should succeed"
    assert "Verdict:" in out, "Report should include a verdict"
    assert "FAKE_URGENCY" in out, "Report should surface detected manipulation"
    assert "SUSPICIOUS_DISCOUNT" in out, "48% off should be flagged"


def test_analyze_json_output_is_valid_json():
    code, out = run(["--json", "analyze", "--name", "widget", "--price", "20.0"])
    assert code == 0, "analyze --json should succeed"
    payload = json.loads(out)
    assert set(payload) >= {"product", "manipulation_flags", "geo_analysis",
                            "recommendation"}, "JSON payload missing sections"
    assert payload["recommendation"]["action"], "JSON should carry a verdict"


def test_analyze_json_preserves_legacy_recommendation_shape():
    code, out = run(["--json", "analyze", "--name", "widget", "--price", "20.0"])
    assert code == 0, "analyze --json should succeed"
    recommendation = json.loads(out)["recommendation"]
    assert set(recommendation) == {"action", "reasoning", "alternatives"}, \
        "Typed decisions must not change the existing CLI JSON contract"


def test_json_stdout_is_not_polluted_by_diagnostics():
    """Regression: 'Glyph loaded successfully.' on stdout broke JSON parsing."""
    code, out = run(["--json", "analyze", "--name", "widget", "--price", "20.0"])
    assert out.lstrip().startswith("{"), "stdout must contain only JSON"
    json.loads(out)


def test_analyze_requires_a_name():
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        code, _ = run(["analyze", "--price", "10"])
    assert code == 2, "Missing product name should exit non-zero"
    assert "name is required" in stderr.getvalue(), "Should explain what is missing"


def test_analyze_reads_listing_from_file(tmp_path=None):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_listing.json")
    listing = {"name": "60W LED Bulb 4-Pack", "price": 24.99, "was_price": 49.99,
               "description": "Subscribe and save!"}
    with open(path, "w") as handle:
        json.dump(listing, handle)
    try:
        code, out = run(["analyze", "--file", path])
        assert code == 0, "Reading a listing file should succeed"
        assert "SUBSCRIPTION_TRAP" in out, "File-sourced listing should be scanned"
    finally:
        os.remove(path)


def test_flags_override_file_values():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_listing2.json")
    with open(path, "w") as handle:
        json.dump({"name": "from file", "price": 1.0}, handle)
    try:
        code, out = run(["--json", "analyze", "--file", path, "--name", "from flag"])
        payload = json.loads(out)
        assert payload["product"]["name"] == "from flag", "Flag should win over file"
        assert payload["product"]["price"] == 1.0, "Unset flags keep file values"
    finally:
        os.remove(path)


def test_missing_listing_file_is_reported():
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        code, _ = run(["analyze", "--file", "no_such_file.json"])
    assert code == 2, "Unreadable listing file should exit non-zero"
    assert "Could not read listing file" in stderr.getvalue(), "Should explain the failure"


def test_negotiate_emits_jibbelink_offer():
    code, out = run(["--json", "analyze", "--name", "widget", "--price", "20.0",
                     "--product-id", "SKU_1", "--negotiate"])
    payload = json.loads(out)
    offer = payload.get("jibbelink_offer")
    assert offer, "--negotiate should attach an offer"
    assert offer["message_type"] == "OFFER", "Should be an OFFER message"
    assert offer["product_id"] == "SKU_1", "Offer should carry the product id"
    assert offer["timestamp"].endswith("Z"), "Timestamp should match the Jibbelink spec"


def test_profile_lists_values_and_oath():
    code, out = run(["profile"])
    assert code == 0, "profile should succeed"
    assert "urgency" in out and "Loyalty oath" in out, "Should show values and the oath"


def test_diy_lookup_known_and_unknown():
    code, out = run(["diy", "--name", "60W LED Bulb"])
    assert code == 0 and "led_bulb" in out, "Known product should resolve"
    code, out = run(["diy", "--name", "obscure gizmo"])
    assert code == 1, "Unknown product should exit non-zero"
    assert "No DIY knowledge" in out, "Should say nothing was found"


PRODUCT_PAGE = """
<html><head><script type="application/ld+json">
{"@type":"Product","name":"Scraped Bulb","description":"LIMITED TIME! Only 3 left!",
 "offers":{"@type":"Offer","price":"24.99","priceCurrency":"USD"}}
</script></head></html>
"""


class _StubLiveSource:
    """Replaces LivePriceSource so CLI tests never touch the network."""

    def __init__(self, offer):
        self.offer = offer

    def __call__(self, *args, **kwargs):
        return self

    def fetch_offer(self, url):
        result = dict(self.offer)
        result.setdefault("url", url)
        return result


def with_stub_source(offer, argv):
    original = cli.LivePriceSource
    cli.LivePriceSource = _StubLiveSource(offer)
    try:
        return run(argv)
    finally:
        cli.LivePriceSource = original


def test_analyze_url_runs_pipeline_on_scraped_data():
    from price_extractor import extract_offer
    offer = extract_offer(PRODUCT_PAGE, url="https://shop.test/bulb")
    code, out = with_stub_source(offer, ["analyze", "--url", "https://shop.test/bulb"])
    assert code == 0, "A scraped listing should analyze cleanly"
    assert "Scraped Bulb" in out, "Should use the scraped product name"
    assert "FAKE_URGENCY" in out, "Should scan the scraped description"
    assert "live, via json-ld" in out, "Should mark the price as live"


def test_analyze_url_reports_robots_denial():
    offer = {"price": None, "error": "robots_denied", "detail": "denied"}
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        code, _ = with_stub_source(offer, ["analyze", "--url", "https://shop.test/x"])
    assert code == 2, "A robots denial should exit non-zero"
    message = stderr.getvalue()
    assert "robots.txt disallows" in message, "Should explain the refusal"
    assert "does not work around that" in message, "Should not offer a bypass"


def test_analyze_url_reports_fetch_failure():
    offer = {"price": None, "error": "fetch_failed", "detail": "HTTP 500"}
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        code, _ = with_stub_source(offer, ["analyze", "--url", "https://shop.test/x"])
    assert code == 2, "A failed fetch should exit non-zero"
    assert "Could not fetch" in stderr.getvalue(), "Should report the failure"


def test_flags_override_scraped_values():
    from price_extractor import extract_offer
    offer = extract_offer(PRODUCT_PAGE, url="https://shop.test/bulb")
    code, out = with_stub_source(offer, ["--json", "analyze", "--url",
                                         "https://shop.test/bulb", "--price", "9.99"])
    payload = json.loads(out)
    assert payload["product"]["price"] == 9.99, "An explicit --price should win"
    assert payload["product"]["name"] == "Scraped Bulb", "Unset fields stay scraped"


def test_url_without_price_does_not_become_free():
    offer = {"name": "Mystery", "price": None, "error": "no_structured_price",
             "detail": "unknown", "description": ""}
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        code, out = with_stub_source(offer, ["analyze", "--url", "https://shop.test/m"])
    assert code == 0, "A missing price should still analyze"
    assert "Price: unknown" in out, "Must show unknown, never $0"


def test_bare_invocation_shows_help():
    code, out = run([])
    assert code == 0, "Bare invocation should succeed"
    assert "usage:" in out.lower(), "Should print help"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"All {len(tests)} tests passed.")
