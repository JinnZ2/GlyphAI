"""Coupling check: a guided checklist for disaster footage, run before sharing.

Dispatch GLYPH-C1. Not a video classifier: no pixel analysis, no model, no
network. The user watches the clip and answers a short set of questions about
whether the scene's LAYERS react to each other. The output helps the user
decide; it never labels a clip REAL or FAKE and never gives a percentage.

PRINCIPLE
    Real events are COUPLED: every layer shares the same air and ground.
      surge / quake / blast -> ground vibration + infrasound
      -> animals and birds react FIRST, trees are driven from the base,
         people turn toward what they feel, shadows share one light.
    Generated scenes are often assembled from UNCOUPLED layers: each part is
    rendered from its own prototype (birds = a calm V formation) and never
    "hears" the event. A missing reaction BETWEEN layers is the durable tell;
    pixel artifacts get fixed first as generators improve.

    Source of the cue set: field-observation practice (OBSERVED). Each cue in
    coupling_cues.json carries its own status and source, and its mechanism
    column states DERIVED / SECONDARY / PROPOSED per row.

ANSWERS
    yes         the layer is visible and reacts as a real event would
    no          the layer is VISIBLE and the expected reaction is absent or
                contradicted
    cannot_see  the layer is not in frame or cannot be judged. A valid answer
                that never counts against the clip.

RESULT
    COUPLING_BROKEN(cues=[...])   one or more expected reactions absent or
                                  contradicted, with the cue ids
    COUPLING_CONSISTENT           every answered cue is consistent, and enough
                                  cues were answered to say so
    NOT_EVALUABLE(reason)         event type unknown, or fewer answered cues
                                  than MIN_ANSWERED_CUES (a PLACEHOLDER)
    Never REAL / FAKE / a percentage.

    [CHOICE 1] COUPLING_BROKEN does not require MIN_ANSWERED_CUES: a single
    contradicted coupling is already an observation about two layers (the
    cue's layer and the event). COUPLING_CONSISTENT does require it, because
    consistency read off one layer is not a statement about coupling.

SHARE STEP
    The share step is where harm lands. Fake disaster clips carry urgency in
    the caption ("share now", "they're hiding this"): a TIME ATTACK on the
    decision to share (research.md section 2.1). The caption is run through
    the existing ManipulationDetector with the share-specific phrases added
    to its URGENCY_WORDS, and each flag is tagged with its mechanism. The
    tool's pause-before-share is itself the countermeasure.

The provenance steps and scope limits are appended to every result,
independent of the verdict, because recycled REAL footage (wrong place, wrong
date) passes every coupling check and only provenance catches it.
"""

import json
import os

from ManipulationDetector import ManipulationDetector

DEFAULT_CUES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "coupling_cues.json")

COUPLING_BROKEN = "COUPLING_BROKEN"
COUPLING_CONSISTENT = "COUPLING_CONSISTENT"
NOT_EVALUABLE = "NOT_EVALUABLE"
VERDICTS = (COUPLING_BROKEN, COUPLING_CONSISTENT, NOT_EVALUABLE)

ANSWER_YES = "yes"
ANSWER_NO = "no"
ANSWER_CANNOT_SEE = "cannot_see"
ANSWERS = (ANSWER_YES, ANSWER_NO, ANSWER_CANNOT_SEE)

STATUSES = ("OBSERVED", "SECONDARY", "DERIVED", "PROPOSED")
TIMINGS = ("before", "during", "after")

# PLACEHOLDER: the minimum number of answered (yes/no) cues before a
# COUPLING_CONSISTENT verdict is issued. Not calibrated; see SCOPE_LIMITS.
MIN_ANSWERED_CUES = 2

REASON_EVENT_TYPE = "event_type"
REASON_TOO_FEW_VISIBLE = "too_few_visible_layers"

# Share-step urgency, added to the detector's URGENCY_WORDS for captions.
# Same substring rule as the product detector: extend the list, no inline
# string checks.
SHARE_URGENCY_WORDS = [
    "share now", "share before", "share this before", "before they delete",
    "before it gets deleted", "before it's deleted", "before its deleted",
    "they're hiding this", "they are hiding this", "they don't want you to see",
    "they dont want you to see", "spread this", "share immediately",
    "share asap", "must share", "everyone needs to see this",
]

# The detection axis from research.md section 2.1 / 2.3, as sets.
MECHANISM_BY_FLAG = {
    "FAKE_URGENCY": ["TIME_ATTACK"],
    "SUBSCRIPTION_TRAP": ["OPTION_SET_ATTACK", "EXIT_ATTACK"],
    "SUSPICIOUS_DISCOUNT": ["MAGNITUDE_ATTACK"],
}

