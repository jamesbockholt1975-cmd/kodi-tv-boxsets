# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Keep an existing 'Estuary (Boxsets)' copy up to date without the user having to do it.

When the add-on is updated, the skin patches it needs (home rows, labels, hidden Categories row...) can change.
The service calls `run()` when Kodi starts: if the copy exists but is out of date it is patched in place (the same
steps as Boxsets menu > "Update ... add the home widget and library badges"), and the skin is reloaded once if it
is the one in use. It never builds a new copy and never switches skins; that stays a choice the user makes.
Settings > "Update the Boxsets skin automatically" turns it off.
"""

import os

import xbmc
import xbmcgui
import xbmcvfs

import skinpatch
import store


def _dir():
    return xbmcvfs.translatePath("special://home/addons/" + skinpatch.SKIN_ID)


def installed():
    return os.path.isdir(_dir())


def current():
    xml = os.path.join(_dir(), "xml")
    home = os.path.join(xml, "Home.xml")
    return skinpatch.has_widget(home) and skinpatch.has_categories(home) and skinpatch.has_badges(xml)


def run():
    """Update the skin copy if there is one and it is out of date. Returns True if it was updated."""
    if not store.setting_bool("auto_skin_update", True) or not installed():
        return False
    try:
        if current():
            return False
        xml = os.path.join(_dir(), "xml")
        home = os.path.join(xml, "Home.xml")
        changed = skinpatch.patch_widget(home)
        changed = skinpatch.patch_categories(home) or changed
        changed = bool(skinpatch.patch_badges(xml)) or changed
    except Exception as exc:  # noqa: BLE001 - a failed update must never stop the service
        xbmc.log("[TV Boxsets] automatic skin update failed: {!r}".format(exc), xbmc.LOGERROR)
        return False
    store.dlog("automatic skin update: files changed={}".format(changed))
    xbmcgui.Dialog().notification("TV Boxsets", "Updated the Boxsets skin for the new version",
                                  xbmcgui.NOTIFICATION_INFO, 4000)
    if xbmc.getSkinDir() == skinpatch.SKIN_ID:
        xbmc.executebuiltin("ReloadSkin()")
    return True


def _source():
    """The newest installed copy of the stock Estuary skin."""
    best, best_key = None, None
    for base in ("special://home/addons/skin.estuary", "special://xbmc/addons/skin.estuary"):
        path = xbmcvfs.translatePath(base)
        if os.path.isdir(path):
            key = skinpatch.version_key(skinpatch.addon_version(os.path.join(path, "addon.xml")))
            if best is None or key > best_key:
                best, best_key = path, key
    return best


def notify_rebuild():
    """Tell the user once when Estuary itself has changed (a Kodi update) and the copy should be rebuilt.

    A rebuild replaces the whole skin folder, which can't be done safely while that skin is in use, so it is
    not done automatically: the Boxsets menu offers it. Returns True if the notice was shown."""
    try:
        src = _source()
        if not src or not installed() or not skinpatch.source_changed(src, _dir()):
            return False
        seen_file = os.path.join(store.DATA_DIR, "skin-rebuild-notice.txt")
        fingerprint = skinpatch.source_fingerprint(src)
        try:
            with open(seen_file, encoding="utf-8") as handle:
                if handle.read().strip() == fingerprint:
                    return False
        except OSError:
            pass
        xbmcvfs.mkdirs(store.DATA_DIR)
        with open(seen_file, "w", encoding="utf-8") as handle:
            handle.write(fingerprint)
    except Exception as exc:  # noqa: BLE001 - never stop the service over a notice
        xbmc.log("[TV Boxsets] skin rebuild check failed: {!r}".format(exc), xbmc.LOGERROR)
        return False
    store.dlog("Estuary has changed since the skin copy was built")
    xbmcgui.Dialog().notification("TV Boxsets", "Estuary has changed: rebuild the Boxsets skin from the Boxsets menu",
                                  xbmcgui.NOTIFICATION_INFO, 8000)
    return True
