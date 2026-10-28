# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Helpers for the right-click scripts used while browsing inside a boxset.

Each script just works out which boxset/item is highlighted and hands the real work to the
add-on through a RunPlugin call, so there is only one copy of the logic (in main.py).
"""

from urllib.parse import parse_qs, urlencode, urlparse

import xbmc


def current_bid():
    """The boxset being browsed, from the folder address."""
    path = xbmc.getInfoLabel("Container.FolderPath")
    return parse_qs(urlparse(path).query).get("bid", [""])[0]


def run_plugin(**params):
    xbmc.executebuiltin("RunPlugin(plugin://plugin.video.tvboxsets/?{})".format(urlencode(params)))


def in_watch_order():
    return "action=watch" in xbmc.getInfoLabel("Container.FolderPath")


def current_key():
    return xbmc.getInfoLabel("ListItem.Property(boxset_key)")


def current_title():
    """The highlighted item's real title (movies carry a '[Movie]' tag in the title the skin draws)."""
    return xbmc.getInfoLabel("ListItem.Property(boxset_title)") or xbmc.getInfoLabel("ListItem.Title")


def move(delta):
    if in_watch_order():
        return run_plugin(action="watch_move", bid=current_bid(), key=current_key(), delta=delta)
    run_plugin(action="move", bid=current_bid(),
               title=current_title(),
               year=xbmc.getInfoLabel("ListItem.Year") or "0",
               media="movie" if xbmc.getInfoLabel("ListItem.DBType") == "movie" else "tvshow",
               delta=delta)


def place():
    if in_watch_order():
        return run_plugin(action="watch_place", bid=current_bid(), key=current_key())
    run_plugin(action="place", bid=current_bid(),
               title=current_title(),
               year=xbmc.getInfoLabel("ListItem.Year") or "0",
               media="movie" if xbmc.getInfoLabel("ListItem.DBType") == "movie" else "tvshow")
