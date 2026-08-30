import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from price_extractor import extract_offer, parse_price, normalize_availability

JSON_LD_PAGE = """
<html><head><title>Store</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"60W LED Bulb 4-Pack",
 "description":"LIMITED TIME! Only 3 left in stock!",
 "offers":{"@type":"Offer","price":"24.99","priceCurrency":"USD",
           "availability":"https://schema.org/InStock"}}
</script></head><body></body></html>
"""

MICRODATA_PAGE = """
<html><body><div itemscope itemtype="https://schema.org/Product">
<meta itemprop="name" content="Widget">
<span itemprop="price" content="12.50"></span>
<meta itemprop="priceCurrency" content="EUR">
<link itemprop="availability" href="https://schema.org/OutOfStock">
</div></body></html>
"""

META_PAGE = """
<html><head>
<meta property="og:title" content="Meta Widget">
<meta property="og:price:amount" content="8.75">
<meta property="og:price:currency" content="GBP">
<meta name="description" content="Subscribe and save 15%!">
</head><body></body></html>
"""


def test_extracts_json_ld_offer():
    offer = extract_offer(JSON_LD_PAGE, url="https://example.com/p")
    assert offer["price"] == 24.99, "Should read the JSON-LD price"
    assert offer["name"] == "60W LED Bulb 4-Pack", "Should read the product name"
    assert offer["currency"] == "USD", "Should read the currency"
    assert offer["availability"] == "IN_STOCK", "Should normalise availability"
    assert offer["source"] == "json-ld", "Should report where the price came from"
    assert offer["url"] == "https://example.com/p", "Should echo the URL"


def test_json_ld_description_feeds_the_detector():
    """The extracted description is what ManipulationDetector scans."""
    from ManipulationDetector import ManipulationDetector
    offer = extract_offer(JSON_LD_PAGE)
    flags = ManipulationDetector().scan_listing(offer)
    assert any(f["type"] == "FAKE_URGENCY" for f in flags), \
        "Urgency language on a real page should be flagged"


def test_falls_back_to_microdata():
    offer = extract_offer(MICRODATA_PAGE)
    assert offer["price"] == 12.50, "Should read microdata price"
    assert offer["currency"] == "EUR", "Should read microdata currency"
    assert offer["availability"] == "OUT_OF_STOCK", "Should normalise availability"
    assert offer["source"] == "microdata", "Should report the microdata source"


def test_falls_back_to_meta_tags():
    offer = extract_offer(META_PAGE)
    assert offer["price"] == 8.75, "Should read og:price:amount"
    assert offer["currency"] == "GBP", "Should read og:price:currency"
    assert offer["name"] == "Meta Widget", "Should fall back to og:title"
    assert offer["source"] == "meta", "Should report the meta source"


def test_missing_price_is_none_not_zero():
    """A page with no price must report unknown, never free."""
    offer = extract_offer("<html><body>no prices here</body></html>")
    assert offer["price"] is None, "Unknown price must be None, not 0"
    assert offer["source"] is None, "No source when nothing was found"


def test_malformed_json_ld_does_not_crash():
    page = """<html><script type="application/ld+json">{not valid json,,}</script>
    <meta property="og:price:amount" content="5.00"></html>"""
    offer = extract_offer(page)
    assert offer["price"] == 5.00, "A broken JSON-LD block should not block fallbacks"


def test_aggregate_offer_uses_lowest_price():
    page = """<html><script type="application/ld+json">
    {"@type":"Product","name":"Bulk","offers":[
      {"@type":"Offer","price":"30.00","priceCurrency":"USD"},
      {"@type":"Offer","price":"19.00","priceCurrency":"USD"}]}
    </script></html>"""
    offer = extract_offer(page)
    assert offer["price"] == 19.00, "Should surface the best available price"


def test_graph_wrapped_json_ld():
    page = """<html><script type="application/ld+json">
    {"@context":"https://schema.org","@graph":[
      {"@type":"WebPage"},
      {"@type":"Product","name":"Graphed","offers":{"@type":"Offer","price":7.5}}]}
    </script></html>"""
    offer = extract_offer(page)
    assert offer["price"] == 7.5 and offer["name"] == "Graphed", \
        "Should walk @graph documents"


def test_parse_price_formats():
    assert parse_price("$1,299.00") == 1299.00, "US thousands separator"
    assert parse_price("1.299,00") == 1299.00, "European format"
    assert parse_price("19,99") == 19.99, "European decimal comma"
    assert parse_price("USD 24.99") == 24.99, "Currency prefix"
    assert parse_price(12.5) == 12.5, "Numeric passthrough"
    assert parse_price(None) is None, "None stays None"
    assert parse_price("free") is None, "Unparseable text is None, not 0"


def test_normalize_availability_variants():
    assert normalize_availability("https://schema.org/InStock") == "IN_STOCK"
    assert normalize_availability("OutOfStock") == "OUT_OF_STOCK"
    assert normalize_availability(None) is None, "Missing availability stays None"


def test_empty_input_is_safe():
    for value in ("", None):
        offer = extract_offer(value)
        assert offer["price"] is None, "Empty input must not raise"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"All {len(tests)} tests passed.")
