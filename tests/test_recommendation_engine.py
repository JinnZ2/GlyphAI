import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glyph_engine import Glyph
from recommendation_engine import RecommendationEngine, generate_recommendation
from diy_knowledge import DIYKnowledge

SERIOUS_FLAG = {"type": "FAKE_URGENCY", "severity": 0.7, "evidence": "x"}
MILD_FLAG = {"type": "SUBSCRIPTION_TRAP", "severity": 0.5, "evidence": "x"}

GEO = [
    {"region": "90210", "in_store": 7.75, "online": 9.99, "distance_miles": 7.5,
     "price_gap": 2.24, "is_local": False, "suggestion": "STAY PUT",
     "source_kind": "mock"},
]


def test_rejects_serious_manipulation_for_low_tolerance_user():
    engine = RecommendationEngine(Glyph())  # profile tolerance is 0.1
    result = engine.recommend({"name": "widget", "price": 24.99}, [SERIOUS_FLAG], GEO)
    assert result["action"] == "REJECT", "Low tolerance + serious flag should REJECT"
    assert result["reasoning"], "REJECT should explain itself"


def test_singular_plural_reasoning_text():
    engine = RecommendationEngine(Glyph())
    one = engine.recommend({"name": "w", "price": 20}, [SERIOUS_FLAG], [])
    assert "1 serious manipulation tactic" in one["reasoning"][0], "Should read singular"
    two = engine.recommend({"name": "w", "price": 20}, [SERIOUS_FLAG, SERIOUS_FLAG], [])
    assert "2 serious manipulation tactics" in two["reasoning"][0], "Should read plural"


def test_mild_flag_yields_caution_not_reject():
    engine = RecommendationEngine(Glyph())
    result = engine.recommend({"name": "widget", "price": 24.99}, [MILD_FLAG], [])
    assert result["action"] == "PROCEED_WITH_CAUTION", \
        "Sub-threshold severity should caution, not reject"


def test_clean_listing_evaluates_alternatives():
    engine = RecommendationEngine(Glyph())
    result = engine.recommend({"name": "widget", "price": 24.99}, [], [])
    assert result["action"] == "EVALUATE_ALTERNATIVES", "Clean listing should not be flagged"


def test_empty_glyph_does_not_crash():
    """Regression: comparing a None glyph value used to raise TypeError."""
    engine = RecommendationEngine(Glyph("does_not_exist.json"))
    result = engine.recommend({"name": "widget", "price": 24.99}, [SERIOUS_FLAG], GEO)
    assert result["action"], "An empty glyph must still produce a verdict"


def test_geographic_alternative_reports_savings():
    engine = RecommendationEngine(Glyph())
    result = engine.recommend({"name": "widget", "price": 24.99}, [], GEO)
    geo_alts = [a for a in result["alternatives"] if a["type"] == "GEOGRAPHIC"]
    assert len(geo_alts) == 1, "Should surface the cheaper in-store option"
    assert geo_alts[0]["savings"] == "$17.24", "Savings should be listing minus in-store"


def test_geographic_alternative_preserves_source_kind():
    engine = RecommendationEngine(Glyph())
    result = engine.recommend({"name": "widget", "price": 24.99}, [], GEO)
    geo_alt = [a for a in result["alternatives"] if a["type"] == "GEOGRAPHIC"][0]
    assert geo_alt["source_kind"] == "mock", \
        "Recommendation must preserve geographic price provenance"


def test_geographic_alternative_does_not_infer_observed_provenance():
    engine = RecommendationEngine(Glyph())
    unlabelled_geo = [dict(GEO[0])]
    del unlabelled_geo[0]["source_kind"]
    result = engine.recommend(
        {"name": "widget", "price": 24.99}, [], unlabelled_geo)
    geo_alt = [a for a in result["alternatives"] if a["type"] == "GEOGRAPHIC"][0]
    assert "source_kind" in geo_alt, "Alternative shape must include provenance"
    assert geo_alt["source_kind"] is None, \
        "Missing provenance must remain unknown, never inferred as observed"


def test_geo_alternative_skipped_when_savings_too_small():
    engine = RecommendationEngine(Glyph())
    result = engine.recommend({"name": "widget", "price": 8.00}, [], GEO)
    assert not [a for a in result["alternatives"] if a["type"] == "GEOGRAPHIC"], \
        "A sub-20% saving should not prompt a trip"


def test_diy_alternative_sourced_from_knowledge_base():
    """DIY suggestions should come from diy_knowledge.json, not be generic."""
    engine = RecommendationEngine(Glyph())
    result = engine.recommend({"name": "60W LED Bulb 4-Pack", "price": 24.99}, [], [])
    diy = [a for a in result["alternatives"] if a["type"] == "DIY"]
    assert len(diy) == 1, "High DIY viability above the price floor should suggest DIY"
    assert diy[0].get("options"), "Known product should carry concrete alternatives"
    assert diy[0].get("repair"), "Known product should carry a repair note"


def test_diy_generic_for_unknown_product():
    engine = RecommendationEngine(Glyph())
    result = engine.recommend({"name": "obscure gizmo", "price": 99.0}, [], [])
    diy = [a for a in result["alternatives"] if a["type"] == "DIY"]
    assert len(diy) == 1 and "options" not in diy[0], \
        "Unknown product should still suggest DIY, without invented specifics"


def test_diy_skipped_below_price_floor():
    engine = RecommendationEngine(Glyph())
    result = engine.recommend({"name": "60W LED Bulb", "price": 12.99}, [], [])
    assert not [a for a in result["alternatives"] if a["type"] == "DIY"], \
        "Cheap items should not trigger DIY"


def test_accepts_now_price_key():
    engine = RecommendationEngine(Glyph())
    result = engine.recommend({"name": "widget", "now_price": 24.99}, [], GEO)
    assert [a for a in result["alternatives"] if a["type"] == "GEOGRAPHIC"], \
        "Engine should read 'now_price' as well as 'price'"


def test_missing_price_does_not_crash():
    engine = RecommendationEngine(Glyph())
    result = engine.recommend({"name": "widget"}, [], GEO)
    assert result["action"], "A listing with no price should still yield a verdict"


def test_functional_wrapper_matches_class():
    glyph = Glyph()
    product = {"name": "widget", "price": 24.99}
    assert generate_recommendation(glyph, product, [SERIOUS_FLAG], GEO) == \
        RecommendationEngine(glyph).recommend(product, [SERIOUS_FLAG], GEO), \
        "Wrapper should match the class result"


def test_injected_knowledge_base_is_used():
    engine = RecommendationEngine(Glyph(), diy_knowledge=DIYKnowledge("missing.json"))
    result = engine.recommend({"name": "60W LED Bulb 4-Pack", "price": 24.99}, [], [])
    diy = [a for a in result["alternatives"] if a["type"] == "DIY"]
    assert diy and "options" not in diy[0], "An empty knowledge base yields generic DIY"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"All {len(tests)} tests passed.")
