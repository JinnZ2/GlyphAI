import datetime

class JibbelinkNegotiator:
    def __init__(self, glyph):
        self.glyph = glyph
        self.transcript = []

    def create_message(self, msg_type, product_id, price, recipient="VENDOR_BOT"):
        message = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "sender": "GLYPH_AI",
            "recipient": recipient,
            "message_type": msg_type,
            "product_id": product_id,
            "proposed_price": price,
            "currency": "USD",
            "negotiation_context": {
                "urgency": self.glyph.get_value("urgency"),
                "budget_flex": self.glyph.get_value("budget_flex"),
                "ethical_threshold": self.glyph.get_value("ethical_threshold"),
                "DIY_viability": self.glyph.get_value("DIY_viability")
            },
            "rationale": "Generated based on user glyph profile.",
            "confidence": 0.95,
            "log_visibility": "FULL",
            "notes": "Prototype message."
        }
        self.transcript.append(message)
        return message

    def summarize_transcript(self):
        return [f"[{msg['timestamp']}] {msg['sender']} sent a {msg['message_type']} for {msg['product_id']} at ${msg['proposed_price']}." for msg in self.transcript]
