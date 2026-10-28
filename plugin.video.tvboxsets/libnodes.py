# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Put the boxsets into Kodi's own library menu, so any skin can show them.

Kodi lets you add "library nodes": small XML files that become entries under Videos. This writes a
"TV Boxsets" folder with one entry per boxset and media type, each a filter on the boxset's Kodi tag
(see tagsync.py: "Boxset: Name"). Skins with a plain Videos menu then list your boxsets with no skin
changes. Only the add-on's own `tvboxsets` folder is ever written or removed.

Kodi uses a custom library folder *instead of* its built-in one, so if you have none yet the built-in
nodes are copied first and left exactly as they were.
"""

import os
import shutil
from xml.sax.saxutils import escape

import xbmcgui
import xbmcvfs

import store
import tagsync
from rules import media as rules_media

FOLDER = "tvboxsets"
PROFILE_LIB = "special://profile/library/"
SYSTEM_LIB = "special://xbmc/system/library/"


def _path(base):
    return xbmcvfs.translatePath(base)


def folder_path():
    return os.path.join(_path(PROFILE_LIB), "video", FOLDER)


def _ensure_custom_tree():
    """Copy Kodi's built-in nodes to the profile if there is no custom set yet. False if impossible."""
    for sub in ("video", "video_flat"):
        dest = os.path.join(_path(PROFILE_LIB), sub)
        if os.path.isdir(dest):
            continue
        src = os.path.join(_path(SYSTEM_LIB), sub)
        if not os.path.isdir(src):
            return sub == "video_flat"  # video_flat is optional; video is not
        shutil.copytree(src, dest)
    return os.path.isdir(os.path.join(_path(PROFILE_LIB), "video"))


def kinds(bs):
    """Which library node types a boxset needs: tvshows and/or movies."""
    if bs.get("rules"):
        value = rules_media(bs["rules"])
        return {"tv": ["tvshows"], "movie": ["movies"]}.get(value, ["tvshows", "movies"])
    out = []
    refs = bs.get("shows", [])
    if any(r.get("type") != "movie" for r in refs):
        out.append("tvshows")
    if any(r.get("type") == "movie" for r in refs):
        out.append("movies")
    return out


def _node(order, label, content, tag):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'
            '<node order="{}" type="filter">\n'
            '  <label>{}</label>\n'
            '  <content>{}</content>\n'
            '  <match>all</match>\n'
            '  <icon>{}</icon>\n'
            '  <rule field="tag" operator="is"><value>{}</value></rule>\n'
            '</node>\n').format(order, escape(label), content, "DefaultTVShows.png" if content == "tvshows"
                                else "DefaultMovies.png", escape(tag))


def _index():
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'
            '<node order="20" visible="Library.HasContent(Movies) | Library.HasContent(TVShows)">\n'
            '  <label>TV Boxsets</label>\n'
            '  <icon>DefaultSets.png</icon>\n'
            '</node>\n')


def build():
    """{file name: text} for the current boxsets."""
    prefix = tagsync.tag_prefix()
    files = {"index.xml": _index()}
    data = store.load()
    order = 0
    for bid, bs in sorted(data.items(), key=lambda kv: kv[1]["name"].lower()):
        types = kinds(bs)
        for content in types:
            order += 1
            label = bs["name"] if len(types) == 1 else "{} ({})".format(
                bs["name"], "TV shows" if content == "tvshows" else "Movies")
            files["boxset-{}-{}.xml".format(bid, content)] = _node(order, label, content, prefix + bs["name"])
    return files


def write():
    """Make the folder match the boxsets. Returns the number of entries (None if it could not be done)."""
    if not tagsync.tag_prefix():
        return None
    if not _ensure_custom_tree():
        return None
    folder = folder_path()
    files = build()
    os.makedirs(folder, exist_ok=True)
    for name in os.listdir(folder):
        if name not in files and name.endswith(".xml"):
            os.remove(os.path.join(folder, name))
    for name, text in files.items():
        target = os.path.join(folder, name)
        try:
            with open(target, encoding="utf-8") as handle:
                if handle.read() == text:
                    continue
        except OSError:
            pass
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text)
    return len(files) - 1


def remove():
    folder = folder_path()
    if os.path.isdir(folder):
        shutil.rmtree(folder)
        return True
    return False


def enable():
    """Boxsets menu > Add the boxsets to Kodi's library menu."""
    if not tagsync.tag_prefix():
        xbmcgui.Dialog().ok("TV Boxsets", "Set a tag prefix in the add-on settings first: the library entries "
                            "find your boxsets by their Kodi tags.")
        return
    if not xbmcgui.Dialog().yesno(
            "Add boxsets to Kodi's library menu",
            "This adds a 'TV Boxsets' folder under Videos > Library in any skin, with one entry per boxset.\n\n"
            "It uses the boxset tags (they will be written now) and, if you have no custom library folder yet, "
            "copies Kodi's built-in library menu into your profile first (nothing in it is changed). "
            "Restart Kodi afterwards. Continue?"):
        return
    tagsync.sync(quiet=True)
    n = write()
    if n is None:
        xbmcgui.Dialog().ok("TV Boxsets", "Couldn't write the library entries (Kodi's built-in library "
                            "folder was not found). Nothing was changed.")
        return
    store.ADDON.setSettingBool("library_nodes", True)
    xbmcgui.Dialog().ok("TV Boxsets", "Added {} boxset entries.\n\nRestart Kodi once; then look under Videos > "
                        "Library > TV Boxsets in your skin. They stay up to date by themselves.".format(n))


def disable():
    """Boxsets menu > Remove the boxsets from Kodi's library menu."""
    if not xbmcgui.Dialog().yesno("Remove library entries",
                                  "Remove the 'TV Boxsets' folder from Kodi's library menu? Your boxsets and "
                                  "tags are not touched."):
        return
    store.ADDON.setSettingBool("library_nodes", False)
    gone = remove()
    xbmcgui.Dialog().notification("TV Boxsets", "Removed the library entries" if gone else "There was nothing to remove",
                                  xbmcgui.NOTIFICATION_INFO, 3000)
