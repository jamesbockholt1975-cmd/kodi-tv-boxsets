# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Background service: keep the home screen rows up to date.

The "Boxsets" and "Continue watching" rows show watched progress, which changes when you
play something or when the library is updated. This watches for those events and bumps the
reload property (see skinpatch.RELOAD_PROPERTY). It waits for a quiet moment first, so a
burst of events (marking a whole boxset watched, say) causes a single refresh.
"""

import os
import time

import xbmc

import badges
import store
import tagsync
import libnodes

EVENTS = {"VideoLibrary.OnUpdate", "VideoLibrary.OnScanFinished", "VideoLibrary.OnRemove",
          "VideoLibrary.OnCleanFinished", "Player.OnStop"}
# Library changes that can add/remove items (or change their ids) and so need new badge files.
LIBRARY_EVENTS = {"VideoLibrary.OnScanFinished", "VideoLibrary.OnRemove", "VideoLibrary.OnCleanFinished"}
QUIET_SECONDS = 2.0


class Debouncer:
    """Collapses a burst of events into one 'due' signal after things go quiet."""

    def __init__(self, quiet=QUIET_SECONDS, clock=time.monotonic):
        self.quiet, self.clock = quiet, clock
        self.pending, self.last = False, 0.0

    def event(self):
        self.pending, self.last = True, self.clock()

    def due(self):
        return self.pending and self.clock() - self.last >= self.quiet

    def fired(self):
        self.pending = False


class Watcher(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.debounce = Debouncer()          # home rows
        self.badge_debounce = Debouncer()    # badge files
        self.tag_debounce = Debouncer(quiet=2.5)  # Kodi tags: soon after a change, but batch quick edits

    def onNotification(self, sender, method, data):
        if method in EVENTS:
            self.debounce.event()
        if method in LIBRARY_EVENTS:
            self.badge_debounce.event()
            self.tag_debounce.event()

    def onSettingsChanged(self):
        store.publish_flags()
        self.debounce.event()
        self.badge_debounce.event()
        self.tag_debounce.event()


def _mtime():
    try:
        return os.path.getmtime(store.DATA_FILE)
    except OSError:
        return 0


def run():
    monitor = Watcher()
    store.bump_reload()  # rows start fresh after Kodi starts
    store.publish_flags()
    badges.sync_badges()
    if store.setting_bool("auto_tags", True):
        tagsync.sync(quiet=True)
    if store.setting_bool("library_nodes", False):
        libnodes.write()
    last_mtime = _mtime()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
        if monitor.debounce.due():
            monitor.debounce.fired()
            store.bump_reload()
        now = _mtime()
        if now != last_mtime:  # boxsets were edited (by the add-on or a right-click script)
            last_mtime = now
            monitor.badge_debounce.event()
            monitor.tag_debounce.event()
        if monitor.badge_debounce.due():
            monitor.badge_debounce.fired()
            badges.sync_badges()
        if monitor.tag_debounce.due():
            monitor.tag_debounce.fired()
            if store.setting_bool("auto_tags", True):  # re-read: the user may have switched it
                tagsync.sync(quiet=True)
            if store.setting_bool("library_nodes", False):
                libnodes.write()


if __name__ == "__main__":
    run()
