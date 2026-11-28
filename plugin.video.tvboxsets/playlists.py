# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Kodi's own video smart playlists (.xsp files), used as the source of a boxset.

Only the list of playlists and their names and types are read here. What a playlist matches is worked out by
Kodi itself (JSON-RPC Files.GetDirectory, see library.playlist_refs), so its rules, sort order and limit are
always applied exactly as Kodi applies them.
"""

import os
import xml.etree.ElementTree as ET

import xbmcvfs

VIDEO_DIR = "special://profile/playlists/video/"
# Playlist types a boxset can use. Episode playlists add the shows those episodes belong to.
KINDS = {"tvshows": "TV shows", "movies": "movies", "episodes": "episodes, as their shows"}


def read(path):
    """{"name", "type"} of a smart playlist file, or None if it isn't one."""
    try:
        with open(path, "rb") as handle:
            root = ET.fromstring(handle.read())
    except (OSError, ET.ParseError):
        return None
    if root.tag != "smartplaylist":
        return None
    stem = os.path.splitext(os.path.basename(path))[0]
    order = root.find("order")
    return {"name": (root.findtext("name") or "").strip() or stem, "type": (root.get("type") or "").strip().lower(),
            "order": ((order.text if order is not None else "") or "").strip().lower(),
            "direction": "descending" if order is not None and (order.get("direction") or "").lower() == "descending"
            else "ascending"}


# Sort methods Kodi's JSON-RPC accepts (List.Sort). A smart playlist's <order> uses the same names.
JSONRPC_SORTS = {"label", "date", "size", "file", "path", "drivetype", "title", "track", "time", "artist", "album",
                 "albumtype", "genre", "country", "year", "rating", "userrating", "votes", "top250", "programcount",
                 "playlist", "episode", "season", "totalepisodes", "watchedepisodes", "tvshowstatus", "tvshowtitle",
                 "sorttitle", "productioncode", "mpaa", "studio", "dateadded", "lastplayed", "playcount", "listeners",
                 "bitrate", "random", "totaldiscs", "originaldate", "bpm", "originaltitle"}


def sort_of(path):
    """The playlist's own order as a JSON-RPC sort, or None (no order, unknown, or unreadable file)."""
    info = read(xbmcvfs.translatePath(path))
    if not info or info["order"] not in JSONRPC_SORTS:
        return None
    return {"method": info["order"], "order": info["direction"]}


def available():
    """[{"path", "name", "type"}] for the video smart playlists a boxset can use, A to Z."""
    folder = xbmcvfs.translatePath(VIDEO_DIR)
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    found = []
    for name in names:
        if not name.lower().endswith(".xsp"):
            continue
        info = read(os.path.join(folder, name))
        if info and info["type"] in KINDS:
            found.append(dict(info, path=VIDEO_DIR + name))
    return sorted(found, key=lambda p: p["name"].lower())


def label(playlist):
    return "{}  ({})".format(playlist["name"], KINDS.get(playlist.get("type"), playlist.get("type") or "?"))


def node_kinds(playlist):
    """Which library node types a playlist's items are."""
    return ["movies"] if playlist.get("type") == "movies" else ["tvshows"]
