import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glyph_engine import Glyph
from geo_price_analyzer import GeoPriceAnalyzer


def test_loads_profile_regardless_of_cwd():
    """The engine must find the profile even when run from another directory."""
    original = os.getcwd()
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        glyph = Glyph()
        assert glyph.get_value("urgency") is not None, "Profile should load from any cwd"
    finally:
        os.chdir(original)


def test_bare_filename_resolves_from_other_cwd():
    """Callers passing 'glyph_profile.json' should still resolve it."""
    original = os.getcwd()
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        glyph = Glyph("glyph_profile.json")
        assert glyph.get_oath(), "Bare filename should resolve to the repo profile"
    finally:
        os.chdir(original)


def test_get_value_returns_default_for_missing_key():
    glyph = Glyph()
    assert glyph.get_value("no_such_key") is None, "Missing key should return None"
    assert glyph.get_value("no_such_key", 0.5) == 0.5, "Should return provided default"


def test_loyalty_oath_present():
    glyph = Glyph()
    assert glyph.is_loyalty_bound() is True, "Profile should be loyalty bound"
    assert "no other" in glyph.get_oath(), "Oath should assert single-user loyalty"


def test_analyzer_survives_empty_glyph():
    """A glyph with no values must not crash the analyzer on a None comparison."""
    glyph = Glyph("does_not_exist.json")
    analyzer = GeoPriceAnalyzer(glyph)
    results = analyzer.analyze_prices("widget", user_zip="90001")
    assert len(results) == 3, "Should still return all mock regions"
    for r in results:
        assert r["suggestion"], "Every region needs a suggestion"


def test_analyzer_marks_local_region():
    glyph = Glyph()
    analyzer = GeoPriceAnalyzer(glyph)
    results = analyzer.analyze_prices("widget", user_zip="90210")
    local = [r for r in results if r["is_local"]]
    assert len(local) == 1 and local[0]["region"] == "90210", \
        "user_zip should mark exactly one region local"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"All {len(tests)} tests passed.")
