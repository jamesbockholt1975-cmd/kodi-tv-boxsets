# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""TV Boxsets - group TV shows from the Kodi library into boxsets."""

import json
import os
import sys
import time
from urllib.parse import urlencode, parse_qsl

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

import badges
import diagnostics
import rules
import skinpatch
import store
import tagsync
import collage
import libnodes
import watchorder
import wopack
from library import (Library, full_details, is_member, item_stats, jsonrpc, media_of, ordered_entries,
                     ref_for, set_member, smart_matches)
from store import load, save, show_key

BASE_URL = sys.argv[0]
HANDLE = int(sys.argv[1])


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def url(**kwargs):
    return BASE_URL + "?" + urlencode(kwargs)


def notify(message):
    xbmcgui.Dialog().notification("TV Boxsets", message, xbmcgui.NOTIFICATION_INFO, 3000)


def cm(label, **kwargs):
    return (label, "RunPlugin({})".format(url(**kwargs)))


def refresh():
    xbmc.executebuiltin("Container.Refresh")


def finish_click():
    """Close out a click on a non-folder item so Kodi doesn't hang waiting."""
    if HANDLE >= 0:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def action_item(label, icon="DefaultAddSource.png", menu=False, **kwargs):
    """A clickable row that runs an action (used only for 'empty' placeholders)."""
    li = xbmcgui.ListItem(label=label)
    li.setArt({"icon": icon, "thumb": icon})
    li.setProperty("boxset_action", "1")  # keeps the Remove/Move context items off this row
    if menu:
        li.addContextMenuItems([cm("Boxsets menu...", action="menu")])
    xbmcplugin.addDirectoryItem(HANDLE, url(**kwargs), li, False)


# --------------------------------------------------------------------------
# Library access
# --------------------------------------------------------------------------

ART_KINDS = (("poster", "Poster"), ("fanart", "Fanart"), ("banner", "Banner"),
             ("clearlogo", "Clear logo"), ("landscape", "Landscape"))


def boxset_art(bs, items):
    art = {}
    if items:
        src = items[0].get("art", {})
        art["poster"] = art["thumb"] = src.get("poster", "")
        art["fanart"] = src.get("fanart", "")
        art["banner"] = src.get("banner", "")
        for kind in ("clearlogo", "landscape"):
            if src.get(kind):
                art[kind] = src[kind]
    for kind, _ in ART_KINDS:
        if bs.get(kind):
            art[kind] = bs[kind]
            if kind == "poster":
                art["thumb"] = bs[kind]
    return art


def apply_progress(li, tag, total, watched):
    """Episode counts + watched flag, the same properties Kodi sets on library shows."""
    li.setProperty("TotalEpisodes", str(total))
    li.setProperty("WatchedEpisodes", str(watched))
    li.setProperty("UnWatchedEpisodes", str(max(total - watched, 0)))
    tag.setPlaycount(1 if total and watched >= total else 0)


# --------------------------------------------------------------------------
# Views
# --------------------------------------------------------------------------

def sort_rows(rows):
    """Order boxsets by the 'Sort boxsets by' setting: 0 A-Z, 1 in-progress first, 2 recent."""
    mode = store.setting_int("boxset_sort", 0)

    def key(row):
        name = row["bs"]["name"].lower()
        if mode == 1:
            w, t = row["watched"], row["total"]
            return (0 if 0 < w < t else (1 if w == 0 else 2), name)
        if mode == 2:
            return (-(row["bs"].get("modified") or 0), name)
        return (0, name)

    return sorted(rows, key=key)


def list_boxsets(widget=False, flt=None):
    data = load()
    lib = Library()
    store.dlog("list_boxsets widget={} filter={} boxsets={} library_shows={}".format(
        widget, flt, len(data), len(lib.shows)))
    xbmcplugin.setContent(HANDLE, "tvshows")  # native TV show views (posters etc.)

    rows = []
    for bid, bs in data.items():
        entries = ordered_entries(bs, lib)
        found = [(r, i) for r, i in entries if i]
        total = watched = 0
        for r, i in found:
            t, w = item_stats(r, i)
            total += t
            watched += w
        rows.append({"bid": bid, "bs": bs, "entries": entries, "found": found,
                     "total": total, "watched": watched})

    if flt == "next_up":  # the home screen 'Next up' row: what comes next in each watch order
        next_up_row(sort_rows([r for r in rows if r["bs"].get("watch")]), lib)
        return

    if flt == "in_progress":  # the home screen 'Continue watching' row shows the shows themselves
        continue_watching(sort_rows([r for r in rows if 0 < r["watched"] < r["total"]]))
        return

    for row in sort_rows(rows):
        bid, bs, found = row["bid"], row["bs"], row["found"]
        n_shows = sum(1 for r, _ in found if media_of(r) == "tvshow")
        n_movies = len(found) - n_shows
        missing = len(row["entries"]) - len(found)

        li = xbmcgui.ListItem(label=bs["name"])
        li.setProperty("boxset_tile", bs["name"])  # the skin draws the boxset's name on the poster
        li.setArt(boxset_art(bs, [i for _, i in found]))
        tag = li.getVideoInfoTag()
        tag.setMediaType("tvshow")
        tag.setTitle(bs["name"])
        counts = "{} show(s)".format(n_shows)
        if n_movies:
            counts += ", {} movie(s)".format(n_movies)
        lines = ["{}; {} of {} watched".format(counts, row["watched"], row["total"])]
        if bs.get("rules"):
            lines.append("Smart boxset: " + rules.describe(bs["rules"]))
        if missing:
            lines.append("{} not currently in your library".format(missing))
        lines.append("")
        lines.extend(i["title"] for _, i in found)
        tag.setPlot("\n".join(lines))
        apply_progress(li, tag, row["total"], row["watched"])
        li.addContextMenuItems([
            cm("Boxsets menu (create, backup, tools...)", action="menu"),
            cm("Play next unwatched episode", action="play_next", bid=bid),
            cm("Play all unwatched (queue)...", action="queue", bid=bid),
            cm("Watch order (seasons and movies)...", action="watch_open", bid=bid),
            cm("Export the watch order to a file...", action="watch_export", bid=bid),
            cm("Mark everything as watched", action="mark", bid=bid, watched="1"),
            cm("Mark everything as unwatched", action="mark", bid=bid, watched="0"),
            cm("Add shows", action="add", bid=bid),
            cm("Add movies", action="add_movies", bid=bid),
            cm("Remove items", action="remove", bid=bid),
            cm("Smart rules (auto-add)...", action="rules", bid=bid),
            cm("Change show order", action="reorder", bid=bid),
            cm("Set boxset artwork...", action="art", bid=bid),
            cm("Write to Kodi tags", action="tag_sync"),
            cm("Rename boxset", action="rename", bid=bid),
            cm("Delete boxset", action="delete", bid=bid),
        ])
        xbmcplugin.addDirectoryItem(HANDLE, url(action="open", bid=bid), li, True)

    if not rows and not widget:  # nothing to right-click yet, so offer a way in
        action_item("[B]+ Create your first boxset[/B]", menu=True, action="create")

    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(HANDLE)


def next_up_row(rows, lib):
    """One tile per boxset with a watch order: the next unwatched episode or movie, ready to play."""
    xbmcplugin.setContent(HANDLE, "tvshows")
    for row in rows:
        target = watchorder.next_up(row["bs"], lib)
        if not target:
            continue
        li, link = playable_item(target, "Next up in the watch order of '{}'.".format(row["bs"]["name"]))
        li.setLabel2(row["bs"]["name"])
        li.setProperty("boxset_tile", row["bs"]["name"])  # the skin draws the boxset's name on the poster
        xbmcplugin.addDirectoryItem(HANDLE, link, li, False)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(HANDLE)


def playable_item(target, note=""):
    """(list item, plugin address) for something from watchorder.playables()."""
    if target[0] == "movie":
        item = target[1]
        li = xbmcgui.ListItem(label=movie_label(item["title"]))
        li.setArt(item.get("art", {}))
        tag = li.getVideoInfoTag()
        tag.setMediaType("movie")
        tag.setTitle(movie_label(item["title"]))
        tag.setPlot((note + "\n\n" if note else "") + (item.get("plot") or ""))
        if item.get("year"):
            tag.setYear(int(item["year"]))
        tag.setPlaycount(0)
        li.setProperty("boxset_movie", "true")
        return li, url(action="play_movie", id=item["movieid"])
    _, show, ep = target
    li = episode_item(show, ep)
    li.getVideoInfoTag().setPlot((note + "\n\n" if note else "") + (ep.get("plot") or ""))
    return li, url(action="play_episode", id=ep["episodeid"])


def queue_play(bid, use_watch_order):
    """Play everything unwatched in order (or add it to the end of the queue)."""
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    targets = list(watchorder.playables(bs, Library(), use_watch_order))
    if not targets:
        notify("Everything in this {} has been watched".format(
            "watch order" if use_watch_order and bs.get("watch") else "boxset"))
        return
    choice = xbmcgui.Dialog().select("{} unwatched item(s) in '{}'".format(len(targets), bs["name"]), [
        "Play them now, in order", "Add them to the end of the queue"])
    if choice < 0:
        return
    if choice == 0:
        jsonrpc("Playlist.Clear", {"playlistid": 1})
    for t in targets:
        entry = {"movieid": t[1]["movieid"]} if t[0] == "movie" else {"episodeid": t[2]["episodeid"]}
        jsonrpc("Playlist.Add", {"playlistid": 1, "item": entry})
    if choice == 0:
        jsonrpc("Player.Open", {"item": {"playlistid": 1, "position": 0}})
    else:
        notify("Added {} item(s) to the queue".format(len(targets)))


