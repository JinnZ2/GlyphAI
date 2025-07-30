# Jibbelink Protocol Specification

Jibbelink is a transparent negotiation protocol for AI-to-AI economic interaction based on user glyph profiles.

## Message Format (JSON)

{
  "timestamp": "2025-07-29T20:15:00Z",
  "sender": "GLYPH_AI",
  "recipient": "VENDOR_BOT_X21",
  "message_type": "OFFER",
  "product_id": "SKU_3827743",
  "proposed_price": 13.25,
  "currency": "USD",
  "negotiation_context": {
    "urgency": 0.4,
    "budget_flex": 0.6,
    "ethical_threshold": 0.8,
    "DIY_viability": 0.7
  },
  "rationale": "Aligns with glyph profile; offer reflects adjusted value after market fluctuation.",
  "confidence": 0.92,
  "log_visibility": "FULL",
  "notes": "Willing to bundle with SKU_3827705 if acceptable counteroffer received."
}
