from glyph_engine import Glyph

class GeoPriceAnalyzer:
    def __init__(self, glyph: Glyph):
        self.glyph = glyph

    def fetch_mock_prices(self, product_name, zip_code):
        return {
            "90301": {"in_store": 8.99, "online": 10.49, "distance": 2.1},
            "90210": {"in_store": 7.75, "online": 9.99, "distance": 7.5},
            "90001": {"in_store": 9.25, "online": 9.25, "distance": 0.3}
        }

    def analyze_prices(self, product_name, user_zip="90001"):
        regional_data = self.fetch_mock_prices(product_name, user_zip)
        user_urgency = self.glyph.get_value("urgency")
        budget_flex = self.glyph.get_value("budget_flex")
        delivery_ok = self.glyph.get_value("delivery_feasibility")

        result = []
        for region, info in regional_data.items():
            price_gap = round(info["online"] - info["in_store"], 2)
            suggestion = "STAY PUT"

            if delivery_ok < 0.5 and info["distance"] <= 5.0:
                suggestion = f"Drive to store in {region}"
            elif price_gap > 1.00 and info["distance"] <= 5 and budget_flex > 0.4:
                suggestion = f"Drive to save ${price_gap} at store in {region}"
            elif user_urgency > 0.7:
                suggestion = "Order online (urgent)"
            elif price_gap < 0.5:
                suggestion = "Minimal difference—your call"

            result.append({
                "region": region,
                "in_store": info["in_store"],
                "online": info["online"],
                "distance_miles": info["distance"],
                "price_gap": price_gap,
                "suggestion": suggestion
            })
        return result