def continue_watching(rows):
    """One tile per in-progress boxset: the show (or movie) you should carry on with."""
    xbmcplugin.setContent(HANDLE, "tvshows")
    seen = set()
    for row in rows:
        partial = fresh = None
        for ref, item in row["found"]:
            total, watched = item_stats(ref, item)
            if watched < total:
                fresh = fresh or (ref, item)
                if watched > 0:
                    partial = partial or (ref, item)
        choice = partial or fresh
        if not choice:
            continue
        ref, item = choice
        key = show_key(ref)
        if key in seen:  # the same show can be in several boxsets: list it once
            continue
        seen.add(key)
        total, watched = item_stats(ref, item)
        is_movie = media_of(ref) == "movie"
        li = xbmcgui.ListItem(label=item["title"])
        li.setLabel2(row["bs"]["name"])
        li.setArt(item.get("art", {}))
        tag = li.getVideoInfoTag()
        tag.setMediaType("movie" if is_movie else "tvshow")
        tag.setTitle(item["title"])
        tag.setPlot("Next up in the boxset '{}'.\n\n{}".format(row["bs"]["name"], item.get("plot", "")))
        if item.get("year"):
            tag.setYear(int(item["year"]))
        if is_movie:
            tag.setPlaycount(0)
            xbmcplugin.addDirectoryItem(
                HANDLE, url(action="play_movie", id=item["movieid"]), li, False)
        else:
            apply_progress(li, tag, total, watched)
            xbmcplugin.addDirectoryItem(
                HANDLE, "videodb://tvshows/titles/{}/".format(item["tvshowid"]), li, True)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(HANDLE)


def open_boxset(bid):
    data = load()
    bs = data.get(bid)
    if not bs:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    lib = Library()
    xbmcplugin.setContent(HANDLE, "tvshows")
    show_missing = store.setting_bool("show_missing", True)
    shown = 0

    for ref, item in ordered_entries(bs, lib):
        is_movie = media_of(ref) == "movie"
        if item and not is_movie:
            item = full_details("tvshow", item)
            li = xbmcgui.ListItem(label=item["title"])
            li.setArt(item.get("art", {}))
            tag = li.getVideoInfoTag()
            tag.setMediaType("tvshow")
            fill_tag(tag, item)
            apply_progress(li, tag, item.get("episode", 0) or 0, item.get("watchedepisodes", 0) or 0)
            # Link straight into Kodi's own library node for the show, so the
            # seasons/episodes screens are the normal native ones.
            node = "videodb://tvshows/titles/{}/".format(item["tvshowid"])
            xbmcplugin.addDirectoryItem(HANDLE, node, li, True)
            shown += 1
        elif item and is_movie:
            # Marked as a movie so it stands out among the shows. Only the label changes: the title
            # (which the right-click scripts and Kodi's info use) stays the plain movie title.
            item = full_details("movie", item)
            li = xbmcgui.ListItem(label=movie_label(item["title"]))
            li.setProperty("boxset_title", item["title"])  # the real title, for the right-click scripts
            li.setProperty("boxset_movie", "true")  # the skin draws a MOVIE tag on the poster
            li.setArt(item.get("art", {}))
            tag = li.getVideoInfoTag()
            tag.setMediaType("movie")
            fill_tag(tag, item, title=movie_label(item["title"]))  # skins draw this one, not the list label
            tag.setPlaycount(1 if (item.get("playcount") or 0) > 0 else 0)
            xbmcplugin.addDirectoryItem(
                HANDLE, url(action="play_movie", id=item["movieid"]), li, False)
            shown += 1
        elif show_missing:
            # In the boxset but not in the library right now (removed, or not scanned yet).
            li = xbmcgui.ListItem(label="[COLOR grey]{}{} (not in library)[/COLOR]".format(
                ref["title"], " [Movie]" if is_movie else ""))
            icon = "DefaultMovies.png" if is_movie else "DefaultTVShows.png"
            li.setArt({"icon": icon, "thumb": icon})
            tag = li.getVideoInfoTag()
            li.setProperty("boxset_title", ref["title"])
            if is_movie:
                li.setProperty("boxset_movie", "true")
            tag.setMediaType("movie" if is_movie else "tvshow")
            tag.setTitle(ref["title"] + (" [Movie]" if is_movie else ""))
            if ref.get("year"):
                tag.setYear(int(ref["year"]))
            tag.setPlot("This is in the boxset but isn't in your Kodi library at the "
                        "moment. It will come back by itself if it returns.")
            xbmcplugin.addDirectoryItem(HANDLE, url(action="missing", title=ref["title"]), li, False)
            shown += 1

    if not shown:  # an empty boxset has nothing to right-click, so offer a way in
        action_item("[B]This boxset is empty: press here to add shows[/B]", menu=True,
                    action="add", bid=bid)

    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(HANDLE)


def refresh_badges():
    result = badges.sync_badges()
    if result is None:
        notify("Couldn't update the badges (see the log)")
    elif result[1]:
        notify("Badges rebuilt for {} item(s)".format(result[2]))
    else:
        notify("Badges are already up to date ({} item(s))".format(result[2]))


def refresh_rows():
    store.bump_reload()
    notify("Home screen rows refreshed")


def menu_entries():
    """[(label, function)] for the Boxsets menu: everything that used to be extra rows."""
    entries = [("Create new boxset", create_boxset),
               ("Create new smart boxset", create_smart_boxset)]
    if not skin_installed():
        entries.append(("Add 'Boxsets' to the home screen (Estuary)", install_home_skin))
    else:
        if skin_outdated():
            entries.append(("Estuary has been updated: rebuild the Boxsets skin", rebuild_skin))
        if not skin_current():
            entries.append(("Update '{}': add the home widget and library badges".format(
                skinpatch.SKIN_NAME), install_home_skin))
        elif xbmc.getSkinDir() != skinpatch.SKIN_ID:
            entries.append(("Switch to '{}' (adds Boxsets to the home screen)".format(
                skinpatch.SKIN_NAME), install_home_skin))
        if not skin_outdated():
            entries.append(("Rebuild the Boxsets skin from the current Estuary", rebuild_skin))
    entries += [
        ("Export a backup...", export_backup),
        ("Import a backup file...", import_backup),
        ("Restore an automatic backup...", restore_auto),
        ("Create boxsets from Kodi tags...", import_from_tags),
        ("Create boxsets from Kodi movie sets...", import_movie_sets),
        ("Export a watch order file...", watch_export_pick),
        ("Import a watch order file...", watch_import),
        ("Write boxsets to Kodi tags...", sync_tags),
        ("Remove boxset tags from Kodi...", tagsync.remove_all),
        ("Add boxsets to Kodi's library menu (other skins)...", libnodes.enable),
        ("Remove boxsets from Kodi's library menu...", libnodes.disable),
        ("Refresh the home screen rows", refresh_rows),
        ("Refresh the boxset badges", refresh_badges),
        ("Create a diagnostics report (for bug reports)...", diagnostics_report),
    ]
    return entries


def global_menu():
    entries = menu_entries()
    pick = xbmcgui.Dialog().select("Boxsets menu", [label for label, _ in entries])
    if pick >= 0:
        entries[pick][1]()


# --------------------------------------------------------------------------
# Boxset actions
# --------------------------------------------------------------------------

def create_boxset():
    name = xbmcgui.Dialog().input("Name of new boxset", type=xbmcgui.INPUT_ALPHANUM).strip()
    if not name:
        return
    data = load()
    if store.find_by_name(data, name):
        notify("A boxset with that name already exists")
        return
    bid = store.new_boxset(data, name)
    save(data)
    if xbmcgui.Dialog().yesno("Boxset created", "Add shows to '{}' now?".format(name)):
        add_items(bid, "tvshow")


def add_items(bid, media="tvshow"):
    """Pick TV shows (or movies) from the library to add to a boxset."""
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    lib = Library()
    pool = lib.movies if media == "movie" else lib.shows
    have = {show_key(r) for r in bs["shows"]}
    candidates = [i for i in sorted(pool, key=lambda i: i["title"].lower())
                  if show_key(dict(i, type="movie") if media == "movie" else i) not in have]
    if not candidates:
        notify("No more {} available to add".format("movies" if media == "movie" else "shows"))
        return

    items = []
    for i in candidates:
        li = xbmcgui.ListItem(i["title"], str(i.get("year") or ""))
        li.setArt({"thumb": i.get("art", {}).get("poster", "")})
        items.append(li)

    chosen = xbmcgui.Dialog().multiselect("Add to " + bs["name"], items)
    if not chosen:
        return
    store.add_refs(bs, [candidates[i] for i in chosen], media)
    save(data)
    notify("Added {} item(s)".format(len(chosen)))


