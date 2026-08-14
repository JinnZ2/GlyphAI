# CLAUDE.md — GlyphAI

## Project Overview

GlyphAI is a value-aligned, negotiation-aware AI assistant that protects user interests in e-commerce. It replaces profit-maximizing algorithms with integrity-maximizing ones by filtering recommendations through a user-defined "glyph" (structured value profile), detecting manipulative marketing tactics, comparing geographic pricing, and enabling bot-to-bot negotiation via the open Jibbelink protocol.

**Current phase:** Phase 0 — Proof of Concept (standard library only, mock data).

## Tech Stack

- **Language:** Python 3.6+ (no walrus operator, match statements, or other 3.7+ syntax in use). Verified against 3.11.
- **Dependencies:** Standard library only — `json`, `datetime`, `time`, `os`, `sys`. `requirements.txt` is entirely commented out; `requests`/`beautifulsoup4`/`playwright` are planned for future phases, not installed.
- **No build system** — run modules directly with `python`. There is nothing to `pip install`.
- **No CI/CD, linting, or formatting tools** are configured yet (no `.github/` directory).

## Repository Structure

```
GlyphAI/
├── glyph_engine.py            # Glyph class — loads user value profile from JSON
├── ManipulationDetector.py    # Detects dark patterns (fake urgency, suspicious discounts, subscription traps)
├── geo_price_analyzer.py      # Geographic price comparison with mock data
├── bot_network_interface.py   # JibbelinkNegotiator — bot-to-bot negotiation protocol
├── scheduler.py               # Simple infinite-loop task runner (60s interval)
├── glyph_profile.json         # User values definition (urgency, budget, ethics, etc.)
├── diy_knowledge.json         # DIY fallback data — STUB: no code reads this yet
├── jibbelink_format.md        # Jibbelink protocol message format spec
├── JibbelinkSecurity.md       # Security framework (SHA256 signatures) — spec only, unimplemented
├── requirements.txt           # All commented out; stdlib-only today
├── .gitignore                 # Python bytecode exclusions
├── examples/
│   ├── demo.py                # Full end-to-end demo of all features
│   └── lightbulb_scenario.py  # Single-product use case example
├── tests/
│   ├── test_manipulation_detector.py  # Detection rule tests
│   └── test_glyph_engine.py           # Profile loading + analyzer robustness tests
├── README.md
├── ARCHITECTURE.md            # System design documentation
├── ROADMAP.md                 # Development roadmap
├── Invite.txt                 # Contribution guidelines
└── LICENSE                    # MIT
```

## Architecture

The system follows a value-driven decision pipeline:

1. **Glyph Profile Layer** (`glyph_engine.py`) — Loads user values from `glyph_profile.json`. Central config source.
2. **Detection Layer** (`ManipulationDetector.py`) — Scans product listings for manipulation patterns, outputs severity-rated flags.
3. **Analysis Layer** (`geo_price_analyzer.py`) — Compares regional prices, recommends in-store vs online based on glyph values.
4. **Negotiation Layer** (`bot_network_interface.py`) — Creates Jibbelink protocol messages for bot-to-bot negotiation.
5. **Scheduling** (`scheduler.py`) — Runs analysis tasks on a loop.

### Known structural gaps

Be aware of these before extending the system:

- **The decision engine lives in an example.** `generate_recommendation()` — which combines flags, geo results, and glyph values into a REJECT / PROCEED_WITH_CAUTION / EVALUATE_ALTERNATIVES verdict — is defined in `examples/demo.py`, not in any importable module. ARCHITECTURE.md calls this the "Evaluation Engine." Anything else needing that logic currently cannot import it; promoting it into a core module is a natural next step.
- **`diy_knowledge.json` is orphaned.** No module loads it, despite `DIY_viability` being a glyph value that drives recommendations. The DIY fallback is suggested generically, never sourced from this file.
- **Jibbelink security is unimplemented.** `JibbelinkSecurity.md` specifies SHA256 signing, but `create_message()` emits unsigned messages with a hardcoded `confidence` of 0.95.
- **Geo data is fully mocked.** `fetch_mock_prices()` returns the same three ZIP codes regardless of the `product_name` or `zip_code` passed in; `user_zip` only marks which region is `is_local`.

## Key Commands

```bash
# Run the full demo
python examples/demo.py

# Run the lightbulb scenario
python examples/lightbulb_scenario.py

# Run the scheduler (infinite loop, 60s intervals)
python scheduler.py

# Run tests
python tests/test_manipulation_detector.py
python tests/test_glyph_engine.py
```

Examples and the scheduler resolve `glyph_profile.json` relative to the repo, so they can be run from any working directory.

## Development Conventions

