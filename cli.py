#!/usr/bin/env python3
"""GlyphAI command line interface.

Run a product listing through the full value-aligned pipeline:
manipulation detection, geographic pricing, and a glyph-based verdict.

Examples:
    python cli.py analyze --name "60W LED Bulb 4-Pack" --price 24.99 \\
        --was-price 49.99 --description "LIMITED TIME! Only 3 left!"

    python cli.py analyze --file listing.json --json
    python cli.py profile
    python cli.py diy --name "60W LED Bulb"
"""

import argparse
import json
import sys

from glyph_engine import Glyph
from ManipulationDetector import ManipulationDetector
from geo_price_analyzer import GeoPriceAnalyzer
from recommendation_engine import RecommendationEngine
from bot_network_interface import JibbelinkNegotiator
from diy_knowledge import DIYKnowledge
from price_sources import LivePriceSource

DEFAULT_ZIP = "90001"


def fetch_listing_from_url(url, cache_dir=None):
    """Fetch a real product page. Returns (listing, error_message)."""
    source = LivePriceSource(cache_dir=cache_dir)
    offer = source.fetch_offer(url)

    if offer.get("error") == "robots_denied":
        return None, (
            f"{url}\n  robots.txt disallows automated access to this page.\n"
            "  GlyphAI does not work around that. Analyze it manually with "
            "--name/--price instead.")
    if offer.get("error") == "fetch_failed":
        return None, f"Could not fetch {url}\n  {offer.get('detail', '')}"

    listing = {"url": url}
    for key in ("name", "description"):
        if offer.get(key):
            listing[key] = offer[key]
    if offer.get("price") is not None:
        listing["price"] = offer["price"]
    if offer.get("currency"):
        listing["currency"] = offer["currency"]
    if offer.get("availability"):
        listing["availability"] = offer["availability"]
    listing["price_source"] = offer.get("source")

    if offer.get("error") == "no_structured_price":
        sys.stderr.write(
            f"Note: no structured price found on {url}. "
            "Price is unknown; pass --price to supply it.\n")
    return listing, None


def build_listing(args):
    """Assemble a listing dict from --url, --file and/or individual flags."""
    listing = {}

    if getattr(args, 'url', None):
        fetched, error = fetch_listing_from_url(args.url, args.cache_dir)
        if error:
            sys.stderr.write(error + "\n")
            return None
        listing.update(fetched)

    if args.file:
        try:
            with open(args.file, 'r') as handle:
                from_file = json.load(handle)
        except Exception as e:
            sys.stderr.write(f"Could not read listing file: {e}\n")
            return None
        if not isinstance(from_file, dict):
            sys.stderr.write("Listing file must contain a JSON object.\n")
            return None
        listing.update(from_file)

    # Explicit flags override anything loaded from the file.
    if args.name is not None:
        listing['name'] = args.name
    if args.price is not None:
        listing['price'] = args.price
    if args.was_price is not None:
        listing['was_price'] = args.was_price
    if args.description is not None:
        listing['description'] = args.description
    if args.vendor is not None:
        listing['vendor'] = args.vendor
    if args.product_id is not None:
        listing['product_id'] = args.product_id

    if not listing.get('name'):
        sys.stderr.write("A product name is required (--name or --file).\n")
        return None
    return listing


def analyze(args):
    glyph = Glyph(args.profile)
    listing = build_listing(args)
    if listing is None:
        return 2

    flags = ManipulationDetector().scan_listing(listing)
    geo_results = GeoPriceAnalyzer(glyph).analyze_prices(listing['name'],
                                                         user_zip=args.zip)
    verdict = RecommendationEngine(glyph).recommend(listing, flags, geo_results)

    payload = {
        "product": listing,
        "manipulation_flags": flags,
        "geo_analysis": geo_results,
        "recommendation": verdict,
    }

    if args.negotiate:
        negotiator = JibbelinkNegotiator(glyph)
        budget_flex = glyph.get_value('budget_flex', 0.5)
        price = listing.get('price', listing.get('now_price')) or 0
        offer = negotiator.create_message(
            msg_type="OFFER",
            product_id=listing.get('product_id', 'UNKNOWN'),
            price=round(price * (1 - budget_flex * 0.2), 2),
            recipient=args.recipient,
        )
        payload["jibbelink_offer"] = offer

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print_report(payload)
    return 0


