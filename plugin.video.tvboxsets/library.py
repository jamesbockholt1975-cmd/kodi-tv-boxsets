# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Library lookups shared by the add-on and its right-click (context menu) scripts."""

import json
import re

import xbmc

import playlists
import rules
import store
from store import show_key

TV_PROPS = ["title", "year", "art", "plot", "genre", "studio", "tag",
            "episode", "watchedepisodes", "uniqueid", "rating", "dateadded", "lastplayed", "playcount", "file"]
MOVIE_PROPS = ["title", "year", "art", "plot", "genre", "studio", "tag", "playcount", "uniqueid", "rating", "dateadded",
               "lastplayed", "resume", "file"]
# Everything Kodi's own information page shows. Fetched one item at a time for the items on screen
# (cast lists for a whole library would be far too heavy).
TV_DETAIL = ["title", "originaltitle", "sorttitle", "year", "premiered", "plot", "genre", "studio", "mpaa",
             "cast", "rating", "ratings", "votes", "userrating", "runtime", "imdbnumber", "uniqueid",
             "playcount", "dateadded", "lastplayed", "episode", "watchedepisodes", "season", "tag", "art"]
MOVIE_DETAIL = ["title", "originaltitle", "sorttitle", "year", "premiered", "plot", "plotoutline", "tagline",
                "genre", "studio", "mpaa", "cast", "director", "writer", "country", "rating", "ratings", "votes",
                "userrating", "runtime", "imdbnumber", "uniqueid", "trailer", "set", "playcount", "dateadded",
                "lastplayed", "tag", "art", "top250", "streamdetails", "resume"]
# Enough to match titles and evaluate smart rules, without artwork and plots (used for badges).
LIGHT_PROPS = ["title", "year", "genre", "studio", "tag", "rating", "dateadded", "file"]
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
        self.playlists = {}  # smart playlist path -> what it matched, for the life of this snapshot

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
    """[(media, library_item)] that the boxset's smart rules and its Kodi smart playlist select right now."""
    found = []
    rule_set = bs.get("rules")
    if rules.has_filters(rule_set):
        kind = rules.media(rule_set)
        if kind in ("tv", "both"):
            found += [("tvshow", s) for s in lib.shows if rules.matches(rule_set, s)]
        if kind in ("movie", "both"):
            found += [("movie", m) for m in lib.movies if rules.matches(rule_set, m)]
    if bs.get("playlist"):
        seen = {show_key(ref_for(item, media)) for media, item in found}
        for media, item in playlist_matches(bs, lib):
            key = show_key(ref_for(item, media))
            if key not in seen:
                seen.add(key)
                found.append((media, item))
    return found


def playlist_refs(path, cache=None):
    """[(media, library id, ref)] that a Kodi smart playlist selects right now, or None if Kodi can't read it.

    Kodi evaluates the playlist (its rules, order and limit). Episodes stand for the show they belong to."""
    if cache is not None and path in cache:
        return cache[path]
    params = {"directory": path, "media": "video", "properties": ["title", "year", "tvshowid"]}
    sort = playlists.sort_of(path)
    if sort:
        # Ask for the playlist's order explicitly, sorted the way Kodi's own lists are (ignoring "The" if set).
        setting = jsonrpc("Settings.GetSettingValue", {"setting": "filelists.ignorethewhensorting"}).get("result")
        sort["ignorearticle"] = bool(setting.get("value")) if isinstance(setting, dict) else False
        params["sort"] = sort
    resp = jsonrpc("Files.GetDirectory", params)
    if "result" not in resp or not isinstance(resp["result"], dict):
        out = None
    else:
        out, seen, shows = [], set(), {}
        for entry in resp["result"].get("files") or []:
            kind = entry.get("type")
            if kind in ("movie", "tvshow") and entry.get("id"):
                key = (kind, entry["id"])
                if key in seen:
                    continue
                ref = ref_for(dict(entry, title=entry.get("title") or entry.get("label") or ""), kind)
            elif kind == "episode" and (entry.get("tvshowid") or 0) > 0:
                key = ("tvshow", entry["tvshowid"])
                if key in seen:
                    continue
                if key[1] not in shows:
                    detail = jsonrpc("VideoLibrary.GetTVShowDetails",
                                     {"tvshowid": key[1], "properties": ["title", "year"]})
                    shows[key[1]] = detail.get("result", {}).get("tvshowdetails")
                if not shows[key[1]]:
                    continue
                ref = ref_for(shows[key[1]], "tvshow")
            else:
                continue  # folders (a playlist grouped by genre etc.), music videos, unknown items
            if not ref["title"]:
                continue
            seen.add(key)
            out.append((key[0], key[1], ref))
    if cache is not None:
        cache[path] = out
    return out


