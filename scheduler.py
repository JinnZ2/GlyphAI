import time
from glyph_engine import Glyph
from geo_price_analyzer import GeoPriceAnalyzer

def run_all_tasks():
    glyph = Glyph()
    print("\n[GLYPH] Loyalty oath active:", glyph.get_oath())
    geo_analyzer = GeoPriceAnalyzer(glyph)

    products = ["capacitor 470uF", "transformer 12V", "paper towels"]
    for product in products:
        print(f"\n[Geo Check] {product.upper()}")
        recs = geo_analyzer.analyze_prices(product)
        for r in recs:
            print(f"→ {r['region']} | In-store ${r['in_store']} | Online ${r['online']} | {r['suggestion']}")

if __name__ == "__main__":
    while True:
        print("\n--- Running scheduled GlyphAI tasks ---")
        run_all_tasks()
        time.sleep(60)
