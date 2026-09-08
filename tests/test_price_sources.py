import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from price_sources import (MockPriceSource, LivePriceSource, get_source,
                           SOURCE_KINDS, SOURCE_KIND_MOCK)
from web_fetch import PoliteFetcher
from glyph_engine import Glyph
from geo_price_analyzer import GeoPriceAnalyzer

PRODUCT_PAGE = """
<html><head><script type="application/ld+json">
{"@type":"Product","name":"Real Bulb","description":"Only 2 left! Subscribe now.",
 "offers":{"@type":"Offer","price":"31.50","priceCurrency":"USD",
           "availability":"https://schema.org/InStock"}}
</script></head></html>
"""


def transport_for(pages, robots="User-agent: *\nDisallow:\n"):
    def transport(url, headers, timeout, max_bytes):
        if url.endswith("/robots.txt"):
            return 200, robots, url
        if url in pages:
            return 200, pages[url], url
        return 404, "", url
    return transport


def live_source(pages, robots="User-agent: *\nDisallow:\n"):
    fetcher = PoliteFetcher(transport=transport_for(pages, robots),
                            min_interval=0, sleep=lambda s: None)
    return LivePriceSource(fetcher=fetcher)


def test_mock_source_is_not_live():
    assert MockPriceSource().is_live is False, "Mock data must be labelled as mock"
    assert LivePriceSource(fetcher=object()).is_live is True, "Live source is live"


def test_mock_source_returns_all_regions():
    regions = MockPriceSource().regional_prices("widget", "90001")
    assert len(regions) == 3, "Mock should return the three regions"
    assert "in_store" in regions["90210"], "Region entries carry in-store prices"


def test_mock_source_marks_every_region_as_mock():
    assert SOURCE_KINDS == frozenset({"mock", "observed", "derived"}), \
        "Provenance vocabulary should remain small and explicit"
    regions = MockPriceSource().regional_prices("widget", "90001")
    assert all(row["source_kind"] == SOURCE_KIND_MOCK
               for row in regions.values()), \
        "Every simulated regional price must be explicitly marked mock"


def test_mock_source_returns_copies():
    source = MockPriceSource()
    first = source.regional_prices("widget", "90001")
    first["90210"]["in_store"] = 0.01
    second = source.regional_prices("widget", "90001")
    assert second["90210"]["in_store"] != 0.01, "Callers must not mutate mock data"


def test_live_source_reads_a_real_offer():
    source = live_source({"https://shop.test/bulb": PRODUCT_PAGE})
    offer = source.fetch_offer("https://shop.test/bulb")
    assert offer["price"] == 31.50, "Should extract the live price"
    assert offer["name"] == "Real Bulb", "Should extract the product name"
    assert offer["availability"] == "IN_STOCK", "Should extract availability"
    assert "error" not in offer, "A good fetch should carry no error"


def test_robots_denied_is_reported_not_raised():
    source = live_source({"https://shop.test/bulb": PRODUCT_PAGE},
                         robots="User-agent: *\nDisallow: /\n")
    offer = source.fetch_offer("https://shop.test/bulb")
    assert offer["error"] == "robots_denied", "Denial should be reported as data"
    assert offer["price"] is None, "No price when access was refused"


def test_fetch_failure_is_reported_not_raised():
    source = live_source({})
    offer = source.fetch_offer("https://shop.test/missing")
    assert offer["error"] == "fetch_failed", "A 404 should be reported, not raised"


def test_page_without_price_is_flagged_unknown():
    source = live_source({"https://shop.test/bare": "<html>nothing</html>"})
    offer = source.fetch_offer("https://shop.test/bare")
    assert offer["price"] is None, "No price means None"
    assert offer["error"] == "no_structured_price", "Should say why it is missing"
    assert "not free" in offer["detail"], "Must warn against reading None as free"


def test_live_source_does_not_invent_regional_data():
    """Regional in-store pricing stays mock; a URL cannot know three ZIPs."""
    source = live_source({"https://shop.test/bulb": PRODUCT_PAGE})
    assert source.regional_prices("bulb", "90001") == \
        MockPriceSource().regional_prices("bulb", "90001"), \
        "Live source must not fabricate regional prices"


def test_get_source_factory():
    assert isinstance(get_source("mock"), MockPriceSource), "Should build a mock source"
    assert isinstance(get_source("live"), LivePriceSource), "Should build a live source"
    try:
        get_source("nonsense")
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown source name should raise")


def test_analyzer_defaults_to_mock_and_accepts_injection():
    glyph = Glyph()
    default_results = GeoPriceAnalyzer(glyph).analyze_prices("widget")
    injected = GeoPriceAnalyzer(glyph, price_source=MockPriceSource())
    assert default_results == injected.analyze_prices("widget"), \
        "Default behaviour must be unchanged by the new seam"
    assert all(row["source_kind"] == SOURCE_KIND_MOCK
               for row in default_results), \
        "Analyzer results must retain mock provenance"


def test_analyzer_does_not_infer_observed_provenance():
    class UnlabelledSource:
        def regional_prices(self, product_name, zip_code):
            return {
                zip_code: {"in_store": 8.0, "online": 10.0, "distance": 1.0}
            }

    results = GeoPriceAnalyzer(
        Glyph(), price_source=UnlabelledSource()).analyze_prices("widget")
    assert "source_kind" in results[0], "Result shape must include provenance"
    assert results[0]["source_kind"] is None, \
        "Missing provenance must remain unknown, never inferred as observed"


def test_deprecated_fetch_mock_prices_still_works():
    """The old method name is kept as an alias for existing callers."""
    analyzer = GeoPriceAnalyzer(Glyph())
    assert len(analyzer.fetch_mock_prices("widget", "90001")) == 3, \
        "fetch_mock_prices should still return regional data"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"All {len(tests)} tests passed.")
