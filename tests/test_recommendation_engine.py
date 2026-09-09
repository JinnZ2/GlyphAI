import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glyph_engine import Glyph
from recommendation_engine import RecommendationEngine, generate_recommendation
from diy_knowledge import DIYKnowledge
from decision_model import Decision

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


def test_recommend_decision_converts_geographic_provenance_to_evidence():
    engine = RecommendationEngine(Glyph())
    decision = engine.recommend_decision(
        {"name": "widget", "price": 24.99}, [], GEO)
    assert isinstance(decision, Decision)
    assert len(decision.evidence) == 1
    assert decision.evidence[0].source == "GeoPriceAnalyzer"
    assert decision.evidence[0].source_kind == "mock"
    assert decision.evidence[0].supporting_data["region"] == "90210"
    assert decision.alternatives[0]["source_kind"] == \
        decision.evidence[0].source_kind


def test_recommend_decision_keeps_missing_provenance_unknown():
    engine = RecommendationEngine(Glyph())
    unlabelled_geo = [dict(GEO[0])]
    del unlabelled_geo[0]["source_kind"]
    decision = engine.recommend_decision(
        {"name": "widget", "price": 24.99}, [], unlabelled_geo)
    assert decision.evidence[0].source_kind is None
    assert decision.alternatives[0]["source_kind"] is None
    assert decision.warnings, "Unknown provenance should be explicit"
    assert decision.missing_information, "Unknown provenance should be recorded"


def test_recommend_decision_treats_invalid_provenance_as_unknown():
    engine = RecommendationEngine(Glyph())
    invalid_geo = [dict(GEO[0], source_kind="fabricated")]
    decision = engine.recommend_decision(
        {"name": "widget", "price": 24.99}, [], invalid_geo)
    assert decision.evidence[0].source_kind is None
    assert decision.alternatives[0]["source_kind"] is None
    assert decision.warnings and decision.missing_information


def test_recommend_decision_treats_invalid_confidence_as_unknown():
    engine = RecommendationEngine(Glyph())
    invalid_confidence_geo = [dict(GEO[0], confidence=float("nan"))]
    decision = engine.recommend_decision(
        {"name": "widget", "price": 24.99}, [], invalid_confidence_geo)
    assert decision.evidence[0].confidence is None, \
        "Invalid confidence must not become non-standard JSON"


def test_recommend_accepts_one_shot_geographic_iterable():
    engine = RecommendationEngine(Glyph())
    result = engine.recommend(
        {"name": "widget", "price": 24.99}, [], (row for row in GEO))
    assert result["alternatives"][0]["type"] == "GEOGRAPHIC", \
        "Typed evidence conversion must not consume generator input twice"


def test_legacy_recommendation_shape_and_behavior_are_unchanged():
    engine = RecommendationEngine(Glyph())
    legacy = engine.recommend(
        {"name": "widget", "price": 24.99}, [SERIOUS_FLAG], GEO)
    typed = engine.recommend_decision(
        {"name": "widget", "price": 24.99}, [SERIOUS_FLAG], GEO)
    assert legacy == typed.to_legacy_dict()
    assert set(legacy) == {"action", "reasoning", "alternatives"}
    assert legacy["action"] == "REJECT"
    assert legacy["alternatives"][0] == {
        "type": "GEOGRAPHIC",
        "description": "In-store at 90210: $7.75",
        "savings": "$17.24",
        "source_kind": "mock",
    }


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


def test_decision_reports_mock_regional_prices():
    """Mock in-store prices must be named as mock in the verdict itself."""
    engine = RecommendationEngine(Glyph())
    decision = engine.recommend_decision({"name": "widget", "price": 24.99}, [], GEO)
    mock_lines = [m for m in decision.missing_information if "mock" in m]
    assert mock_lines and "90210" in mock_lines[0], \
        "Verdict should say which regional prices are mock"


def test_decision_reports_unverifiable_was_price():
    engine = RecommendationEngine(Glyph())
    decision = engine.recommend_decision(
        {"name": "widget", "price": 24.99, "was_price": 49.99}, [], [])
    assert any("price history" in m and "49.99" in m
               for m in decision.missing_information), \
        "A was-price with no history to check it against is an unknown"


def test_decision_reports_unknown_price_without_calling_it_zero():
    engine = RecommendationEngine(Glyph())
    decision = engine.recommend_decision({"name": "widget"}, [], [])
    price_lines = [m for m in decision.missing_information if "price is unknown" in m]
    assert price_lines, "A missing price must be listed as unknown"
    assert "$0" not in " ".join(decision.missing_information)


def test_decision_lists_glyph_values_with_no_data_source():
    """ethical_threshold has weight in the profile but nothing to act on."""
    engine = RecommendationEngine(Glyph())
    decision = engine.recommend_decision({"name": "widget", "price": 24.99}, [], [])
    joined = " ".join(decision.missing_information)
    assert "ethical_threshold" in joined, "Unsourced glyph value must be declared"
    assert "not applied" in joined, "Verdict must say the value was not applied"


def test_empty_glyph_declares_no_unsourced_values():
    engine = RecommendationEngine(Glyph("does_not_exist.json"))
    decision = engine.recommend_decision({"name": "widget", "price": 24.99}, [], [])
    assert not any("not applied" in m for m in decision.missing_information), \
        "A value the profile does not set is not an unknown"


def test_unknowns_do_not_change_legacy_result():
    engine = RecommendationEngine(Glyph())
    product = {"name": "widget", "price": 24.99, "was_price": 49.99}
    legacy = engine.recommend(product, [], GEO)
    assert set(legacy) == {"action", "reasoning", "alternatives"}, \
        "Unknowns live on the Decision, not in the legacy dict"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"All {len(tests)} tests passed.")
