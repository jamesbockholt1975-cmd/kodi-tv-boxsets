# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Badge pictures: how the skin knows which library items are in a boxset, and which.

A skin can't look up "is this item in a boxset?" for every poster on screen, but it can show an
image whose file name contains the item's library id. For every item that is in a boxset there are
two small pictures in the add-on's userdata `badges` folder:

    r<N>/tvshow_12.png        the round badge icon (used in list rows)
    r<N>/tvshow_12_name.png   a pill with the icon and the boxset name (used on posters)

Items that are not in a boxset simply have no file, so the skin shows nothing for them.

Why a numbered folder? Kodi keeps a picture it has already drawn for as long as the path stays the
same, even if the file is overwritten. So every change builds a complete new folder `r<N+1>`, and the
skin's picture path includes N (read from the Home-window property `tvboxsets_badge_rev`). When the
number changes, every visible badge is reloaded at once, so labels never go stale. Old folders are
removed once newer ones exist. Identical pictures are hard-linked (or copied) from one stored copy.
"""

import hashlib
import json
import os
import re
import shutil

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

import labelimg
import library
import skinpatch
import store

STATE_FILE = "state.json"
LABEL_CACHE = "_labels"       # drawn labels, kept between updates so each is only drawn once
ICON_COPY = "_icon.png"
LOOK = "1"                    # bump when the label's appearance changes, so every label is redrawn
KEEP_REVISIONS = 2            # the current folder and the one before it
REV_DIR = re.compile(r"^r(\d+)$")
LEGACY = re.compile(r"^(tvshow|movie)_(\d+)(_name)?\.png$")


def file_name(media, dbid, label=False):
    return "{}_{}{}.png".format(media, dbid, "_name" if label else "")


def _state(badge_dir):
    try:
        with open(os.path.join(badge_dir, STATE_FILE), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(badge_dir, state):
    with open(os.path.join(badge_dir, STATE_FILE), "w", encoding="utf-8") as f:
        json.dump(state, f)


def current_rev(badge_dir=None):
    return int(_state(badge_dir or store.BADGE_DIR).get("rev", 0) or 0)


def publish_rev(rev):
    """Tell the skin which folder to read, so every badge on screen reloads."""
    try:
        xbmcgui.Window(10000).setProperty(skinpatch.BADGE_REV_PROPERTY, str(rev))
    except Exception:  # noqa: BLE001 - a display refresh must never break a sync
        pass


def _link_or_copy(src, dst):
    try:
        os.link(src, dst)
    except (OSError, NotImplementedError, AttributeError):
        shutil.copyfile(src, dst)


def desired_files(wanted, atlas=None, show_names=True):
    """{file name: label text, or None for the plain icon} for the items that should have badges.

    `wanted` is {(media, id): [boxset names]}; a plain set of (media, id) also works (icon only).
    """
    if not isinstance(wanted, dict):
        wanted = {key: [] for key in wanted}
    desired = {}
    for (media, dbid), names in wanted.items():
        text = labelimg.label_text(names) if (show_names and atlas and names) else None
        desired[file_name(media, dbid)] = None
        desired[file_name(media, dbid, True)] = text
    return desired


def _signature(desired):
    return hashlib.sha1(json.dumps([LOOK, sorted(desired.items(), key=lambda kv: kv[0])]).encode("utf-8")).hexdigest()


def sync_files(wanted, badge_dir, on_src, atlas=None, show_names=True):
    """Make the badge folder match `wanted`. Returns (revision, changed, item_count)."""
    os.makedirs(badge_dir, exist_ok=True)
    desired = desired_files(wanted, atlas, show_names)
    items = len(desired) // 2
    sig = _signature(desired)
    state = _state(badge_dir)
    rev = int(state.get("rev", 0) or 0)
    if state.get("sig") == sig and os.path.isdir(os.path.join(badge_dir, "r{}".format(rev))):
        return rev, False, items

    # Never reuse a folder number: a reused path would let Kodi keep showing the old picture.
    on_disk = [int(m.group(1)) for m in (REV_DIR.match(n) for n in os.listdir(badge_dir)) if m]
    rev = max([rev] + on_disk) + 1
    new_dir = os.path.join(badge_dir, "r{}".format(rev))
    shutil.rmtree(new_dir, ignore_errors=True)
    os.makedirs(new_dir)
    cache_dir = os.path.join(badge_dir, LABEL_CACHE)
    os.makedirs(cache_dir, exist_ok=True)
    icon_copy = os.path.join(badge_dir, ICON_COPY)
    if not os.path.exists(icon_copy) or os.path.getsize(icon_copy) != os.path.getsize(on_src):
        shutil.copyfile(on_src, icon_copy)

    used_labels = set()
    for name, text in sorted(desired.items()):
        target = os.path.join(new_dir, name)
        if text is None:
            _link_or_copy(icon_copy, target)
            continue
        key = hashlib.sha1("{}|{}".format(LOOK, text).encode("utf-8")).hexdigest() + ".png"
        used_labels.add(key)
        cached = os.path.join(cache_dir, key)
        if not os.path.exists(cached):
            with open(cached, "wb") as f:
                f.write(labelimg.render_label(atlas, text)[0])
        _link_or_copy(cached, target)

    _save_state(badge_dir, {"rev": rev, "sig": sig, "items": items})
    _cleanup(badge_dir, rev, used_labels)
    return rev, True, items


def _cleanup(badge_dir, current, used_labels):
    """Remove folders older than the previous revision, unused cached labels and pre-0.11.1 files."""
    for name in os.listdir(badge_dir):
        path = os.path.join(badge_dir, name)
        m = REV_DIR.match(name)
        if m and int(m.group(1)) <= current - KEEP_REVISIONS:
            shutil.rmtree(path, ignore_errors=True)
        elif LEGACY.match(name):  # flat files from earlier versions: stale, and no longer read
            try:
                os.remove(path)
            except OSError:
                pass
    cache_dir = os.path.join(badge_dir, LABEL_CACHE)
    for name in os.listdir(cache_dir):
        if name not in used_labels:
            try:
                os.remove(os.path.join(cache_dir, name))
            except OSError:
                pass


def _paths():
    base = xbmcvfs.translatePath(xbmcaddon.Addon("plugin.video.tvboxsets").getAddonInfo("path"))
    res = os.path.join(base, "resources")
    return os.path.join(res, "badge.png"), os.path.join(res, "glyphs.json.z")


def sync_badges():
    """Bring the badge pictures in line with the boxsets and library.

    Returns (revision, changed, item_count), or None if it failed. Always (re)publishes the
    revision so the skin is reading the right folder.
    """
    try:
        on_src, glyphs = _paths()
        wanted = {}
        if store.setting_bool("show_badges", True):
            data = store.load()
            if data:
                wanted = library.boxset_names(data, library.Library(light=True))
        show_names = store.setting_bool("show_names", True) and os.path.exists(glyphs)
        atlas = labelimg.load_atlas(glyphs) if (show_names and wanted) else None
        result = sync_files(wanted, store.BADGE_DIR, on_src, atlas, show_names)
        publish_rev(result[0])
        store.dlog("badges: revision {} ({}), {} item(s)".format(
            result[0], "rebuilt" if result[1] else "unchanged", result[2]))
        return result
    except Exception as exc:  # noqa: BLE001 - badges are cosmetic; never break the add-on
        xbmc.log("[TV Boxsets] badge sync failed: {!r}".format(exc), xbmc.LOGERROR)
        return None