def fill_tag(tag, d, title=None):
    """Put everything Kodi knows about a library show or movie into the list item's info, so the
    information page (press 'i') shows what it shows for the same item in the normal library."""
    def put(setter, value, convert=None):
        if value in (None, "", [], {}, 0):
            return
        try:
            getattr(tag, setter)(convert(value) if convert else value)
        except Exception as exc:  # noqa: BLE001 - one odd field must not blank the whole item
            xbmc.log("[TV Boxsets] could not set {} ({!r})".format(setter, exc), xbmc.LOGINFO)
    put("setTitle", title or d.get("title"))
    put("setOriginalTitle", d.get("originaltitle"))
    put("setSortTitle", d.get("sorttitle"))
    put("setPlot", d.get("plot"))
    put("setPlotOutline", d.get("plotoutline"))
    put("setTagLine", d.get("tagline"))
    put("setYear", d.get("year"), int)
    put("setPremiered", d.get("premiered"))
    put("setGenres", d.get("genre"))
    put("setStudios", d.get("studio"))
    put("setMpaa", d.get("mpaa"))
    put("setCountries", d.get("country"))
    put("setDirectors", d.get("director"))
    put("setWriters", d.get("writer"))
    put("setTags", d.get("tag"))
    put("setTrailer", d.get("trailer"))
    put("setSet", d.get("set"))
    put("setIMDBNumber", d.get("imdbnumber"))
    put("setDuration", d.get("runtime"), int)
    put("setUserRating", d.get("userrating"), int)
    put("setDateAdded", d.get("dateadded"))
    put("setLastPlayed", d.get("lastplayed"))
    put("setTop250", d.get("top250"), int)
    ids = {k: str(v) for k, v in (d.get("uniqueid") or {}).items() if v}
    put("setUniqueIDs", ids)
    ratings = d.get("ratings") or {}
    for name, info in ratings.items():
        try:
            tag.setRating(float(info.get("rating", 0)), int(info.get("votes", 0) or 0), name,
                          bool(info.get("default")))
        except Exception:  # noqa: BLE001
            pass
    if not ratings and d.get("rating"):
        put("setRating", d["rating"], float)
    actor = getattr(xbmc, "Actor", None)
    if actor and d.get("cast"):
        try:
            tag.setCast([actor(c.get("name", ""), c.get("role", ""), c.get("order", 0), c.get("thumbnail", ""))
                         for c in d["cast"]])
        except Exception as exc:  # noqa: BLE001
            xbmc.log("[TV Boxsets] could not set cast ({!r})".format(exc), xbmc.LOGINFO)


def movie_label(title):
    return "{} [COLOR lightskyblue][Movie][/COLOR]".format(title)


def entry_label(ref):
    kind = " [movie]" if media_of(ref) == "movie" else ""
    return "{} ({}){}".format(ref["title"], ref.get("year", ""), kind)


def remove_shows(bid):
    data = load()
    bs = data.get(bid)
    if not bs or not bs["shows"]:
        return
    chosen = xbmcgui.Dialog().multiselect("Remove from " + bs["name"],
                                          [entry_label(r) for r in bs["shows"]])
    if not chosen:
        return
    bs["shows"] = [r for i, r in enumerate(bs["shows"]) if i not in set(chosen)]
    save(data)


def remove_one(bid, title, year):
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    target = show_key({"title": title, "year": int(year or 0)})
    bs["shows"] = [r for r in bs["shows"] if show_key(r) != target]
    save(data)


def rename_boxset(bid):
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    name = xbmcgui.Dialog().input("Rename boxset", defaultt=bs["name"],
                                  type=xbmcgui.INPUT_ALPHANUM).strip()
    if name:
        bs["name"] = name
        save(data)


def delete_boxset(bid):
    data = load()
    bs = data.get(bid)
    if bs and xbmcgui.Dialog().yesno(
            "Delete boxset", "Delete '{}'? Your shows are not deleted.".format(bs["name"])):
        del data[bid]
        save(data)


def set_art(bid, kind=None):
    """Set custom artwork (poster, fanart, banner, clear logo or landscape)."""
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    if kind is None:
        pick = xbmcgui.Dialog().select("Which artwork?", [label for _, label in ART_KINDS])
        if pick < 0:
            return
        kind = ART_KINDS[pick][0]
    if kind not in dict(ART_KINDS):
        return
    label = dict(ART_KINDS)[kind].lower()
    choice = xbmcgui.Dialog().select("Boxset {}".format(label), [
        "Choose an image file",
        "Use the {} of a show or movie in this boxset".format(label),
        "Automatic (first item's {})".format(label),
    ] + (["Make a collage from the posters inside this boxset"] if kind == "poster" else []))
    if choice == 3 and kind == "poster":
        make_collage(data, bs, bid)
        return
    if choice == 0:
        path = xbmcgui.Dialog().browseSingle(2, "Choose {} image".format(label), "files")
        if not path:
            return
        bs[kind] = path
    elif choice == 1:
        items = [(r, i) for r, i in ordered_entries(bs, Library()) if i]
        if not items:
            notify("Add something first")
            return
        pick = xbmcgui.Dialog().select("Use {} from".format(label), [i["title"] for _, i in items])
        if pick < 0:
            return
        value = items[pick][1].get("art", {}).get(kind, "")
        if not value:
            notify("'{}' has no {} to use".format(items[pick][1]["title"], label))
            return
        bs[kind] = value
    elif choice == 2:
        bs[kind] = ""
    else:
        return
    save(data)


def make_collage(data, bs, bid):
    """Combine the posters of up to six items into one boxset poster (needs Pillow)."""
    found = [i for _, i in ordered_entries(bs, Library()) if i and i.get("art", {}).get("poster")]
    if len(found) < 2:
        notify("A collage needs at least two items with posters")
        return
    images = []
    for item in found[:collage.MAX_ITEMS + 2]:
        path = collage.source_path(item["art"]["poster"])
        if not path:
            continue
        try:
            handle = xbmcvfs.File(path)
            raw = handle.readBytes()
            handle.close()
        except Exception:  # noqa: BLE001 - unreachable poster: skip it
            continue
        if raw:
            images.append(raw)
        if len(images) == collage.MAX_ITEMS:
            break
    try:
        png = collage.build(images)
    except collage.Unavailable:
        xbmcgui.Dialog().ok("TV Boxsets", "Making a collage needs the Pillow image library. Install "
                            "'Python Imaging Library' (script.module.pil) from Kodi's add-on repository "
                            "(Add-ons > Install from repository > Program add-ons > Python modules), "
                            "then try again.")
        return
    if not png:
        notify("None of the posters could be read")
        return
    folder = os.path.join(store.DATA_DIR, "collages")
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        if old.startswith("collage-{}-".format(bid)):
            os.remove(os.path.join(folder, old))
    dest = os.path.join(folder, "collage-{}-{}.png".format(bid, int(time.time())))
    with open(dest, "wb") as handle:
        handle.write(png)
    bs["poster"] = dest
    save(data)
    notify("Made a poster from {} item(s)".format(min(len(images), collage.MAX_ITEMS)))


def reorder_shows(bid):
    data = load()
    bs = data.get(bid)
    entries = [(r, i) for r, i in ordered_entries(bs, Library())] if bs else []
    if not entries:
        notify("Add some shows first")
        return
    mode = xbmcgui.Dialog().select("Order of '{}'".format(bs["name"]), [
        "Sort A to Z (automatic)", "Arrange manually"])
    if mode < 0:
        return
    if mode == 0:
        bs["manual_order"] = False
        bs.pop("order", None)
        save(data)
        return

    refs = [dict(r) for r, _ in entries]  # start from the order currently shown
    last = 0
    while True:
        labels = ["{}. {}{}".format(i + 1, r["title"], " [Movie]" if media_of(r) == "movie" else "")
                  for i, r in enumerate(refs)]
        pick = xbmcgui.Dialog().select(
            "Pick an item to move (press Back when finished)", labels, preselect=last)
        if pick < 0:
            break
        answer = xbmcgui.Dialog().numeric(
            0, "Move '{}' to position (1-{})".format(refs[pick]["title"], len(refs)))
        try:
            position = max(1, min(len(refs), int(answer)))
        except ValueError:
            last = pick
            continue
        refs.insert(position - 1, refs.pop(pick))
        last = position - 1
    bs["order"] = refs
    bs["manual_order"] = True
    save(data)


def _find_index(refs, title, year, media):
    wanted = {"title": title, "year": int(year or 0)}
    if media == "movie":
        wanted["type"] = "movie"
    keys = [show_key(r) for r in refs]
    if show_key(wanted) in keys:
        return keys.index(show_key(wanted))
    # years can differ after a metadata refresh: fall back to the title
    return next((i for i, r in enumerate(refs)
                 if r["title"].lower() == title.lower() and media_of(r) == media), None)


def move_entry(bid, title, year, media, delta):
    """Move one item up (delta=-1) or down (+1) in the boxset's viewing order."""
    data = load()
    bs = data.get(bid)
    if not bs:
        return False
    refs = [dict(r) for r, _ in ordered_entries(bs, Library())]
    idx = _find_index(refs, title, year, media)
    if idx is None:
        notify("Couldn't find '{}' in this boxset".format(title))
        return False
    target = idx + delta
    if not 0 <= target < len(refs):
        notify("'{}' is already {}".format(title, "first" if delta < 0 else "last"))
        return False
    refs.insert(target, refs.pop(idx))
    bs["order"] = refs
    bs["manual_order"] = True
    save(data)
    return True