def playlist_matches(bs, lib):
    """[(media, library_item)] for the boxset's Kodi smart playlist (empty if it has none or Kodi can't read it)."""
    playlist = bs.get("playlist")
    if not playlist:
        return []
    refs = playlist_refs(playlist["path"], getattr(lib, "playlists", None)) or []
    shows = {s.get("tvshowid"): s for s in lib.shows}
    movies = {m.get("movieid"): m for m in lib.movies} if any(r[0] == "movie" for r in refs) else {}
    found = []
    for media, item_id, ref in refs:
        item = (movies if media == "movie" else shows).get(item_id) or lib.find(ref)
        if item:
            found.append((media, item))
    return found


def ordered_entries(bs, lib):
    """[(ref, library_item_or_None)] in display order: saved entries plus smart matches.

    Order: A-Z by default (a boxset linked to a Kodi smart playlist: the playlist's own order), or by release
    year or A-Z if the boxset's `sort` says so. With a manual order, the saved `order` list decides (anything
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
    entries = manual + smart
    mode = bs.get("sort") or ("playlist" if bs.get("playlist") else None)
    if mode == "playlist":  # the Kodi smart playlist's own order; anything else (added by hand) after it, A-Z
        pos = {}
        for media, item in playlist_matches(bs, lib):
            pos.setdefault(show_key(ref_for(item, media)), len(pos))
        listed = [e for e in entries if e[1] and show_key(ref_for(e[1], media_of(e[0]))) in pos]
        listed.sort(key=lambda e: pos[show_key(ref_for(e[1], media_of(e[0])))])
        keys = {id(e) for e in listed}
        return listed + sorted([e for e in entries if id(e) not in keys], key=by_title)
    if mode == "file":  # file (or show folder) name, numbers in order: "MCU9-" before "MCU10-"; no file name last
        def file_key(e):
            name = re.split(r"[\\/]", ((e[1] or {}).get("file") or "").rstrip("\\/"))[-1].lower()
            return [(0, int(part), "") if part.isdigit() else (1, 0, part) for part in re.split(r"(\d+)", name) if part]
        named = sorted([e for e in entries if file_key(e)], key=lambda e: (file_key(e), by_title(e)))
        return named + sorted([e for e in entries if not file_key(e)], key=by_title)
    if mode in ("year", "year_desc"):  # release year; items with no year go last
        def year_of(e):
            return int((e[1] or {}).get("year") or e[0].get("year") or 0)
        sign = -1 if mode == "year_desc" else 1
        dated = sorted([e for e in entries if year_of(e)], key=lambda e: (sign * year_of(e), by_title(e)))
        return dated + sorted([e for e in entries if not year_of(e)], key=by_title)
    return sorted(entries, key=by_title)


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
    if key in {show_key(r) for r in bs.get("excluded", [])}:
        return False
    if bs.get("playlist") and any(show_key(r) == key for _, _, r in playlist_refs(bs["playlist"]["path"]) or []):
        return True
    rule_set = bs.get("rules")
    if item and rules.has_filters(rule_set):
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
