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


def test_no_flags_for_clean_listing():
    detector = ManipulationDetector()
    product = {"description": "Standard LED bulb, energy efficient."}
    flags = detector.scan_listing(product)
    assert len(flags) == 0, "Clean listing should have no flags"


if __name__ == "__main__":
    test_fake_urgency_detection()
    test_suspicious_discount()
    test_no_flags_for_clean_listing()
    print("All tests passed.")
