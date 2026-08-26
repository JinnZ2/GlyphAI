#!/usr/bin/env python3
"""
GlyphAI Demo: Complete flow from product query to actionable recommendation
Shows manipulation detection, geo pricing, and Jibbelink negotiation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glyph_engine import Glyph
from geo_price_analyzer import GeoPriceAnalyzer
from bot_network_interface import JibbelinkNegotiator
from ManipulationDetector import ManipulationDetector
from recommendation_engine import generate_recommendation

def main():
    print("=" * 60)
    print("GlyphAI - Complete Flow Demonstration")
    print("=" * 60)
    
    # Load user glyph
    print("\n📋 Loading your glyph profile...")
    glyph = Glyph('glyph_profile.json')
    print(f"✓ Loyalty oath: {glyph.get_oath()[:50]}...")
    
    # Mock product listing (in real version, this comes from scraping)
    product = {
        "name": "60W LED Bulb 4-Pack",
        "price": 24.99,
        "was_price": 49.99,
        "vendor": "Amazon",
        "product_id": "SKU_3827743",
        "description": "LIMITED TIME OFFER! Only 3 left in stock! Subscribe and save 15%!",
        "url": "https://example.com/product"
    }
    
    print(f"\n🛒 Analyzing: {product['name']}")
    print(f"   Price: ${product['price']} (was ${product['was_price']})")
    print(f"   Vendor: {product['vendor']}")
    
    # Manipulation detection
    print("\n🔍 Scanning for manipulation tactics...")
    detector = ManipulationDetector()
    flags = detector.scan(product)
    
    if flags:
        print(f"   🚩 {len(flags)} issues detected:")
        for flag in flags:
            print(f"      • {flag['type']}: {flag['evidence']}")
    else:
        print("   ✓ No obvious manipulation detected")
    
    # Geographic price analysis
    print("\n📍 Checking regional prices...")
    geo_analyzer = GeoPriceAnalyzer(glyph)
    geo_results = geo_analyzer.analyze_prices(product['name'], user_zip="90001")
    
    for result in geo_results:
        print(f"   {result['region']}: In-store ${result['in_store']} | "
              f"Online ${result['online']} | {result['suggestion']}")
    
    # Generate recommendation
    print("\n💡 GlyphAI Recommendation:")
    rec = generate_recommendation(glyph, product, flags, geo_results)
    
    print(f"\n   Action: {rec['action']}")
    if rec['reasoning']:
        print("\n   Reasoning:")
        for reason in rec['reasoning']:
            print(f"      {reason}")
    
    if rec['alternatives']:
        print("\n   Alternatives:")
        for alt in rec['alternatives']:
            print(f"      • {alt['type']}: {alt['description']}")
            if 'savings' in alt:
                print(f"        (Save {alt['savings']})")
    
    # Jibbelink negotiation (if user wants to proceed)
    print("\n🤖 Jibbelink Protocol Demo:")
    negotiator = JibbelinkNegotiator(glyph)
    
    # Create initial offer based on glyph values
    target_price = product['price'] * (1 - glyph.get_value('budget_flex') * 0.2)
    message = negotiator.create_message(
        msg_type="OFFER",
        product_id=product['product_id'],
        price=round(target_price, 2),
        recipient="VENDOR_BOT_AMAZON"
    )
    
    print(f"   Sent OFFER to {message['recipient']}")
    print(f"   Proposed price: ${message['proposed_price']}")
    print(f"   Negotiation context: urgency={message['negotiation_context']['urgency']}, "
          f"DIY_viability={message['negotiation_context']['DIY_viability']}")
    
    print("\n" + "=" * 60)
    print("Demo complete. This is what GlyphAI does:")
    print("  1. Loads your values (glyph profile)")
    print("  2. Detects manipulation in listings")
    print("  3. Compares regional pricing")
    print("  4. Generates value-aligned recommendations")
    print("  5. Can negotiate via Jibbelink protocol")
    print("\nAll decisions are transparent and traceable.")
    print("=" * 60)

if __name__ == "__main__":
    main()
