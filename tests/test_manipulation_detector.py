# tests/test_manipulation_detector.py
def test_fake_urgency_detection():
    detector = ManipulationDetector()
    product = {"description": "LIMITED TIME ONLY 3 LEFT"}
    flags = detector.scan(product)
    assert any(f['type'] == 'FAKE_URGENCY' for f in flags)
