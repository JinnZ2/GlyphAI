class ManipulationDetector:
    """Scans product listings for dark patterns.

    Every flag has the shape:
        {"type": "FLAG_NAME", "severity": <float 0-1>, "evidence": "..."}
    """

    URGENCY_WORDS = [
        'limited time', 'only', 'left in stock', 'ending soon', 'hurry',
        'act now', 'while supplies last'
    ]

    SUBSCRIPTION_WORDS = ['subscribe', 'auto-renew', 'auto renew', 'recurring']

    # A discount steeper than this is treated as a possible inflated anchor price.
    DISCOUNT_THRESHOLD = 0.4

    def scan_listing(self, product_data):
        flags = []

        # Urgency manipulation
        desc = product_data.get('description', '').lower()
        if any(word in desc for word in self.URGENCY_WORDS):
            flags.append({
                "type": "FAKE_URGENCY",
                "severity": 0.7,
                "evidence": "Uses time-pressure language without evidence"
            })

        # Price anchoring. Listings use either 'price' or 'now_price' for the
        # current price, so accept both rather than silently skipping the check.
        was_price = product_data.get('was_price')
        now_price = product_data.get('now_price')
        if now_price is None:
            now_price = product_data.get('price')

        if was_price and now_price and was_price > 0:
            discount = (was_price - now_price) / was_price
            if discount > self.DISCOUNT_THRESHOLD:
                flags.append({
                    "type": "SUSPICIOUS_DISCOUNT",
                    "severity": 0.6,
                    "evidence": "{:.0f}% off may indicate inflated 'original' price".format(discount * 100)
                })

        # Subscription traps
        if any(word in desc for word in self.SUBSCRIPTION_WORDS):
            flags.append({
                "type": "SUBSCRIPTION_TRAP",
                "severity": 0.5,
                "evidence": "May include recurring charges"
            })

        return flags

    # Alias so callers that used the demo's shorter name keep working.
    def scan(self, product_data):
        return self.scan_listing(product_data)
