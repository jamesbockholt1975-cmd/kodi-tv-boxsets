# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Share a watch order as a small file, and read one made by someone else.

The file is plain JSON: a name and a list of entries (a season, a run of episodes, or a movie). Each entry
carries the title and year plus the show's or movie's ids (IMDb / TMDB / TVDB) when Kodi knows them, so
the order can be matched in another person's library even when titles or years are spelled differently.
Nothing else about your library (paths, watched state, artwork) is in the file.
"""

FORMAT = "tvboxsets-watchorder"
VERSION = 1
MAX_ENTRIES = 2000


def ids_of(item):
    return {str(k): str(v) for k, v in ((item or {}).get("uniqueid") or {}).items() if v}


def build(name, rows, created_by=""):
    """The file contents for the visible rows of a watch order (see watchorder.resolve)."""
    entries = []
    for row in rows:
        entry = {k: row["entry"][k] for k in ("title", "year", "type", "season", "first", "last")
                 if row["entry"].get(k) not in (None, "")}
        ids = ids_of(row.get("item"))
        if ids:
            entry["ids"] = ids
        entries.append(entry)
    return {"format": FORMAT, "version": VERSION, "name": name, "created_by": created_by, "entries": entries}


def _int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse(obj):
    """Check a loaded file. Returns {"name", "entries"} (cleaned), or None if it is not a watch order."""
    if not isinstance(obj, dict) or obj.get("format") != FORMAT:
        return None
    if (_int(obj.get("version"), 0) or 0) > VERSION:
        return None  # made by a newer version: don't guess
    raw = obj.get("entries")
    if not isinstance(raw, list) or not raw:
        return None
    entries = []
    for e in raw[:MAX_ENTRIES]:
        if not isinstance(e, dict) or not isinstance(e.get("title"), str) or not e["title"].strip():
            continue
        clean = {"title": e["title"].strip(), "year": _int(e.get("year"), 0) or 0}
        if e.get("type") == "movie":
            clean["type"] = "movie"
        else:
            clean["season"] = _int(e.get("season"), 1)
            for k in ("first", "last"):
                if _int(e.get(k)) is not None:
                    clean[k] = _int(e[k])
        ids = e.get("ids")
        if isinstance(ids, dict):
            clean["ids"] = {str(k): str(v) for k, v in ids.items() if isinstance(v, (str, int)) and str(v)}
        entries.append(clean)
    if not entries:
        return None
    name = obj.get("name") if isinstance(obj.get("name"), str) and obj["name"].strip() else "Imported watch order"
    return {"name": name.strip()[:80], "entries": entries}


def _id_index(lib):
    index = getattr(lib, "_wopack_ids", None)
    if index is None:
        index = {}
        for kind, items in (("movie", lib.movies), ("tvshow", lib.shows)):
            for item in items:
                for k, v in ids_of(item).items():
                    index.setdefault((kind, k, v), item)
        lib._wopack_ids = index
    return index


def find_item(lib, entry):
    """The library item for an entry: by shared id first, then title + year, then a unique title."""
    kind = "movie" if entry.get("type") == "movie" else "tvshow"
    index = _id_index(lib)
    for k, v in (entry.get("ids") or {}).items():
        if (kind, k, v) in index:
            return index[(kind, k, v)]
    ref = {"title": entry["title"], "year": entry.get("year", 0) or 0}
    if kind == "movie":
        ref["type"] = "movie"
    return lib.find(ref)


def match(entries, lib):
    """[(entry for the boxset, library item or None)] with titles/years taken from the library where found."""
    out = []
    for e in entries:
        item = find_item(lib, e)
        mine = {k: v for k, v in e.items() if k != "ids"}
        if item:
            mine["title"] = item["title"]
            mine["year"] = item.get("year", 0) or 0
        out.append((mine, item))
    return out
