## How GlyphAI Works

1. **Glyph** (user values) → stored locally as JSON
2. **Product Data** → entered by hand, or read from a live page by
   `web_fetch.PoliteFetcher` + `price_extractor` (JSON-LD / microdata / meta),
   selected via `price_sources`
3. **Evaluation Engine** (`recommendation_engine.py`) → rule-based, uses glyph
   thresholds to turn flags + prices into a verdict
4. **Output** → actionable recommendation + manipulation warnings, via `cli.py`

Pipeline: `Glyph` → `ManipulationDetector` → `GeoPriceAnalyzer` →
`RecommendationEngine` → (optional) `JibbelinkNegotiator`. `cli.py` is the
reference caller that wires these together.

### Current Status
- ✅ Glyph schema defined
- ✅ GeoPriceAnalyzer working (with mock data)
- ✅ Jibbelink protocol spec'd
- ✅ Manipulation detection (FAKE_URGENCY, SUSPICIOUS_DISCOUNT, SUBSCRIPTION_TRAP)
- ✅ End-to-end example that runs (`examples/demo.py`)
- ✅ Evaluation engine importable as a core module, with 48 tests
- ✅ CLI interface (`python cli.py analyze|profile|diy`)
- ✅ DIY fallback wired to `diy_knowledge.json` (thin data, working lookup)
- ✅ Live price fetching from real product pages (`--url`), robots-respecting
- ⚠️ Regional in-store pricing still mock (needs store-inventory APIs)
- ❌ Jibbelink signing (spec'd in JibbelinkSecurity.md, messages still unsigned)

### Next Steps
See ROADMAP.md
