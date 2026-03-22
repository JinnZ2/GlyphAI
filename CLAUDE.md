# CLAUDE.md — GlyphAI

## Project Overview

GlyphAI is a value-aligned, negotiation-aware AI assistant that protects user interests in e-commerce. It replaces profit-maximizing algorithms with integrity-maximizing ones by filtering recommendations through a user-defined "glyph" (structured value profile), detecting manipulative marketing tactics, comparing geographic pricing, and enabling bot-to-bot negotiation via the open Jibbelink protocol.

**Current phase:** Phase 0 — Proof of Concept (standard library only, mock data).

## Tech Stack

- **Language:** Python 3.6+
- **Dependencies:** Standard library only (`json`, `datetime`, `time`, `abc`). `requests` and `beautifulsoup4` are planned for future phases.
- **No build system** — run modules directly with `python`.
- **No CI/CD, linting, or formatting tools** are configured yet.

## Repository Structure

```
GlyphAI/
├── glyph_engine.py            # Glyph class — loads user value profile from JSON
├── ManipulationDetector.py    # Detects dark patterns (fake urgency, suspicious discounts, subscription traps)
├── geo_price_analyzer.py      # Geographic price comparison with mock data
├── bot_network_interface.py   # JibbelinkNegotiator — bot-to-bot negotiation protocol
├── scheduler.py               # Simple infinite-loop task runner (60s interval)
├── glyph_profile.json         # User values definition (urgency, budget, ethics, etc.)
├── diy_knowledge.json         # DIY fallback knowledge base
├── jibbelink_format.md        # Jibbelink protocol message format spec
├── JibbelinkSecurity.md       # Security framework (SHA256 signatures)
├── requirements.txt           # Python dependencies (mostly future/planned)
├── examples/
│   ├── demo.py                # Full end-to-end demo of all features
│   └── lightbulb_scenario.py  # Single-product use case example
├── tests/
│   └── test_manipulation_detector.py  # Basic assertion-based tests
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
```

## Development Conventions

- **File naming:** Core modules use `snake_case.py` except `ManipulationDetector.py` (PascalCase — existing convention).
- **Class naming:** PascalCase (`Glyph`, `ManipulationDetector`, `GeoPriceAnalyzer`, `JibbelinkNegotiator`).
- **No test framework** — tests use plain Python assertions. Run test files directly.
- **No `.env` files** — configuration lives in JSON files (`glyph_profile.json`, `diy_knowledge.json`).
- **Mock data** — all external data sources are currently mocked inline. Real scraping is planned for future phases.

## Key Concepts

- **Glyph:** A structured JSON profile defining user values (urgency, budget flexibility, manipulation tolerance, ethical threshold, etc.). Each value has a numeric score 0–1, optional notes, and an `auto_learn` flag.
- **Loyalty enforcement:** The glyph includes a binding oath — the AI represents one user only, with no dual loyalties.
- **Jibbelink protocol:** An open JSON-based protocol for bot-to-bot price negotiation. Messages include sender/recipient IDs, confidence scores, and log visibility settings.
- **Manipulation flags:** Detection outputs include `FAKE_URGENCY`, `SUSPICIOUS_DISCOUNT`, and `SUBSCRIPTION_TRAP` with severity ratings.

## Important Notes for AI Assistants

- This is an early-stage project (Phase 0). Keep changes simple and aligned with existing patterns.
- All modules currently use only the Python standard library. Do not add external dependencies without explicit approval.
- The glyph profile values (0–1 scale) drive all decision logic. Respect the user's value thresholds.
- When adding new detection patterns to `ManipulationDetector.py`, follow the existing flag format: `{"flag": "FLAG_NAME", "severity": "low|medium|high", "evidence": "..."}`.
- When adding new Jibbelink message types, follow the spec in `jibbelink_format.md` and security requirements in `JibbelinkSecurity.md`.
- Test new functionality by adding assertion-based tests in `tests/`.
