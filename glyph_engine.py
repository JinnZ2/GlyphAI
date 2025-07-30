import json

class Glyph:
    def __init__(self, file_path='glyph_profile.json'):
        self.file_path = file_path
        self.profile = self.load_profile()

    def load_profile(self):
        try:
            with open(self.file_path, 'r') as file:
                data = json.load(file)
                print("Glyph loaded successfully.")
                return data
        except Exception as e:
            print(f"Failed to load glyph profile: {e}")
            return {}

    def get_value(self, key):
        if key in self.profile:
            return self.profile[key].get('value', None)
        return None

    def get_note(self, key):
        return self.profile.get(key, {}).get('note', '')

    def is_auto_learn(self, key):
        return self.profile.get(key, {}).get('auto_learn', False)

    def get_oath(self):
        return self.profile.get("loyalty_enforcement", {}).get("oath", "")

    def is_loyalty_bound(self):
        return self.profile.get("loyalty_enforcement", {}).get("binding", False)

    def list_keys(self):
        return list(self.profile.keys())