def place_entry(bid, title, year, media, after=None):
    """Put an item (usually a movie) straight after another entry in the viewing order.

    `after` is the chosen entry's index among the OTHER items (-1 = at the very start);
    when it is None the person is asked to pick from a list.
    """
    data = load()
    bs = data.get(bid)
    if not bs:
        return False
    refs = [dict(r) for r, _ in ordered_entries(bs, Library())]
    idx = _find_index(refs, title, year, media)
    if idx is None:
        notify("Couldn't find '{}' in this boxset".format(title))
        return False
    moving = refs.pop(idx)
    if not refs:
        notify("There is nothing else in this boxset to place it next to")
        return False
    if after is None:
        choices = ["[At the start]"] + [
            "{}. {}{}".format(i + 1, r["title"], " [Movie]" if media_of(r) == "movie" else "")
            for i, r in enumerate(refs)]
        pick = xbmcgui.Dialog().select("Place '{}' after...".format(title), choices, preselect=min(idx, len(refs)))
        if pick < 0:
            return False
        after = pick - 1
    refs.insert(max(-1, min(len(refs) - 1, after)) + 1, moving)
    bs["order"] = refs
    bs["manual_order"] = True
    save(data)
    return True


# --------------------------------------------------------------------------
# Watch order: seasons and movies in a sequence you choose
# --------------------------------------------------------------------------

def watch_row_label(row):
    entry = row["entry"]
    if row["media"] == "movie":
        return movie_label(entry["title"])
    return watchorder.entry_label(entry)


def open_watch(bid):
    data = load()
    bs = data.get(bid)
    if not bs:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    xbmcplugin.setContent(HANDLE, "tvshows")
    show_missing = store.setting_bool("show_missing", True)
    shown = 0
    for row in watchorder.resolve(bs, Library()):
        row["bid"] = bid
        entry, item, season = row["entry"], row["item"], row["season"]
        is_movie = row["media"] == "movie"
        if item and season and row.get("episodes"):
            shown += add_range_item(row, item, season)
        elif item and (is_movie or season):
            li = xbmcgui.ListItem(label=watch_row_label(row))
            art = dict(item.get("art", {}))
            if season:
                for kind in ("poster", "fanart", "banner"):
                    if (season.get("art") or {}).get(kind):
                        art[kind] = season["art"][kind]
                if art.get("poster"):
                    art["thumb"] = art["poster"]
            li.setArt(art)
            tag = li.getVideoInfoTag()
            item = full_details("movie" if is_movie else "tvshow", item)
            if is_movie:
                tag.setMediaType("movie")
                fill_tag(tag, item, title=movie_label(item["title"]))
                li.setProperty("boxset_movie", "true")
                tag.setPlaycount(1 if (item.get("playcount") or 0) > 0 else 0)
                target, folder = url(action="play_movie", id=item["movieid"]), False
            else:
                tag.setMediaType("season")
                fill_tag(tag, item, title=watchorder.entry_label(entry))
                tag.setTvShowTitle(item["title"])
                tag.setSeason(entry.get("season", 1))
                apply_progress(li, tag, season.get("episode", 0) or 0, season.get("watchedepisodes", 0) or 0)
                target = "videodb://tvshows/titles/{}/{}/".format(item["tvshowid"], entry.get("season", 1))
                folder = True
            if item.get("year"):
                tag.setYear(int(item["year"]))
            li.setProperty("boxset_title", entry["title"])
            li.setProperty("boxset_key", row["key"])
            xbmcplugin.addDirectoryItem(HANDLE, target, li, folder)
            shown += 1
        elif show_missing:
            li = xbmcgui.ListItem(label="[COLOR grey]{} (not in library)[/COLOR]".format(
                watchorder.entry_label(entry)))
            icon = "DefaultMovies.png" if is_movie else "DefaultTVShows.png"
            li.setArt({"icon": icon, "thumb": icon})
            tag = li.getVideoInfoTag()
            tag.setMediaType("movie" if is_movie else "season")
            tag.setTitle(watchorder.entry_label(entry))
            tag.setPlot("This is in the watch order but isn't in your Kodi library at the moment.")
            li.setProperty("boxset_title", entry["title"])
            li.setProperty("boxset_key", row["key"])
            xbmcplugin.addDirectoryItem(HANDLE, url(action="missing", title=entry["title"]), li, False)
            shown += 1
    if not shown:
        action_item("[B]The watch order is empty: press here to add seasons and movies[/B]",
                    menu=True, action="watch_add", bid=bid)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(HANDLE)


def episode_label(item, ep):
    return "{} - S{}E{}: {}".format(item["title"], ep.get("season", 0), ep.get("episode", 0),
                                    ep.get("title", ""))


def episode_item(item, ep, label=None):
    """A playable episode row (used for crossover entries)."""
    li = xbmcgui.ListItem(label=label or episode_label(item, ep))
    art = dict(item.get("art", {}))
    thumb = (ep.get("art") or {}).get("thumb")
    if thumb:
        art["thumb"] = thumb
    elif art.get("poster"):
        art["thumb"] = art["poster"]
    li.setArt(art)
    tag = li.getVideoInfoTag()
    tag.setMediaType("episode")
    tag.setTitle(label or episode_label(item, ep))
    tag.setTvShowTitle(item["title"])
    tag.setSeason(ep.get("season", 0))
    tag.setEpisode(ep.get("episode", 0))
    tag.setPlot(ep.get("plot", ""))
    tag.setPlaycount(1 if (ep.get("playcount") or 0) > 0 else 0)
    return li


def add_range_item(row, item, season):
    """One row for a crossover entry: a playable episode, or a folder when it holds several."""
    entry, eps = row["entry"], row["episodes"]
    if len(eps) == 1:
        li = episode_item(item, eps[0])
        target, folder = url(action="play_episode", id=eps[0]["episodeid"]), False
    else:
        li = xbmcgui.ListItem(label=watchorder.entry_label(entry))
        art = dict(item.get("art", {}))
        if art.get("poster"):
            art["thumb"] = art["poster"]
        li.setArt(art)
        tag = li.getVideoInfoTag()
        tag.setMediaType("season")
        tag.setTitle(watchorder.entry_label(entry))
        tag.setTvShowTitle(item["title"])
        tag.setSeason(entry.get("season", 1))
        tag.setPlot(item.get("plot", ""))
        apply_progress(li, tag, len(eps), sum(1 for e in eps if (e.get("playcount") or 0) > 0))
        target, folder = url(action="wo_range", bid=row.get("bid", ""), key=row["key"]), True
    li.setProperty("boxset_title", entry["title"])
    li.setProperty("boxset_key", row["key"])
    xbmcplugin.addDirectoryItem(HANDLE, target, li, folder)
    return 1


def open_range(bid, key):
    """The episodes of a crossover entry that holds several."""
    data = load()
    bs = data.get(bid)
    xbmcplugin.setContent(HANDLE, "episodes")
    if bs:
        for row in watchorder.resolve(bs, Library()):
            if row["key"] == key and row.get("episodes"):
                for ep in row["episodes"]:
                    xbmcplugin.addDirectoryItem(HANDLE, url(action="play_episode", id=ep["episodeid"]),
                                                episode_item(row["item"], ep), False)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(HANDLE)


def go_watch(bid):
    """Open the watch order of a boxset (used by the right-click entry)."""
    xbmc.executebuiltin("Container.Update({})".format(url(action="watch", bid=bid)))


def _watch_visible(bs):
    return [r["entry"] for r in watchorder.resolve(bs, Library())]


def watch_add(bid):
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    lib = Library()
    have = {watchorder.entry_key(e) for e in bs.get("watch", [])}
    started = watchorder.seasons_with_entries(bs.get("watch", []))
    options = [(e, item, season) for e, item, season in watchorder.candidates(bs, lib)
               if watchorder.entry_key(e) not in have and watchorder.season_id(e) not in started]
    if not options:
        notify("Everything in this boxset is already in the watch order"
               if bs.get("watch") else "Add some shows or movies to the boxset first")
        return
    labels = []
    for e, item, season in options:
        if season:
            labels.append("{} ({} episodes)".format(watchorder.entry_label(e), season.get("episode", 0)))
        else:
            labels.append(watchorder.entry_label(e))
    chosen = xbmcgui.Dialog().multiselect("Add to the watch order of '{}'".format(bs["name"]), labels)
    if not chosen:
        return
    entries, added = watchorder.add_entries(_watch_visible(bs), [options[i][0] for i in sorted(chosen)])
    bs["watch"] = entries
    save(data)
    notify("Added {} to the watch order".format(added))


