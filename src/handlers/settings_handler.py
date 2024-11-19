import ujson
import os


class SettingsHandler:
    def __init__(self, settings_file="user_settings.json"):
        self.settings_file = f"/{settings_file}"
        # Default settings
        self.default_settings = {
            "LCD_SETTINGS": {
                "contrast": 1,
                "invert": 0,
                "poweroff": False,
                "poweron": True,
                "rotate": 0,
            },
            "DEVICE_SETTINGS": {
                "pwr_save": False,
                "screen_timeout": 30000,
                "pwr_save_boot": False,
            },
            "current_mode": 0,
            "settings_index": 0,
        }
        self.settings = self.load_settings()

    """Load settings from the JSON file. If the file doesn't exist, use default settings"""

    def load_settings(self):
        try:
            os.stat(self.settings_file)
        except OSError:
            print("[INFO] Settings file not found. Creating new file with defaults.")
            self.save_settings()
            return self.default_settings

        try:
            with open(self.settings_file, "r") as f:
                settings = ujson.load(f)
            print("[INFO] User settings loaded successfully.")
            return settings
        except (OSError, ValueError):
            print(
                "[WARNING] No saved settings found or file corrupted. Using defaults."
            )
            return self.default_settings
        except Exception as e:
            print(f"[ERROR] Failed to load settings: {e}")
            return self.default_settings

    """Save the current settings to a JSON file"""

    def save_settings(self):
        try:
            with open(self.settings_file, "w") as f:
                ujson.dump(self.settings, f)
            print("[INFO] User settings saved successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to save settings: {e}")

    """
    Retrieve a specific setting. If section is provided, retrieve from that section
    If no section is provided, retrieve from the top level of settings
    """

    def get_setting(self, key, section=None):

        if section:
            # Look for key in a specific section
            if section in self.settings and key in self.settings[section]:
                return self.settings[section][key]
            else:
                raise KeyError(f"Setting '{key}' not found in section '{section}'")
        else:
            # Look for key in top-level settings
            if key in self.settings:
                return self.settings[key]
            else:
                raise KeyError(f"Setting '{key}' not found in top-level settings")

    """Update a specific setting in the top level or a section"""

    def update_setting(self, key, value, section=None):
        if section:
            if section in self.settings:
                self.settings[section][key] = value
            else:
                raise KeyError(f"Section '{section}' not found")
        else:
            self.settings[key] = value
        self.save_settings()

    """Reset all settings to default values"""

    def reset_settings(self):

        self.settings = self.default_settings.copy()
        self.save_settings()
        print("[INFO] Settings have been reset to default.")
