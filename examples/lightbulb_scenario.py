from glyph_engine import Glyph
from geo_price_analyzer import GeoPriceAnalyzer
from manipulation_detector import ManipulationDetector

# Load user glyph
glyph = Glyph.from_file("examples/user_glyph.json")

# Mock product listing
product = {
    "name": "60W LED Bulb",
    "price": 12.99,
    "vendor": "Amazon",
    "description": "LIMITED TIME OFFER! Only 3 left in stock!",
    "was_price": 24.99
}

# Run analysis
detector = ManipulationDetector()
flags = detector.scan_listing(product)

analyzer = GeoPriceAnalyzer(glyph)
geo_results = analyzer.analyze_prices(product['name'], user_zip="90001")

# Output
print("🚩 Manipulation Detected:", flags)
print("📍 Price Analysis:", geo_results)
print("💡 Recommendation:", generate_recommendation(glyph, flags, geo_results))
