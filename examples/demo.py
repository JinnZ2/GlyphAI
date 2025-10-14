#!/usr/bin/env python3
"""
GlyphAI Demo: Complete flow from product query to actionable recommendation
Shows manipulation detection, geo pricing, and Jibbelink negotiation
"""

import json
from glyph_engine import Glyph
from geo_price_analyzer import GeoPriceAnalyzer
from jibbelink_negotiator import JibbelinkNegotiator

class ManipulationDetector:
    """Detects dark patterns in product listings"""
    
    def scan(self, product):
        flags = []
        desc = product.get('description', '').lower()
        
        # Fake urgency
        urgency_words = ['limited time', 'only', 'left in stock', 'ending soon', 'hurry']
        if any(word in desc for word in urgency_words):
            flags.append({
                "type": "FAKE_URGENCY",
                "severity": 0.7,
                "evidence": "Uses time-pressure language without evidence"
            })
        
        # Suspicious discounts
        if product.get('was_price') and product.get('price'):
            discount = (product['was_price'] - product['price']) / product['was_price']
            if discount > 0.4:
                flags.append({
                    "type": "SUSPICIOUS_DISCOUNT",
                    "severity": 0.6,
                    "evidence": f"{discount*100:.0f}% off - original price may be inflated"
                })
        
        # Subscription traps
        if 'subscribe' in desc or 'auto-renew' in desc:
            flags.append({
                "type": "SUBSCRIPTION_TRAP",
                "severity": 0.5,
                "evidence": "May include recurring charges"
            })
        
        return flags

def generate_recommendation(glyph, product, manipulation_flags, geo_results):
    """Core decision logic based on glyph values"""
    
    manipulation_tolerance = glyph.get_value('manipulation_tolerance')
    diy_viability = glyph.get_value('DIY_viability')
    ethical_threshold = glyph.get_value('ethical_threshold')
    
    recommendation = {
        "action": None,
        "reasoning": [],
        "alternatives": []
    }
    
    # Check manipulation flags
    if manipulation_flags:
        high_severity = [f for f in manipulation_flags if f['severity'] > 0.6]
        if high_severity and manipulation_tolerance < 0.3:
            recommendation["action"] = "REJECT"
            recommendation["reasoning"].append(
                f"🚫 This listing shows {len(high_severity)} serious manipulation tactics"
            )
            recommendation["reasoning"].append(
                "Your glyph profile indicates low tolerance for this behavior"
            )
    
    # Check geographic alternatives
    if geo_results:
        best_deal = min(geo_results, key=lambda x: x['in_store'])
        current_price = product.get('price', 999)
        
        if best_deal['in_store'] < current_price * 0.8:  # 20% savings threshold
            savings = current_price - best_deal['in_store']
            recommendation["alternatives"].append({
                "type": "GEOGRAPHIC",
                "description": f"In-store at {best_deal['region']}: ${best_deal['in_store']}",
                "savings": f"${savings:.2f}"
            })
    
    # Check DIY viability
    if diy_viability > 0.7 and product.get('price', 0) > 15:
        recommendation["alternatives"].append({
            "type": "DIY",
            "description": "Consider making/repairing instead",
            "note": "High DIY viability in your glyph profile"
        })
    
    # Default action if not rejected
    if not recommendation["action"]:
        if manipulation_flags and manipulation_tolerance < 0.5:
            recommendation["action"] = "PROCEED_WITH_CAUTION"
        else:
            recommendation["action"] = "EVALUATE_ALTERNATIVES"
    
    return recommendation

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
OR:

$ python examples/demo.py

🛒 Analyzing: 60W LED Bulb

📊 Your Glyph Profile:
  • Urgency: Medium (0.6)
  • Budget flexibility: Low (0.4)
  • Manipulation tolerance: Very Low (0.1)
  • DIY viability: High (0.9)

🚩 Manipulation Detected:
  ⚠️ FAKE_URGENCY: "Only 3 left" (severity: 0.7)
  ⚠️ SUSPICIOUS_DISCOUNT: 48% off suggests inflated original price

📍 Geographic Analysis:
  • In-store (2.1 mi): $8.99
  • Online: $12.99
  • Recommendation: Drive to store, save $4.00

💡 GlyphAI Recommendation:
Based on your values, this listing is trying to manipulate you.
The "limited time" claim is almost certainly false.
You can get this for $8.99 in-store, or make a DIY alternative.

Would you like DIY instructions? [y/n]
