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
├── cli.py                     # Command line entry point (analyze / profile / diy)
├── glyph_engine.py            # Glyph class — loads user value profile from JSON
├── ManipulationDetector.py    # Detects dark patterns (fake urgency, suspicious discounts, subscription traps)
├── geo_price_analyzer.py      # Geographic price comparison with mock data
├── price_sources.py           # MockPriceSource / LivePriceSource behind one seam
├── web_fetch.py               # PoliteFetcher — robots.txt, rate limit, cache
├── price_extractor.py         # Reads JSON-LD / microdata / meta price data
├── recommendation_engine.py   # RecommendationEngine — the evaluation engine (verdicts)
├── diy_knowledge.py           # DIYKnowledge — loads and matches diy_knowledge.json
├── bot_network_interface.py   # JibbelinkNegotiator — bot-to-bot negotiation protocol
├── scheduler.py               # Simple infinite-loop task runner (60s interval)
├── glyph_profile.json         # User values definition (urgency, budget, ethics, etc.)
├── diy_knowledge.json         # DIY alternatives + repair notes, keyed by product terms
├── jibbelink_format.md        # Jibbelink protocol message format spec
├── JibbelinkSecurity.md       # Security framework (SHA256 signatures) — spec only, unimplemented
├── requirements.txt           # All commented out; stdlib-only today
├── .gitignore                 # Python bytecode exclusions
├── examples/
│   ├── demo.py                # Full end-to-end demo of all features
│   └── lightbulb_scenario.py  # Single-product use case example
├── tests/
│   ├── run_all.py                     # Runs every test_*.py module
│   ├── test_manipulation_detector.py  # Detection rule tests
│   ├── test_glyph_engine.py           # Profile loading + analyzer robustness tests
│   ├── test_recommendation_engine.py  # Verdict logic + DIY sourcing
│   ├── test_diy_knowledge.py          # Knowledge lookup + matching
│   ├── test_price_extractor.py        # JSON-LD / microdata / meta extraction
│   ├── test_web_fetch.py              # robots, rate limiting, caching
│   ├── test_price_sources.py          # Mock vs live source behaviour
│   └── test_cli.py                    # CLI behaviour and output contracts
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

The pipeline is wired end to end by `cli.py`, which is the reference caller: glyph → detector → geo → engine → (optional) negotiator.

### Known structural gaps

Be aware of these before extending the system:

- **Regional in-store pricing is still mock.** `MockPriceSource` returns the same three ZIP codes regardless of product or ZIP; `user_zip` only marks which region is `is_local`. Live fetching (`--url`) reads a *single real product page*; it cannot know in-store prices in three ZIP codes, and `LivePriceSource.regional_prices()` deliberately delegates to the mock rather than fabricating them. Real regional data needs per-vendor store-inventory APIs.
- **Live extraction only reads structured data.** `price_extractor` handles JSON-LD, microdata and price meta tags. Sites that render prices only in styled markup return `price: None`, which means *unknown* — never treat it as free or as zero. `test_missing_price_is_none_not_zero` guards this.
- **Live fetching is unverified against real retailers.** It is tested against a local HTTP server and injected transports; no external site was reachable from the development sandbox. Expect per-site surprises (JS-rendered prices, bot walls) on first real use.
- **Jibbelink security is unimplemented.** `JibbelinkSecurity.md` specifies SHA256 signing, but `create_message()` emits unsigned messages with a hardcoded `confidence` of 0.95.
- **`ethical_threshold` has no data source.** It is a glyph value with real weight in the user's profile (0.8), but listings carry no sourcing/labor data to compare it against, so no rule consumes it. It was previously read and silently discarded in the recommendation logic. Wiring it up requires a vendor-ethics data source, not just a new rule.
- **`diy_knowledge.json` is thin.** Matching and loading work, but the file holds a single entry (`led_bulb`). It grows by adding entries, not code. Do not invent repair facts to pad it.

## Key Commands

