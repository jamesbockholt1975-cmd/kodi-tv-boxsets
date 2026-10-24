# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Right-click a library TV show or movie > Boxsets...

Shows every boxset with a tick against the ones the item is already in. Tick or untick to
add it or take it out, or choose "+ New boxset..." to start another.
"""

import xbmc
import xbmcgui

import store
from library import is_member, jsonrpc, ref_for, set_member
from store import load, save

NEW = "[B]+ New boxset...[/B]"


def notify(message):
    xbmcgui.Dialog().notification("TV Boxsets", message, xbmcgui.NOTIFICATION_INFO, 3000)


def focused_item():
    """(ref, item): the highlighted library item as a boxset entry plus its library details."""
    try:
        dbid = int(xbmc.getInfoLabel("ListItem.DBID"))
    except ValueError:
        return None, None
    props = ["title", "year", "genre", "studio", "tag"]
    if xbmc.getInfoLabel("ListItem.DBType") == "movie":
        details = jsonrpc("VideoLibrary.GetMovieDetails", {"movieid": dbid, "properties": props}
                          ).get("result", {}).get("moviedetails")
        media = "movie"
    else:
        details = jsonrpc("VideoLibrary.GetTVShowDetails", {"tvshowid": dbid, "properties": props}
                          ).get("result", {}).get("tvshowdetails")
        media = "tvshow"
    if not details:
        return None, None
    return ref_for(details, media), details


def main():
    ref, item = focused_item()
    if not ref:
        notify("Couldn't read this item from the library")
        return

    data = load()
    ids = sorted(data, key=lambda b: data[b]["name"].lower())
    labels = ["{}{}".format(data[b]["name"], "  (smart)" if data[b].get("rules") else "") for b in ids]
    labels.append(NEW)
    preselect = [i for i, b in enumerate(ids) if is_member(data[b], ref, item)]
    chosen = xbmcgui.Dialog().multiselect("Boxsets for '{}'".format(ref["title"]), labels,
                                          preselect=preselect)
    if chosen is None:  # cancelled
        return

    added, removed = [], []
    for i, bid in enumerate(ids):
        want, have = i in chosen, i in preselect
        if want != have:
            set_member(data[bid], ref, item, want)
            (added if want else removed).append(data[bid]["name"])

    if len(ids) in chosen:  # "+ New boxset..."
        name = xbmcgui.Dialog().input("Name of new boxset", type=xbmcgui.INPUT_ALPHANUM).strip()
        if name:
            bid = store.find_by_name(data, name) or store.new_boxset(data, name)
            if not is_member(data[bid], ref, item):
                set_member(data[bid], ref, item, True)
                added.append(data[bid]["name"])

    if not added and not removed:
        return
    save(data)
    parts = []
    if added:
        parts.append("added to " + ", ".join(added))
    if removed:
        parts.append("removed from " + ", ".join(removed))
    notify("'{}': {}".format(ref["title"], "; ".join(parts)))


if __name__ == "__main__":
    main()
