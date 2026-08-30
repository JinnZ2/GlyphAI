import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diy_knowledge import DIYKnowledge


def test_loads_from_any_cwd():
    original = os.getcwd()
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        assert DIYKnowledge().list_keys(), "Knowledge should load from any directory"
    finally:
        os.chdir(original)


def test_matches_product_name_containing_key_terms():
    knowledge = DIYKnowledge()
    entry = knowledge.lookup("60W LED Bulb 4-Pack")
    assert entry is not None, "'led_bulb' should match an LED bulb listing"
    assert entry["matched_key"] == "led_bulb", "Should report which key matched"


def test_match_is_case_and_punctuation_insensitive():
    knowledge = DIYKnowledge()
    assert knowledge.lookup("led-bulb") is not None, "Hyphens should not defeat matching"
    assert knowledge.lookup("LED BULB") is not None, "Matching should ignore case"


def test_partial_key_does_not_match():
    knowledge = DIYKnowledge()
    assert knowledge.lookup("ceiling fan") is None, "Unrelated product should not match"
    assert knowledge.lookup("bulb") is None, \
        "Every term in the key must be present, not just one"


def test_alternatives_and_repair_accessors():
    knowledge = DIYKnowledge()
    assert knowledge.alternatives("60W LED Bulb"), "Should return alternatives list"
    assert knowledge.repair_note("60W LED Bulb"), "Should return a repair note"


def test_unknown_product_returns_empty_not_none():
    knowledge = DIYKnowledge()
    assert knowledge.alternatives("obscure gizmo") == [], "Unknown product yields []"
    assert knowledge.repair_note("obscure gizmo") == "", "Unknown product yields ''"


def test_missing_file_degrades_gracefully():
    knowledge = DIYKnowledge("does_not_exist.json")
    assert knowledge.list_keys() == [], "Missing file should yield empty knowledge"
    assert knowledge.lookup("anything") is None, "Lookup must not raise"


def test_lookup_returns_a_copy():
    knowledge = DIYKnowledge()
    entry = knowledge.lookup("60W LED Bulb")
    entry["alternatives"] = []
    assert knowledge.alternatives("60W LED Bulb"), \
        "Mutating a lookup result must not corrupt the loaded knowledge"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"All {len(tests)} tests passed.")