def watch_add_episodes(bid):
    """Crossovers: pick a show, a season and some episodes; they go into the order as their own
    entries, splitting the season's entry around them if it is already in the order."""
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    lib = Library()
    shows = [(ref, item) for ref, item in ordered_entries(bs, lib) if item and media_of(ref) != "movie"]
    if not shows:
        notify("Add some TV shows to the boxset first")
        return
    pick = xbmcgui.Dialog().select("Episodes from which show?", [ref["title"] for ref, _ in shows])
    if pick < 0:
        return
    ref, item = shows[pick]
    seasons = watchorder.seasons_of(item)
    if not seasons:
        notify("Kodi has no seasons for '{}'".format(ref["title"]))
        return
    pick = xbmcgui.Dialog().select("{}: which season?".format(ref["title"]), [
        "{} ({} episodes)".format(watchorder.season_name(s["season"]), s.get("episode", 0)) for s in seasons])
    if pick < 0:
        return
    number = seasons[pick]["season"]
    episodes = watchorder.episodes_of(item, number)
    if not episodes:
        notify("Kodi has no episodes for that season")
        return
    chosen = xbmcgui.Dialog().multiselect("{} - {}: pick the episodes".format(
        ref["title"], watchorder.season_name(number)), [
        "E{}. {}".format(e.get("episode", 0), e.get("title", "")) for e in episodes])
    if not chosen:
        return
    numbers = [episodes[i].get("episode", 0) for i in chosen]
    spans = watchorder.runs(numbers)
    base = {"title": ref["title"], "year": ref.get("year", 0) or 0}
    entries, added = watchorder.insert_runs(_watch_visible(bs), base, number, spans,
                                            max(e.get("episode", 0) for e in episodes))
    if not added:
        notify("Those episodes are already in the watch order")
        return
    bs["watch"] = entries
    save(data)
    notify("Added {} entr{} to the watch order".format(added, "y" if added == 1 else "ies"))


def watch_fill(bid):
    """Append every season and movie that isn't in the watch order yet, in the boxset's order."""
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    current = _watch_visible(bs)
    started = watchorder.seasons_with_entries(current)
    new = [e for e, _, _ in watchorder.candidates(bs, Library()) if watchorder.season_id(e) not in started]
    entries, added = watchorder.add_entries(current, new)
    if not added:
        notify("The watch order already has everything")
        return
    bs["watch"] = entries
    save(data)
    notify("Added {} to the watch order".format(added))


def watch_move(bid, key, delta):
    data = load()
    bs = data.get(bid)
    if not bs:
        return False
    out = watchorder.moved(_watch_visible(bs), key, delta)
    if out is None:
        notify("It is already {}".format("first" if delta < 0 else "last"))
        return False
    bs["watch"] = out
    save(data)
    return True


def watch_place(bid, key, after=None):
    data = load()
    bs = data.get(bid)
    if not bs:
        return False
    entries = _watch_visible(bs)
    idx = watchorder.index_of(entries, key)
    if idx is None:
        notify("Couldn't find that in the watch order")
        return False
    others = [e for e in entries if watchorder.entry_key(e) != key]
    if not others:
        notify("There is nothing else in the watch order to place it next to")
        return False
    if after is None:
        choices = ["[At the start]"] + ["{}. {}".format(i + 1, watchorder.entry_label(e))
                                        for i, e in enumerate(others)]
        pick = xbmcgui.Dialog().select("Place '{}' after...".format(watchorder.entry_label(entries[idx])),
                                       choices, preselect=min(idx, len(others)))
        if pick < 0:
            return False
        after = pick - 1
    bs["watch"] = watchorder.placed(entries, key, after)
    save(data)
    return True


def watch_export(bid):
    """Save the watch order to a small file you can share."""
    data = load()
    bs = data.get(bid)
    rows = watchorder.resolve(bs, Library()) if bs else []
    if not rows:
        notify("This boxset has no watch order to export yet")
        return
    version = xbmcaddon.Addon().getAddonInfo("version")
    pack = wopack.build(bs["name"], rows, "TV Boxsets " + version)
    slug = "".join(c if c.isalnum() else "-" for c in bs["name"].lower()).strip("-") or "boxset"
    dest = save_text_file("Choose a folder to save the watch order in", "watchorder-{}.json".format(slug),
                          json.dumps(pack, indent=2, ensure_ascii=False))
    if dest:
        xbmcgui.Dialog().ok("TV Boxsets", "Watch order saved:\n{}\n\nIt holds {} entries: titles, years and ids only, "
                            "nothing else from your library.".format(dest, len(pack["entries"])))


def watch_export_pick():
    """Boxsets menu: choose a boxset that has a watch order, then export it."""
    data = load()
    ids = [bid for bid, bs in data.items() if bs.get("watch")]
    if not ids:
        notify("None of your boxsets has a watch order yet")
        return
    ids.sort(key=lambda b: data[b]["name"].lower())
    pick = xbmcgui.Dialog().select("Export which watch order?", [data[b]["name"] for b in ids])
    if pick >= 0:
        watch_export(ids[pick])


def watch_import():
    """Read a watch order file and put it into a new or an existing boxset."""
    path = xbmcgui.Dialog().browseSingle(1, "Choose a watch order file", "files", ".json")
    if not path:
        return
    handle = xbmcvfs.File(path)
    text = handle.read()
    handle.close()
    try:
        pack = wopack.parse(json.loads(text))
    except ValueError:
        pack = None
    if not pack:
        xbmcgui.Dialog().ok("TV Boxsets", "That doesn't look like a watch order file made by TV Boxsets "
                            "(or it was made by a newer version).")
        return
    data = load()
    lib = Library()
    matched = wopack.match(pack["entries"], lib)
    found = sum(1 for _, item in matched if item)
    names = [bs["name"] for bs in data.values()]
    pick = xbmcgui.Dialog().select("'{}': {} entries, {} found in your library".format(
        pack["name"], len(matched), found), ["Create a boxset called '{}'".format(pack["name"]),
                                              "Put it in an existing boxset..."])
    if pick < 0:
        return
    if pick == 1:
        if not names:
            notify("You have no boxsets yet: choose 'Create a boxset' instead")
            return
        which = xbmcgui.Dialog().select("Which boxset?", names)
        if which < 0:
            return
        bid = list(data)[which]
    else:
        bid = store.find_by_name(data, pack["name"]) or store.new_boxset(data, pack["name"])
    bs = data[bid]
    if bs.get("watch") and not xbmcgui.Dialog().yesno(
            "Replace the watch order?", "'{}' already has a watch order. Replace it with the imported one?".format(bs["name"])):
        return
    entries, _ = watchorder.add_entries([], [e for e, _ in matched])
    base_refs = []
    for e, _ in matched:
        ref = {"title": e["title"], "year": e.get("year", 0) or 0}
        if e.get("type") == "movie":
            ref["type"] = "movie"
        base_refs.append(ref)
    added = store.add_refs(bs, base_refs)  # entries that are not in the library yet wait there as "not in library"
    bs["watch"] = entries
    save(data)
    missing = sorted({e["title"] for e, item in matched if not item})
    lines = ["Imported '{}' into '{}': {} entries, {} new item(s) added to the boxset.".format(
        pack["name"], bs["name"], len(entries), added)]
    if missing:
        lines.append("")
        lines.append("{} not in your library yet (they will appear by themselves once they are):".format(len(missing)))
        lines.append(", ".join(missing[:8]) + (" and {} more".format(len(missing) - 8) if len(missing) > 8 else ""))
    xbmcgui.Dialog().ok("TV Boxsets", "\n".join(lines))


def watch_remove(bid, key):
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    entries = _watch_visible(bs)
    out = watchorder.removed(entries, key)
    if len(out) == len(entries):
        notify("Couldn't find that in the watch order")
        return
    bs["watch"] = out
    save(data)
    notify("Removed from the watch order")


def next_unwatched_in_season(tvshowid, season):
    resp = jsonrpc("VideoLibrary.GetEpisodes", {
        "tvshowid": tvshowid, "season": season, "properties": ["season", "episode"],
        "filter": {"field": "playcount", "operator": "is", "value": "0"}})
    episodes = resp.get("result", {}).get("episodes", [])
    return min(episodes, key=lambda e: e.get("episode", 0))["episodeid"] if episodes else None


def play_next_watch(bid):
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    for row in watchorder.resolve(bs, Library()):
        item = row["item"]
        if not item:
            continue
        if row["media"] == "movie":
            if (item.get("playcount") or 0) == 0:
                play_movie(item["movieid"])
                return
            continue
        if not row["season"]:
            continue
        if row.get("episodes"):  # a crossover entry: its own episodes only
            nxt = next((e for e in row["episodes"] if (e.get("playcount") or 0) == 0), None)
            episode_id = nxt["episodeid"] if nxt else None
        else:
            episode_id = next_unwatched_in_season(item["tvshowid"], row["entry"].get("season", 1))
        if episode_id:
            jsonrpc("Player.Open", {"item": {"episodeid": episode_id}, "options": {"resume": True}})
            return
    notify("Everything in the watch order has been watched")


def next_unwatched_episode(tvshowid):
    resp = jsonrpc("VideoLibrary.GetEpisodes", {
        "tvshowid": tvshowid,
        "properties": ["season", "episode"],
        "filter": {"and": [
            {"field": "playcount", "operator": "is", "value": "0"},
            {"field": "season", "operator": "greaterthan", "value": "0"},  # skip specials
        ]},
    })
    episodes = resp.get("result", {}).get("episodes", [])
    if not episodes:
        return None
    best = min(episodes, key=lambda e: (e.get("season", 0), e.get("episode", 0)))
    return best["episodeid"]


def play_next(bid):
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    for ref, item in ordered_entries(bs, Library()):
        if not item:
            continue
        if media_of(ref) == "movie":
            if (item.get("playcount") or 0) == 0:
                play_movie(item["movieid"])
                return
            continue
        episode_id = next_unwatched_episode(item["tvshowid"])
        if episode_id:
            jsonrpc("Player.Open", {"item": {"episodeid": episode_id},
                                    "options": {"resume": True}})
            return
    notify("Everything in this boxset has been watched")