PROVENANCE_STEPS = [
    "1. Who posted it first? Find the earliest upload, not the loudest.",
    "2. Reverse-search a frame (screenshot one clear frame; search it).",
    "3. Check the date and place against the event: was there a flood / quake / fire there, then?",
    "4. Look for a published fact-check on this clip.",
    "5. Run a watermark / provenance check where a tool is available (C2PA, platform labels).",
]

SCOPE_LIMITS = [
    "Absence is not proof: real footage can lack animals (none present, frame too tight, audio stripped).",
    "Coupling cues depend on the viewer having seen real events; this checklist is a translation of a field baseline, not a replacement for one.",
    "Recycled real footage (wrong place, wrong date) passes every coupling check. The provenance steps catch that; coupling does not.",
    "Accuracy of this checklist: UNMEASURED. Rating it requires the four-arm test (untrained | artifact checklist | coupling checklist | field-baseline viewers) on watermark-confirmed fakes.",
]


# ---------------------------------------------------------------- cue set

REQUIRED_CUE_KEYS = ("id", "layer", "question", "expected_if_real",
                     "typical_if_generated", "timing", "applies_to",
                     "status", "source", "mechanism")


def validate_cues(data):
    """Raise ValueError on any cue row missing a field, status or source.

    A cue with no stated status or no source would enter the checklist as if
    it were established, which is the reading the status column exists to
    prevent.
    """
    if not isinstance(data, dict) or "cues" not in data or "event_types" not in data:
        raise ValueError("cue file must carry 'cues' and 'event_types'")
    events = data["event_types"]
    seen = set()
    for row in data["cues"]:
        missing = [k for k in REQUIRED_CUE_KEYS if k not in row]
        if missing:
            raise ValueError("cue {} missing {}".format(row.get("id"), missing))
        if row["id"] in seen:
            raise ValueError("duplicate cue id {}".format(row["id"]))
        seen.add(row["id"])
        if row["status"] not in STATUSES:
            raise ValueError("cue {} has status {!r}".format(row["id"], row["status"]))
        if row["timing"] not in TIMINGS:
            raise ValueError("cue {} has timing {!r}".format(row["id"], row["timing"]))
        if not row["source"]:
            raise ValueError("cue {} has no source".format(row["id"]))
        mech = row["mechanism"]
        if not isinstance(mech, dict) or mech.get("status") not in STATUSES \
                or "claim" not in mech or "source" not in mech:
            raise ValueError("cue {} mechanism must state claim, status and source"
                             .format(row["id"]))
        unknown = [e for e in row["applies_to"] if e not in events]
        if unknown or not row["applies_to"]:
            raise ValueError("cue {} applies_to {!r} outside event_types"
                             .format(row["id"], row["applies_to"]))
    return data


def load_cues(path=None):
    """Load and validate the cue set (default: coupling_cues.json beside this module)."""
    with open(path or DEFAULT_CUES, "r", encoding="utf-8") as handle:
        return validate_cues(json.load(handle))


def event_types(cues=None):
    return list((cues or load_cues())["event_types"])


def cues_for(event_type, cues=None):
    """Cue rows that apply to one event type, in file order. Empty for an unknown type."""
    data = cues or load_cues()
    if event_type not in data["event_types"]:
        return []
    return [row for row in data["cues"] if event_type in row["applies_to"]]


def questions(event_type, cues=None):
    """The guided walk: (cue id, layer, timing, question) for each applicable cue."""
    return [(row["id"], row["layer"], row["timing"], row["question"])
            for row in cues_for(event_type, cues)]


# ---------------------------------------------------------------- share step

def share_flags(caption, detector=None):
    """Run the caption through the ManipulationDetector, tagged with mechanism.

    Reuses the detector's rule and flag shape; the share-specific phrases are
    added to a per-instance copy of URGENCY_WORDS so product listings are not
    affected. Each returned flag is the detector's three keys plus
    `mechanism` (a list, per research.md section 2.3); the detector's own
    output is not modified.
    """
    if not caption:
        return []
    detector = detector or ManipulationDetector()
    detector.URGENCY_WORDS = list(ManipulationDetector.URGENCY_WORDS) + SHARE_URGENCY_WORDS
    flags = []
    for flag in detector.scan_listing({"description": caption}):
        tagged = dict(flag)
        tagged["mechanism"] = list(MECHANISM_BY_FLAG.get(flag["type"], ["UNASSIGNED"]))
        flags.append(tagged)
    return flags


# ---------------------------------------------------------------- evaluate

def _not_evaluable(reason, detail, answered, cannot_see, caption):
    return {
        "verdict": NOT_EVALUABLE,
        "reason": reason,
        "detail": detail,
        "cues": [],
        "answered": answered,
        "cannot_see": cannot_see,
        "share_flags": share_flags(caption),
        "provenance_steps": list(PROVENANCE_STEPS),
        "scope_limits": list(SCOPE_LIMITS),
    }


