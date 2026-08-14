## How GlyphAI Works

1. **Glyph** (user values) → stored locally as JSON
2. **Product Data** → scraped or fetched via API
3. **Evaluation Engine** → LLM or rule-based, uses glyph to analyze
4. **Output** → actionable recommendation + manipulation warnings

### Current Status
- ✅ Glyph schema defined
- ✅ GeoPriceAnalyzer working (with mock data)
- ✅ Jibbelink protocol spec'd
- ✅ Manipulation detection (FAKE_URGENCY, SUSPICIOUS_DISCOUNT, SUBSCRIPTION_TRAP)
- ✅ End-to-end example that runs (`examples/demo.py`)
- ❌ Real scraping (needs implementation)
- ⚠️ DIY fallback (knowledge base stub in `diy_knowledge.json`, not yet wired in)

### Next Steps
See ROADMAP.md
