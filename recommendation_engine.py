from decision_model import (Decision, Evidence, normalize_confidence,
                            normalize_source_kind)
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
    # Glyph values that carry weight but have no data source yet. When the
    # profile sets one, the verdict says so instead of silently skipping it.
    UNSOURCED_VALUES = {
        "ethical_threshold": "sourcing or labor data",
        "repairability_bias": "repairability or parts-availability data",
        "signal_noise_ratio": "paid-placement or ranking data",
    }

    def __init__(self, glyph, diy_knowledge=None):
        self.glyph = glyph
        self.diy = diy_knowledge if diy_knowledge is not None else DIYKnowledge()

    def recommend(self, product, manipulation_flags=None, geo_results=None):
        """Return the historical dictionary result used by the CLI and callers."""
        return self.recommend_decision(
            product, manipulation_flags, geo_results).to_legacy_dict()

    def recommend_decision(self, product, manipulation_flags=None,
                           geo_results=None):
        """Return a typed Decision without changing legacy verdict behavior."""
        manipulation_flags = manipulation_flags or []
        geo_results = list(geo_results or [])
        geographic_evidence = [
            self._geographic_evidence(product, result)
            for result in geo_results
        ]

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
            best_index, best_deal = min(
                enumerate(geo_results), key=lambda item: item[1]['in_store'])
            best_evidence = geographic_evidence[best_index]
            current_price = product.get('price', product.get('now_price'))
            if current_price is not None and \
                    best_deal['in_store'] < current_price * self.GEO_SAVINGS_RATIO:
                savings = current_price - best_deal['in_store']
                recommendation["alternatives"].append({
                    "type": "GEOGRAPHIC",
                    "description": "In-store at {}: ${}".format(
                        best_deal['region'], best_deal['in_store']),
                    "savings": "${:.2f}".format(savings),
                    "source_kind": best_evidence.source_kind
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

        warnings, missing_information = self._unknowns(
            product, geo_results, geographic_evidence)

        return Decision.from_recommendation(
            recommendation,
            warnings=warnings,
            evidence=geographic_evidence,
            missing_information=missing_information,
        )

    def _unknowns(self, product, geo_results, geographic_evidence):
        """What this verdict could not verify, stated rather than implied.

        Returns (warnings, missing_information). A verdict that lists its
        unknowns cannot be mistaken for one that checked everything.
        """
        warnings = []
        missing = []

        current_price = product.get('price', product.get('now_price'))
        if current_price is None:
            missing.append(
                "Listing price is unknown; it was not treated as zero")
        if product.get('was_price') is not None:
            missing.append(
                "Advertised original price ${} could not be checked against "
                "price history; no price history exists yet (ROADMAP.md)".format(
                    product['was_price']))

        mock_regions = [
            result.get("region", "unknown")
            for result, evidence in zip(geo_results, geographic_evidence)
            if evidence.source_kind == "mock"
        ]
        if mock_regions:
            missing.append(
                "In-store prices for region(s) {} are mock data, not observed "
                "(ROADMAP.md)".format(", ".join(str(r) for r in mock_regions)))

        unknown_regions = [
            result.get("region", "unknown")
            for result, evidence in zip(geo_results, geographic_evidence)
            if evidence.source_kind is None
        ]
        if unknown_regions:
            warnings.append("Some geographic price evidence has unknown provenance")
            missing.append(
                "Geographic price provenance for region(s): {}".format(
                    ", ".join(str(region) for region in unknown_regions)))

        for key, needs in sorted(self.UNSOURCED_VALUES.items()):
            value = self.glyph.get_value(key)
            if value is not None:
                missing.append(
                    "Your glyph weights {} at {}, but the listing carries no {}; "
                    "that value was not applied".format(key, value, needs))

        return warnings, missing

    @staticmethod
    def _geographic_evidence(product, result):
        """Convert one legacy geographic row into typed evidence."""
        name = product.get("name", "product")
        region = result.get("region", "unknown")
        confidence = normalize_confidence(result.get("confidence"))
        supporting_data = {
            key: value for key, value in result.items()
            if key not in {"source_kind", "confidence"}
        }
        return Evidence(
            source="GeoPriceAnalyzer",
            claim="In-store price for {} in {} is ${}".format(
                name, region, result.get("in_store")),
            source_kind=normalize_source_kind(result.get("source_kind")),
            confidence=confidence,
            supporting_data=supporting_data,
        )


def generate_recommendation(glyph, product, manipulation_flags, geo_results):
    """Functional wrapper kept for the original examples/demo.py call site."""
    return RecommendationEngine(glyph).recommend(product, manipulation_flags,
                                                 geo_results)
