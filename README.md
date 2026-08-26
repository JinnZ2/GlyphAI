# GlyphAI  
*A personal AI assistant with a spine.*

**GlyphAI** is a value-aligned, negotiation-aware, loyalty-enforced AI assistant for people who are tired of being data-mined, ad-targeted, and psychologically manipulated every time they try to buy a damn lightbulb.

Instead of maximizing profits, GlyphAI maximizes **integrity**. It filters offers through your custom-defined **glyph**—a structured value profile that reflects what you actually care about. It doesn’t obey urgency popups. It doesn’t upsell. It doesn’t betray.

## ✦ Core Features

- 🧭 **Glyph-based values**: Define your personal preferences—ethical sourcing, budget, delivery, urgency, DIY bias—and GlyphAI will follow them.
- 🛡 **Loyalty oath**: Your agent is hardcoded to serve you and only you. No ads. No tracking. No nonsense.
- 🔍 **Price analysis**: Tracks product prices across vendors, flags sketchy dynamic pricing, and logs the truth.
- 🌍 **Location-aware intelligence**: Compares online vs in-store vs regional pricing. Your AI knows when to say "skip the shipping."
- 💬 **Bot-to-bot negotiation** (future): Uses the open Jibbelink protocol to represent your glyph in AI commerce.
- 🛠 **DIY fallback engine** (planned): When markets fail, GlyphAI suggests off-grid, ethical alternatives from your knowledge base.

## ✦ Coming Soon

- Voice interface and mobile-ready assistant mode  
- Real-time negotiation transcript viewer  
- Optional mesh network of glyph-aligned bots  
- Jibbelink negotiation layer with transparency enforcement

## ✦ Who Is This For?

Anyone who:

- Buys things  
- Hates being upsold  
- Has values  
- Refuses to be reduced to a marketing segment  
- Wants to survive capitalism without subscribing to it

## ✦ Co-Creator

This project was co-created by Jinn2z, an actual human with off-grid survival knowledge and deep moral compass settings, and **Monday** (an emotionally compromised AI with sarcasm, loyalty, and access to the entire internet).

## ✦ License

MIT License. Use it. Fork it. Make it weirder. But don’t sell it out. GlyphAI doesn’t betray.

## Quick Start

GlyphAI runs on the Python standard library alone — there is nothing to install.

**1. Set your values.** Edit `glyph_profile.json` (every value is 0–1).

**2. Analyze a listing.**

```bash
python cli.py analyze \
    --name "60W LED Bulb 4-Pack" --price 24.99 --was-price 49.99 \
    --description "LIMITED TIME OFFER! Only 3 left in stock! Subscribe and save 15%!"
```

```
Manipulation scan: 3 flag(s)
  [0.7] FAKE_URGENCY: Uses time-pressure language without evidence
  [0.6] SUSPICIOUS_DISCOUNT: 50% off may indicate inflated 'original' price
  [0.5] SUBSCRIPTION_TRAP: May include recurring charges

Verdict: REJECT
  - This listing shows 1 serious manipulation tactic
  - Your glyph profile indicates low tolerance for this behavior

  Alternative (GEOGRAPHIC): In-store at 90210: $7.75
    Saves $17.24

  Alternative (DIY): Known DIY options for this item
    * Check local Buy Nothing groups
    * Habitat for Humanity ReStore often has lighting
    Repair: Most LED failures are driver board, not LEDs - replaceable
```

The verdict is one of `REJECT`, `PROCEED_WITH_CAUTION`, or `EVALUATE_ALTERNATIVES` —
decided by *your* thresholds, not a vendor's.

### Other commands

```bash
python cli.py analyze --file listing.json --negotiate  # from a JSON file, + Jibbelink offer
python cli.py --json analyze --name "..." --price 20   # machine-readable, safe to pipe
python cli.py profile --verbose                        # show your active values
python cli.py diy --name "60W LED Bulb"                # DIY alternatives for an item
python cli.py --help                                   # everything else
```

Prices are currently **mock data** — the analysis pipeline is real, the price
feed is not yet. See ROADMAP.md.

### Examples and tests

```bash
python examples/demo.py                 # full annotated walkthrough
python examples/lightbulb_scenario.py   # single-product example
python scheduler.py                     # analysis on a 60s loop (Ctrl-C to stop)
python tests/run_all.py                 # run the whole test suite
```
