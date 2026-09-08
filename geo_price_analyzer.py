from glyph_engine import Glyph
from price_sources import MockPriceSource

# Fallbacks used when a glyph profile is missing a key, so analysis degrades
# gracefully instead of crashing on a None comparison.
DEFAULT_URGENCY = 0.5
DEFAULT_BUDGET_FLEX = 0.5
DEFAULT_DELIVERY_FEASIBILITY = 1.0


class GeoPriceAnalyzer:
    def __init__(self, glyph: Glyph, price_source=None):
        self.glyph = glyph
        self.price_source = price_source or MockPriceSource()

    def fetch_mock_prices(self, product_name, zip_code):
        """Deprecated alias — use `self.price_source.regional_prices()`."""
        return self.price_source.regional_prices(product_name, zip_code)

    def analyze_prices(self, product_name, user_zip="90001"):
        regional_data = self.price_source.regional_prices(product_name, user_zip)
        user_urgency = self.glyph.get_value("urgency", DEFAULT_URGENCY)
        budget_flex = self.glyph.get_value("budget_flex", DEFAULT_BUDGET_FLEX)
        delivery_ok = self.glyph.get_value("delivery_feasibility",
                                           DEFAULT_DELIVERY_FEASIBILITY)

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
                "is_local": region == user_zip,
                "suggestion": suggestion,
                "source_kind": info.get("source_kind")
            })
        return result