def evaluate(event_type, answers, caption=None, cues=None):
    """Evaluate a clip from the user's answers.

    answers: {cue_id: "yes" | "no" | "cannot_see"}. Cue ids not asked are
    treated as cannot_see (listed under `unanswered`). An answer outside the
    vocabulary or a cue id outside the event's cue set raises ValueError,
    since a silently ignored answer would read as cannot_see.
    """
    data = cues or load_cues()
    answers = answers or {}
    if event_type not in data["event_types"]:
        return _not_evaluable(REASON_EVENT_TYPE,
                              "unknown event type {!r}; known: {}".format(
                                  event_type, ", ".join(data["event_types"])),
                              0, 0, caption)
    rows = cues_for(event_type, data)
    ids = [row["id"] for row in rows]
    for cue_id, answer in answers.items():
        if cue_id not in ids:
            raise ValueError("cue {!r} does not apply to event {!r}".format(cue_id, event_type))
        if answer not in ANSWERS:
            raise ValueError("answer for {} must be one of {}, got {!r}".format(
                cue_id, ANSWERS, answer))

    broken = [i for i in ids if answers.get(i) == ANSWER_NO]
    consistent = [i for i in ids if answers.get(i) == ANSWER_YES]
    unseen = [i for i in ids if answers.get(i, ANSWER_CANNOT_SEE) == ANSWER_CANNOT_SEE]
    unanswered = [i for i in ids if i not in answers]
    answered = len(broken) + len(consistent)

    if broken:
        verdict, reason, detail = COUPLING_BROKEN, None, None
    elif answered >= MIN_ANSWERED_CUES:
        verdict, reason, detail = COUPLING_CONSISTENT, None, None
    else:
        verdict = NOT_EVALUABLE
        reason = REASON_TOO_FEW_VISIBLE
        detail = "{} cue(s) answered yes/no; {} needed (PLACEHOLDER minimum)".format(
            answered, MIN_ANSWERED_CUES)

    return {
        "verdict": verdict,
        "reason": reason,
        "detail": detail,
        "cues": broken,
        "consistent": consistent,
        "cannot_see": len(unseen),
        "unanswered": unanswered,
        "answered": answered,
        "event_type": event_type,
        "share_flags": share_flags(caption),
        "provenance_steps": list(PROVENANCE_STEPS),
        "scope_limits": list(SCOPE_LIMITS),
    }


# ---------------------------------------------------------------- guided walk

def ask(event_type, input_fn=input, output_fn=print, cues=None):
    """Walk the user through the questions for one event type.

    Returns the answers dict for evaluate(). input_fn / output_fn are
    injectable so tests never touch stdin or stdout. Any answer not in the
    vocabulary is re-asked; an empty line means cannot_see.
    """
    data = cues or load_cues()
    answers = {}
    for cue_id, layer, timing, question in questions(event_type, data):
        output_fn("[{}] ({}, {}) {}".format(cue_id, layer, timing, question))
        while True:
            raw = input_fn("  yes / no / cannot_see (blank = cannot_see): ").strip().lower()
            if raw == "":
                raw = ANSWER_CANNOT_SEE
            if raw in ANSWERS:
                answers[cue_id] = raw
                break
            output_fn("  answer with yes, no or cannot_see")
    return answers


# ---------------------------------------------------------------- render

def render(result, cues=None):
    """Plain-text report. Carries the scope limits and provenance steps every time."""
    data = cues or load_cues()
    by_id = {row["id"]: row for row in data["cues"]}
    lines = []
    verdict = result["verdict"]
    if verdict == COUPLING_BROKEN:
        lines.append("Coupling: BROKEN on {}".format(", ".join(result["cues"])))
        for cue_id in result["cues"]:
            row = by_id.get(cue_id)
            if row:
                lines.append("  {} ({}): expected {}; typical if generated: {}".format(
                    cue_id, row["layer"], row["expected_if_real"], row["typical_if_generated"]))
    elif verdict == COUPLING_CONSISTENT:
        lines.append("Coupling: CONSISTENT across {} answered cue(s)".format(result["answered"]))
    else:
        lines.append("Coupling: NOT EVALUABLE ({}): {}".format(result["reason"], result["detail"]))
    lines.append("  answered: {}   cannot_see: {}".format(
        result.get("answered", 0), result.get("cannot_see", 0)))
    if result.get("share_flags"):
        lines.append("")
        lines.append("Caption flags (share step):")
        for flag in result["share_flags"]:
            lines.append("  {} severity {:.1f} mechanism {}: {}".format(
                flag["type"], flag["severity"], ",".join(flag["mechanism"]), flag["evidence"]))
        lines.append("  The pause before sharing is the countermeasure.")
    lines.append("")
    lines.append("Before sharing, regardless of the result above:")
    for step in result["provenance_steps"]:
        lines.append("  " + step)
    lines.append("")
    lines.append("Scope limits:")
    for limit in result["scope_limits"]:
        lines.append("  - " + limit)
    return "\n".join(lines)
