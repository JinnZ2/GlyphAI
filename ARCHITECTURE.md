## How GlyphAI Works

1. **Glyph** (user values) → stored locally as JSON
2. **Product Data** → scraped or fetched via API
3. **Evaluation Engine** → LLM or rule-based, uses glyph to analyze
4. **Output** → actionable recommendation + manipulation warnings

### Current Status
- ✅ Glyph schema defined
- ✅ GeoPriceAnalyzer working (with mock data)
- ✅ Jibbelink protocol spec'd
- ⚠️ Manipulation detection (partial)
- ❌ Real scraping (needs implementation)
- ❌ DIY fallback (needs knowledge base)

### Next Steps
See ROADMAP.md
