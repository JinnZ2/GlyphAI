class ManipulationDetector:
    def scan_listing(self, product_data):
        flags = []
        
        # Urgency manipulation
        if any(word in product_data['description'].lower() 
               for word in ['limited time', 'only X left', 'ending soon']):
            flags.append({
                "type": "FAKE_URGENCY",
                "severity": 0.7,
                "evidence": "Uses time-pressure language"
            })
        
        # Price anchoring
        if product_data.get('was_price') and product_data.get('now_price'):
            discount = (product_data['was_price'] - product_data['now_price']) / product_data['was_price']
            if discount > 0.5:
                flags.append({
                    "type": "SUSPICIOUS_DISCOUNT",
                    "severity": 0.6,
                    "evidence": f"{discount*100:.0f}% off may indicate inflated 'original' price"
                })
        
        return flags
