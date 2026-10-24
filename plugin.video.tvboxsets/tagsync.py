# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Write boxset membership into Kodi as tags.

Estuary's video info dialog already has a "Tags" row, so once an item carries a tag such as
"Boxset: Marvel" the dialog shows which boxsets it is in. Only tags that start with the
configured prefix (default "Boxset:") are ever added or removed; your own tags are never
touched. Boxsets stay the master copy and tags only ever follow them.
"""

import xbmcgui

import store
from library import Library, jsonrpc, media_of, ordered_entries


def notify(message):
    xbmcgui.Dialog().notification("TV Boxsets", message, xbmcgui.NOTIFICATION_INFO, 3000)


def tag_prefix():
    """The text put in front of boxset names when they are written as Kodi tags."""
    value = store.setting_str("tag_prefix", "Boxset:").strip()
    return value + " " if value else ""


def _write(media, ident, tags):
    if media == "movie":
        jsonrpc("VideoLibrary.SetMovieDetails", {"movieid": ident, "tag": tags})
    else:
        jsonrpc("VideoLibrary.SetTVShowDetails", {"tvshowid": ident, "tag": tags})


def _apply(todo, quiet, heading):
    progress = None
    if not quiet:
        progress = xbmcgui.DialogProgress()
        progress.create("TV Boxsets", heading)
    done = 0
    for n, (media, ident, tags) in enumerate(todo):
        if progress:
            progress.update(int(100 * n / len(todo)), "{} of {}".format(n + 1, len(todo)))
            if progress.iscanceled():
                break
        _write(media, ident, tags)
        done += 1
    if progress:
        progress.close()
    return done


def sync(quiet=False):
    """Make the boxset tags match the boxsets. Returns how many items were changed (None = skipped).

    quiet=True is for the background service: no dialogs, no notifications.
    """
    prefix = tag_prefix()
    if not prefix:
        if not quiet:
            xbmcgui.Dialog().ok("TV Boxsets", "Set a tag prefix in the add-on settings first, so "
                                "your own tags can never be mixed up with boxset tags.")
        return None
    data = store.load()
    lib = Library(light=True)
    wanted = {}  # (media, library id) -> set of tags
    for bs in data.values():
        for ref, item in ordered_entries(bs, lib):
            if item:
                media = media_of(ref)
                ident = (media, item["movieid"] if media == "movie" else item["tvshowid"])
                wanted.setdefault(ident, set()).add(prefix + bs["name"])

    todo = []
    for media, pool in (("tvshow", lib.shows), ("movie", lib.movies)):
        for item in pool:
            ident = (media, item["movieid"] if media == "movie" else item["tvshowid"])
            current = item.get("tag") or []
            mine = {t for t in current if t.startswith(prefix)}
            if mine != wanted.get(ident, set()):
                keep = [t for t in current if not t.startswith(prefix)]
                todo.append((media, ident[1], keep + sorted(wanted.get(ident, set()))))

    if not todo:
        if not quiet:
            notify("Kodi tags are already up to date")
        return 0
    done = _apply(todo, quiet, "Writing tags...")
    store.dlog("tags: updated {} item(s)".format(done))
    if not quiet:
        notify("Updated tags on {} item(s)".format(done))
    return done


def remove_all():
    """Take every boxset tag (anything starting with the prefix) off every item."""
    prefix = tag_prefix()
    if not prefix:
        xbmcgui.Dialog().ok("TV Boxsets", "Set a tag prefix in the add-on settings first.")
        return None
    if not xbmcgui.Dialog().yesno(
            "Remove boxset tags",
            "Remove every tag starting with '{}' from your shows and movies?\n\nYour boxsets and "
            "your own tags are not touched. If 'Keep Kodi tags in step' is on, they will come back "
            "- turn that setting off first.".format(prefix.strip())):
        return None
    lib = Library(light=True)
    todo = []
    for media, pool in (("tvshow", lib.shows), ("movie", lib.movies)):
        for item in pool:
            current = item.get("tag") or []
            if any(t.startswith(prefix) for t in current):
                ident = item["movieid"] if media == "movie" else item["tvshowid"]
                todo.append((media, ident, [t for t in current if not t.startswith(prefix)]))
    if not todo:
        notify("There were no boxset tags to remove")
        return 0
    done = _apply(todo, False, "Removing tags...")
    notify("Removed boxset tags from {} item(s)".format(done))
    return done
