"""Stand-in for `xbmcaddon`. Settings live in SETTINGS so tests can change them."""

import os

SETTINGS = {"keep_backups": 10, "show_missing": True, "debug_logging": False,
            "boxset_sort": 0, "tag_prefix": "Boxset:", "show_badges": True, "auto_tags": False, "show_names": True}


class Addon:
    def __init__(self, addon_id=None):
        pass

    def getAddonInfo(self, key):
        if key == "version":
            return "0.0.0-test"
        if key == "path":
            return os.environ["TVB_ADDON_PATH"]
        return "special://profile/addon_data/plugin.video.tvboxsets/"

    def getSettingBool(self, key):
        return bool(SETTINGS[key])

    def setSettingBool(self, key, value):
        SETTINGS[key] = bool(value)
        return True

    def getSettingInt(self, key):
        return int(SETTINGS[key])

    def getSettingString(self, key):
        return str(SETTINGS[key])
