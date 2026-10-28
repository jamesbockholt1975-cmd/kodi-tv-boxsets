# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Library lookups shared by the add-on and its right-click (context menu) scripts."""

import json

import xbmc

import rules
import store
from store import show_key

TV_PROPS = ["title", "year", "art", "plot", "genre", "studio", "tag",
            "episode", "watchedepisodes", "uniqueid", "rating", "dateadded"]
MOVIE_PROPS = ["title", "year", "art", "plot", "genre", "studio", "tag", "playcount", "uniqueid", "rating", "dateadded"]
# Everything Kodi's own information page shows. Fetched one item at a time for the items on screen
# (cast lists for a whole library would be far too heavy).
TV_DETAIL = ["title", "originaltitle", "sorttitle", "year", "premiered", "plot", "genre", "studio", "mpaa",
             "cast", "rating", "ratings", "votes", "userrating", "runtime", "imdbnumber", "uniqueid",
             "playcount", "dateadded", "lastplayed", "episode", "watchedepisodes", "season", "tag", "art"]
MOVIE_DETAIL = ["title", "originaltitle", "sorttitle", "year", "premiered", "plot", "plotoutline", "tagline",
                "genre", "studio", "mpaa", "cast", "director", "writer", "country", "rating", "ratings", "votes",
                "userrating", "runtime", "imdbnumber", "uniqueid", "trailer", "set", "playcount", "dateadded",
                "lastplayed", "tag", "art", "top250"]
# Enough to match titles and evaluate smart rules, without artwork and plots (used for badges).
LIGHT_PROPS = ["title", "year", "genre", "studio", "tag", "rating", "dateadded"]
LIGHT_TV = LIGHT_PROPS + ["episode", "watchedepisodes"]  # what smart rules (unwatched) need
LIGHT_MOVIE = LIGHT_PROPS + ["playcount"]


def jsonrpc(method, params=None):
    req = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        req["params"] = params
    return json.loads(xbmc.executeJSONRPC(json.dumps(req)))


def full_details(media, item):
    """The library item with every field the information page shows (the item itself if Kodi can't say)."""
    if media == "movie":
        resp = jsonrpc("VideoLibrary.GetMovieDetails", {"movieid": item["movieid"], "properties": MOVIE_DETAIL})
        extra = resp.get("result", {}).get("moviedetails")
    else:
        resp = jsonrpc("VideoLibrary.GetTVShowDetails", {"tvshowid": item["tvshowid"], "properties": TV_DETAIL})
        extra = resp.get("result", {}).get("tvshowdetails")
    return dict(item, **extra) if extra else item


def media_of(ref):
    return "movie" if ref.get("type") == "movie" else "tvshow"


def ref_for(item, media):
    """A boxset entry for a library item."""
    ref = {"title": item["title"], "year": item.get("year", 0) or 0}
    if media == "movie":
        ref["type"] = "movie"
    return ref


class Library:
    """Snapshot of the library, with forgiving lookups.

    TV shows are loaded straight away. Movies are only fetched the first time something
    needs them, so people who only use TV boxsets never pay for a big movie query.
    """

    def __init__(self, light=False):
        self._movie_props = LIGHT_MOVIE if light else MOVIE_PROPS
        resp = jsonrpc("VideoLibrary.GetTVShows", {"properties": LIGHT_TV if light else TV_PROPS})
        self.shows = resp.get("result", {}).get("tvshows", [])
        self._movies = None
        self._tv_index = None
        self._movie_index = None

    @property
    def movies(self):
        if self._movies is None:
            resp = jsonrpc("VideoLibrary.GetMovies", {"properties": self._movie_props})
            self._movies = resp.get("result", {}).get("movies", [])
        return self._movies

    @staticmethod
    def _index(items, media):
        by_key, by_title = {}, {}
        for item in items:
            by_key[show_key(dict(item, type="movie") if media == "movie" else item)] = item
            by_title.setdefault(item["title"].lower(), []).append(item)
        return by_key, by_title

    def find(self, ref):
        """Exact title+year match, else a unique title match (years change on refresh)."""
        if media_of(ref) == "movie":
            if self._movie_index is None:
                self._movie_index = self._index(self.movies, "movie")
            by_key, by_title = self._movie_index
        else:
            if self._tv_index is None:
                self._tv_index = self._index(self.shows, "tvshow")
            by_key, by_title = self._tv_index
        item = by_key.get(show_key(ref))
        if item:
            return item
        candidates = by_title.get(ref.get("title", "").lower(), [])
        return candidates[0] if len(candidates) == 1 else None


