## Phase 0: Proof of Concept (Current)
- [x] Glyph schema
- [x] GeoPriceAnalyzer with mock data
- [x] One end-to-end example that runs
- [x] Manipulation detection library

## Phase 1: MVP (Someone Picks This Up)
- [ ] Real price scraping (3-5 major vendors) — **blocked:** needs external
      dependencies (`requests`/`beautifulsoup4`); everything else is stdlib
- [ ] Price history tracking
- [x] CLI interface (`python cli.py analyze|profile|diy`)
- [x] Basic DIY fallback — `diy_knowledge.json` is loaded and matched by
      `diy_knowledge.py`; grow it by adding entries, not code

## Phase 2: Usable (Community Adoption)
- [ ] Browser extension
- [ ] Multi-vendor comparison
- [ ] Community-maintained manipulation patterns
- [ ] Jibbelink v0.1 implementation

## Phase 3: Infrastructure (Long-term)
- [ ] Federated glyph verification
- [ ] DIY knowledge base integration
- [ ] Legal defense fund for scraping challenges
