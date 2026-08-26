import json
import os
import sys

# Resolve the default profile next to this module so the engine works no matter
# which directory the caller was run from.
DEFAULT_PROFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'glyph_profile.json')


class Glyph:
    def __init__(self, file_path=None):
        if file_path is None:
            file_path = DEFAULT_PROFILE
        elif not os.path.isabs(file_path) and not os.path.exists(file_path):
            # A bare name like 'glyph_profile.json' should still find the
            # repo's profile when the caller is run from another directory.
            fallback = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    file_path)
            if os.path.exists(fallback):
                file_path = fallback
        self.file_path = file_path
        self.profile = self.load_profile()

    def load_profile(self):
        try:
            with open(self.file_path, 'r') as file:
                data = json.load(file)
                # Diagnostics go to stderr so stdout stays machine-parseable
                # (see `cli.py --json`).
                print("Glyph loaded successfully.", file=sys.stderr)
                return data
        except Exception as e:
            print(f"Failed to load glyph profile: {e}", file=sys.stderr)
            return {}

    def get_value(self, key, default=None):
        """Return the numeric value for a glyph key, or `default` if absent."""
        entry = self.profile.get(key)
        if isinstance(entry, dict):
            value = entry.get('value')
            if value is not None:
                return value
        return default

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
