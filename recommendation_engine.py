from diy_knowledge import DIYKnowledge

# Fallbacks so a sparse or failed-to-load glyph degrades instead of crashing.
DEFAULT_MANIPULATION_TOLERANCE = 0.5
DEFAULT_DIY_VIABILITY = 0.5


class RecommendationEngine:
    """Combines glyph values, manipulation flags and geo pricing into a verdict.

    This is the "Evaluation Engine" described in ARCHITECTURE.md. Verdicts:
      REJECT                 — serious manipulation, below the user's tolerance
      PROCEED_WITH_CAUTION   — manipulation present but tolerable
      EVALUATE_ALTERNATIVES  — nothing disqualifying; weigh the alternatives
    """

    # A flag above this severity counts as a "serious" tactic.
    HIGH_SEVERITY = 0.6
    # Below this manipulation_tolerance, serious flags trigger an outright REJECT.
    REJECT_TOLERANCE = 0.3
    # Below this, any flag at all downgrades the verdict to caution.
    CAUTION_TOLERANCE = 0.5
    # An in-store price below this fraction of the listing is worth a trip.
    GEO_SAVINGS_RATIO = 0.8
    # DIY is only suggested above this glyph value and this price.
    DIY_VIABILITY_FLOOR = 0.7
    DIY_PRICE_FLOOR = 15.0

    def __init__(self, glyph, diy_knowledge=None):
        self.glyph = glyph
        self.diy = diy_knowledge if diy_knowledge is not None else DIYKnowledge()

    def recommend(self, product, manipulation_flags=None, geo_results=None):
        manipulation_flags = manipulation_flags or []
        geo_results = geo_results or []

        tolerance = self.glyph.get_value('manipulation_tolerance',
                                         DEFAULT_MANIPULATION_TOLERANCE)
        diy_viability = self.glyph.get_value('DIY_viability', DEFAULT_DIY_VIABILITY)

        recommendation = {
            "action": None,
            "reasoning": [],
            "alternatives": []
        }

        # Manipulation check
        high_severity = [f for f in manipulation_flags
                         if f.get('severity', 0) > self.HIGH_SEVERITY]
        if high_severity and tolerance < self.REJECT_TOLERANCE:
            recommendation["action"] = "REJECT"
            recommendation["reasoning"].append(
                "This listing shows {} serious manipulation tactic{}".format(
                    len(high_severity), "" if len(high_severity) == 1 else "s")
            )
            recommendation["reasoning"].append(
                "Your glyph profile indicates low tolerance for this behavior"
            )

        # Geographic alternative
        if geo_results:
            best_deal = min(geo_results, key=lambda x: x['in_store'])
            current_price = product.get('price', product.get('now_price'))
            if current_price is not None and \
                    best_deal['in_store'] < current_price * self.GEO_SAVINGS_RATIO:
                savings = current_price - best_deal['in_store']
                recommendation["alternatives"].append({
                    "type": "GEOGRAPHIC",
                    "description": "In-store at {}: ${}".format(
                        best_deal['region'], best_deal['in_store']),
                    "savings": "${:.2f}".format(savings)
                })

        # DIY alternative, sourced from diy_knowledge.json when the product is known
        price = product.get('price', product.get('now_price')) or 0
        if diy_viability > self.DIY_VIABILITY_FLOOR and price > self.DIY_PRICE_FLOOR:
            name = product.get('name', '')
            alternative = {
                "type": "DIY",
                "description": "Consider making/repairing instead",
                "note": "High DIY viability in your glyph profile"
            }
            options = self.diy.alternatives(name)
            repair = self.diy.repair_note(name)
            if options:
                alternative["options"] = options
            if repair:
                alternative["repair"] = repair
            if options or repair:
                alternative["description"] = "Known DIY options for this item"
            recommendation["alternatives"].append(alternative)

        # Default verdict
        if not recommendation["action"]:
            if manipulation_flags and tolerance < self.CAUTION_TOLERANCE:
                recommendation["action"] = "PROCEED_WITH_CAUTION"
            else:
                recommendation["action"] = "EVALUATE_ALTERNATIVES"

        return recommendation


def generate_recommendation(glyph, product, manipulation_flags, geo_results):
    """Functional wrapper kept for the original examples/demo.py call site."""
    return RecommendationEngine(glyph).recommend(product, manipulation_flags,
                                                 geo_results)
