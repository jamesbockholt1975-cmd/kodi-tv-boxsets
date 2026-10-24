# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Smart boxset rules: decide which library items belong, and describe the rules.

Pure Python (no Kodi imports). A rule set is a plain dict saved in the boxset:

    {"media": "tv" | "movie" | "both",
     "genre": "Drama", "tag": "Marvel", "studio": "HBO",
     "year_min": 2010, "year_max": 2020, "title_contains": "star"}

Every filter that is present must match (they are combined with AND). A rule set with
no filters matches nothing, so an empty set can never swallow the whole library.
"""

FILTERS = ("genre", "tag", "studio", "year_min", "year_max", "title_contains")
MEDIA_LABELS = {"tv": "TV shows only", "movie": "Movies only", "both": "TV shows and movies"}


def media(rules):
    value = (rules or {}).get("media", "tv")
    return value if value in MEDIA_LABELS else "tv"


def has_filters(rules):
    return bool(rules) and any(rules.get(f) for f in FILTERS)


def _values(item, field):
    values = item.get(field) or []
    if isinstance(values, str):
        values = [values]
    return [str(v).lower() for v in values]


def matches(rules, item):
    """True if `item` (a library dict with title/year/genre/studio/tag) fits every filter."""
    if not has_filters(rules):
        return False
    for field in ("genre", "tag", "studio"):
        wanted = rules.get(field)
        if wanted and wanted.lower() not in _values(item, field):
            return False
    year = item.get("year") or 0
    if rules.get("year_min") and (not year or year < rules["year_min"]):
        return False
    if rules.get("year_max") and (not year or year > rules["year_max"]):
        return False
    needle = rules.get("title_contains")
    if needle and needle.lower() not in (item.get("title") or "").lower():
        return False
    return True


def facet(items, field):
    """Sorted, de-duplicated values of genre/studio/tag across `items` (for pick-lists)."""
    seen = {}
    for item in items:
        for value in item.get(field) or []:
            seen.setdefault(str(value).lower(), str(value))
    return sorted(seen.values(), key=str.lower)


def describe(rules):
    """One line such as 'TV shows only; genre = Drama; years 2010-2020'."""
    if not has_filters(rules):
        return "no rules set"
    parts = [MEDIA_LABELS[media(rules)]]
    for field in ("genre", "tag", "studio"):
        if rules.get(field):
            parts.append("{} = {}".format(field, rules[field]))
    lo, hi = rules.get("year_min"), rules.get("year_max")
    if lo and hi:
        parts.append("years {}-{}".format(lo, hi))
    elif lo:
        parts.append("year {} or later".format(lo))
    elif hi:
        parts.append("year {} or earlier".format(hi))
    if rules.get("title_contains"):
        parts.append('title contains "{}"'.format(rules["title_contains"]))
    return "; ".join(parts)