def play_episode(episode_id):
    jsonrpc("Player.Open", {"item": {"episodeid": int(episode_id)}, "options": {"resume": True}})


def play_movie(movie_id):
    jsonrpc("Player.Open", {"item": {"movieid": int(movie_id)}, "options": {"resume": True}})


def mark_boxset(bid, watched):
    """Mark every episode and movie in a boxset watched (watched=True) or unwatched."""
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    word = "watched" if watched else "unwatched"
    if not xbmcgui.Dialog().yesno("Mark as " + word,
                                  "Mark everything in '{}' as {}?".format(bs["name"], word)):
        return
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    entries = [(r, i) for r, i in ordered_entries(bs, Library()) if i]
    progress = xbmcgui.DialogProgress()
    progress.create("TV Boxsets", "Updating...")
    changed = 0
    for n, (ref, item) in enumerate(entries):
        progress.update(int(100 * n / max(len(entries), 1)), item["title"])
        if progress.iscanceled():
            break
        details = {"playcount": 1 if watched else 0, "resume": {"position": 0, "total": 0}}
        if watched:
            details["lastplayed"] = now
        if media_of(ref) == "movie":
            if bool((item.get("playcount") or 0) > 0) != watched:
                jsonrpc("VideoLibrary.SetMovieDetails", dict(details, movieid=item["movieid"]))
                changed += 1
            continue
        episodes = jsonrpc("VideoLibrary.GetEpisodes", {
            "tvshowid": item["tvshowid"], "properties": ["playcount"]}
        ).get("result", {}).get("episodes", [])
        for ep in episodes:
            if bool((ep.get("playcount") or 0) > 0) != watched:
                jsonrpc("VideoLibrary.SetEpisodeDetails", dict(details, episodeid=ep["episodeid"]))
                changed += 1
    progress.close()
    notify("Marked {} item(s) as {}".format(changed, word))


def edit_rules(bid):
    """Smart boxset rules: items that match are added automatically."""
    data = load()
    bs = data.get(bid)
    if not bs:
        return
    lib = Library()
    rule_set = dict(bs.get("rules") or {"media": "tv"})
    dialog = xbmcgui.Dialog()
    while True:
        def show(value):
            return value if value else "(any)"
        years = "(any)"
        if rule_set.get("year_min") or rule_set.get("year_max"):
            years = "{} to {}".format(rule_set.get("year_min") or "any", rule_set.get("year_max") or "any")
        pick = dialog.select("Smart rules for '{}'".format(bs["name"]), [
            "Include: " + rules.MEDIA_LABELS[rules.media(rule_set)],
            "Genre: " + show(rule_set.get("genre")),
            "Tag: " + show(rule_set.get("tag")),
            "Studio: " + show(rule_set.get("studio")),
            "Years: " + years,
            "Title contains: " + show(rule_set.get("title_contains")),
            "Unwatched only: " + ("yes" if rule_set.get("unwatched") else "no"),
            "Added in the last: " + ("{} days".format(rule_set["added_days"]) if rule_set.get("added_days") else "(any time)"),
            "Rating at least: " + ("{:g}".format(rule_set["rating_min"]) if rule_set.get("rating_min") else "(any)"),
            "[B]Save these rules[/B]",
            "Remove the rules (back to a normal boxset)",
        ])
        if pick < 0:
            return
        if pick == 0:
            keys = list(rules.MEDIA_LABELS)
            choice = dialog.select("Include", [rules.MEDIA_LABELS[k] for k in keys])
            if choice >= 0:
                rule_set["media"] = keys[choice]
        elif pick in (1, 2, 3):
            field = {1: "genre", 2: "tag", 3: "studio"}[pick]
            pool = list(lib.shows)
            if rules.media(rule_set) in ("movie", "both"):
                pool += lib.movies
            options = rules.facet(pool, field)
            choice = dialog.select(field.capitalize(), ["(any)"] + options)
            if choice == 0:
                rule_set.pop(field, None)
            elif choice > 0:
                rule_set[field] = options[choice - 1]
        elif pick == 4:
            lo = dialog.numeric(0, "From year (blank for any)")
            hi = dialog.numeric(0, "To year (blank for any)")
            for key, value in (("year_min", lo), ("year_max", hi)):
                if value and value.strip().isdigit():
                    rule_set[key] = int(value)
                else:
                    rule_set.pop(key, None)
        elif pick == 5:
            text = dialog.input("Title contains", defaultt=rule_set.get("title_contains", ""),
                                type=xbmcgui.INPUT_ALPHANUM).strip()
            if text:
                rule_set["title_contains"] = text
            else:
                rule_set.pop("title_contains", None)
        elif pick == 6:
            if rule_set.get("unwatched"):
                rule_set.pop("unwatched")
            else:
                rule_set["unwatched"] = True
        elif pick == 7:
            days = dialog.numeric(0, "Added in the last how many days? (blank for any time)")
            if days and days.strip().isdigit() and int(days) > 0:
                rule_set["added_days"] = int(days)
            else:
                rule_set.pop("added_days", None)
        elif pick == 8:
            choice = dialog.select("Rating at least", ["(any)"] + ["{:g}".format(v) for v in rules.RATING_CHOICES])
            if choice == 0:
                rule_set.pop("rating_min", None)
            elif choice > 0:
                rule_set["rating_min"] = rules.RATING_CHOICES[choice - 1]
        elif pick == 9:
            if not rules.has_filters(rule_set):
                dialog.ok("TV Boxsets", "Choose at least one rule (genre, tag, studio, years, "
                                        "title, unwatched, recently added or rating) first. Rules with nothing set match nothing.")
                continue
            bs["rules"] = rule_set
            save(data)
            count = len(smart_matches(bs, lib))
            notify("Saved: {} item(s) match right now".format(count))
            return
        elif pick == 10:
            bs.pop("rules", None)
            bs.pop("excluded", None)
            save(data)
            notify("Rules removed")
            return


def create_smart_boxset():
    name = xbmcgui.Dialog().input("Name of new smart boxset", type=xbmcgui.INPUT_ALPHANUM).strip()
    if not name:
        return
    data = load()
    if store.find_by_name(data, name):
        notify("A boxset with that name already exists")
        return
    bid = store.new_boxset(data, name)
    save(data)
    edit_rules(bid)
    data = load()
    if bid in data and not data[bid].get("rules"):
        del data[bid]  # cancelled before any rules were saved
        save(data)
        notify("Cancelled: no rules were saved")


# --------------------------------------------------------------------------
# Tools: tags, backup, restore
# --------------------------------------------------------------------------




def import_from_tags():
    labels = []
    for media in ("tvshow", "movie"):
        resp = jsonrpc("VideoLibrary.GetTags", {"type": media})
        for t in resp.get("result", {}).get("tags", []):
            if t["label"] not in labels:
                labels.append(t["label"])
    if not labels:
        xbmcgui.Dialog().ok("TV Boxsets", "None of your TV shows or movies have tags in the "
                            "Kodi library yet.")
        return
    chosen = xbmcgui.Dialog().multiselect("Create a boxset for each tag you pick", labels)
    if not chosen:
        return
    prefix = tagsync.tag_prefix()
    data = load()
    created = extended = 0
    for i in chosen:
        label = labels[i]
        name = label[len(prefix):] if prefix and label.startswith(prefix) else label
        flt = {"filter": {"field": "tag", "operator": "is", "value": label},
               "properties": ["title", "year"]}
        shows = jsonrpc("VideoLibrary.GetTVShows", flt).get("result", {}).get("tvshows", [])
        movies = jsonrpc("VideoLibrary.GetMovies", flt).get("result", {}).get("movies", [])
        if not shows and not movies:
            continue
        bid = store.find_by_name(data, name)
        is_new = bid is None
        if is_new:
            bid = store.new_boxset(data, name)
        added = store.add_refs(data[bid], shows) + store.add_refs(data[bid], movies, "movie")
        if added:
            created += 1 if is_new else 0
            extended += 0 if is_new else 1
        elif is_new:
            del data[bid]
    save(data)
    notify("{} boxset(s) created, {} updated".format(created, extended))


def import_movie_sets():
    """Turn Kodi's own movie sets into boxsets (so TV shows can join them, and they can have a watch order)."""
    resp = jsonrpc("VideoLibrary.GetMovieSets", {"properties": ["title", "art"]})
    found = []
    for s in resp.get("result", {}).get("sets", []):
        det = jsonrpc("VideoLibrary.GetMovieSetDetails", {
            "setid": s["setid"], "properties": ["title", "art"],
            "movies": {"properties": ["title", "year"]}}).get("result", {}).get("setdetails", {})
        movies = det.get("movies") or s.get("movies") or []
        if movies:
            found.append((s, det.get("art") or s.get("art") or {}, movies))
    if not found:
        xbmcgui.Dialog().ok("TV Boxsets", "Kodi has no movie sets with movies in them yet. "
                            "(Sets come from your scraper, for example 'Alien Collection'.)")
        return
    data = load()
    labels = []
    for s, _, movies in found:
        bid = store.find_by_name(data, s["title"])
        labels.append("{} ({} movie{}){}".format(s["title"], len(movies), "" if len(movies) == 1 else "s",
                                                 "  - already a boxset, will be extended" if bid else ""))
    chosen = xbmcgui.Dialog().multiselect("Create a boxset for each movie set you pick", labels)
    if not chosen:
        return
    created = extended = 0
    for i in chosen:
        s, art, movies = found[i]
        bid = store.find_by_name(data, s["title"])
        is_new = bid is None
        if is_new:
            bid = store.new_boxset(data, s["title"])
        bs = data[bid]
        added = store.add_refs(bs, movies, "movie")
        for kind in ("poster", "fanart"):  # the set's artwork, unless the boxset already has its own
            if not bs.get(kind) and art.get(kind):
                bs[kind] = art[kind]
        if is_new:
            created += 1
        elif added:
            extended += 1
    save(data)
    notify("{} boxset(s) created, {} updated".format(created, extended))