def smart_matches(bs, lib):
    """[(media, library_item)] that the boxset's smart rules select right now."""
    rule_set = bs.get("rules")
    if not rules.has_filters(rule_set):
        return []
    kind = rules.media(rule_set)
    found = []
    if kind in ("tv", "both"):
        found += [("tvshow", s) for s in lib.shows if rules.matches(rule_set, s)]
    if kind in ("movie", "both"):
        found += [("movie", m) for m in lib.movies if rules.matches(rule_set, m)]
    return found


def ordered_entries(bs, lib):
    """[(ref, library_item_or_None)] in display order: saved entries plus smart matches.

    Order: A-Z by default. With a manual order, the saved `order` list decides (anything
    not in it goes last, A-Z). Older boxsets that were ordered before `order` existed keep
    working: their saved entries come first in saved order, then smart matches A-Z.
    """
    manual = [(r, lib.find(r)) for r in bs["shows"]]
    have = {show_key(r) for r in bs["shows"]}
    excluded = {show_key(r) for r in bs.get("excluded", [])}
    smart = []
    for media, item in smart_matches(bs, lib):
        ref = ref_for(item, media)
        key = show_key(ref)
        if key in have or key in excluded:
            continue
        have.add(key)
        smart.append((ref, item))
    by_title = lambda e: e[0]["title"].lower()  # noqa: E731
    if bs.get("manual_order") and bs.get("order"):
        pos = {show_key(r): i for i, r in enumerate(bs["order"])}
        return sorted(manual + smart, key=lambda e: (pos.get(show_key(e[0]), len(pos)), by_title(e)))
    if bs.get("manual_order"):
        return manual + sorted(smart, key=by_title)
    return sorted(manual + smart, key=by_title)


def item_stats(ref, item):
    """(total, watched): episodes for a TV show, 1 for a movie."""
    if not item:
        return 0, 0
    if media_of(ref) == "movie":
        return 1, 1 if (item.get("playcount") or 0) > 0 else 0
    return item.get("episode", 0) or 0, item.get("watchedepisodes", 0) or 0


def is_member(bs, ref, item=None):
    """Is this library item in the boxset (saved entry, or a smart match that isn't excluded)?"""
    key = show_key(ref)
    if any(show_key(r) == key for r in bs["shows"]):
        return True
    rule_set = bs.get("rules")
    if item and rules.has_filters(rule_set) and key not in {show_key(r) for r in bs.get("excluded", [])}:
        wanted = rules.media(rule_set)
        if (media_of(ref) == "movie" and wanted in ("movie", "both")) or (
                media_of(ref) == "tvshow" and wanted in ("tv", "both")):
            return rules.matches(rule_set, item)
    return False


def set_member(bs, ref, item, want):
    """Put the item in (want=True) or take it out of the boxset, whichever kind it is."""
    key = show_key(ref)
    if want:
        bs["excluded"] = [r for r in bs.get("excluded", []) if show_key(r) != key]
        if not bs["excluded"]:
            bs.pop("excluded")
        if not is_member(bs, ref, item):
            store.add_refs(bs, [ref])
    else:
        bs["shows"] = [r for r in bs["shows"] if show_key(r) != key]
        if is_member(bs, ref, item):  # still a smart match: keep it out explicitly
            bs.setdefault("excluded", []).append(dict(ref))


def boxset_names(data, lib):
    """{(media, library id): [boxset names]} for every library item that is in a boxset."""
    names = {}
    for bs in data.values():
        for ref, item in ordered_entries(bs, lib):
            if item:
                key = ("movie", item["movieid"]) if media_of(ref) == "movie" else ("tvshow", item["tvshowid"])
                names.setdefault(key, []).append(bs["name"])
    return names


def boxset_members(data, lib):
    """{(media, library id)} of every library item that is in at least one boxset."""
    return set(boxset_names(data, lib))
