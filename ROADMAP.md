## Phase 0: Proof of Concept (Current)
- [x] Glyph schema
- [x] GeoPriceAnalyzer with mock data
- [x] One end-to-end example that runs
- [x] Manipulation detection library

## Phase 1: MVP (Someone Picks This Up)
- [x] Real price fetching — `cli.py analyze --url` reads live pages via
      JSON-LD / microdata / meta tags, with a robots-respecting fetcher.
      Still stdlib-only; no scraping dependencies were needed.
- [ ] Per-vendor coverage (3-5 major vendors) — the generic structured-data
      reader works on any site that publishes schema.org markup. Sites that
      render prices only in styled HTML, or that disallow crawling, need
      either a per-vendor adapter or manual entry.
- [ ] Regional in-store pricing — needs per-vendor store-inventory APIs;
      currently mock and labelled as such
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