def print_report(payload):
    listing = payload["product"]
    print("=" * 60)
    print(f"GlyphAI analysis: {listing['name']}")
    print("=" * 60)

    price = listing.get('price', listing.get('now_price'))
    if price is not None:
        line = f"Price: ${price}"
        if listing.get('was_price'):
            line += f" (was ${listing['was_price']})"
        if listing.get('price_source'):
            line += f"  [live, via {listing['price_source']}]"
        print(line)
    elif listing.get('url'):
        print("Price: unknown (no structured price data on the page)")
    if listing.get('vendor'):
        print(f"Vendor: {listing['vendor']}")
    if listing.get('availability'):
        print(f"Availability: {listing['availability']}")
    if listing.get('url'):
        print(f"URL: {listing['url']}")

    flags = payload["manipulation_flags"]
    print(f"\nManipulation scan: {len(flags)} flag(s)")
    for flag in flags:
        print(f"  [{flag['severity']:.1f}] {flag['type']}: {flag['evidence']}")
    if not flags:
        print("  No manipulation patterns detected.")

    print("\nRegional pricing (mock data — see ROADMAP.md):")
    for row in payload["geo_analysis"]:
        local = " (local)" if row.get("is_local") else ""
        print(f"  {row['region']}{local}: in-store ${row['in_store']} | "
              f"online ${row['online']} | {row['suggestion']}")

    verdict = payload["recommendation"]
    print(f"\nVerdict: {verdict['action']}")
    for reason in verdict["reasoning"]:
        print(f"  - {reason}")
    for alt in verdict["alternatives"]:
        print(f"\n  Alternative ({alt['type']}): {alt['description']}")
        if alt.get('savings'):
            print(f"    Saves {alt['savings']}")
        for option in alt.get('options', []):
            print(f"    * {option}")
        if alt.get('repair'):
            print(f"    Repair: {alt['repair']}")

    offer = payload.get("jibbelink_offer")
    if offer:
        print(f"\nJibbelink OFFER to {offer['recipient']}: "
              f"${offer['proposed_price']} ({offer['timestamp']})")
    print("=" * 60)


def profile(args):
    glyph = Glyph(args.profile)
    if args.json:
        print(json.dumps(glyph.profile, indent=2))
        return 0
    print("Glyph profile values:")
    for key in glyph.list_keys():
        value = glyph.get_value(key)
        if value is None:
            continue
        learn = " (auto-learn)" if glyph.is_auto_learn(key) else ""
        print(f"  {key:<24} {value}{learn}")
        note = glyph.get_note(key)
        if note and args.verbose:
            print(f"      {note}")
    oath = glyph.get_oath()
    if oath:
        print(f"\nLoyalty oath (binding={glyph.is_loyalty_bound()}):\n  {oath}")
    return 0


def diy(args):
    knowledge = DIYKnowledge()
    entry = knowledge.lookup(args.name)
    if args.json:
        print(json.dumps(entry, indent=2))
        return 0
    if not entry:
        print(f"No DIY knowledge for '{args.name}'.")
        print(f"Known entries: {', '.join(knowledge.list_keys()) or 'none'}")
        return 1
    print(f"DIY options for '{args.name}' (matched '{entry['matched_key']}'):")
    for option in entry.get('alternatives', []):
        print(f"  * {option}")
    if entry.get('repair'):
        print(f"\nRepair note: {entry['repair']}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="glyphai",
        description="Value-aligned product analysis driven by your glyph profile.")
    parser.add_argument('--profile', default=None,
                        help="Path to a glyph profile (default: glyph_profile.json)")
    parser.add_argument('--json', action='store_true', help="Emit JSON output")
    sub = parser.add_subparsers(dest='command')

    analyze_parser = sub.add_parser('analyze', help="Analyze a product listing")
    analyze_parser.add_argument('--name', help="Product name")
    analyze_parser.add_argument('--price', type=float, help="Current price")
    analyze_parser.add_argument('--was-price', type=float, dest='was_price',
                                help="Advertised original price")
    analyze_parser.add_argument('--description', help="Listing description text")
    analyze_parser.add_argument('--vendor', help="Vendor name")
    analyze_parser.add_argument('--product-id', dest='product_id', help="SKU or product id")
    analyze_parser.add_argument('--file', help="JSON file containing the listing")
    analyze_parser.add_argument('--url',
                                help="Fetch a real product page (obeys robots.txt)")
    analyze_parser.add_argument('--cache-dir', dest='cache_dir', default=None,
                                help="Directory for caching fetched pages")
    analyze_parser.add_argument('--zip', default=DEFAULT_ZIP, help="Your ZIP code")
    analyze_parser.add_argument('--negotiate', action='store_true',
                                help="Also generate a Jibbelink OFFER message")
    analyze_parser.add_argument('--recipient', default="VENDOR_BOT",
                                help="Jibbelink recipient id")
    analyze_parser.set_defaults(func=analyze)

    profile_parser = sub.add_parser('profile', help="Show the active glyph profile")
    profile_parser.add_argument('--verbose', action='store_true',
                                help="Include the note for each value")
    profile_parser.set_defaults(func=profile)

    diy_parser = sub.add_parser('diy', help="Look up DIY alternatives for a product")
    diy_parser.add_argument('--name', required=True, help="Product name")
    diy_parser.set_defaults(func=diy)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, 'command', None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
