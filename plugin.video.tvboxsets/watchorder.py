# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""A boxset's watch order: seasons of its shows and its movies, in a sequence you choose.

The boxset's ordinary order lists whole shows. The watch order lets one show come back later,
for example Show A season 1, Show B season 1, a film, Show A season 2. It is kept in the boxset
as `watch`, a list of entries:

    {"title": "Show A", "year": 2010, "season": 2}      one whole season of a TV show
    {"title": "Show A", "year": 2010, "season": 2,
     "first": 8, "last": 9}                              episodes 8-9 of that season (a crossover)
    {"title": "Film",   "year": 2012, "type": "movie"}  a movie

`first` / `last` are optional: a missing `first` means "from the start of the season" and a missing
`last` "to the end", so a season split around a crossover is three entries (1-7, 8-9, 10-).

Only items that are still in the boxset are shown, so removing a show from the boxset takes its
seasons out of the watch order too.
"""

from library import jsonrpc, media_of, ordered_entries
from store import show_key


def base_ref(entry):
    ref = {"title": entry["title"], "year": entry.get("year", 0) or 0}
    if entry.get("type") == "movie":
        ref["type"] = "movie"
    return ref


def entry_range(entry):
    """(first, last) of a ranged season entry; (None, None) for a whole season."""
    return entry.get("first"), entry.get("last")


def is_ranged(entry):
    return entry.get("type") != "movie" and entry_range(entry) != (None, None)


def entry_key(entry):
    if entry.get("type") == "movie":
        return show_key(entry)
    key = "season:{}|{}|{}".format(entry.get("title", "").lower(), entry.get("year", 0) or 0,
                                   entry.get("season", 1))
    if is_ranged(entry):
        first, last = entry_range(entry)
        key += "|{}-{}".format("" if first is None else first, "" if last is None else last)
    return key


def season_id(entry):
    """Which season of which show an entry belongs to."""
    return (entry.get("title", "").lower(), entry.get("year", 0) or 0, entry.get("season", 1))


def seasons_with_entries(entries):
    """Seasons that already have an entry (whole, or any part of it)."""
    return {season_id(e) for e in entries if e.get("type") != "movie"}


def season_name(number):
    return "Specials" if number == 0 else "Season {}".format(number)


def range_text(entry):
    """'S3E8', 'S3E8-E9', 'S3E10+' or 'S3 up to E7' for a ranged season entry."""
    n = entry.get("season", 1)
    first, last = entry_range(entry)
    if first is None:
        return "S{} up to E{}".format(n, last)
    if last is None:
        return "S{}E{}+".format(n, first)
    return "S{}E{}".format(n, first) if first == last else "S{}E{}-E{}".format(n, first, last)


def entry_label(entry):
    if entry.get("type") == "movie":
        return "{} [Movie]".format(entry["title"])
    if is_ranged(entry):
        return "{} - {}".format(entry["title"], range_text(entry))
    return "{} - {}".format(entry["title"], season_name(entry.get("season", 1)))


def in_range(entry, number):
    first, last = entry_range(entry)
    return (first is None or number >= first) and (last is None or number <= last)


def seasons_of(item):
    """The seasons Kodi knows for a library show, in order."""
    resp = jsonrpc("VideoLibrary.GetSeasons", {
        "tvshowid": item["tvshowid"],
        "properties": ["season", "episode", "watchedepisodes", "art"]})
    seasons = resp.get("result", {}).get("seasons", [])
    return sorted((s for s in seasons if s.get("season", -1) >= 0), key=lambda s: s["season"])


def episodes_of(item, season):
    """Episodes of one season, in order."""
    resp = jsonrpc("VideoLibrary.GetEpisodes", {
        "tvshowid": item["tvshowid"], "season": season,
        "properties": ["season", "episode", "title", "plot", "playcount", "art"]})
    return sorted(resp.get("result", {}).get("episodes", []), key=lambda e: e.get("episode", 0))


def candidates(bs, lib):
    """[(entry, library item, season info or None)] for everything that could go in the order,
    in the boxset's own order (a show's seasons ascending)."""
    found = []
    for ref, item in ordered_entries(bs, lib):
        if not item:
            continue
        if media_of(ref) == "movie":
            found.append((base_ref(ref), item, None))
            continue
        for season in seasons_of(item):
            entry = {"title": ref["title"], "year": ref.get("year", 0) or 0, "season": season["season"]}
            found.append((entry, item, season))
    return found


def resolve(bs, lib):
    """Visible rows of the watch order: [{"entry", "key", "media", "item", "season"}].

    `item` is None when the show/movie is not in the library right now; `season` is None for
    movies, or when that season is not in the library.
    """
    members, by_title = {}, {}
    for ref, item in ordered_entries(bs, lib):
        members[show_key(ref)] = (ref, item)
        by_title.setdefault((media_of(ref), ref["title"].lower()), []).append((ref, item))
    seasons_cache, episodes_cache = {}, {}
    rows = []
    for entry in bs.get("watch", []):
        base = base_ref(entry)
        hit = members.get(show_key(base))
        if hit is None:  # years change when metadata is refreshed: fall back to a unique title
            same = by_title.get((media_of(base), base["title"].lower()), [])
            hit = same[0] if len(same) == 1 else None
        if hit is None:
            continue  # no longer in the boxset
        item = hit[1]
        season = None
        if entry.get("type") != "movie" and item:
            if item["tvshowid"] not in seasons_cache:
                seasons_cache[item["tvshowid"]] = {s["season"]: s for s in seasons_of(item)}
            season = seasons_cache[item["tvshowid"]].get(entry.get("season", 1))
        episodes = None
        if season and is_ranged(entry):
            ck = (item["tvshowid"], entry.get("season", 1))
            if ck not in episodes_cache:
                episodes_cache[ck] = episodes_of(item, ck[1])
            episodes = [e for e in episodes_cache[ck] if in_range(entry, e.get("episode", 0))]
            if not episodes:
                season = None  # nothing of that range in the library: shown as missing
        rows.append({"entry": entry, "key": entry_key(entry),
                     "media": "movie" if entry.get("type") == "movie" else "season",
                     "item": item, "season": season, "episodes": episodes})
    return rows


def add_entries(entries, new):
    """`entries` plus the `new` ones that are not in it yet. Returns (list, how many were added)."""
    have = {entry_key(e) for e in entries}
    out = [dict(e) for e in entries]
    added = 0
    for e in new:
        if entry_key(e) not in have:
            out.append(dict(e))
            have.add(entry_key(e))
            added += 1
    return out, added


def index_of(entries, key):
    return next((i for i, e in enumerate(entries) if entry_key(e) == key), None)


def moved(entries, key, delta):
    """The list with one entry moved up (-1) or down (+1); None if it can't move."""
    idx = index_of(entries, key)
    if idx is None or not 0 <= idx + delta < len(entries):
        return None
    out = [dict(e) for e in entries]
    out.insert(idx + delta, out.pop(idx))
    return out