```bash
# Analyze a listing (the primary entry point)
python cli.py analyze --name "60W LED Bulb 4-Pack" --price 24.99 --was-price 49.99 \
    --description "LIMITED TIME! Only 3 left!"

# Analyze a real product page (obeys robots.txt; caching recommended)
python cli.py analyze --url https://example.com/product --cache-dir .cache

# Machine-readable output, safe to pipe
python cli.py --json analyze --file listing.json

# Inspect the active profile / look up DIY options
python cli.py profile --verbose
python cli.py diy --name "60W LED Bulb"

# Run the full demo
python examples/demo.py

# Run the lightbulb scenario
python examples/lightbulb_scenario.py

# Run the scheduler (infinite loop, 60s intervals)
python scheduler.py

# Run all tests (or run any single test file directly)
python tests/run_all.py
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

**`PoliteFetcher`** (`web_fetch.py`)
- `fetch(url)` → page text; raises `RobotsDenied` or `FetchError`. `can_fetch(url)`, `crawl_delay(url)`.
- Constructor takes `transport`, `sleep` and `clock` — inject these in tests so they never touch the network or actually sleep (see `tests/test_web_fetch.py`).
- A 5xx on `robots.txt` is treated as denial, a 404 as "no restrictions".

**`price_extractor`** (`price_extractor.py`)
- `extract_offer(html, url=None)` → `{name, price, currency, availability, description, source, url}`. `source` names which strategy won (`json-ld`, `microdata`, `meta`).
- `parse_price()` handles `$1,299.00` and `1.299,00`; returns `None` for anything unparseable.

**`MockPriceSource` / `LivePriceSource`** (`price_sources.py`)
- Both expose `regional_prices(product_name, zip_code)`; `LivePriceSource` adds `fetch_offer(url)`.
- `fetch_offer` never raises — failures come back as `error` (`robots_denied`, `fetch_failed`, `no_structured_price`) so one bad vendor cannot abort a run.
- `is_live` marks whether numbers are real. `GeoPriceAnalyzer(glyph, price_source=None)` defaults to the mock, so existing behaviour is unchanged.

**`RecommendationEngine`** (`recommendation_engine.py`)
- `RecommendationEngine(glyph, diy_knowledge=None)`; `recommend(product, manipulation_flags=None, geo_results=None)` → `{"action", "reasoning", "alternatives"}`.
- `action` is one of `REJECT`, `PROCEED_WITH_CAUTION`, `EVALUATE_ALTERNATIVES`.
- Thresholds are class attributes (`HIGH_SEVERITY`, `REJECT_TOLERANCE`, `CAUTION_TOLERANCE`, `GEO_SAVINGS_RATIO`, `DIY_VIABILITY_FLOOR`, `DIY_PRICE_FLOOR`) — tune these rather than editing conditionals.
- `generate_recommendation(glyph, product, flags, geo)` is a functional wrapper kept for the original demo call site.
- Injecting `diy_knowledge` is how tests substitute a knowledge base; it defaults to the real one.

**`DIYKnowledge`** (`diy_knowledge.py`)
- `lookup(product_name)` → entry dict plus `matched_key`, or `None`. `alternatives(name)` → list, `repair_note(name)` → str, `list_keys()`.
- Matching is token-based: every underscore-separated term in a key must appear in the product name, so `led_bulb` matches `"60W LED Bulb 4-Pack"` but not `"bulb"`. The most specific match wins.
- `lookup()` returns a copy — mutating it will not corrupt the loaded knowledge.

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
- **The crawler stays polite — this is a values constraint, not a style one.** `web_fetch.PoliteFetcher` obeys robots.txt (including `Crawl-delay`), rate-limits per host, identifies itself honestly, caps response size, and always sets a timeout. Do **not** add user-agent rotation, proxy pools, CAPTCHA solving, or a `--ignore-robots` flag. A project that exists to resist manipulation does not get to manipulate. When a site says no, `RobotsDenied` is the correct outcome and the CLI tells the user to analyze it manually.
- **A missing price is `None`, not `0`.** Anything reading extractor output must treat `None` as unknown. Defaulting it to zero would make free-looking listings sail through the engine.
- **Diagnostics go to stderr, never stdout.** `cli.py --json` must emit only JSON on stdout so it can be piped. `Glyph.load_profile()` and `DIYKnowledge.load_knowledge()` print their status to `sys.stderr` for exactly this reason; `test_json_stdout_is_not_polluted_by_diagnostics` guards it.
- **Decision logic belongs in `recommendation_engine.py`,** not in examples or the CLI. `cli.py` only orchestrates and formats.
- **Watch for silently-skipped logic.** Because `Glyph.load_profile()` swallows errors and the detector uses `.get()` throughout, a mismatched key produces no exception — the rule just never fires. When adding a rule, add a test proving it fires on data shaped the way the examples actually emit it.
