import json
import os
import re
import sys

# Resolve the knowledge file next to this module so lookups work from any cwd.
DEFAULT_KNOWLEDGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'diy_knowledge.json')


def _tokenize(text):
    """Lowercase word tokens, e.g. '60W LED Bulb 4-Pack' -> {60w, led, bulb, 4, pack}."""
    return set(re.split(r'[^a-z0-9]+', str(text).lower())) - {''}


class DIYKnowledge:
    """Loads DIY alternatives and repair notes from diy_knowledge.json.

    Entry keys are underscore-separated terms ('led_bulb'). A product matches
    an entry when every term in the key appears in the product name, so
    '60W LED Bulb 4-Pack' matches 'led_bulb'. The most specific match wins.
    """

    def __init__(self, file_path=None):
        self.file_path = file_path or DEFAULT_KNOWLEDGE
        self.knowledge = self.load_knowledge()

    def load_knowledge(self):
        try:
            with open(self.file_path, 'r') as file:
                return json.load(file)
        except Exception as e:
            # Match Glyph's tolerant behaviour: degrade, never crash a run.
            print(f"Failed to load DIY knowledge: {e}", file=sys.stderr)
            return {}

    def lookup(self, product_name):
        """Return the best matching entry dict, or None."""
        product_tokens = _tokenize(product_name)
        best_key = None
        best_score = 0
        for key in self.knowledge:
            key_tokens = _tokenize(key)
            if key_tokens and key_tokens <= product_tokens:
                if len(key_tokens) > best_score:
                    best_key, best_score = key, len(key_tokens)
        if best_key is None:
            return None
        entry = dict(self.knowledge[best_key])
        entry['matched_key'] = best_key
        return entry

    def alternatives(self, product_name):
        """Return the list of suggested alternatives for a product ([] if none)."""
        entry = self.lookup(product_name)
        return list(entry.get('alternatives', [])) if entry else []

    def repair_note(self, product_name):
        """Return the repair note for a product ('' if none)."""
        entry = self.lookup(product_name)
        return entry.get('repair', '') if entry else ''

    def list_keys(self):
        return list(self.knowledge.keys())