def placed(entries, key, after):
    """The list with one entry put straight after position `after` of the OTHER entries
    (-1 = first); None if the entry isn't there."""
    idx = index_of(entries, key)
    if idx is None:
        return None
    out = [dict(e) for e in entries]
    entry = out.pop(idx)
    out.insert(max(-1, min(len(out) - 1, after)) + 1, entry)
    return out


def removed(entries, key):
    return [dict(e) for e in entries if entry_key(e) != key]


def runs(numbers):
    """Consecutive episode numbers grouped: [8, 9, 12] -> [(8, 9), (12, 12)]."""
    out = []
    for n in sorted(set(numbers)):
        if out and n == out[-1][1] + 1:
            out[-1] = (out[-1][0], n)
        else:
            out.append((n, n))
    return out


def insert_runs(entries, base, season, spans, last_episode):
    """Put episode ranges (spans) of one season into the order.

    If a whole-season (or larger ranged) entry already covers a span, that entry is split around it,
    in place: 1-7, the new 8-9, then 10 onwards. Otherwise the span goes at the end. `last_episode` is
    the season's last episode number, so a span that runs to the end leaves no empty tail.
    Returns (new list, how many spans were added).
    """
    out = [dict(e) for e in entries]
    added = 0
    for a, b in spans:
        new = {"title": base["title"], "year": base.get("year", 0) or 0, "season": season,
               "first": a, "last": b}
        if entry_key(new) in {entry_key(e) for e in out}:
            continue
        for i, e in enumerate(out):
            if e.get("type") == "movie" or season_id(e) != season_id(new):
                continue
            lo, hi = entry_range(e)
            if not ((lo is None or lo <= a) and (hi is None or hi >= b)):
                continue
            pieces = []
            if (lo is None and a > 1) or (lo is not None and lo < a):
                pieces.append(dict(e, first=lo, last=a - 1))
            pieces.append(new)
            if (hi is None and b < last_episode) or (hi is not None and hi > b):
                pieces.append(dict(e, first=b + 1, last=hi))
            for p in pieces:  # drop empty keys so a plain range stays tidy
                for k in ("first", "last"):
                    if p.get(k) is None:
                        p.pop(k, None)
            out[i:i + 1] = pieces
            break
        else:
            out.append(new)
        added += 1
    return out, added