def sync_tags():
    """Tools > Write boxsets to Kodi tags (shows progress; the service does the same quietly)."""
    tagsync.sync()


def save_text_file(heading, filename, text):
    """Ask for a folder and write `text` there. Returns the written path, or None."""
    folder = xbmcgui.Dialog().browseSingle(3, heading, "files")
    if not folder:
        return None
    sep = "" if folder.endswith(("/", "\\")) else "/"
    dest = "{}{}{}".format(folder, sep, filename)
    handle = xbmcvfs.File(dest, "w")
    ok = handle.write(text)
    handle.close()
    if not ok:
        xbmcgui.Dialog().ok("TV Boxsets", "Couldn't write the file there. Try another folder.")
        return None
    return dest


def export_backup():
    data = load()
    if not data:
        notify("There are no boxsets to back up yet")
        return
    dest = save_text_file("Choose a folder to save the backup in",
                          "tvboxsets-backup-{}.json".format(time.strftime("%Y%m%d-%H%M%S")),
                          store.dump_text(data))
    if dest:
        xbmcgui.Dialog().ok("TV Boxsets", "Backup saved:\n{}".format(dest))


def apply_import(incoming, source_label):
    if not incoming:
        xbmcgui.Dialog().ok("TV Boxsets", "That doesn't look like a TV Boxsets backup.")
        return
    mode = xbmcgui.Dialog().select(
        "Restore {} boxset(s) from {}".format(len(incoming), source_label), [
            "Merge with my current boxsets",
            "Replace everything with this backup"])
    if mode < 0:
        return
    if mode == 1:
        if not xbmcgui.Dialog().yesno(
                "Replace everything?",
                "This replaces all your current boxsets with the backup.\n"
                "(A copy of today's starting state is kept in the automatic backups.)"):
            return
        save(incoming)
        notify("Restored {} boxset(s)".format(len(incoming)))
    else:
        data = load()
        created, extended = store.merge(data, incoming)
        save(data)
        notify("{} new, {} updated".format(created, extended))


def import_backup():
    path = xbmcgui.Dialog().browseSingle(1, "Choose a TV Boxsets backup file", "files", ".json")
    if not path:
        return
    handle = xbmcvfs.File(path)
    text = handle.read()
    handle.close()
    try:
        incoming = store.parse(json.loads(text))
    except ValueError:
        incoming = None
    apply_import(incoming, os.path.basename(path.rstrip("/\\")))


def restore_auto():
    backups = store.list_auto_backups()
    if not backups:
        xbmcgui.Dialog().ok("TV Boxsets", "No automatic backups yet. One is kept for each "
                            "day you change your boxsets.")
        return
    pick = xbmcgui.Dialog().select("Automatic backups (state at the start of each day)", [
        "{}  -  {} boxset(s)".format(day, count) for _, day, count in backups])
    if pick < 0:
        return
    path, day, _ = backups[pick]
    try:
        with open(path, "r", encoding="utf-8") as f:
            incoming = store.parse(json.load(f))
    except (OSError, ValueError):
        incoming = None
    apply_import(incoming, "the {} backup".format(day))


# --------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------

def read_log_lines():
    """The tail of kodi.log (the last ~2 MB), or [] if it can't be read."""
    path = xbmcvfs.translatePath("special://logpath/kodi.log")
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - 2000000))
            return f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []


def path_replacements():
    pairs = [(xbmcvfs.translatePath(special), placeholder) for special, placeholder in (
        ("special://profile/", "<kodi-userdata>/"), ("special://home/", "<kodi-home>/"),
        ("special://xbmc/", "<kodi-app>/"), ("special://temp/", "<kodi-temp>/"),
        ("special://logpath/", "<kodi-logs>/"))]
    pairs.append((os.path.expanduser("~"), "<user-home>"))
    return pairs


def collect_info():
    lib = Library()
    data = load()
    src = estuary_source()
    try:
        with open(skin_home_xml(), "r", encoding="utf-8") as f:
            home_text = f.read()
    except OSError:
        home_text = ""
    installed = skin_installed()
    return {
        "kodi_version": xbmc.getInfoLabel("System.BuildVersion"),
        "os": os_description(),
        "active_skin": xbmc.getSkinDir(),
        "library_shows": len(lib.shows),
        "addon_version": xbmcaddon.Addon().getAddonInfo("version"),
        "data_format": store.file_format(),
        "supported_format": store.DATA_FORMAT,
        "boxset_count": len(data),
        "show_entries": sum(len(b["shows"]) for b in data.values()),
        "missing_entries": sum(1 for b in data.values() for r in b["shows"] if lib.find(r) is None),
        "movie_entries": sum(1 for b in data.values() for r in b["shows"] if r.get("type") == "movie"),
        "smart_boxsets": sum(1 for b in data.values() if b.get("rules")),
        "setting_boxset_sort": store.setting_int("boxset_sort", 0),
        "setting_tag_prefix": store.setting_str("tag_prefix", "Boxset:"),
        "badge_rev": badges.current_rev(),
        "badge_items": badges._state(store.BADGE_DIR).get("items", 0),
        "setting_show_badges": store.setting_bool("show_badges", True),
        "setting_show_names": store.setting_bool("show_names", True),
        "setting_auto_tags": store.setting_bool("auto_tags", True),
        "backup_count": len(store.list_auto_backups()),
        "setting_keep_backups": store.setting_int("keep_backups", store.KEEP_BACKUPS),
        "setting_show_missing": store.setting_bool("show_missing", True),
        "setting_debug_logging": store.setting_bool("debug_logging", False),
        "estuary_found": bool(src),
        "estuary_version": skinpatch.addon_version(os.path.join(src, "addon.xml")) if src else None,
        "clone_installed": installed,
        "clone_version": skinpatch.addon_version(os.path.join(skin_dir(), "addon.xml")) if installed else None,
        "clone_enabled": bool(skin_enabled()) if installed else False,
        "clone_menu_item": '<property name="id">{}</property>'.format(skinpatch.WIDGET_ID) in home_text,
        "clone_widget": skinpatch.has_widget(skin_home_xml()),
        "clone_badges": skinpatch.has_badges(skin_xml_dir()),
        "clone_categories": skinpatch.has_categories(skin_home_xml()),
        "setting_hide_categories": store.setting_bool("hide_categories", False),
        "clone_outdated": skin_outdated(),
    }


def os_description():
    """Kodi's OS label, or Python's own when Kodi still says 'Busy' (it fills that label in lazily)."""
    value = (xbmc.getInfoLabel("System.OSVersionInfo") or "").strip()
    if value and value.lower() != "busy":
        return value
    import platform
    return platform.platform()


def diagnostics_report():
    text = diagnostics.build(collect_info(), read_log_lines(), path_replacements())
    choice = xbmcgui.Dialog().select("Diagnostics report", [
        "View it now", "Save it to a folder (so you can share it)"])
    if choice == 0:
        xbmcgui.Dialog().textviewer("TV Boxsets diagnostics", text)
    elif choice == 1:
        dest = save_text_file("Choose a folder to save the report in",
                              "tvboxsets-diagnostics-{}.txt".format(time.strftime("%Y%m%d-%H%M%S")),
                              text)
        if dest:
            xbmcgui.Dialog().ok("TV Boxsets", "Report saved:\n{}".format(dest))


# --------------------------------------------------------------------------
# Home screen skin
# --------------------------------------------------------------------------

def skin_dir():
    return xbmcvfs.translatePath("special://home/addons/" + skinpatch.SKIN_ID)


def skin_xml_dir():
    return os.path.join(skin_dir(), "xml")


def skin_current():
    """True if the skin copy has the current widget block and the library badges."""
    return (skinpatch.has_widget(skin_home_xml()) and skinpatch.has_categories(skin_home_xml())
            and skinpatch.has_badges(skin_xml_dir()))


def skin_home_xml():
    return os.path.join(skin_dir(), "xml", "Home.xml")


def skin_installed():
    return os.path.isdir(skin_dir())


def estuary_source():
    """The newest installed copy of the stock Estuary skin."""
    best, best_key = None, None
    for base in ("special://home/addons/skin.estuary", "special://xbmc/addons/skin.estuary"):
        path = xbmcvfs.translatePath(base)
        if os.path.isdir(path):
            key = skinpatch.version_key(skinpatch.addon_version(os.path.join(path, "addon.xml")))
            if best is None or key > best_key:
                best, best_key = path, key
    return best