- **File naming:** Core modules use `snake_case.py` except `ManipulationDetector.py` (PascalCase — existing convention).
- **Class naming:** PascalCase (`Glyph`, `ManipulationDetector`, `GeoPriceAnalyzer`, `JibbelinkNegotiator`).
- **No test framework** — tests use plain Python assertions. Each test file auto-discovers its own `test_*` functions in `__main__` and prints per-test results, so a new test only needs to be defined, not registered.
- **No `.env` files** — configuration lives in JSON files (`glyph_profile.json`, `diy_knowledge.json`).
- **Mock data** — all external data sources are currently mocked inline. Real scraping is planned for future phases.

## Module API Reference

**`Glyph`** (`glyph_engine.py`)
- `Glyph(file_path=None)` — defaults to `DEFAULT_PROFILE`, resolved next to the module. A bare filename that isn't found in the cwd falls back to the repo copy, so callers work from any directory.
- `get_value(key, default=None)` — returns the numeric value, or `default` when the key is absent or has no value. **Always pass a default** when the result feeds a comparison; a bare `get_value()` on a missing key returns `None` and will raise on `<`/`>`.
- `get_note(key)`, `is_auto_learn(key)`, `get_oath()`, `is_loyalty_bound()`, `list_keys()`.
- A failed load prints a message and yields an empty profile rather than raising — callers must tolerate empty glyphs.

**`ManipulationDetector`** (`ManipulationDetector.py`)
- `scan_listing(product_data)` → list of flags. `scan()` is an alias.
- Tunable class attributes: `URGENCY_WORDS`, `SUBSCRIPTION_WORDS`, `DISCOUNT_THRESHOLD` (0.4). Extend these lists rather than adding inline string checks.
- Reads `was_price` plus either `price` or `now_price`.

**`GeoPriceAnalyzer`** (`geo_price_analyzer.py`)
- `analyze_prices(product_name, user_zip="90001")` → one dict per region with `region`, `in_store`, `online`, `distance_miles`, `price_gap`, `is_local`, `suggestion`.
- Module constants `DEFAULT_URGENCY`, `DEFAULT_BUDGET_FLEX`, `DEFAULT_DELIVERY_FEASIBILITY` back the glyph lookups so a sparse profile degrades instead of crashing.

**`JibbelinkNegotiator`** (`bot_network_interface.py`)
- `create_message(msg_type, product_id, price, recipient="VENDOR_BOT")` → message dict, also appended to `self.transcript`.
- `summarize_transcript()` → list of human-readable strings.
- Timestamps use `datetime.now(timezone.utc)` formatted as `%Y-%m-%dT%H:%M:%SZ` to match `jibbelink_format.md`. Do not reintroduce `utcnow()` — it is deprecated in 3.12+.

## Key Concepts

- **Glyph:** A structured JSON profile defining user values (urgency, budget flexibility, manipulation tolerance, ethical threshold, etc.). Each value has a numeric score 0–1, optional notes, and an `auto_learn` flag.
- **Loyalty enforcement:** The glyph includes a binding oath — the AI represents one user only, with no dual loyalties.
- **Jibbelink protocol:** An open JSON-based protocol for bot-to-bot price negotiation. Messages include sender/recipient IDs, confidence scores, and log visibility settings.
- **Manipulation flags:** Detection outputs include `FAKE_URGENCY`, `SUSPICIOUS_DISCOUNT`, and `SUBSCRIPTION_TRAP` with severity ratings.

## Important Notes for AI Assistants

- This is an early-stage project (Phase 0). Keep changes simple and aligned with existing patterns.
- All modules currently use only the Python standard library. Do not add external dependencies without explicit approval.
- The glyph profile values (0–1 scale) drive all decision logic. Respect the user's value thresholds.
- When adding new detection patterns to `ManipulationDetector.py`, follow the existing flag format: `{"type": "FLAG_NAME", "severity": <float 0.0–1.0>, "evidence": "..."}`. Severity is a **float**, not a string — `test_flag_shape` enforces this.
- `ManipulationDetector` is the single source of truth for detection. Do not re-implement it inside examples; import it. Its `scan()` method is an alias for `scan_listing()`.
- Listings may carry the current price as either `price` or `now_price`; the detector accepts both. Keep it that way when adding price-based rules.
- When adding new Jibbelink message types, follow the spec in `jibbelink_format.md` and security requirements in `JibbelinkSecurity.md`.
- Test new functionality by adding assertion-based tests in `tests/`.
- **Keep file access cwd-independent.** Resolve data files relative to the module (see `DEFAULT_PROFILE`), never against the caller's working directory. Verify by running the examples and tests from outside the repo root.
- **Watch for silently-skipped logic.** Because `Glyph.load_profile()` swallows errors and the detector uses `.get()` throughout, a mismatched key produces no exception — the rule just never fires. When adding a rule, add a test proving it fires on data shaped the way the examples actually emit it.
