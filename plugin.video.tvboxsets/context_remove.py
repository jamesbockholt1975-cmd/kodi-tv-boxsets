# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Context menu item: remove the highlighted item from the boxset being browsed."""

from urllib.parse import urlparse, parse_qs

import xbmc
import xbmcgui

import store
from store import load, save, show_key


def notify(message):
    xbmcgui.Dialog().notification("TV Boxsets", message, xbmcgui.NOTIFICATION_INFO, 3000)


def main():
    import ctxutil
    if ctxutil.in_watch_order():  # in the watch order, Remove takes it out of the order only
        ctxutil.run_plugin(action="watch_remove", bid=ctxutil.current_bid(), key=ctxutil.current_key())
        return
    path = xbmc.getInfoLabel("Container.FolderPath")
    bid = parse_qs(urlparse(path).query).get("bid", [""])[0]
    title = xbmc.getInfoLabel("ListItem.Property(boxset_title)") or xbmc.getInfoLabel("ListItem.Title")
    is_movie = xbmc.getInfoLabel("ListItem.DBType") == "movie"
    try:
        year = int(xbmc.getInfoLabel("ListItem.Year"))
    except ValueError:
        year = 0

    data = load()
    bs = data.get(bid)
    if not bs or not title:
        notify("Couldn't tell which boxset this is")
        return

    ref = {"title": title, "year": year}
    if is_movie:
        ref["type"] = "movie"
    target = show_key(ref)
    same_kind = [r for r in bs["shows"] if (r.get("type") == "movie") == is_movie]
    matches = [r for r in bs["shows"] if show_key(r) == target]
    if not matches:  # fall back to title only, in case the year didn't line up
        matches = [r for r in same_kind if r["title"].lower() == title.lower()]
    smart = bool(bs.get("rules"))
    if not matches and not smart:
        notify("Couldn't find '{}' in this boxset".format(title))
        return

    extra = "\n\nIt matches this smart boxset's rules, so it will be left out from now on." if (
        smart and not matches) else ""
    if not xbmcgui.Dialog().yesno(
            "Remove from boxset",
            "Remove '{}' from '{}'?\n\nIt stays in your library.{}".format(title, bs["name"], extra)):
        return

    if matches:
        bs["shows"].remove(matches[0])
    else:
        excluded = bs.setdefault("excluded", [])
        if target not in {show_key(r) for r in excluded}:
            excluded.append(ref)
    save(data)
    notify("Removed '{}'".format(title))
    xbmc.executebuiltin("Container.Refresh")


if __name__ == "__main__":
    main()