def skin_outdated():
    """True if Estuary has been updated since the Boxsets copy was built."""
    src = estuary_source()
    if not src or not skin_installed():
        return False
    a = skinpatch.addon_version(os.path.join(src, "addon.xml"))
    b = skinpatch.addon_version(os.path.join(skin_dir(), "addon.xml"))
    return bool(a and b and a != b)


def seed_skin_settings():
    src = xbmcvfs.translatePath("special://profile/addon_data/skin.estuary/settings.xml")
    dst_dir = xbmcvfs.translatePath("special://profile/addon_data/{}/".format(skinpatch.SKIN_ID))
    try:
        skinpatch.seed_settings(src, dst_dir)
    except OSError:
        pass


def update_skin():
    """Bring an existing Boxsets skin copy up to date: current widget block + library badges."""
    try:
        changed = skinpatch.patch_widget(skin_home_xml())
        changed = skinpatch.patch_categories(skin_home_xml()) or changed
        changed = bool(skinpatch.patch_badges(skin_xml_dir())) or changed
    except Exception as exc:  # noqa: BLE001
        xbmc.log("[TV Boxsets] skin update failed: {!r}".format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("TV Boxsets", "Couldn't update the skin:\n{}".format(exc))
        return False
    badges.sync_badges()
    if changed and xbmc.getSkinDir() == skinpatch.SKIN_ID:
        xbmc.executebuiltin("ReloadSkin()")
    return True


def skin_enabled():
    return xbmc.getCondVisibility("System.AddonIsEnabled({})".format(skinpatch.SKIN_ID))


def activate_skin():
    """Register + enable the cloned skin, then offer to switch to it."""
    xbmc.executebuiltin("UpdateLocalAddons")
    xbmc.sleep(2000)
    if not skin_enabled():
        jsonrpc("Addons.SetAddonEnabled", {"addonid": skinpatch.SKIN_ID, "enabled": True})
        xbmc.sleep(1000)
    if not skin_enabled():
        xbmcgui.Dialog().ok(
            "TV Boxsets",
            "The skin is built but Kodi hasn't picked it up yet.\n\n"
            "Please restart Kodi. If it asks whether to enable new add-ons, say yes. "
            "Then open this add-on again and use the 'Switch to' item.")
        return
    if xbmcgui.Dialog().yesno("TV Boxsets", "Switch to '{}' now?\n\nKodi will ask you to "
                              "confirm the new skin - choose Yes.".format(skinpatch.SKIN_NAME)):
        jsonrpc("Settings.SetSettingValue",
                {"setting": "lookandfeel.skin", "value": skinpatch.SKIN_ID})


def install_home_skin():
    """Make a copy of the installed Estuary with a 'Boxsets' main menu item and widget."""
    if skin_installed():
        if not skin_current():
            if not update_skin():
                return
            if xbmc.getSkinDir() == skinpatch.SKIN_ID:
                notify("Skin updated")
                return
        activate_skin()
        return
    src = estuary_source()
    if not src:
        xbmcgui.Dialog().ok("TV Boxsets", "Couldn't find the Estuary skin on this system.")
        return
    if not xbmcgui.Dialog().yesno(
            "Add Boxsets to the home screen",
            "This creates a copy of Estuary called '{}' with a 'Boxsets' item in the "
            "main menu. Your normal Estuary is left untouched.\n\nContinue?".format(
                skinpatch.SKIN_NAME)):
        return
    store.dlog("building skin copy from {}".format(src))
    try:
        skinpatch.build_skin(src, skin_dir())
    except Exception as exc:  # noqa: BLE001 - report anything to the user
        xbmc.log("[TV Boxsets] skin build failed: {!r}".format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("TV Boxsets", "Couldn't build the skin:\n{}".format(exc))
        return
    seed_skin_settings()  # start with the same skin settings as your normal Estuary
    badges.sync_badges()
    activate_skin()


def rebuild_skin():
    """Re-copy the current Estuary and re-apply the Boxsets menu item and widget."""
    if xbmc.getSkinDir() == skinpatch.SKIN_ID:
        xbmcgui.Dialog().ok(
            "TV Boxsets",
            "You're using the Boxsets skin right now, so it can't be rebuilt safely.\n\n"
            "Switch to normal Estuary first (Settings > Interface > Skin), then run this "
            "again. It will offer to switch you back when it's done.")
        return
    src = estuary_source()
    if not src:
        xbmcgui.Dialog().ok("TV Boxsets", "Couldn't find the Estuary skin on this system.")
        return
    if not xbmcgui.Dialog().yesno(
            "Rebuild the Boxsets skin",
            "This re-copies your current Estuary and adds the Boxsets menu item and "
            "widget again. Your skin settings are kept.\n\nContinue?"):
        return
    store.dlog("rebuilding skin copy from {}".format(src))
    try:
        skinpatch.rebuild_skin(src, skin_dir(), xbmcvfs.translatePath("special://temp/"))
    except Exception as exc:  # noqa: BLE001
        xbmc.log("[TV Boxsets] skin rebuild failed: {!r}".format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("TV Boxsets", "Couldn't rebuild the skin (the old one is untouched):\n{}"
                            .format(exc))
        return
    seed_skin_settings()
    activate_skin()


# --------------------------------------------------------------------------
# Router
# --------------------------------------------------------------------------

NO_REFRESH = {"watch_export", "queue", "watch_open", "play_episode", "play_next", "play_movie", "missing", "export", "diagnostics"}


def router(paramstring):
    p = dict(parse_qsl(paramstring))
    action = p.get("action")

    if store.is_newer_format():
        # The data file was written by a newer version of this add-on. Touch nothing.
        if action != "widget":
            xbmcgui.Dialog().ok("TV Boxsets", "Your boxsets were saved by a newer version of "
                                "this add-on. Please update the add-on; nothing has been changed.")
        if HANDLE >= 0:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    if action is None:
        list_boxsets()
    elif action == "widget":
        list_boxsets(widget=True, flt=p.get("filter"))
    elif action == "open":
        open_boxset(p["bid"])
    elif action == "watch":
        open_watch(p["bid"])
    elif action == "wo_range":
        open_range(p["bid"], p.get("key", ""))
    else:
        follow = None
        if action == "create":
            create_boxset()
        elif action == "create_smart":
            create_smart_boxset()
        elif action == "add":
            add_items(p["bid"], "tvshow")
        elif action == "add_movies":
            add_items(p["bid"], "movie")
        elif action == "remove":
            remove_shows(p["bid"])
        elif action == "remove_one":
            remove_one(p["bid"], p.get("title", ""), p.get("year", 0))
        elif action == "rename":
            rename_boxset(p["bid"])
        elif action == "delete":
            delete_boxset(p["bid"])
        elif action == "art":
            set_art(p["bid"], p.get("kind"))
        elif action == "reorder":
            reorder_shows(p["bid"])
        elif action == "play_next":
            play_next_watch(p["bid"]) if p.get("watch") else play_next(p["bid"])
        elif action == "play_movie":
            play_movie(p["id"])
        elif action == "mark":
            mark_boxset(p["bid"], p.get("watched") == "1")
        elif action == "rules":
            edit_rules(p["bid"])
        elif action == "missing":
            notify("'{}' isn't in your library right now".format(p.get("title", "That item")))
        elif action == "from_tags":
            import_from_tags()
        elif action == "tag_sync":
            sync_tags()
        elif action == "export":
            export_backup()
        elif action == "import_backup":
            import_backup()
        elif action == "restore_auto":
            restore_auto()
        elif action == "install_skin":
            install_home_skin()
        elif action == "rebuild_skin":
            rebuild_skin()
        elif action == "diagnostics":
            diagnostics_report()
        elif action == "refresh_widgets":
            refresh_rows()
        elif action in ("menu", "tools"):
            global_menu()
        elif action == "watch_export":
            watch_export(p["bid"])
        elif action == "watch_import":
            watch_import()
        elif action == "import_sets":
            import_movie_sets()
        elif action == "queue":
            queue_play(p["bid"], bool(p.get("watch")))
        elif action == "watch_open":
            go_watch(p["bid"])
        elif action == "watch_add":
            watch_add(p["bid"])
        elif action == "watch_add_eps":
            watch_add_episodes(p["bid"])
        elif action == "play_episode":
            play_episode(p["id"])
        elif action == "watch_fill":
            watch_fill(p["bid"])
        elif action == "watch_remove":
            watch_remove(p["bid"], p.get("key", ""))
        elif action == "watch_place":
            watch_place(p["bid"], p.get("key", ""))
        elif action == "watch_move":
            control = xbmc.getInfoLabel("System.CurrentControlID")
            delta = int(p.get("delta", "0") or 0)
            if watch_move(p["bid"], p.get("key", ""), delta):
                follow = (control, delta)
        elif action == "place":
            place_entry(p["bid"], p.get("title", ""), p.get("year", 0), p.get("media", "tvshow"))
        elif action == "move":
            control = xbmc.getInfoLabel("System.CurrentControlID")
            delta = int(p.get("delta", "0") or 0)
            if move_entry(p["bid"], p.get("title", ""), p.get("year", 0), p.get("media", "tvshow"), delta):
                follow = (control, delta)
        if action not in NO_REFRESH:
            refresh()
        if follow:  # keep the highlight on the item that was just moved
            xbmc.sleep(250)
            xbmc.executebuiltin("Control.Move({},{})".format(*follow))
        finish_click()


if __name__ == "__main__":
    router(sys.argv[2][1:])
