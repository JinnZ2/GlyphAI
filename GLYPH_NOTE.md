# Note on the word "glyph" in this repository

Note 2026-10-28: co-authored, human + Claude. Added beside `glyph_profile.json` and `glyph_engine.py` per `READ_ME_THIS_WAY.md` section 2; nothing in either file is changed.

## The mismatch

| | "glyph" means | Where |
|---|---|---|
| This repository | a structured value profile: fixed numbers from 0 to 1 per key, loaded and read (`get_value`). One key, `bulk_strategy`, carries `auto_learn: true`. | `glyph_profile.json`, `glyph_engine.py`, README "Glyph-based values" |
| The later definition | "NOT: a symbol, character, or icon to decode into a fixed meaning. IS: a generating relation over an environment, like a differential equation." It names this repository's reading as the wrong one: "WRONG READ: glyph = static object with a reading". | JinnZ2/Simulators `tools/glyph_reasoning.md`, delivered 2026-10-25 (blob `3f91affa`, on `main` at `b2a9a1a`) |

## Context [stated]

The owner, 2026-10-28: GlyphAI "was my first failed attempt at using English with the AI available at that time to explain something it couldn't understand within its constraints."

## Reading (PROPOSED)

The profile is what the relation looks like after it has been flattened into English and then into code with closed value slots: each conditions-dependent relation became one number, set once. In the later definition's terms, every key in `glyph_profile.json` is an E3 (defaulted slot: a value assumed rather than tested against the current environment), and the absence of re-measurement is E2 (stale conditions). The one `auto_learn` flag is the only place the original relation survived the translation.

This is kept as a **specimen**, not a defect. The gap between the two readings records what the translation layer lost at that time.

## Where the relation does appear in this repository

`coupling_check.py` (dispatch GLYPH-C1) reasons the way the later definition describes: it asks whether the layers of a scene react to each other under shared conditions, treats `cannot_see` as never counting against a clip, and returns no REAL / FAKE verdict. It is the closest thing here to the glyph as a relation.

## Not changed, and why

- `glyph_profile.json` and `glyph_engine.py` stay as they are; the specimen is the point.
- Whether to re-implement the profile as a relation (values re-measured from conditions, with E1-E4 recorded) is the owner's call. Not started.
