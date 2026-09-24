"""Coupling check (dispatch GLYPH-C1).

Fixtures F1-F6 are implementation-authored: they are REGRESSION checks on
the scorer, not validation of the checklist against any footage. The
checklist's accuracy is UNMEASURED and every render says so.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import coupling_check as cc
from ManipulationDetector import ManipulationDetector


def _all_yes(event, **overrides):
    answers = {cue_id: cc.ANSWER_YES for cue_id, _, _, _ in cc.questions(event)}
    answers.update(overrides)
    return answers


# ------------------------------------------------------------ fixtures F1-F6

def test_f1_flood_birds_calm_v_before_water_is_broken():
    result = cc.evaluate("flood", _all_yes("flood", **{"C-BIRD-1": "no"}))
    assert result["verdict"] == cc.COUPLING_BROKEN
    assert result["cues"] == ["C-BIRD-1"]


def test_f2_flood_birds_flush_rest_ok_is_consistent():
    result = cc.evaluate("flood", _all_yes("flood"))
    assert result["verdict"] == cc.COUPLING_CONSISTENT
    assert result["cues"] == []


def test_f3_all_cannot_see_is_not_evaluable():
    answers = {cue_id: cc.ANSWER_CANNOT_SEE for cue_id, _, _, _ in cc.questions("flood")}
    result = cc.evaluate("flood", answers)
    assert result["verdict"] == cc.NOT_EVALUABLE
    assert result["reason"] == cc.REASON_TOO_FEW_VISIBLE
    assert result["answered"] == 0


def test_f4_object_unflips_is_broken_on_c_obj_1():
    result = cc.evaluate("earthquake", _all_yes("earthquake", **{"C-OBJ-1": "no"}))
    assert result["verdict"] == cc.COUPLING_BROKEN
    assert result["cues"] == ["C-OBJ-1"]


def test_f5_unknown_event_type_is_not_evaluable():
    result = cc.evaluate("meteor", {})
    assert result["verdict"] == cc.NOT_EVALUABLE
    assert result["reason"] == cc.REASON_EVENT_TYPE
    assert "meteor" in result["detail"]


def test_f6_caption_share_before_they_delete_it_is_a_time_attack():
    result = cc.evaluate("flood", _all_yes("flood"),
                         caption="Share before they delete it!!")
    flags = result["share_flags"]
    assert any(f["type"] == "FAKE_URGENCY" for f in flags), "share urgency should fire"
    assert all("TIME_ATTACK" in f["mechanism"] for f in flags
               if f["type"] == "FAKE_URGENCY")


# ------------------------------------------------------------ answer semantics

def test_cannot_see_never_counts_against_the_clip():
    answers = _all_yes("flood")
    answers["C-BIRD-1"] = cc.ANSWER_CANNOT_SEE
    answers["C-ANIMAL-1"] = cc.ANSWER_CANNOT_SEE
    result = cc.evaluate("flood", answers)
    assert result["verdict"] == cc.COUPLING_CONSISTENT
    assert result["cannot_see"] == 2


def test_unasked_cues_read_as_cannot_see_and_are_listed():
    result = cc.evaluate("flood", {"C-BIRD-1": "yes", "C-OBJ-1": "yes"})
    assert result["verdict"] == cc.COUPLING_CONSISTENT
    assert "C-SOIL-1" in result["unanswered"]
    assert result["cannot_see"] == len(cc.questions("flood")) - 2


def test_one_answered_cue_alone_is_below_the_placeholder_minimum():
    result = cc.evaluate("flood", {"C-BIRD-1": "yes"})
    assert result["verdict"] == cc.NOT_EVALUABLE
    assert result["reason"] == cc.REASON_TOO_FEW_VISIBLE


def test_a_single_contradiction_is_still_broken():
    """[CHOICE 1]: BROKEN does not wait for the minimum; a contradiction is an observation."""
    result = cc.evaluate("flood", {"C-BIRD-1": "no"})
    assert result["verdict"] == cc.COUPLING_BROKEN
    assert result["cues"] == ["C-BIRD-1"]


def test_unknown_answer_value_raises():
    try:
        cc.evaluate("flood", {"C-BIRD-1": "maybe"})
    except ValueError:
        return
    raise AssertionError("an answer outside yes/no/cannot_see must not be silently ignored")


def test_cue_outside_event_raises():
    try:
        cc.evaluate("flood", {"C-FIRE-1": "no"})
    except ValueError:
        return
    raise AssertionError("a cue that does not apply to the event must be refused")


# ------------------------------------------------------------ output contract

def test_verdict_vocabulary_and_no_real_fake_or_percentage():
    for event in cc.event_types():
        for answers in (_all_yes(event), {}, _all_yes(event, **{"C-OBJ-1": "no"})):
            result = cc.evaluate(event, answers, caption="share now")
            assert result["verdict"] in cc.VERDICTS
            text = cc.render(result)
            assert re.search(r"\b(REAL|FAKE)\b", text) is None, text
            assert "%" not in text, text
            assert "confidence" not in text.lower()


def test_provenance_and_scope_limits_ride_every_result():
    for result in (cc.evaluate("flood", _all_yes("flood")),
                   cc.evaluate("flood", {}),
                   cc.evaluate("nope", {})):
        assert result["provenance_steps"] == cc.PROVENANCE_STEPS
        assert result["scope_limits"] == cc.SCOPE_LIMITS
        assert len(result["provenance_steps"]) == 5
        text = cc.render(result)
        for step in cc.PROVENANCE_STEPS:
            assert step in text
        assert "UNMEASURED" in text


# ------------------------------------------------------------ share step reuse

def test_share_flags_reuse_the_detector_and_keep_its_shape():
    flags = cc.share_flags("LIMITED TIME, they're hiding this")
    assert flags, "urgency should fire"
    for flag in flags:
        assert set(flag) == {"type", "severity", "evidence", "mechanism"}
        assert isinstance(flag["severity"], float)
        assert isinstance(flag["mechanism"], list) and flag["mechanism"]


def test_share_phrases_do_not_leak_into_product_detection():
    """Adding share words to a per-instance list must not change the class list."""
    cc.share_flags("share before they delete it")
    assert "share before" not in ManipulationDetector.URGENCY_WORDS
    assert ManipulationDetector().scan_listing({"description": "share before they delete it"}) == []


def test_empty_caption_gives_no_flags():
    assert cc.share_flags("") == []
    assert cc.share_flags(None) == []


def test_plain_caption_gives_no_flags():
    assert cc.share_flags("Footage from the river this morning.") == []


# ------------------------------------------------------------ cue data file

def test_every_cue_row_carries_status_source_and_mechanism_status():
    data = cc.load_cues()
    for row in data["cues"]:
        assert row["status"] in cc.STATUSES, row["id"]
        assert row["source"], row["id"]
        assert row["mechanism"]["status"] in cc.STATUSES, row["id"]
        assert row["mechanism"]["source"], row["id"]
        assert row["timing"] in cc.TIMINGS, row["id"]


def test_dispatch_example_rows_are_present_with_stated_statuses():
    by_id = {row["id"]: row for row in cc.load_cues()["cues"]}
    assert by_id["C-BIRD-1"]["status"] == "OBSERVED"
    assert by_id["C-BIRD-1"]["mechanism"]["status"] == "SECONDARY"
    assert by_id["C-BIRD-1"]["timing"] == "before"
    assert by_id["C-TREE-1"]["status"] == "DERIVED"
    assert by_id["C-OBJ-1"]["status"] == "SECONDARY"
    for cue_id in ("C-PEOPLE-1", "C-LIGHT-1", "C-SOIL-1"):
        assert cue_id in by_id


def test_every_event_type_has_cues():
    data = cc.load_cues()
    assert set(data["event_types"]) == {"flood", "debris_flow", "earthquake",
                                        "wildfire", "storm", "explosion", "collapse"}
    for event in data["event_types"]:
        assert len(cc.cues_for(event, data)) >= cc.MIN_ANSWERED_CUES, event


def test_validate_cues_refuses_a_row_without_status():
    data = cc.load_cues()
    del data["cues"][0]["status"]
    try:
        cc.validate_cues(data)
    except ValueError:
        return
    raise AssertionError("a cue without a status must be refused")


def test_validate_cues_refuses_an_unstated_mechanism_status():
    data = cc.load_cues()
    data["cues"][0]["mechanism"]["status"] = "TRUE"
    try:
        cc.validate_cues(data)
    except ValueError:
        return
    raise AssertionError("a mechanism status outside the vocabulary must be refused")


# ------------------------------------------------------------ guided walk

def test_ask_walks_every_cue_and_reasks_bad_input():
    scripted = iter(["no", "", "banana", "yes"] + [""] * 20)
    said = []
    answers = cc.ask("explosion", input_fn=lambda prompt: next(scripted),
                     output_fn=said.append)
    ids = [cue_id for cue_id, _, _, _ in cc.questions("explosion")]
    assert list(answers) == ids
    assert answers[ids[0]] == "no"
    assert answers[ids[1]] == "cannot_see"
    assert answers[ids[2]] == "yes"
    assert any("answer with yes" in line for line in said)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print("  ok  {}".format(test.__name__))
    print("All {} tests passed.".format(len(tests)))
