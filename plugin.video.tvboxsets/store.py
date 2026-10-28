# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared boxset storage: load/save, automatic daily backups, merge helpers."""

import copy
import json
import os
import shutil
import time
import uuid

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

import skinpatch

ADDON = xbmcaddon.Addon("plugin.video.tvboxsets")
DATA_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
DATA_FILE = os.path.join(DATA_DIR, "boxsets.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
BADGE_DIR = os.path.join(DATA_DIR, "badges")
# Kept forever: a copy of the file as it was before it was first upgraded to this format.
KEEP_BACKUPS = 10  # default; the add-on setting "keep_backups" overrides it

# Data file format.  1 = the bare {id: boxset} dict used up to 0.5.0.
#                    2 = {"format": 2, "saved_by": "<version>", "boxsets": {id: boxset}}
#                    3 = same wrapper; boxsets may hold movies ("type": "movie" entries),
#                        smart "rules", "excluded" items, more artwork kinds and "modified".
DATA_FORMAT = 3
PRE_MIGRATION_BACKUP = os.path.join(BACKUP_DIR, "pre-format{}-boxsets.json".format(DATA_FORMAT))


# --------------------------------------------------------------------------
# Settings + debug logging
# --------------------------------------------------------------------------

def setting_bool(key, default):
    try:
        return ADDON.getSettingBool(key)
    except Exception:  # noqa: BLE001 - setting missing/unreadable: use the default
        return default


def setting_str(key, default):
    try:
        return ADDON.getSettingString(key)
    except Exception:  # noqa: BLE001
        return default


def setting_int(key, default):
    try:
        return ADDON.getSettingInt(key)
    except Exception:  # noqa: BLE001
        return default


def dlog(message):
    """Extra detail in kodi.log, only when 'Write extra detail to the Kodi log' is on."""
    if setting_bool("debug_logging", False):
        xbmc.log("[TV Boxsets] " + message, xbmc.LOGINFO)


# --------------------------------------------------------------------------
# Load / save
# --------------------------------------------------------------------------

def _read_raw():
    """The parsed JSON in the data file, or None if it is missing or unreadable."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def parse(obj):
    """Return the boxsets dict from either file format, or None if it isn't boxsets data."""
    if isinstance(obj, dict) and "format" in obj and "boxsets" in obj:
        boxsets = obj["boxsets"]
        return boxsets if valid(boxsets) else None
    return obj if valid(obj) else None


def file_format():
    """1, 2, ... for the data file on disk; None if there isn't a readable one."""
    raw = _read_raw()
    if raw is None:
        return None
    if isinstance(raw, dict) and "format" in raw and "boxsets" in raw:
        return raw["format"] if isinstance(raw["format"], int) else None
    return 1


def is_newer_format():
    """True if the file was written by a newer add-on than this one."""
    fmt = file_format()
    return isinstance(fmt, int) and fmt > DATA_FORMAT


def _backup_before_migration():
    try:
        if not os.path.exists(PRE_MIGRATION_BACKUP):
            xbmcvfs.mkdirs(BACKUP_DIR)
            shutil.copy2(DATA_FILE, PRE_MIGRATION_BACKUP)
    except OSError:
        pass


def load():
    """The boxsets as a dict. Old (format 1) files are read as they are and upgraded on save."""
    raw = _read_raw()
    if raw is None:
        return {}
    data = parse(raw)
    if data is None:
        return {}
    fmt = file_format()
    if isinstance(fmt, int) and fmt < DATA_FORMAT:
        _backup_before_migration()
    return data


def bump_reload():
    """Tell the home screen rows that boxsets changed, so Kodi reloads them."""
    try:
        xbmcgui.Window(10000).setProperty(skinpatch.RELOAD_PROPERTY, str(time.time()))
    except Exception:  # noqa: BLE001 - never let a display refresh break a save
        pass


def dump_text(data):
    """JSON text for a data file / export, in the current format."""
    return json.dumps({"format": DATA_FORMAT, "saved_by": ADDON.getAddonInfo("version"),
                       "boxsets": data}, indent=2, ensure_ascii=False)


def _auto_backup():
    """Once per day, keep a copy of the file as it was before the first change."""
    if not os.path.isfile(DATA_FILE):
        return
    try:
        xbmcvfs.mkdirs(BACKUP_DIR)
        dest = os.path.join(BACKUP_DIR, "boxsets-{}.json".format(time.strftime("%Y%m%d")))
        if not os.path.exists(dest):
            shutil.copy2(DATA_FILE, dest)
            files = sorted(f for f in os.listdir(BACKUP_DIR)
                           if f.startswith("boxsets-") and f.endswith(".json"))
            keep = max(1, setting_int("keep_backups", KEEP_BACKUPS))
            for old in files[:-keep]:
                os.remove(os.path.join(BACKUP_DIR, old))
    except OSError:
        pass  # a failed backup must never stop a save


def _stamp_modified(data):
    """Give each boxset that changed since the last save a fresh 'modified' time."""
    old = parse(_read_raw()) or {}
    now = int(time.time())
    for bid, bs in data.items():
        before = old.get(bid)
        strip = lambda b: {k: v for k, v in b.items() if k != "modified"}  # noqa: E731
        if before is None or strip(before) != strip(bs):
            bs["modified"] = now


def save(data):
    xbmcvfs.mkdirs(DATA_DIR)
    _auto_backup()
    _stamp_modified(data)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(dump_text(data))
    os.replace(tmp, DATA_FILE)
    bump_reload()


def list_auto_backups():
    """[(path, 'YYYY-MM-DD', boxset_count)], newest first."""
    out = []
    if not os.path.isdir(BACKUP_DIR):
        return out
    for name in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if not (name.startswith("boxsets-") and name.endswith(".json")):
            continue
        path = os.path.join(BACKUP_DIR, name)
        stamp = name[len("boxsets-"):-len(".json")]
        pretty = "{}-{}-{}".format(stamp[:4], stamp[4:6], stamp[6:8]) if len(stamp) == 8 else stamp
        try:
            with open(path, "r", encoding="utf-8") as f:
                boxsets = parse(json.load(f))
        except (OSError, ValueError):
            continue
        if boxsets is None:
            continue
        out.append((path, pretty, len(boxsets)))
    return out


# --------------------------------------------------------------------------
# Helpers shared by the browser, context menus and import tools
# --------------------------------------------------------------------------

def show_key(show):
    """Identity of a boxset entry. Movies are keyed separately from TV shows."""
    prefix = "movie:" if show.get("type") == "movie" else ""
    return "{}{}|{}".format(prefix, show.get("title", "").lower(), show.get("year", 0) or 0)


def valid(data):
    """Is this parsed JSON shaped like a boxsets file?"""
    return isinstance(data, dict) and all(
        isinstance(b, dict) and isinstance(b.get("name"), str)
        and isinstance(b.get("shows", []), list) for b in data.values())


def find_by_name(data, name):
    for bid, bs in data.items():
        if bs["name"].lower() == name.lower():
            return bid
    return None


def new_boxset(data, name):
    bid = uuid.uuid4().hex[:8]
    data[bid] = {"name": name, "shows": [], "poster": "", "fanart": "", "manual_order": False}
    return bid


def add_refs(bs, refs, media="tvshow"):
    """Add entries that aren't already in the boxset. Returns how many were added."""
    have = {show_key(r) for r in bs["shows"]}
    added = 0
    for r in refs:
        ref = {"title": r["title"], "year": r.get("year", 0) or 0}
        if media == "movie" or r.get("type") == "movie":
            ref["type"] = "movie"
        if show_key(ref) not in have:
            bs["shows"].append(ref)
            have.add(show_key(ref))
            added += 1
    return added


ART_KEYS = ("poster", "fanart", "banner", "clearlogo", "landscape")


def merge(current, incoming):
    """Merge `incoming` boxsets into `current` (in place). Returns (new, extended)."""
    created = extended = 0
    for bid, bs in incoming.items():
        existing = find_by_name(current, bs["name"])
        if existing:
            target = current[existing]
            if add_refs(target, bs.get("shows", [])):
                extended += 1
            for key in ART_KEYS:
                if not target.get(key) and bs.get(key):
                    target[key] = bs[key]
            if bs.get("watch") and not target.get("watch"):
                target["watch"] = copy.deepcopy(bs["watch"])
            if bs.get("rules") and not target.get("rules"):
                target["rules"] = copy.deepcopy(bs["rules"])
        else:
            new_id = bid if bid not in current else uuid.uuid4().hex[:8]
            fresh = copy.deepcopy(bs)
            fresh["shows"] = []
            fresh.setdefault("poster", "")
            fresh.setdefault("fanart", "")
            fresh["manual_order"] = bool(bs.get("manual_order"))
            current[new_id] = fresh
            add_refs(fresh, bs.get("shows", []))
            created += 1
    return created, extended
