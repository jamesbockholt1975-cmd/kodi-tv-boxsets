# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Boxsets menu > Check my boxsets: find problems in the saved boxsets and fix the obvious ones.

Pure Python apart from the library lookups it is given. Nothing is changed by `scan`; the fix functions edit
the boxset data in place and return how many things they changed, so the caller decides what to save.
"""

import watchorder
from library import media_of, ordered_entries
from store import show_key


def _label(ref):
    year = " ({})".format(ref["year"]) if ref.get("year") else ""
    return "{}{}{}".format(ref["title"], year, " [movie]" if media_of(ref) == "movie" else "")


def _item_id(ref, item):
    return (media_of(ref), item.get("movieid") if media_of(ref) == "movie" else item.get("tvshowid"))


def library_ready(lib):
    """False when the library looks empty (for example a network drive is offline): never 'fix' then."""
    return bool(lib.shows or lib.movies)


def mostly_missing(report, data):
    """True when over half of the saved entries are missing: more likely a drive or scan problem than a clean-up."""
    saved = sum(len(bs["shows"]) for bs in data.values())
    return saved >= 4 and len(report["missing"]) * 2 > saved


def scan(data, lib):
    """A report dict describing what is wrong (or notable) in the boxsets."""
    report = {"boxsets": len(data), "items": 0, "missing": [], "duplicates": [], "empty": [],
              "smart_empty": [], "watch_hidden": [], "watch_no_season": [], "shared": []}
    seen = {}
    for bid, bs in data.items():
        entries = ordered_entries(bs, lib)
        report["items"] += len(entries)
        found = [(r, i) for r, i in entries if i]
        if not entries:
            (report["smart_empty"] if bs.get("rules") else report["empty"]).append(bs["name"])
        for ref in bs["shows"]:
            if not lib.find(ref):
                report["missing"].append((bs["name"], _label(ref)))
        ids = {}
        for ref in bs["shows"]:
            item = lib.find(ref)
            if item:
                key = _item_id(ref, item)
                if key in ids:
                    report["duplicates"].append((bs["name"], _label(ref)))
                ids[key] = True
        for ref, item in found:
            seen.setdefault(_item_id(ref, item), (ref, []))[1].append(bs["name"])
        if bs.get("watch"):
            rows = watchorder.resolve(bs, lib)
            visible = {watchorder.entry_key(r["entry"]) for r in rows}
            for entry in bs["watch"]:
                if watchorder.entry_key(entry) not in visible:
                    report["watch_hidden"].append((bs["name"], watchorder.entry_label(entry)))
            for row in rows:
                if row["item"] and row["media"] != "movie" and row["season"] is None:
                    report["watch_no_season"].append((bs["name"], watchorder.entry_label(row["entry"])))
    report["shared"] = sorted(((_label(ref), names) for ref, names in seen.values() if len(names) > 1),
                              key=lambda x: x[0].lower())
    return report


def problems(report):
    """How many fixable and reportable problems there are (shared items are only information)."""
    return sum(len(report[k]) for k in ("missing", "duplicates", "empty", "smart_empty", "watch_hidden", "watch_no_season"))


def text(report):
    lines = ["{} boxset(s), {} item(s) in total.".format(report["boxsets"], report["items"]), ""]

    def section(title, rows, fmt):
        if rows:
            lines.append("{} ({}):".format(title, len(rows)))
            lines.extend("  " + fmt(r) for r in rows[:25])
            if len(rows) > 25:
                lines.append("  ... and {} more".format(len(rows) - 25))
            lines.append("")

    section("Not in your library right now", report["missing"], lambda r: "{}: {}".format(*r))
    section("Duplicate entries (the same library item twice)", report["duplicates"], lambda r: "{}: {}".format(*r))
    section("Empty boxsets", report["empty"], lambda r: r)
    section("Smart boxsets that match nothing", report["smart_empty"], lambda r: r)
    section("Watch order entries for items no longer in the boxset", report["watch_hidden"], lambda r: "{}: {}".format(*r))
    section("Watch order seasons your library doesn't have", report["watch_no_season"], lambda r: "{}: {}".format(*r))
    if problems(report) == 0:
        lines.append("No problems found.")
        lines.append("")
    section("In more than one boxset (for information)", report["shared"], lambda r: "{}: {}".format(r[0], ", ".join(r[1])))
    return "\n".join(lines).rstrip()


def remove_missing(data, lib):
    """Take saved entries that aren't in the library out of their boxsets (and out of the order lists)."""
    removed = 0
    for bs in data.values():
        gone = [r for r in bs["shows"] if not lib.find(r)]
        if not gone:
            continue
        keys = {show_key(r) for r in gone}
        bs["shows"] = [r for r in bs["shows"] if show_key(r) not in keys]
        if bs.get("order"):
            bs["order"] = [r for r in bs["order"] if show_key(r) not in keys]
        removed += len(gone)
    return removed


def remove_duplicates(data, lib):
    removed = 0
    for bs in data.values():
        seen, keep = set(), []
        for ref in bs["shows"]:
            item = lib.find(ref)
            key = _item_id(ref, item) if item else None
            if key is not None and key in seen:
                removed += 1
                continue
            if key is not None:
                seen.add(key)
            keep.append(ref)
        bs["shows"] = keep
    return removed


def clean_watch(data, lib):
    """Drop watch order entries whose show or movie is no longer in the boxset."""
    removed = 0
    for bs in data.values():
        if not bs.get("watch"):
            continue
        visible = {watchorder.entry_key(r["entry"]) for r in watchorder.resolve(bs, lib)}
        keep = [e for e in bs["watch"] if watchorder.entry_key(e) in visible]
        removed += len(bs["watch"]) - len(keep)
        bs["watch"] = keep
    return removed
