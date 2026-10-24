# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build a plain-text diagnostics report for bug reports.

Pure Python (no Kodi imports). The report contains versions, yes/no checks and counts
only. It never includes show titles or boxset names, and file paths are scrubbed.
"""

import time

MAX_LOG_LINES = 60


def yes_no(value):
    if value is None:
        return "unknown"
    return "yes" if value else "no"


def scrub(text, replacements):
    """Replace each (real, placeholder) pair, longest first, so paths don't leak names."""
    for real, placeholder in sorted(replacements, key=lambda r: -len(r[0] or "")):
        if real:
            text = text.replace(real, placeholder)
            text = text.replace(real.replace("\\", "/"), placeholder)
    return text


def filter_log(lines, limit=MAX_LOG_LINES):
    """Keep only the add-on's own lines (plus anything naming it), newest last."""
    keep = [ln.rstrip("\r\n") for ln in lines
            if "[TV Boxsets]" in ln or "plugin.video.tvboxsets" in ln
            or "skin.estuary.boxsets" in ln]
    return keep[-limit:]


def build(info, log_lines, replacements=()):
    """`info` is a dict of facts gathered by the add-on; returns the report text."""
    g = info.get
    lines = [
        "TV Boxsets diagnostics report",
        "Generated: " + time.strftime("%Y-%m-%d %H:%M:%S"),
        "(Versions, checks and counts only. No show or boxset names are included.)",
        "",
        "[Kodi]",
        "Kodi version: {}".format(g("kodi_version") or "unknown"),
        "Operating system: {}".format(g("os") or "unknown"),
        "Active skin: {}".format(g("active_skin") or "unknown"),
        "TV shows in library: {}".format(g("library_shows", "unknown")),
        "",
        "[Add-on]",
        "Add-on version: {}".format(g("addon_version") or "unknown"),
        "Data file format: {} (this add-on writes format {})".format(
            g("data_format") or "none yet", g("supported_format")),
        "Boxsets: {}".format(g("boxset_count", 0)),
        "Show entries in boxsets: {}".format(g("show_entries", 0)),
        "Movie entries: {}; smart boxsets: {}".format(g("movie_entries", 0), g("smart_boxsets", 0)),
        "Entries not found in the library: {}".format(g("missing_entries", 0)),
        "Automatic backups kept: {}".format(g("backup_count", 0)),
        "Settings: keep_backups={}, show_missing={}, debug_logging={}, boxset_sort={}, tag_prefix={!r}".format(
            g("setting_keep_backups"), yes_no(g("setting_show_missing")),
            yes_no(g("setting_debug_logging")), g("setting_boxset_sort"), g("setting_tag_prefix")),
        "Settings: show_badges={}, show_names={}, auto_tags={}".format(
            yes_no(g("setting_show_badges")), yes_no(g("setting_show_names")), yes_no(g("setting_auto_tags"))),
        "",
        "[Home screen skin]",
        "Stock Estuary found: {} (version {})".format(
            yes_no(g("estuary_found")), g("estuary_version") or "n/a"),
        "Boxsets skin copy installed: {} (version {})".format(
            yes_no(g("clone_installed")), g("clone_version") or "n/a"),
        "Boxsets skin copy enabled in Kodi: {}".format(yes_no(g("clone_enabled"))),
        "Boxsets menu item in Home.xml: {}".format(yes_no(g("clone_menu_item"))),
        "Boxsets widget in Home.xml: {}".format(yes_no(g("clone_widget"))),
        "Library badges in the skin copy: {}".format(yes_no(g("clone_badges"))),
        "Badge pictures: folder r{}, {} item(s)".format(g("badge_rev", 0), g("badge_items", 0)),
        "Estuary newer than the copy (rebuild suggested): {}".format(yes_no(g("clone_outdated"))),
        "",
        "[Recent add-on log lines]",
    ]
    log = filter_log(log_lines)
    lines.extend(log if log else ["(none found)"])
    return scrub("\n".join(lines) + "\n", replacements)
