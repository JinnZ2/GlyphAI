import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ManipulationDetector import ManipulationDetector


def test_fake_urgency_detection():
    detector = ManipulationDetector()
    product = {"description": "LIMITED TIME ONLY 3 left in stock"}
    flags = detector.scan_listing(product)
    assert any(f['type'] == 'FAKE_URGENCY' for f in flags), "Should detect fake urgency"


def test_suspicious_discount():
    detector = ManipulationDetector()
    product = {"description": "Great deal", "was_price": 100, "now_price": 30}
    flags = detector.scan_listing(product)
    assert any(f['type'] == 'SUSPICIOUS_DISCOUNT' for f in flags), "Should detect suspicious discount"


def test_suspicious_discount_with_price_key():
    """Listings that use 'price' instead of 'now_price' must still be checked."""
    detector = ManipulationDetector()
    product = {"description": "Great deal", "was_price": 24.99, "price": 12.99}
    flags = detector.scan_listing(product)
    assert any(f['type'] == 'SUSPICIOUS_DISCOUNT' for f in flags), \
        "Should detect a 48% discount given as 'price'"


def test_subscription_trap():
    detector = ManipulationDetector()
    product = {"description": "Subscribe and save 15%!"}
    flags = detector.scan_listing(product)
    assert any(f['type'] == 'SUBSCRIPTION_TRAP' for f in flags), "Should detect subscription trap"


def test_no_flags_for_clean_listing():
    detector = ManipulationDetector()
    product = {"description": "Standard LED bulb, energy efficient."}
    flags = detector.scan_listing(product)
    assert len(flags) == 0, "Clean listing should have no flags"


def test_modest_discount_not_flagged():
    detector = ManipulationDetector()
    product = {"description": "Standard LED bulb", "was_price": 100, "price": 90}
    flags = detector.scan_listing(product)
    assert not any(f['type'] == 'SUSPICIOUS_DISCOUNT' for f in flags), \
        "A 10% discount should not be flagged"


def test_zero_was_price_does_not_crash():
    detector = ManipulationDetector()
    product = {"description": "Free sample", "was_price": 0, "price": 0}
    flags = detector.scan_listing(product)
    assert isinstance(flags, list), "Zero prices should not raise"


def test_scan_alias_matches_scan_listing():
    detector = ManipulationDetector()
    product = {"description": "LIMITED TIME! Subscribe and save",
               "was_price": 50, "price": 10}
    assert detector.scan(product) == detector.scan_listing(product), \
        "scan() alias should match scan_listing()"


def test_flag_shape():
    detector = ManipulationDetector()
    flags = detector.scan_listing({"description": "limited time offer"})
    for flag in flags:
        assert set(flag) == {"type", "severity", "evidence"}, "Unexpected flag keys"
        assert isinstance(flag["severity"], float), "Severity should be a float 0-1"
        assert 0.0 <= flag["severity"] <= 1.0, "Severity out of range"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"All {len(tests)} tests passed.")
