import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision_model import Decision, Evidence


def test_evidence_serialization():
    evidence = Evidence(
        source="GeoPriceAnalyzer",
        claim="In-store price for widget in 90210 is $7.75",
        source_kind="mock",
        confidence=0.0,
        supporting_data={"region": "90210", "in_store": 7.75},
    )
    assert evidence.to_dict() == {
        "source": "GeoPriceAnalyzer",
        "claim": "In-store price for widget in 90210 is $7.75",
        "source_kind": "mock",
        "confidence": 0.0,
        "supporting_data": {"region": "90210", "in_store": 7.75},
    }
    json.dumps(evidence.to_dict())


def test_evidence_missing_provenance_stays_unknown():
    serialized = Evidence(
        source="GeoPriceAnalyzer",
        claim="A regional price was supplied",
        source_kind=None,
    ).to_dict()
    assert "source_kind" in serialized
    assert serialized["source_kind"] is None, \
        "Absent provenance must not be inferred as observed"


def test_evidence_rejects_source_kind_outside_vocabulary():
    try:
        Evidence("source", "claim", "fabricated")
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown provenance kinds must not enter the model")


def test_domain_objects_reject_invalid_confidence():
    invalid_values = [float("nan"), float("inf"), -0.1, 1.1, True]
    for value in invalid_values:
        for factory in (
                lambda: Evidence("source", "claim", "mock", value),
                lambda: Decision("REJECT", confidence=value)):
            try:
                factory()
            except ValueError:
                pass
            else:
                raise AssertionError(
                    "Confidence must be finite and between zero and one")


def test_evidence_serialization_detaches_nested_supporting_data():
    supporting_data = {"regions": [{"zip": "90210"}]}
    serialized = Evidence(
        "GeoPriceAnalyzer", "Regional price", "mock",
        supporting_data=supporting_data).to_dict()
    serialized["supporting_data"]["regions"][0]["zip"] = "changed"
    assert supporting_data["regions"][0]["zip"] == "90210", \
        "Serialized evidence must not expose nested domain data"


def test_evidence_serialization_rejects_non_json_supporting_data():
    evidence = Evidence(
        "GeoPriceAnalyzer", "Regional price", "mock",
        supporting_data={"not_json": float("nan")})
    try:
        evidence.to_dict()
    except ValueError:
        pass
    else:
        raise AssertionError("Serialization must not emit non-standard JSON")


def test_decision_serialization():
    evidence = Evidence("GeoPriceAnalyzer", "Mock regional price", "mock")
    decision = Decision(
        action="EVALUATE_ALTERNATIVES",
        confidence=0.0,
        reasoning=("No disqualifying manipulation was found",),
        warnings=("Regional prices are simulated",),
        evidence=(evidence,),
        missing_information=("Observed regional prices",),
        alternatives=({"type": "GEOGRAPHIC", "source_kind": "mock"},),
    )
    serialized = decision.to_dict()
    assert serialized == {
        "action": "EVALUATE_ALTERNATIVES",
        "confidence": 0.0,
        "reasoning": ["No disqualifying manipulation was found"],
        "warnings": ["Regional prices are simulated"],
        "evidence": [evidence.to_dict()],
        "missing_information": ["Observed regional prices"],
        "alternatives": [{"type": "GEOGRAPHIC", "source_kind": "mock"}],
    }
    assert decision.verdict == decision.action
    json.dumps(serialized)


def test_conversion_from_existing_recommendation_result():
    recommendation = {
        "action": "PROCEED_WITH_CAUTION",
        "reasoning": ["reason"],
        "alternatives": [{"type": "DIY", "description": "repair"}],
    }
    decision = Decision.from_recommendation(recommendation)
    assert decision.to_legacy_dict() == recommendation
    assert decision.to_dict()["confidence"] is None, \
        "Uncalibrated confidence must remain unknown, not become a score"
    assert decision.to_dict()["warnings"] == []
    assert decision.to_dict()["evidence"] == []
    assert decision.to_dict()["missing_information"] == []


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"All {len(tests)} tests passed.")
