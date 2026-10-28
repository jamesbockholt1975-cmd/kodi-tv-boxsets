#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Feature tests for the TV Boxsets add-on, run against stand-in Kodi modules.

Usage:  python3 tests/run_tests.py

Nothing here talks to a real Kodi: tests/kodi_mocks/ fakes the `xbmc*` modules and
everything happens in a throw-away temp folder. It checks the add-on's logic
(views, storage, backups, skin patching); it cannot check how Kodi renders anything.
"""
import atexit
import glob
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.abspath(os.path.join(HERE, "..", "plugin.video.tvboxsets"))

ROOT = tempfile.mkdtemp(prefix="tvboxsets-test-")
atexit.register(shutil.rmtree, ROOT, True)
os.environ["TVB_TEST_ROOT"] = ROOT
for d in ("home/addons", "xbmc/addons/skin.estuary/xml", "xbmc/addons/skin.estuary/media",
          "profile/addon_data/skin.estuary", "temp", "log"):
    os.makedirs(os.path.join(ROOT, d))
shutil.copy(os.path.join(HERE, "fixtures", "Home.xml"),
            os.path.join(ROOT, "xbmc/addons/skin.estuary/xml/Home.xml"))
for _name in os.listdir(os.path.join(HERE, "fixtures", "xml")):  # tiny stand-ins for the view files
    shutil.copy(os.path.join(HERE, "fixtures", "xml", _name), os.path.join(ROOT, "xbmc/addons/skin.estuary/xml", _name))
os.environ["TVB_ADDON_PATH"] = ADDON + os.sep
with open(os.path.join(ROOT, "xbmc/addons/skin.estuary/addon.xml"), "w") as f:
    f.write('<addon id="skin.estuary" version="6.0.0" name="Estuary" provider-name="x"><requires/></addon>')
with open(os.path.join(ROOT, "xbmc/addons/skin.estuary/media/Textures.xbt"), "w") as f:
    f.write("x")
with open(os.path.join(ROOT, "profile/addon_data/skin.estuary/settings.xml"), "w") as f:
    f.write('<settings><setting id="home_no_tvshows_categories_widget">false</setting></settings>')
os.chdir(ROOT)

sys.path[:0] = [os.path.join(HERE, "kodi_mocks"), ADDON]
sys.argv = ["plugin://plugin.video.tvboxsets/", "1", ""]

import json  # noqa: E402
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, store, skinpatch, diagnostics  # noqa: E402
import library, ctxutil, badges, service, tagsync, labelimg, skinpatch  # noqa: E402
import main  # noqa: E402

D = xbmcgui.Dialog
CHECKS = [0, 0]


def ok(cond, msg):
    CHECKS[0] += 1
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        CHECKS[1] += 1
        sys.exit("Test failed: " + msg)


def nomod(data):
    return {k: {kk: vv for kk, vv in v.items() if kk != "modified"} for k, v in data.items()}


def run(query, skin="skin.estuary"):
    xbmcplugin.ITEMS.clear(); xbmc.SKIN = skin; xbmc.BUILTINS.clear(); D.Q.clear(); D.LOG.clear()
    main.router(query)
    return list(xbmcplugin.ITEMS)


def runq(query, **scripted):
    xbmcplugin.ITEMS.clear(); xbmc.BUILTINS.clear(); D.LOG.clear()
    D.Q.clear(); D.Q.update({k: list(v) for k, v in scripted.items()})
    main.router(query)
    return list(xbmcplugin.ITEMS)


xbmc.LIB = [
    {"tvshowid": 1, "title": "Alpha", "year": 2010, "art": {"poster": "pA", "fanart": "fA"},
     "episode": 10, "watchedepisodes": 4, "plot": "a", "genre": ["Drama"], "studio": ["HBO"], "tag": ["Franchise"]},
    {"tvshowid": 2, "title": "Beta", "year": 2015, "art": {"poster": "pB"},
     "episode": 8, "watchedepisodes": 8, "plot": "b", "genre": ["Comedy"], "studio": ["HBO"], "tag": []},
    {"tvshowid": 3, "title": "Gamma", "year": 2020, "art": {"poster": "pG", "fanart": "fG"},
     "episode": 5, "watchedepisodes": 0, "plot": "g", "genre": ["Drama", "Sci-Fi"], "studio": ["BBC"], "tag": ["Franchise"]},
]
store.save({"b1": {"name": "Saga", "shows": [
    {"title": "Gamma", "year": 2020}, {"title": "Alpha", "year": 2010},
    {"title": "Beta", "year": 2014}, {"title": "Zeta", "year": 1999}],
    "poster": "", "fanart": ""}})  # Beta's year differs (fuzzy match); Zeta isn't in the library
store.save(store.load())          # second save creates today's automatic backup

print("== root view: progress, missing, tools")
items = run("")
tile = [i for i in items if i[0].label == "Saga"][0][0]
ok(tile.props["TotalEpisodes"] == "23" and tile.props["WatchedEpisodes"] == "12", "tile progress 12/23")
ok("1 not currently" in tile.tag.d["Plot"], "tile plot mentions the missing show")
labels = [i[0].label for i in items]
ok(labels == ["Saga"], "boxset list shows only boxsets (no Create/Tools/setup rows): %s" % labels)
menu_labels = [l for l, _ in main.menu_entries()]
ok(all(any(k in l for l in menu_labels) for k in ("Create new boxset", "Create new smart", "Add 'Boxsets' to the home screen", "Export a backup", "Import a backup", "Restore an automatic", "from Kodi tags", "to Kodi tags", "Refresh the home screen rows", "diagnostics")),
   "everything that used to be a row is in the Boxsets menu")
ok(all(any(k in c[0] for c in tile.ctx) for k in (
    "Play next unwatched", "artwork", "order", "Smart rules", "Mark everything as watched", "Add movies", "Kodi tags", "Boxsets menu")),
   "tile context menu has play/artwork/order/smart/mark/movies/tags and the Boxsets menu")
ok(not [1 for m, p in xbmc.RPC_LOG if m == "VideoLibrary.GetMovies"], "TV-only boxsets never query the movie library")
ok([i[0].label for i in run("action=widget")] == ["Saga"], "widget view shows boxsets only")

print("== open boxset (A-Z, fuzzy year match, missing entry)")
items = run("action=open&bid=b1")
names = [i[0].label for i in items]
ok(names[:3] == ["Alpha", "Beta", "Gamma"], "alphabetical order; Beta matched despite year mismatch")
ok("not in library" in names[3] and items[3][2] is False, "missing show shown greyed, non-folder")
ok(items[1][0].tag.d.get("Playcount") == 1, "fully watched show flagged watched")
ok(items[0][0].props["UnWatchedEpisodes"] == "6", "show unwatched count")
ok(items[0][1].startswith("videodb://tvshows/titles/1/"), "links into the native library node")

print("== manual order")
runq("action=reorder&bid=b1", select=[1, 2, -1], numeric=["1"])
ok(store.load()["b1"]["manual_order"] is True, "manual order saved")
ok(run("action=open&bid=b1")[0][0].label == "Gamma", "Gamma moved to the top")
runq("action=reorder&bid=b1", select=[0])
ok(store.load()["b1"]["manual_order"] is False, "back to A-Z")
runq("action=reorder&bid=b1", select=[1, 0, -1], numeric=["1"])

print("== custom artwork")
runq("action=art&bid=b1&kind=poster", select=[0], browseSingle=["C:/art/saga.jpg"])
runq("action=art&bid=b1&kind=fanart", select=[1, 0])
b = store.load()["b1"]
ok(b["poster"] == "C:/art/saga.jpg", "custom poster from file")
ok(b["fanart"] != "", "fanart taken from a show")
tile = [i for i in run("") if i[0].label == "Saga"][0][0]
ok(tile.art["poster"] == "C:/art/saga.jpg" and tile.art["fanart"] == b["fanart"], "tile uses custom poster + fanart")
runq("action=art&bid=b1&kind=poster", select=[2])
ok(store.load()["b1"]["poster"] == "", "reset to automatic")

print("== play next unwatched")
xbmc.EPISODES = {3: [{"episodeid": 302, "season": 1, "episode": 2}, {"episodeid": 301, "season": 1, "episode": 1}]}
xbmc.RPC_LOG.clear(); runq("action=play_next&bid=b1")
opens = [p for m, p in xbmc.RPC_LOG if m == "Player.Open"]
ok(opens and opens[0]["item"]["episodeid"] == 301 and opens[0]["options"]["resume"], "plays S1E1 of first show with unwatched, resume on")
flt = [p for m, p in xbmc.RPC_LOG if m == "VideoLibrary.GetEpisodes"][0]["filter"]
ok(any(f["field"] == "season" for f in flt["and"]), "specials excluded by filter")
xbmc.EPISODES = {}; xbmc.RPC_LOG.clear(); runq("action=play_next&bid=b1")
ok(not [1 for m, p in xbmc.RPC_LOG if m == "Player.Open"], "nothing to play: no Player.Open")

print("== tags -> boxsets")
xbmc.TAGS = {"tvshow": ["Franchise", "Empty"], "movie": []}
runq("action=from_tags", multiselect=[[0, 1]])
d = store.load(); fid = store.find_by_name(d, "Franchise")
ok(fid and [r["title"] for r in d[fid]["shows"]] == ["Alpha", "Gamma"], "boxset created from tag with its shows")
ok(store.find_by_name(d, "Empty") is None, "tag with no shows ignored")

print("== backup / restore")
os.makedirs("out", exist_ok=True)
runq("action=export", browseSingle=[os.path.abspath("out") + "/"])
files = glob.glob("out/tvboxsets-backup-*.json")
ok(len(files) == 1, "export wrote a file")
d = store.load(); del d[fid]; store.save(d)
ok(store.find_by_name(store.load(), "Franchise") is None, "deleted a boxset")
runq("action=import_backup", browseSingle=[os.path.abspath(files[0])], select=[0])
ok(store.find_by_name(store.load(), "Franchise"), "merge import brought it back")
with open("out/bad.json", "w") as f:
    f.write('{"x": 5}')
runq("action=import_backup", browseSingle=[os.path.abspath("out/bad.json")])
ok(any(k == "ok" and "doesn't look like" in v for k, v in D.LOG), "rejects non-backup files")
ok(len(store.list_auto_backups()) >= 1, "automatic backup exists")
store.save({"only": {"name": "Temp", "shows": []}})
runq("action=restore_auto", select=[0, 1], yesno=[True])
ok(store.find_by_name(store.load(), "Saga"), "restored from automatic backup (replace)")

print("== skin: install, widget, settings seed")
runq("action=install_skin", yesno=[True, False])
cl = "home/addons/skin.estuary.boxsets"
ok(os.path.isdir(cl), "skin copy created")
hx = open(cl + "/xml/Home.xml", encoding="utf-8").read()
ok("Property(id),tvboxsets" in hx and "ActivateWindow(Videos,plugin://plugin.video.tvboxsets/,return)" in hx, "menu item + widget present")
ok("skin.estuary.boxsets" in open(cl + "/addon.xml").read(), "addon id changed")
ok(os.path.isfile("profile/addon_data/skin.estuary.boxsets/settings.xml"), "Estuary skin settings copied across")
ok("skin.estuary.boxsets" in xbmc.ENABLED, "skin enabled via JSON-RPC")
ok(not main.skin_outdated(), "not outdated right after build")
xbmc.SKIN = "skin.estuary"
ok(any(l.startswith("Switch to") for l, _ in main.menu_entries()), "menu offers the switch-to entry")
xbmc.SKIN = "skin.estuary.boxsets"
ok(not any(l.startswith("Switch to") for l, _ in main.menu_entries()), "no switch-to entry once the skin is active")
xbmc.SKIN = "skin.estuary"

import xml.etree.ElementTree as ET, collections  # noqa: E402
tree = ET.parse(cl + "/xml/Home.xml")
ids = [e.get("id") for e in tree.iter("control") if e.get("id")]
ok(not [i for i, c in collections.Counter(ids).items() if c > 1], "patched Home.xml is well-formed with no duplicate control ids")
ok(sum(1 for e in tree.iter("item") if (e.findtext("label") or "").strip() == "Boxsets") == 1, "exactly one Boxsets menu item")
ok(skinpatch.patch_widget(cl + "/xml/Home.xml") is False, "patching twice is a no-op")

print("== skin: outdated detection + rebuild")
with open("xbmc/addons/skin.estuary/addon.xml", "w") as f:
    f.write('<addon id="skin.estuary" version="6.1.0" name="Estuary" provider-name="x"><requires/></addon>')
ok(main.skin_outdated(), "Estuary update detected")
xbmc.SKIN = "skin.estuary"
ok(any("rebuild" in l.lower() and "updated" in l.lower() for l, _ in main.menu_entries()), "menu flags that Estuary was updated")
with open("profile/addon_data/skin.estuary.boxsets/settings.xml", "w") as f:
    f.write("<settings>MY-CHANGE</settings>")
xbmc.SKIN = "skin.estuary.boxsets"; D.LOG.clear(); main.rebuild_skin()
ok(any(k == "ok" and "can't be rebuilt safely" in v for k, v in D.LOG), "rebuild blocked while the Boxsets skin is active")
xbmc.SKIN = "skin.estuary"; D.Q.clear(); D.Q.update({"yesno": [True, False]}); main.rebuild_skin()
ok('version="6.1.0"' in open(cl + "/addon.xml").read(), "rebuilt from newer Estuary")
ok("Property(id),tvboxsets" in open(cl + "/xml/Home.xml", encoding="utf-8").read(), "rebuilt skin has item + widget")
ok("MY-CHANGE" in open("profile/addon_data/skin.estuary.boxsets/settings.xml").read(), "skin settings kept across rebuild")
ok(not main.skin_outdated(), "no longer outdated")
os.remove("xbmc/addons/skin.estuary/xml/Home.xml")  # break the source: the build must fail safely
with open("xbmc/addons/skin.estuary/addon.xml", "w") as f:
    f.write('<addon id="skin.estuary" version="6.2.0" name="Estuary" provider-name="x"><requires/></addon>')
D.Q.clear(); D.Q.update({"yesno": [True]}); main.rebuild_skin()
ok('version="6.1.0"' in open(cl + "/addon.xml").read() and os.path.exists(cl + "/xml/Home.xml"),
   "failed rebuild leaves the working skin untouched")
ok(os.listdir("temp") == [], "no temp build folders left behind")

print("== context menus")
import context, context_remove  # noqa: E402
store.save({"b1": {"name": "Saga", "shows": [{"title": "Alpha", "year": 2010}]}})
xbmc.INFO.clear(); xbmc.INFO.update({"ListItem.DBID": "3"})
D.Q.clear(); D.Q.update({"multiselect": [[1]], "input": ["New Set"]}); context.main()
d = store.load(); nid = store.find_by_name(d, "New Set")
ok(nid and d[nid]["shows"][0]["title"] == "Gamma", "'Boxsets...' can start a new boxset and add the show")
D.Q.clear(); D.Q.update({"multiselect": [[0]]}); context.main()
ok(len(store.load()[nid]["shows"]) == 1 and D.LAST_MULTI["preselect"] == [0] and "New Set" in D.LAST_MULTI["options"][0], "the boxset it is already in comes up ticked; leaving it ticked changes nothing")
xbmc.INFO.clear()
xbmc.INFO.update({"Container.FolderPath": "plugin://plugin.video.tvboxsets/?action=open&bid=b1",
                  "ListItem.Title": "Alpha", "ListItem.Year": "2010"})
D.Q.clear(); D.Q.update({"yesno": [True]}); context_remove.main()
ok(store.load()["b1"]["shows"] == [], "context 'remove' works")


print("== data format + migration")
v1 = {"v1id": {"name": "Old Set", "shows": [{"title": "Alpha", "year": 2010}], "poster": "", "fanart": ""}}
if os.path.exists(store.PRE_MIGRATION_BACKUP):
    os.remove(store.PRE_MIGRATION_BACKUP)
with open(store.DATA_FILE, "w") as f:
    json.dump(v1, f)  # a bare dict, exactly what 0.5.0 wrote
ok(store.file_format() == 1 and store.load() == v1, "format 1 file loads unchanged")
with open(store.PRE_MIGRATION_BACKUP) as f:
    ok(json.load(f) == v1, "a copy is kept before the file is upgraded")
store.save(store.load())
raw = json.load(open(store.DATA_FILE))
ok(raw["format"] == 3 and nomod(raw["boxsets"]) == v1 and "saved_by" in raw, "saved in format 3")
ok(store.file_format() == 3 and nomod(store.load()) == v1, "format 3 reloads")
ok(store.parse(v1) == v1 and store.parse({"format": 2, "boxsets": v1}) == v1
   and store.parse({"x": 5}) is None and store.parse([1]) is None, "parse() accepts both formats, rejects junk")
future = {"format": 99, "boxsets": {"x": {"name": "Future", "shows": []}}}
with open(store.DATA_FILE, "w") as f:
    json.dump(future, f)
before = open(store.DATA_FILE).read()
ok(store.is_newer_format(), "newer format detected")
runq("action=create", input=["Should Not Save"])
ok(open(store.DATA_FILE).read() == before, "newer-format file left untouched")
ok(any(k == "ok" and "newer version" in v for k, v in D.LOG), "user is told to update the add-on")
runq("action=widget")
ok(not any(k == "ok" for k, v in D.LOG), "home widget stays silent (no dialog) on a newer file")
store.save(v1)

print("== settings")
for f in glob.glob(os.path.join(store.BACKUP_DIR, "boxsets-*.json")):
    os.remove(f)
for day in ("20240101", "20240102", "20240103", "20240104", "20240105"):
    with open(os.path.join(store.BACKUP_DIR, "boxsets-{}.json".format(day)), "w") as f:
        f.write(store.dump_text({}))
xbmcaddon.SETTINGS["keep_backups"] = 3
store.save(store.load())
left = sorted(f for f in os.listdir(store.BACKUP_DIR) if f.startswith("boxsets-"))
ok(len(left) == 3 and left[0] == "boxsets-20240104.json", "keep_backups=3 trims old backups: %s" % left)
ok(os.path.exists(store.PRE_MIGRATION_BACKUP), "pre-migration copy is never trimmed")
xbmcaddon.SETTINGS["keep_backups"] = 10
store.save({"b1": {"name": "Saga", "shows": [{"title": "Alpha", "year": 2010}, {"title": "Zeta", "year": 1999}]}})
ok(any("not in library" in i[0].label for i in run("action=open&bid=b1")), "missing shows shown by default")
xbmcaddon.SETTINGS["show_missing"] = False
ok(not any("not in library" in i[0].label for i in run("action=open&bid=b1")), "show_missing off hides them")
xbmcaddon.SETTINGS["show_missing"] = True
xbmc.LOGS.clear(); run("")
ok(not any("list_boxsets" in m for _, m in xbmc.LOGS), "no extra logging by default")
xbmcaddon.SETTINGS["debug_logging"] = True
xbmc.LOGS.clear(); run("")
ok(any("[TV Boxsets] list_boxsets" in m for _, m in xbmc.LOGS), "debug_logging adds [TV Boxsets] lines")
xbmcaddon.SETTINGS["debug_logging"] = False

print("== diagnostics report")
xbmc.INFO.clear()
xbmc.INFO.update({"System.BuildVersion": "22.0-RC1 (test)", "System.OSVersionInfo": "Windows 11 test"})
home = os.path.expanduser("~")
with open("log/kodi.log", "w") as f:
    f.write("\n".join(["INFO other stuff", "ERROR [TV Boxsets] skin build failed: {}/x".format(home),
                       "noise", "INFO plugin.video.tvboxsets did a thing", "INFO unrelated"]))
store.save({"b1": {"name": "Secret Boxset Name", "shows": [
    {"title": "Alpha", "year": 2010}, {"title": "Zeta Missing", "year": 1999}]}})
runq("action=diagnostics", select=[0])
text = [v for k, v in D.LOG if k == "textviewer"][0]
ok("22.0-RC1" in text and "Windows 11 test" in text, "report has Kodi + OS version")
ok("Boxsets: 1" in text and "Show entries in boxsets: 2" in text and "Entries not found in the library: 1" in text, "report has counts")
ok("Data file format: 3" in text and "supports" not in text.split("[Add-on]")[0], "report has data format")
ok(all(n not in text for n in ("Secret Boxset Name", "Alpha", "Zeta Missing")), "no show or boxset names in the report")
ok(home not in text and "<user-home>" in text, "user's home path scrubbed")
ok("skin build failed" in text and "did a thing" in text and "other stuff" not in text and "unrelated" not in text,
   "only the add-on's own log lines included")
runq("action=diagnostics", select=[1], browseSingle=[os.path.abspath("out") + "/"])
ok(len(glob.glob("out/tvboxsets-diagnostics-*.txt")) == 1, "report can be saved to a folder")
ok(diagnostics.scrub("/a/b/c", [("/a", "<A>"), ("/a/b", "<AB>")]) == "<AB>/c", "scrub replaces longest path first")
ok(len(diagnostics.filter_log(["[TV Boxsets] %d" % i for i in range(500)])) == diagnostics.MAX_LOG_LINES, "log lines capped")


print("== format 2 -> 3 migration")
d2 = {"format": 2, "saved_by": "0.6.1", "boxsets": {"x": {"name": "Two", "shows": [{"title": "Alpha", "year": 2010}], "poster": "", "fanart": ""}}}
if os.path.exists(store.PRE_MIGRATION_BACKUP):
    os.remove(store.PRE_MIGRATION_BACKUP)
with open(store.DATA_FILE, "w") as f:
    json.dump(d2, f)
ok(store.file_format() == 2 and "x" in store.load(), "format 2 file loads")
ok(os.path.exists(store.PRE_MIGRATION_BACKUP) and "pre-format3" in store.PRE_MIGRATION_BACKUP
   and json.load(open(store.PRE_MIGRATION_BACKUP)) == d2, "copy of the old file kept before upgrading to format 3")
store.save(store.load())
ok(store.file_format() == 3, "saved as format 3")

print("== smart-boxset rules (pure logic)")
import rules  # noqa: E402
item = {"title": "Star Trek", "year": 1966, "genre": ["Sci-Fi", "Drama"], "studio": ["Paramount"], "tag": ["Classic"]}
ok(rules.matches({"genre": "drama"}, item) and not rules.matches({"genre": "Comedy"}, item), "genre match, case-insensitive")
ok(rules.matches({"studio": "paramount", "tag": "classic"}, item), "studio + tag")
ok(not rules.matches({}, item) and not rules.matches({"media": "both"}, item), "rules with no filters match nothing")
ok(rules.matches({"year_min": 1960, "year_max": 1970}, item) and not rules.matches({"year_min": 1970}, item)
   and not rules.matches({"year_max": 1950}, item), "year range")
ok(not rules.matches({"year_min": 1900}, {"title": "x", "year": 0}), "unknown year never matches a year rule")
ok(rules.matches({"title_contains": "TREK"}, item) and not rules.matches({"title_contains": "wars"}, item), "title contains")
ok(not rules.matches({"genre": "Drama", "year_min": 2000}, item), "all filters must match (AND)")
ok(rules.media({}) == "tv" and rules.media({"media": "both"}) == "both" and rules.media({"media": "junk"}) == "tv", "media defaults to tv")
ok(rules.describe({"media": "both", "genre": "Drama", "year_min": 2010, "year_max": 2020}) == "TV shows and movies; genre = Drama; years 2010-2020", "rules described in words")
ok(rules.facet([{"genre": ["drama", "Sci-Fi"]}, {"genre": ["Drama"]}], "genre") == ["drama", "Sci-Fi"], "facet de-duplicates case-insensitively")

print("== movies: mixed boxsets")
xbmc.MOVIES = [
    {"movieid": 10, "title": "Film One", "year": 2012, "art": {"poster": "pM1"}, "plot": "m", "genre": ["Drama"], "studio": ["Acme"], "tag": [], "playcount": 0},
    {"movieid": 11, "title": "Film Two", "year": 2015, "art": {}, "plot": "", "genre": ["Action"], "studio": [], "tag": [], "playcount": 1},
]
store.save({"m1": {"name": "Mixed", "shows": [{"title": "Alpha", "year": 2010}], "poster": "", "fanart": ""}})
runq("action=add_movies&bid=m1", multiselect=[[0, 1]])
refs = store.load()["m1"]["shows"]
ok([r.get("type") for r in refs] == [None, "movie", "movie"] and refs[1]["title"] == "Film One", "movies added with type 'movie'")
ok(store.show_key({"title": "Film Two", "year": 2015}) != store.show_key({"title": "Film Two", "year": 2015, "type": "movie"}), "a movie and a show with the same title are different entries")
tile = [i for i in run("") if i[0].label == "Mixed"][0][0]
ok(tile.props["TotalEpisodes"] == "12" and tile.props["WatchedEpisodes"] == "5", "progress counts episodes + movies (%s/%s)" % (tile.props["WatchedEpisodes"], tile.props["TotalEpisodes"]))
ok(tile.tag.d["Plot"].startswith("1 show(s), 2 movie(s); 5 of 12 watched"), "tile summary mentions movies")
items = run("action=open&bid=m1")
names = [i[0].label for i in items]
ML = lambda t: t + " [COLOR lightskyblue][Movie][/COLOR]"  # noqa: E731
ok(names[:3] == ["Alpha", ML("Film One"), ML("Film Two")] and items[0][2] is True, "mixed boxset lists shows and movies A-Z, movies labelled [Movie]")
ok("[Movie]" not in items[0][0].label, "shows are not labelled")
mi = items[1][0]
ok(mi.tag.d.get("Title") == ML("Film One") and mi.props.get("boxset_title") == "Film One", "the title the skin draws carries [Movie]; the real title is kept in a property")
ok(mi.props.get("boxset_movie") == "true" and "boxset_movie" not in items[0][0].props, "movies (not shows) are marked for the skin's MOVIE tag")
ok(items[1][2] is False and "action=play_movie&id=10" in items[1][1] and items[1][0].tag.d["MediaType"] == "movie", "movie item plays through the add-on")
ok(items[2][0].tag.d.get("Playcount") == 1, "watched movie flagged watched")
xbmc.RPC_LOG.clear(); runq("action=play_movie&id=10")
ok(any(m == "Player.Open" and p["item"] == {"movieid": 10} and p["options"]["resume"] for m, p in xbmc.RPC_LOG), "play_movie opens the movie with resume")
xbmc.EPISODES = {1: [{"episodeid": 101, "season": 1, "episode": 1, "playcount": 1}]}
xbmc.RPC_LOG.clear(); runq("action=play_next&bid=m1")
ok(any(m == "Player.Open" and p["item"] == {"movieid": 10} for m, p in xbmc.RPC_LOG), "play-next moves on to the first unwatched movie")
d = store.load(); d["m1"]["shows"].append({"title": "Ghost Film", "year": 1990, "type": "movie"}); store.save(d)
ghost = [i for i in run("action=open&bid=m1") if "Ghost Film" in i[0].label][0][0]
ok("not in library" in ghost.label and ghost.art["icon"] == "DefaultMovies.png", "missing movie shown greyed with a movie icon")
d = store.load(); d["m1"]["shows"] = [r for r in d["m1"]["shows"] if r["title"] not in ("Film Two", "Ghost Film")]; store.save(d)
xbmc.INFO.clear(); xbmc.INFO.update({"ListItem.DBID": "11", "ListItem.DBType": "movie"})
D.Q.clear(); D.Q.update({"multiselect": [[0]]}); context.main()
added = [r for r in store.load()["m1"]["shows"] if r["title"] == "Film Two"]
ok(added and added[0]["type"] == "movie" and added[0]["year"] == 2015, "right-click on a library movie adds it to a boxset")
xbmc.INFO.clear()
xbmc.INFO.update({"Container.FolderPath": "plugin://plugin.video.tvboxsets/?action=open&bid=m1", "ListItem.Title": "Film Two", "ListItem.Year": "2015", "ListItem.DBType": "movie"})
D.Q.clear(); D.Q.update({"yesno": [True]}); context_remove.main()
left = [r["title"] for r in store.load()["m1"]["shows"]]
ok("Film Two" not in left and "Alpha" in left and "Film One" in left, "context remove takes out just that movie")

print("== smart boxsets")
store.save({})
runq("action=create_smart", input=["Dramas"], select=[1, 2, 6])
d = store.load(); sid = store.find_by_name(d, "Dramas")
ok(sid and d[sid]["rules"] == {"media": "tv", "genre": "Drama"}, "smart boxset built through the rule editor")
ok([i[0].label for i in run("action=open&bid=%s" % sid)][:2] == ["Alpha", "Gamma"], "smart boxset fills itself from the library")
tile = [i for i in run("") if i[0].label == "Dramas"][0][0]
ok("Smart boxset: TV shows only; genre = Drama" in tile.tag.d["Plot"], "tile describes the rules")
runq("action=add&bid=%s" % sid, multiselect=[[1]])
ok([i[0].label for i in run("action=open&bid=%s" % sid)][:3] == ["Alpha", "Beta", "Gamma"], "a hand-picked show joins the smart matches")

def remove_via_context(bid, title, year, dbtype="tvshow"):
    xbmc.INFO.clear()
    xbmc.INFO.update({"Container.FolderPath": "plugin://plugin.video.tvboxsets/?action=open&bid=%s" % bid,
                      "ListItem.Title": title, "ListItem.Year": str(year), "ListItem.DBType": dbtype})
    D.Q.clear(); D.Q.update({"yesno": [True]}); context_remove.main()

remove_via_context(sid, "Alpha", 2010)
b = store.load()[sid]
ok([r["title"] for r in b["excluded"]] == ["Alpha"], "removing a rule match adds it to the exclusions")
ok([i[0].label for i in run("action=open&bid=%s" % sid)][:2] == ["Beta", "Gamma"], "excluded item stays out")
remove_via_context(sid, "Beta", 2015)
b = store.load()[sid]
ok(b["shows"] == [] and len(b["excluded"]) == 1, "removing a hand-picked show deletes it (no exclusion needed)")
d = store.load(); d[sid]["shows"] = [{"title": "Gamma", "year": 2020}]; d[sid]["manual_order"] = True; d[sid]["excluded"] = []; store.save(d)
ok([i[0].label for i in run("action=open&bid=%s" % sid)][:2] == ["Gamma", "Alpha"], "manual order: saved entries first, then smart matches A-Z (no duplicates)")
runq("action=create_smart", input=["Recent"], select=[4, 6], numeric=["2012", "2018"])
rid = store.find_by_name(store.load(), "Recent")
ok(store.load()[rid]["rules"] == {"media": "tv", "year_min": 2012, "year_max": 2018}, "year rule saved")
ok([i[0].label for i in run("action=open&bid=%s" % rid)][:1] == ["Beta"], "year rule selects only Beta (2015)")
runq("action=create_smart", input=["Nothing"], select=[6, -1])
ok(any(k == "ok" and "at least one rule" in v for k, v in D.LOG), "saving with no rules is refused")
ok(store.find_by_name(store.load(), "Nothing") is None, "cancelled smart boxset is not kept")
d = store.load(); d[rid]["rules"] = {"media": "both", "genre": "Drama"}; store.save(d)
ok([i[0].label for i in run("action=open&bid=%s" % rid)][:3] == ["Alpha", ML("Film One"), "Gamma"], "smart rules can include movies")
runq("action=rules&bid=%s" % rid, select=[7])
ok("rules" not in store.load()[rid], "rules can be removed, leaving a normal boxset")

print("== mark watched / unwatched")
store.save({"w1": {"name": "Watchlist", "shows": [{"title": "Alpha", "year": 2010}, {"title": "Film One", "year": 2012, "type": "movie"}], "poster": "", "fanart": ""}})
xbmc.MOVIES[0]["playcount"] = 0
xbmc.EPISODES = {1: [{"episodeid": 101, "season": 1, "episode": 1, "playcount": 1}, {"episodeid": 102, "season": 1, "episode": 2, "playcount": 0}]}
def sets():
    return [(m, p) for m, p in xbmc.RPC_LOG if m.startswith("VideoLibrary.Set")]
xbmc.RPC_LOG.clear(); runq("action=mark&bid=w1&watched=1", yesno=[False])
ok(not sets(), "cancelling the confirmation changes nothing")
xbmc.RPC_LOG.clear(); runq("action=mark&bid=w1&watched=1", yesno=[True])
calls = sets()
ok(sorted((m.split(".")[1], p.get("episodeid") or p.get("movieid")) for m, p in calls) == [("SetEpisodeDetails", 102), ("SetMovieDetails", 10)], "only items that weren't watched are updated")
ok(all(p["playcount"] == 1 and "lastplayed" in p and p["resume"] == {"position": 0, "total": 0} for _, p in calls), "marked watched with a play date and cleared resume points")
xbmc.RPC_LOG.clear(); runq("action=mark&bid=w1&watched=0", yesno=[True])
ok(sorted(p.get("episodeid") or p.get("movieid") for _, p in sets()) == [10, 101, 102] and all(p["playcount"] == 0 for _, p in sets()), "mark unwatched resets episodes and the movie")

print("== write boxsets to Kodi tags")
xbmc.LIB[0]["tag"] = ["Franchise", "Boxset: Old Set", "MyOwn"]; xbmc.LIB[1]["tag"] = []; xbmc.LIB[2]["tag"] = ["Franchise"]
xbmc.MOVIES[0]["tag"] = ["Boxset: Gone"]; xbmc.MOVIES[1]["tag"] = []
store.save({"s2": {"name": "Saga2", "shows": [{"title": "Alpha", "year": 2010}, {"title": "Beta", "year": 2015}, {"title": "Film Two", "year": 2015, "type": "movie"}], "poster": "", "fanart": ""}})
xbmcaddon.SETTINGS["tag_prefix"] = "Boxset:"
xbmc.RPC_LOG.clear(); runq("action=tag_sync")
tv = {p["tvshowid"]: p["tag"] for m, p in xbmc.RPC_LOG if m == "VideoLibrary.SetTVShowDetails"}
mv = {p["movieid"]: p["tag"] for m, p in xbmc.RPC_LOG if m == "VideoLibrary.SetMovieDetails"}
ok(tv.get(1) == ["Franchise", "MyOwn", "Boxset: Saga2"], "your own tags are kept, stale boxset tag replaced: %s" % tv.get(1))
ok(tv.get(2) == ["Boxset: Saga2"] and 3 not in tv, "other shows tagged only where needed")
ok(mv.get(11) == ["Boxset: Saga2"] and mv.get(10) == [], "movies tagged, and a stale boxset tag removed")
xbmc.RPC_LOG.clear(); runq("action=tag_sync")
ok(not [1 for m, p in xbmc.RPC_LOG if m.startswith("VideoLibrary.Set")], "running it again changes nothing")
xbmcaddon.SETTINGS["tag_prefix"] = ""
xbmc.RPC_LOG.clear(); runq("action=tag_sync")
ok(not [1 for m, p in xbmc.RPC_LOG if m.startswith("VideoLibrary.Set")] and any(k == "ok" and "prefix" in v for k, v in D.LOG), "an empty prefix is refused (so user tags can't be touched)")
xbmcaddon.SETTINGS["tag_prefix"] = "Set:"
xbmc.RPC_LOG.clear(); runq("action=tag_sync")
tv = {p["tvshowid"]: p["tag"] for m, p in xbmc.RPC_LOG if m == "VideoLibrary.SetTVShowDetails"}
ok("Set: Saga2" in tv.get(1, []) and "Boxset: Saga2" in tv.get(1, []), "a different prefix is a separate namespace")
xbmcaddon.SETTINGS["tag_prefix"] = "Boxset:"
xbmc.TAGS = {"tvshow": ["Boxset: Stripped"], "movie": []}
xbmc.LIB[2]["tag"] = ["Boxset: Stripped"]
runq("action=from_tags", multiselect=[[0]])
ok(store.find_by_name(store.load(), "Stripped"), "importing tags strips the boxset prefix from the name")

print("== sorting boxsets + continue-watching row")
store.save({"a": {"name": "Aaa-complete", "shows": [{"title": "Beta", "year": 2015}], "poster": "", "fanart": ""},
            "b": {"name": "Bbb-new", "shows": [{"title": "Gamma", "year": 2020}], "poster": "", "fanart": ""},
            "c": {"name": "Ccc-partial", "shows": [{"title": "Alpha", "year": 2010}], "poster": "", "fanart": ""}})
d = store.load(); d["a"]["modified"] = 200; d["b"]["modified"] = 300; d["c"]["modified"] = 100; store.save(d)
order = lambda q="": [i[0].label for i in run(q) if i[0].label in ("Aaa-complete", "Bbb-new", "Ccc-partial")]  # noqa: E731
ok(order() == ["Aaa-complete", "Bbb-new", "Ccc-partial"], "sort: name")
xbmcaddon.SETTINGS["boxset_sort"] = 1
ok(order() == ["Ccc-partial", "Bbb-new", "Aaa-complete"], "sort: in progress first, then unwatched, then finished")
xbmcaddon.SETTINGS["boxset_sort"] = 2
ok(order() == ["Bbb-new", "Aaa-complete", "Ccc-partial"], "sort: recently changed first")
xbmcaddon.SETTINGS["boxset_sort"] = 0
cw = run("action=widget&filter=in_progress")
ok([i[0].label for i in cw] == ["Alpha"] and cw[0][0].label2 == "Ccc-partial", "continue-watching row shows the show (boxset name as the second line)")
ok(cw[0][1].startswith("videodb://tvshows/titles/1/") and cw[0][2] is True and "Next up in the boxset 'Ccc-partial'" in cw[0][0].tag.d["Plot"], "tile opens the show's own seasons page")
runq("action=rename&bid=c", input=["Ccc-renamed"])
after = store.load()
ok(after["a"]["modified"] == 200 and after["b"]["modified"] == 300 and after["c"]["modified"] > 300, "only the boxset that changed gets a new 'modified' time")

print("== more artwork types")
store.save({"b1": {"name": "Art", "shows": [{"title": "Gamma", "year": 2020}], "poster": "", "fanart": ""}})
xbmc.LIB[2]["art"].update({"clearlogo": "clG", "landscape": "lsG"})
runq("action=art&bid=b1", select=[2, 0], browseSingle=["C:/art/banner.png"])
runq("action=art&bid=b1", select=[3, 1, 0])
runq("action=art&bid=b1&kind=landscape", select=[1, 0])
b = store.load()["b1"]
ok(b.get("banner") == "C:/art/banner.png" and b.get("clearlogo") == "clG" and b.get("landscape") == "lsG", "banner, clear logo and landscape can be set")
tile = [i for i in run("") if i[0].label == "Art"][0][0]
ok(tile.art["banner"] == "C:/art/banner.png" and tile.art["clearlogo"] == "clG" and tile.art["landscape"] == "lsG", "tile carries all artwork types")
before = store.load()["b1"].copy()
runq("action=art&bid=b1&kind=nonsense")
ok(store.load()["b1"] == before, "unknown artwork kind is ignored")

print("== home widget v2 upgrade")
fx = open(os.path.join(HERE, "fixtures", "Home.xml"), encoding="utf-8", newline="").read()
old_block = ('\t\t\t<control type="group" id="99000">\n'
             '\t\t\t\t<visible>String.IsEqual(Container(9000).ListItem.Property(id),tvboxsets)</visible>\n'
             '\t\t\t\t<control type="grouplist" id="99001">\n'
             '\t\t\t\t\t<include content="WidgetListPoster">\n'
             '\t\t\t\t\t\t<param name="content_path" value="plugin://plugin.video.tvboxsets/?action=widget"/>\n'
             '\t\t\t\t\t</include>\n\t\t\t\t</control>\n\t\t\t</control>\n')
os.makedirs("oldhome", exist_ok=True)
with open("oldhome/Home.xml", "w", encoding="utf-8", newline="") as f:
    f.write(fx.replace('\t\t\t<control type="group" id="7000">', old_block + '\t\t\t<control type="group" id="7000">', 1))
ok(not skinpatch.has_widget("oldhome/Home.xml"), "an old (v1) widget block is not counted as current")
ok(skinpatch.patch_widget("oldhome/Home.xml") is True and skinpatch.has_widget("oldhome/Home.xml"), "old block upgraded in place")
tree = ET.parse("oldhome/Home.xml")
groups = [e for e in tree.iter("control") if e.get("id") == "99000"]
rows = [i.find('param[@name="content_path"]').get("value") for i in groups[0].findall('.//include[@content="WidgetListPoster"]')]
ok(len(groups) == 1 and rows == [skinpatch.WIDGET_PATH, skinpatch.WIDGET_CONTINUE_PATH],
   "exactly one group, two rows; & correctly escaped and values read back unchanged")
ok(all("reload=$INFO[Window(Home).Property(tvboxsets_reload)]" in r for r in rows), "both rows carry the reload value")
# simulate the previous (v2) block: older marker, no reload value
text = open("oldhome/Home.xml", encoding="utf-8", newline="").read()
text = text.replace("tvboxsets-widget v3", "tvboxsets-widget v2").replace("&amp;reload=$INFO[Window(Home).Property(tvboxsets_reload)]", "")
with open("oldhome/Home.xml", "w", encoding="utf-8", newline="") as f:
    f.write(text)
ok(not skinpatch.has_widget("oldhome/Home.xml") and skinpatch.patch_widget("oldhome/Home.xml") is True, "a v2 block (no reload value) is upgraded to v3")
ok(sum(1 for e in ET.parse("oldhome/Home.xml").iter("control") if e.get("id") == "99000") == 1, "still exactly one widget group after upgrading from v2")
ok(skinpatch.patch_widget("oldhome/Home.xml") is False, "upgrade is idempotent")

print("== diagnostics knows the new things")
store.save({"m1": {"name": "Mixed", "shows": [{"title": "Film One", "year": 2012, "type": "movie"}], "rules": {"media": "tv", "genre": "Drama"}, "poster": "", "fanart": ""}})
runq("action=diagnostics", select=[0])
text = [v for k, v in D.LOG if k == "textviewer"][0]
ok("Movie entries: 1; smart boxsets: 1" in text and "boxset_sort=0" in text and "tag_prefix='Boxset:'" in text, "report includes movie/smart counts and the new settings")


print("== home rows refresh when boxsets change (the reload fix)")
import service  # noqa: E402
prop = skinpatch.RELOAD_PROPERTY
def current():
    return xbmcgui.Window(10000).getProperty(prop)
store.save({"r1": {"name": "Refresh", "shows": [], "poster": "", "fanart": ""}})
first = current()
ok(first != "", "saving boxsets sets the home-window reload value")
import time as _t; _t.sleep(0.01)
runq("action=create", input=["Brand New"], yesno=[False])
ok(current() != first, "creating a boxset changes the reload value (so the row reloads)")
second = current(); _t.sleep(0.01)
runq("action=add&bid=r1", multiselect=[[0]])
ok(current() != second, "adding a show changes the reload value")
third = current(); _t.sleep(0.01)
xbmc.INFO.clear(); xbmc.INFO.update({"ListItem.DBID": "1", "ListItem.DBType": "tvshow"})
D.Q.clear(); D.Q.update({"multiselect": [[0]]}); context.main()
ok(current() != third, "the right-click 'Boxsets...' also refreshes the rows")
before = current(); _t.sleep(0.01)
runq("action=refresh_widgets")
ok(current() != before, "Tools > Refresh the home screen rows works as a manual fallback")
ok(all(skinpatch.RELOAD_PROPERTY in r for r in (skinpatch.WIDGET_PATH, skinpatch.WIDGET_CONTINUE_PATH)), "row addresses reference the property the add-on sets")

now = [100.0]
deb = service.Debouncer(quiet=2.0, clock=lambda: now[0])
ok(not deb.due(), "debouncer: nothing pending at first")
deb.event(); now[0] = 100.5; deb.event(); now[0] = 101.9
ok(not deb.due(), "debouncer: still busy while events keep arriving")
now[0] = 102.6
ok(deb.due(), "debouncer: fires once things have been quiet for 2 seconds")
deb.fired()
ok(not deb.due(), "debouncer: a burst of events gives just one refresh")
w = service.Watcher()
w.onNotification("xbmc", "Player.OnStop", "{}")
ok(w.debounce.pending, "service reacts to playback stopping")
w.debounce.fired(); w.onNotification("xbmc", "VideoLibrary.OnUpdate", "{}")
ok(w.debounce.pending, "service reacts to library updates")
w.debounce.fired(); w.onNotification("xbmc", "Application.OnVolumeChanged", "{}")
ok(not w.debounce.pending, "service ignores unrelated notifications")
mark = current(); _t.sleep(0.01)
service.run()
ok(current() != mark, "service refreshes the rows when it starts")
svc = ET.parse(os.path.join(ADDON, "addon.xml")).getroot().find("extension[@point='xbmc.service']")
ok(svc is not None and svc.get("library") == "service.py" and os.path.exists(os.path.join(ADDON, "service.py")), "addon.xml registers the service")


print("== cleaner lists: the extra rows moved into the right-click menu")
store.save({})
items = run("")
ok(len(items) == 1 and "Create your first boxset" in items[0][0].label and "action=create" in items[0][1]
   and any("Boxsets menu" in c[0] for c in items[0][0].ctx), "empty list: one 'create your first boxset' row, with the menu on right-click")
store.save({"e1": {"name": "Empty", "shows": [], "poster": "", "fanart": ""}})
items = run("action=open&bid=e1")
ok(len(items) == 1 and "empty" in items[0][0].label.lower() and "action=add" in items[0][1], "empty boxset: one 'add shows' row, nothing else")
store.save({"b1": {"name": "Saga", "shows": [{"title": "Alpha", "year": 2010}, {"title": "Beta", "year": 2015}], "poster": "", "fanart": ""}})
ok([i[0].label for i in run("action=open&bid=b1")] == ["Alpha", "Beta"], "inside a boxset: just the shows (no Play/Add rows)")
labels = [l for l, _ in main.menu_entries()]
runq("action=menu", select=[labels.index("Create new boxset")], input=["Via Menu"], yesno=[False])
ok(store.find_by_name(store.load(), "Via Menu"), "choosing 'Create new boxset' in the Boxsets menu works")
runq("action=tools", select=[-1])
ok(any(k == "select" for k, _ in D.LOG), "the old Tools link now opens the same menu")

print("== continue watching: the show to carry on with")
xbmc.MOVIES[0].update({"playcount": 0, "tag": []})
xbmc.LIB[0]["episode"], xbmc.LIB[0]["watchedepisodes"] = 10, 4
xbmc.LIB[1]["episode"], xbmc.LIB[1]["watchedepisodes"] = 8, 8
xbmc.LIB[2]["episode"], xbmc.LIB[2]["watchedepisodes"] = 5, 0
A, B, G = ({"title": "Alpha", "year": 2010}, {"title": "Beta", "year": 2015}, {"title": "Gamma", "year": 2020})
F1 = {"title": "Film One", "year": 2012, "type": "movie"}
box = lambda name, shows: {"name": name, "shows": shows, "poster": "", "fanart": ""}  # noqa: E731
store.save({"p1": box("P1", [G, A]), "p2": box("P2", [B, G]), "p3": box("P3", [A, F1]), "p4": box("P4", [B, F1]),
            "p5": box("P5", [B]), "p6": box("P6", [G])})
cw = run("action=widget&filter=in_progress")
ok([i[0].label for i in cw] == ["Alpha", "Gamma", "Film One"], "partly-watched show preferred, else first unwatched, shows listed once: %s" % [i[0].label for i in cw])
ok([i[0].label2 for i in cw] == ["P1", "P2", "P4"], "each tile names its boxset on the second line")
ok(cw[2][2] is False and "action=play_movie&id=10" in cw[2][1], "an unwatched movie is offered as a play tile")
ok("P5" not in [i[0].label2 for i in cw] and "P6" not in [i[0].label2 for i in cw], "finished and not-started boxsets are left out")

print("== move up / move down")
from urllib.parse import urlencode  # noqa: E402
def mv(bid, title, year, delta, media="tvshow"):
    xbmc.INFO["System.CurrentControlID"] = "50"
    xbmc.BUILTINS.clear()
    runq("action=move&" + urlencode({"bid": bid, "title": title, "year": year, "media": media, "delta": delta}))
    return [c for c in xbmc.BUILTINS if c.startswith("Control.Move")]
titles = lambda bid: [i[0].label for i in run("action=open&bid=" + bid)]  # noqa: E731
store.save({"mv": box("Order", [A, B, G])})
ok(mv("mv", "Gamma", 2020, -1) == ["Control.Move(50,-1)"] and titles("mv") == ["Alpha", "Gamma", "Beta"], "move up (A-Z becomes a manual order); highlight follows the item")
b = store.load()["mv"]
ok(b["manual_order"] is True and [r["title"] for r in b["order"]] == ["Alpha", "Gamma", "Beta"] and [r["title"] for r in b["shows"]] == ["Alpha", "Beta", "Gamma"], "order saved separately; membership untouched")
ok(mv("mv", "Alpha", 2010, 1) == ["Control.Move(50,1)"] and titles("mv") == ["Gamma", "Alpha", "Beta"], "move down")
ok(mv("mv", "Gamma", 2020, -1) == [] and titles("mv") == ["Gamma", "Alpha", "Beta"], "already first: nothing changes, no highlight move")
ok(mv("mv", "Beta", 2015, 1) == [] and titles("mv") == ["Gamma", "Alpha", "Beta"], "already last: nothing changes")
ok(mv("mv", "Alpha", 1999, 1) != [] and titles("mv") == ["Gamma", "Beta", "Alpha"], "a year mismatch falls back to the title")
d = store.load(); d["mv"]["shows"].append({"title": "Film One", "year": 2012, "type": "movie"}); store.save(d)
ok(titles("mv") == ["Gamma", "Beta", "Alpha", ML("Film One")], "something added later goes to the end of a manual order")
ok(mv("mv", "Film One", 2012, -1, "movie") != [] and titles("mv")[2] == ML("Film One"), "movies move too")
store.save({"sm": dict(box("Smart", [B]), rules={"media": "tv", "genre": "Drama"})})
ok(titles("sm") == ["Alpha", "Beta", "Gamma"], "smart boxset starts A-Z")
ok(mv("sm", "Gamma", 2020, -1) != [] and titles("sm") == ["Alpha", "Gamma", "Beta"], "smart boxsets can be ordered too")
ok([r["title"] for r in store.load()["sm"]["shows"]] == ["Beta"], "smart matches were not turned into saved entries")
runq("action=reorder&bid=sm", select=[1, 1, -1], numeric=["1"])  # starts from the order shown: Alpha, Gamma, Beta
ok(titles("sm")[0] == "Gamma" and [r["title"] for r in store.load()["sm"]["shows"]] == ["Beta"], "the 'Change show order' dialog also works on smart boxsets")
runq("action=reorder&bid=sm", select=[0])
ok("order" not in store.load()["sm"] and titles("sm") == ["Alpha", "Beta", "Gamma"], "choosing A-Z again clears the manual order")

print("== right-click scripts inside a boxset")
import runpy  # noqa: E402
xbmc.INFO.clear()
xbmc.INFO.update({"Container.FolderPath": "plugin://plugin.video.tvboxsets/?action=open&bid=mv",
                  "ListItem.Title": "Gamma", "ListItem.Year": "2020", "ListItem.DBType": "tvshow"})
def run_script(name):
    xbmc.BUILTINS.clear()
    runpy.run_path(os.path.join(ADDON, name), run_name="__main__")
    return xbmc.BUILTINS[-1]
cmd = run_script("ctx_move_up.py")
ok(cmd.startswith("RunPlugin(plugin://plugin.video.tvboxsets/?") and all(x in cmd for x in ("action=move", "bid=mv", "title=Gamma", "year=2020", "media=tvshow", "delta=-1")), "Move up script hands the right details to the add-on")
ok("delta=1" in run_script("ctx_move_down.py") and "action=move" in run_script("ctx_move_down.py"), "Move down script")
ok("action=play_next" in run_script("ctx_play_next.py") and "bid=mv" in run_script("ctx_play_next.py"), "Play next script")
ok("action=add&" in run_script("ctx_add_shows.py") + "&" and "bid=mv" in run_script("ctx_add_shows.py"), "Add shows script")
ok("action=add_movies" in run_script("ctx_add_movies.py"), "Add movies script")
ok("action=menu" in run_script("ctx_menu.py"), "Boxsets menu script")
xbmc.INFO["ListItem.DBType"] = "movie"
ok("media=movie" in run_script("ctx_move_up.py"), "Move script knows when the highlighted item is a movie")
addon_root = ET.parse(os.path.join(ADDON, "addon.xml")).getroot()
ctx_items = list(addon_root.iter("item"))
ok(all(os.path.exists(os.path.join(ADDON, i.get("library"))) for i in ctx_items), "every right-click item's script file exists (%d items)" % len(ctx_items))
ok(len({i.findtext("label") for i in ctx_items}) == len(ctx_items), "right-click labels are all different")
inside = [i for i in ctx_items if i.get("library") != "context.py"]
ok(all(("action=open" in i.findtext("visible") or "action=watch" in i.findtext("visible")) for i in inside), "in-boxset items only show while browsing a boxset or its watch order")
ok(all("boxset_action" in i.findtext("visible") for i in inside if i.get("library") in ("ctx_move_up.py", "ctx_move_down.py", "context_remove.py")), "Move/Remove are hidden on placeholder rows")

print("== place an item after another")
store.save({"pl": box("Placing", [A, B, G, {"title": "Film One", "year": 2012, "type": "movie"}])})
plain = lambda bid: [__import__("re").sub(r"\s*\[[^\]]*\]", "", t).strip() for t in titles(bid)]  # noqa: E731
def place(bid, title, year, media, pick):
    runq("action=place&" + urlencode({"bid": bid, "title": title, "year": year, "media": media}), select=[pick])
ok(plain("pl") == ["Alpha", "Beta", "Film One", "Gamma"], "starting order is A-Z")
place("pl", "Film One", 2012, "movie", 1)  # list: [At the start], 1. Alpha, 2. Beta, 3. Gamma -> after Alpha
ok(plain("pl") == ["Alpha", "Film One", "Beta", "Gamma"], "a movie can be placed straight after a chosen show")
place("pl", "Film One", 2012, "movie", 0)
ok(plain("pl")[0] == "Film One", "or at the very start")
place("pl", "Film One", 2012, "movie", 3)
ok(plain("pl") == ["Alpha", "Beta", "Gamma", "Film One"], "or at the very end (after the last item)")
b = store.load()["pl"]
ok(b["manual_order"] is True and len(b["shows"]) == 4, "placing sets a manual order and keeps membership")
place("pl", "Gamma", 2020, "tvshow", -1)
ok(plain("pl") == ["Alpha", "Beta", "Gamma", "Film One"], "cancelling the dialog changes nothing")
store.save({"one": box("Solo", [A])})
place("one", "Alpha", 2010, "tvshow", 0)
ok(plain("one") == ["Alpha"], "a single item has nothing to be placed next to")
xbmc.INFO["ListItem.DBType"] = "movie"; xbmc.INFO["ListItem.Title"] = "Film One"; xbmc.INFO["ListItem.Year"] = "2012"
cmdp = run_script("ctx_place.py")
ok(all(x in cmdp for x in ("action=place", "bid=mv", "media=movie")) and "Film" in cmdp, "Place script hands the right details to the add-on")
xbmc.INFO["ListItem.Title"] = ML("Film One"); xbmc.INFO["ListItem.Property(boxset_title)"] = "Film One"
ok("title=Film+One&" in run_script("ctx_place.py") + "&" and "%5B" not in run_script("ctx_move_up.py"), "right-click scripts send the real title, not the labelled one")
ok(any(i.get("library") == "ctx_place.py" and "boxset_action" in i.findtext("visible") for i in ctx_items), "Place is hidden on placeholder rows")

print("== watch order: seasons and movies in a sequence you choose")
import watchorder  # noqa: E402
xbmc.SEASONS = {1: [{"season": 1, "episode": 10, "watchedepisodes": 4, "art": {"poster": "pA-s1"}},
                    {"season": 2, "episode": 6, "watchedepisodes": 0, "art": {}}],
                2: [{"season": 1, "episode": 8, "watchedepisodes": 8, "art": {}}],
                3: [{"season": 0, "episode": 2, "watchedepisodes": 0, "art": {}}, {"season": 1, "episode": 5, "watchedepisodes": 0, "art": {}}]}
store.save({"wo": box("Saga", [A, G, F1])})
wcands = watchorder.candidates(store.load()["wo"], library.Library())
ok([watchorder.entry_label(e) for e, _, _ in wcands] == ["Alpha - Season 1", "Alpha - Season 2", "Film One [Movie]", "Gamma - Specials", "Gamma - Season 1"],
   "candidates: every season of each show (specials too) and the movies, in the boxset's order")
wlist = lambda: [i for i in run("action=watch&bid=wo")]  # noqa: E731
wlabels = lambda: [watchorder.entry_label(e) for e in store.load()["wo"].get("watch", [])]  # noqa: E731
wi = wlist()
ok(len(wi) == 1 and wi[0][0].props.get("boxset_action") == "1" and "action=watch_add" in wi[0][1], "an empty watch order offers a way in")
runq("action=watch_add&bid=wo", multiselect=[[4, 0, 2]])
ok(wlabels() == ["Alpha - Season 1", "Film One [Movie]", "Gamma - Season 1"], "added the chosen seasons and movies (in list order)")
ok(store.load()["wo"]["shows"] == [A, G, F1], "the boxset's own membership is untouched")
wi = wlist()
ok([wi[0][0].label, wi[2][0].label] == ["Alpha - Season 1", "Gamma - Season 1"] and wi[1][0].label.startswith("Film One"), "the watch order lists them in the saved order")
ok(wi[0][1] == "videodb://tvshows/titles/1/1/" and wi[0][2] is True and wi[2][1] == "videodb://tvshows/titles/3/1/", "a season links to Kodi's own season screen")
ok(wi[1][2] is False and "action=play_movie&id=10" in wi[1][1] and wi[1][0].props.get("boxset_movie") == "true", "a movie plays, and is marked for the MOVIE tag")
ok(wi[0][0].props["TotalEpisodes"] == "10" and wi[0][0].props["WatchedEpisodes"] == "4" and wi[0][0].art.get("poster") == "pA-s1", "a season shows its own progress and poster")
ok(wi[0][0].props["boxset_key"] == "season:alpha|2010|1" and wi[1][0].props["boxset_key"] == "movie:film one|2012", "each row carries its key for the right-click scripts")
runq("action=watch_add&bid=wo", multiselect=[[0]])
ok(wlabels() == ["Alpha - Season 1", "Film One [Movie]", "Gamma - Season 1", "Alpha - Season 2"], "adding later puts new entries at the end; the dialog no longer offers what is already in")
runq("action=watch_move&bid=wo&key=season:alpha|2010|2&delta=-1")
ok(wlabels()[2:] == ["Alpha - Season 2", "Gamma - Season 1"], "move up")
ok(any(c.startswith("Control.Move") for c in xbmc.BUILTINS), "the highlight follows the moved row")
runq("action=watch_move&bid=wo&key=season:alpha|2010|1&delta=-1")
ok(wlabels()[0] == "Alpha - Season 1", "already first: nothing changes")
runq("action=watch_place&bid=wo&key=season:alpha|2010|2", select=[1])  # [start], 1 Alpha S1 ...
ok(wlabels() == ["Alpha - Season 1", "Alpha - Season 2", "Film One [Movie]", "Gamma - Season 1"], "place a season straight after another")
runq("action=watch_place&bid=wo&key=movie:film one|2012", select=[0])
ok(wlabels()[0] == "Film One [Movie]", "or at the start")
runq("action=watch_place&bid=wo&key=movie:film one|2012", select=[-1])
ok(wlabels()[0] == "Film One [Movie]", "cancelling the place dialog changes nothing")
runq("action=watch_remove&bid=wo&key=season:gamma|2020|1")
ok("Gamma - Season 1" not in wlabels() and store.load()["wo"]["shows"] == [A, G, F1], "removing from the watch order keeps the show in the boxset")
runq("action=watch_fill&bid=wo")
ok(wlabels() == ["Film One [Movie]", "Alpha - Season 1", "Alpha - Season 2", "Gamma - Specials", "Gamma - Season 1"], "'Fill from boxset' appends everything missing")
runq("action=watch_fill&bid=wo")
ok(len(wlabels()) == 5, "filling again adds nothing")
d = store.load(); d["wo"]["shows"] = [A, F1]; store.save(d)
ok(not any("Gamma" in i[0].label for i in wlist()), "when a show leaves the boxset its seasons leave the watch order view")
d = store.load(); d["wo"]["shows"] = [A, G, F1]; store.save(d)
ok(any("Gamma" in i[0].label for i in wlist()), "...and come back in the same place if it returns before the order is changed")
d = store.load(); d["wo"]["watch"].append({"title": "Alpha", "year": 2010, "season": 9}); store.save(d)
miss = [i for i in wlist() if "Season 9" in i[0].label]
ok(len(miss) == 1 and "not in library" in miss[0][0].label, "a season the library doesn't have is shown as missing")
d = store.load(); d["wo"]["watch"].pop(); store.save(d)
# play next in the watch order
xbmc.EPISODES = {1: [{"episodeid": 101, "season": 1, "episode": 1, "playcount": 1}, {"episodeid": 102, "season": 1, "episode": 2, "playcount": 0},
                     {"episodeid": 201, "season": 2, "episode": 1, "playcount": 0}]}
d = store.load(); d["wo"]["watch"] = [{"title": "Alpha", "year": 2010, "season": 2}, {"title": "Alpha", "year": 2010, "season": 1}]; store.save(d)
xbmc.RPC_LOG.clear(); runq("action=play_next&bid=wo&watch=1")
opened = [p for m, p in xbmc.RPC_LOG if m == "Player.Open"]
ok(opened and opened[0]["item"] == {"episodeid": 201}, "play next follows the watch order (season 2 first here)")
# right-click scripts
xbmc.INFO.clear()
xbmc.INFO.update({"Container.FolderPath": "plugin://plugin.video.tvboxsets/?action=watch&bid=wo", "ListItem.Title": "Alpha - Season 2",
                  "ListItem.Property(boxset_key)": "season:alpha|2010|2", "ListItem.DBType": "season"})
cmd_up = run_script("ctx_move_up.py")
ok(all(x in cmd_up for x in ("action=watch_move", "bid=wo", "delta=-1")) and "key=season%3Aalpha%7C2010%7C2" in cmd_up, "Move up in the watch order sends the row's key")
ok("action=watch_place" in run_script("ctx_place.py"), "Place sends the watch order action")
ok("action=watch_remove" in run_script("context_remove.py") and "key=season" in xbmc.BUILTINS[-1], "Remove in the watch order takes it out of the order only")
ok("watch=1" in run_script("ctx_play_next.py"), "Play next knows it is in the watch order")
ok("action=watch_add" in run_script("ctx_watch_add.py") and "action=watch_fill" in run_script("ctx_watch_fill.py"), "Add and Fill scripts")
xbmc.INFO["Container.FolderPath"] = "plugin://plugin.video.tvboxsets/?action=open&bid=wo"
ok("action=watch_open" in run_script("ctx_watch_open.py"), "'Watch order...' is reachable from inside a boxset")
xbmc.BUILTINS.clear(); runq("action=watch_open&bid=wo")
ok(any(c.startswith("Container.Update(") and "action=watch&bid=wo" in c for c in xbmc.BUILTINS) and "Container.Refresh" not in xbmc.BUILTINS, "opening it uses Container.Update and no refresh")
vis = {i.get("library"): i.findtext("visible") for i in addon_root.iter("item")}
ok("action=watch" in vis["ctx_watch_add.py"] and "action=open" not in vis["ctx_watch_add.py"], "Add/Fill entries only show inside the watch order")
ok("action=open" in vis["ctx_watch_open.py"], "'Watch order...' shows inside a boxset")
bk = store.dump_text({"w": dict(box("W", [A]), watch=[{"title": "Alpha", "year": 2010, "season": 1}])})
ok(json.loads(bk)["boxsets"]["w"]["watch"][0]["season"] == 1, "the watch order is saved in the data file")
cur = {"x": box("W", [A])}; store.merge(cur, {"w": dict(box("W", [A]), watch=[{"title": "Alpha", "year": 2010, "season": 1}])})
ok(cur["x"].get("watch") and cur["x"]["watch"][0]["season"] == 1, "importing a backup brings a watch order into a boxset that has none")

print("== watch order: crossover episodes")
xbmc.EPISODES = {1: [{"episodeid": 100 + n, "season": 1, "episode": n, "title": "T%d" % n, "playcount": 1 if n <= 4 else 0, "plot": "", "art": {}} for n in range(1, 11)]
                 + [{"episodeid": 200 + n, "season": 2, "episode": n, "title": "U%d" % n, "playcount": 0, "plot": "", "art": {}} for n in range(1, 7)]}
d = store.load(); d["wo"]["watch"] = [{"title": "Alpha", "year": 2010, "season": 1}, {"title": "Film One", "year": 2012, "type": "movie"}]; store.save(d)
runq("action=watch_add_eps&bid=wo", select=[0, 0], multiselect=[[7, 8]])
ok(wlabels() == ["Alpha - S1 up to E7", "Alpha - S1E8-E9", "Alpha - S1E10+", "Film One [Movie]"], "a crossover splits the season's entry around it: before, the crossover, after")
wi = wlist()
ok(wi[1][2] is True and "action=wo_range" in wi[1][1] and wi[1][0].props["TotalEpisodes"] == "2", "a range of several episodes is a folder with its own progress")
ok(wi[2][2] is False and "action=play_episode&id=110" in wi[2][1] and wi[2][0].tag.d.get("MediaType") == "episode", "a single episode plays directly")
ok(wi[0][0].props["TotalEpisodes"] == "7" and wi[0][0].props["WatchedEpisodes"] == "4", "the first part counts only its own episodes (7, 4 watched)")
runq("action=watch_add_eps&bid=wo", select=[0, 0], multiselect=[[2]])
ok(wlabels()[:3] == ["Alpha - S1 up to E2", "Alpha - S1E3", "Alpha - S1E4-E7"], "an episode inside an existing part splits that part again")
n_before = wlabels()
runq("action=watch_add_eps&bid=wo", select=[0, 0], multiselect=[[2]])
ok(wlabels() == n_before, "adding the same episode again changes nothing")
runq("action=watch_add&bid=wo", multiselect=[None])
ok("Alpha - Season 1" not in D.LAST_MULTI["options"] and any(o.startswith("Alpha - Season 2") for o in D.LAST_MULTI["options"]), "the season dialog no longer offers a season that already has entries")
runq("action=watch_fill&bid=wo")
ok(not any(l == "Alpha - Season 1" for l in wlabels()) and "Alpha - Season 2" in wlabels(), "'Fill' skips a season that is already in the order, in parts")
kk = "season:alpha|2010|1|8-9"
rv = run("action=wo_range&bid=wo&key=" + kk)
ok(len(rv) == 2 and all(i[2] is False and "action=play_episode" in i[1] for i in rv) and rv[0][0].label.startswith("Alpha - S1E8"), "opening a range lists its episodes, playable")
d = store.load(); d["wo"]["watch"] = [e for e in d["wo"]["watch"] if watchorder.entry_key(e) != "season:alpha|2010|2"]; store.save(d)
d = store.load(); d["wo"]["watch"] = [e for e in d["wo"]["watch"] if e.get("type") == "movie" or e.get("season") == 1]; store.save(d)
xbmc.RPC_LOG.clear(); runq("action=play_next&bid=wo&watch=1")
opened = [p for m, p in xbmc.RPC_LOG if m == "Player.Open"]
ok(opened and opened[0]["item"] == {"episodeid": 105}, "play next goes through the parts in order: episode 5 is the first unwatched")
runq("action=watch_remove&bid=wo&key=" + kk)
ok("Alpha - S1E8-E9" not in wlabels() and "Alpha - S1E10+" in wlabels(), "removing a part leaves the others where they are")
b, c = {"title": "A", "year": 1}, [{"title": "A", "year": 1, "season": 3}]
lab = lambda es: [watchorder.entry_label(e) for e in es]  # noqa: E731
ok(lab(watchorder.insert_runs(c, b, 3, [(1, 2)], 22)[0]) == ["A - S3E1-E2", "A - S3E3+"], "a crossover at the start leaves no empty part before it")
ok(lab(watchorder.insert_runs(c, b, 3, [(21, 22)], 22)[0]) == ["A - S3 up to E20", "A - S3E21-E22"], "...and none after it when it runs to the end")
ok(lab(watchorder.insert_runs([], b, 3, [(8, 9)], 22)[0]) == ["A - S3E8-E9"], "with no entry for the season it is simply added")
ok(watchorder.runs([9, 8, 12, 8]) == [(8, 9), (12, 12)], "chosen episodes are grouped into consecutive runs")
xbmc.INFO.clear()
xbmc.INFO["Container.FolderPath"] = "plugin://plugin.video.tvboxsets/?action=wo_range&bid=wo&key=x"
import ctxutil as _cu  # noqa: E402
ok(not _cu.in_watch_order() and "action=watch" not in xbmc.INFO["Container.FolderPath"], "inside a range folder the watch-order menu entries stay hidden")
xbmc.INFO["Container.FolderPath"] = "plugin://plugin.video.tvboxsets/?action=watch&bid=wo"
ok("action=watch_add_eps" in run_script("ctx_watch_add_eps.py"), "Add episodes script")

print("== 'Boxsets...' on a library show or movie")
store.save({"a": box("Alpha Manual", [A]), "b": dict(box("Beta Smart", []), rules={"media": "tv", "genre": "Drama"}), "c": box("Gamma Only", [G])})
snap = lambda: nomod(store.load())  # noqa: E731
xbmc.INFO.clear(); xbmc.INFO.update({"ListItem.DBID": "1", "ListItem.DBType": "tvshow"})
before = snap()
runq("context", multiselect=[[0, 1]]); D.Q.clear(); D.Q.update({"multiselect": [[0, 1]]}); context.main()
ok(D.LAST_MULTI["preselect"] == [0, 1] and D.LAST_MULTI["options"] == ["Alpha Manual", "Beta Smart  (smart)", "Gamma Only", "[B]+ New boxset...[/B]"], "dialog lists every boxset, ticking the ones it is already in (manual and smart)")
ok(snap() == before, "leaving the ticks as they were changes nothing")
D.Q.clear(); D.Q.update({"multiselect": [None]}); context.main()
ok(snap() == before, "cancelling changes nothing")
D.Q.clear(); D.Q.update({"multiselect": [[0]]}); context.main()
b = store.load()
ok(b["b"]["excluded"][0]["title"] == "Alpha" and b["a"]["shows"] == [A], "unticking a smart boxset leaves the item out of it from now on")
D.Q.clear(); D.Q.update({"multiselect": [[0]]}); context.main()
ok(D.LAST_MULTI["preselect"] == [0], "it now shows as not in the smart boxset")
D.Q.clear(); D.Q.update({"multiselect": [[0, 1]]}); context.main()
ok("excluded" not in store.load()["b"], "ticking it again lifts the exclusion")
D.Q.clear(); D.Q.update({"multiselect": [[1]]}); context.main()
b = store.load()
ok(b["a"]["shows"] == [] and not b["b"].get("excluded") and b["b"]["rules"], "unticking a hand-picked boxset removes the entry; the smart one still matches")
D.Q.clear(); D.Q.update({"multiselect": [[1, 2]]}); context.main()
ok([r["title"] for r in store.load()["c"]["shows"]] == ["Gamma", "Alpha"], "ticking another boxset adds the item to it")
D.Q.clear(); D.Q.update({"multiselect": [[]]}); context.main()
b = store.load()
ok(b["a"]["shows"] == [] and b["c"]["shows"] == [G] and b["b"]["excluded"][0]["title"] == "Alpha", "confirming with nothing ticked takes it out of everything")
xbmc.INFO.clear(); xbmc.INFO.update({"ListItem.DBID": "10", "ListItem.DBType": "movie"})
D.Q.clear(); D.Q.update({"multiselect": [[0]]}); context.main()
ref = store.load()["a"]["shows"][0]
ok(ref["title"] == "Film One" and ref["type"] == "movie", "works for movies too (stored as a movie)")


print("== badge pictures (a fresh numbered folder for every change)")
on_src = os.path.join(ADDON, "resources", "badge.png")
ok(open(on_src, "rb").read(8) == b"\x89PNG\r\n\x1a\n", "the badge picture is a real PNG")
bd = os.path.join(ROOT, "badge-unit")
ok(badges.sync_files({("tvshow", 1), ("movie", 10)}, bd, on_src) == (1, True, 2), "the first sync builds folder r1 for 2 items")
ok(sorted(os.listdir(os.path.join(bd, "r1"))) == ["movie_10.png", "movie_10_name.png", "tvshow_1.png", "tvshow_1_name.png"]
   and open(os.path.join(bd, "r1", "tvshow_1.png"), "rb").read() == open(on_src, "rb").read()
   and open(os.path.join(bd, "r1", "tvshow_1_name.png"), "rb").read() == open(on_src, "rb").read(), "each item gets <type>_<id>.png and <type>_<id>_name.png (the plain icon when no names are given)")
ok(badges.sync_files({("tvshow", 1), ("movie", 10)}, bd, on_src) == (1, False, 2) and not os.path.exists(os.path.join(bd, "r2")), "nothing changed: same folder, no new revision")
ok(badges.sync_files({("tvshow", 1)}, bd, on_src) == (2, True, 1) and sorted(os.listdir(os.path.join(bd, "r2"))) == ["tvshow_1.png", "tvshow_1_name.png"], "a change builds r2 holding only the items that are still in a boxset (no file at all for the others)")
ok(os.path.isdir(os.path.join(bd, "r1")), "the previous folder is kept for a while")
open(os.path.join(bd, "tvshow_5.png"), "wb").write(b"old")       # a flat file left by an earlier version
ok(badges.sync_files({("tvshow", 1), ("tvshow", 2)}, bd, on_src)[0] == 3 and not os.path.exists(os.path.join(bd, "r1")) and os.path.isdir(os.path.join(bd, "r2")), "older folders are removed once newer ones exist")
ok(not os.path.exists(os.path.join(bd, "tvshow_5.png")), "flat pictures left by earlier versions (which could show stale badges) are cleaned up")
ok(badges.current_rev(bd) == 3, "the current revision is remembered")
with open(os.path.join(bd, "state.json"), "w") as f:
    f.write("{damaged")
os.makedirs(os.path.join(bd, "r7"))
ok(badges.sync_files({("tvshow", 1)}, bd, on_src)[0] == 8, "a damaged state file can never reuse an old folder number (that would show stale pictures): it continues after the highest folder")

print("== the label goes when you take the show out of the wrong boxset")
xbmc.MOVIES = [
    {"movieid": 10, "title": "Film One", "year": 2012, "art": {}, "plot": "", "genre": ["Drama"], "studio": [], "tag": [], "playcount": 0},
    {"movieid": 11, "title": "Film Two", "year": 2015, "art": {}, "plot": "", "genre": ["Action"], "studio": [], "tag": [], "playcount": 1},
]
xbmc.LIB[0]["tag"], xbmc.LIB[2]["tag"] = ["Franchise"], ["Franchise"]
atlas0 = labelimg.load_atlas(os.path.join(ADDON, "resources", "glyphs.json.z"))
rev_path = lambda: os.path.join(store.BADGE_DIR, "r%s" % xbmcgui.Window(10000).getProperty(skinpatch.BADGE_REV_PROPERTY))  # noqa: E731
skin_url = lambda name: (skinpatch.BADGE_DIR_SPECIAL + "/" + name).replace("$INFO[Window(Home).Property(%s)]" % skinpatch.BADGE_REV_PROPERTY, xbmcgui.Window(10000).getProperty(skinpatch.BADGE_REV_PROPERTY))  # noqa: E731
shutil.rmtree(store.BADGE_DIR, ignore_errors=True)
store.save({"w": box("Wrong", [A])})
r1 = badges.sync_badges()
label_wrong = open(os.path.join(rev_path(), "tvshow_1_name.png"), "rb").read()
url_wrong = skin_url("tvshow_1_name.png")
ok(r1[1] and label_wrong == labelimg.render_label(atlas0, "Wrong")[0], "put into the wrong boxset: the poster picture says 'Wrong'")
store.save({"w": box("Wrong", [])})
r2 = badges.sync_badges()
ok(r2[0] == r1[0] + 1 and not os.path.exists(os.path.join(rev_path(), "tvshow_1_name.png")) and not os.path.exists(os.path.join(rev_path(), "tvshow_1.png")), "taken out again: the new folder has no picture for it")
url_removed = skin_url("tvshow_1_name.png")
ok(url_removed != url_wrong and "/r%d/" % r2[0] in url_removed, "the address the skin reads CHANGES, so Kodi can't keep showing the old label: %s" % url_removed.split("badges/")[1])
store.save({"w": box("Wrong", []), "r": box("Right", [A])})
r3 = badges.sync_badges()
ok(open(os.path.join(rev_path(), "tvshow_1_name.png"), "rb").read() == labelimg.render_label(atlas0, "Right")[0] and skin_url("tvshow_1_name.png") not in (url_wrong, url_removed), "put into the right boxset: the new picture says 'Right' at yet another address")
store.save({"w": box("Wrong", [A]), "r": box("Right", [A])})
badges.sync_badges()
ok(open(os.path.join(rev_path(), "tvshow_1_name.png"), "rb").read() == labelimg.render_label(atlas0, "Right +1")[0], "in two boxsets it reads 'Right +1'")
store.save({"w": box("Wrong", []), "r": box("Right", [A])})
badges.sync_badges()
ok(open(os.path.join(rev_path(), "tvshow_1_name.png"), "rb").read() == labelimg.render_label(atlas0, "Right")[0], "...and back to 'Right' when the wrong one is removed")
ok(badges.sync_badges()[1] is False and skin_url("tvshow_1_name.png") == skin_url("tvshow_1_name.png"), "a sync with nothing to change keeps the same address (no needless reloads)")

store.save({"k1": box("Kept", [A, F1, {"title": "Ghost", "year": 1990}]),
            "k2": dict(box("Auto", []), rules={"media": "tv", "genre": "Comedy"})})
xbmc.RPC_LOG.clear()
res = badges.sync_badges()
icons = lambda: sorted(n for n in os.listdir(rev_path()) if not n.endswith("_name.png"))  # noqa: E731
ok(res[1] and icons() == ["movie_10.png", "tvshow_1.png", "tvshow_2.png"], "saved entries and smart matches get pictures (missing items skipped): %s" % icons())
gets = [p for m, p in xbmc.RPC_LOG if m in ("VideoLibrary.GetTVShows", "VideoLibrary.GetMovies")]
ok(all("art" not in p["properties"] and "plot" not in p["properties"] for p in gets), "the badge check asks Kodi for the light set of fields (no artwork or plots)")
store.save({"k1": box("Kept", [A])})
badges.sync_badges()
ok(icons() == ["tvshow_1.png"], "removing items from boxsets removes their pictures")
xbmcaddon.SETTINGS["show_badges"] = False
badges.sync_badges()
ok(icons() == [], "turning the setting off leaves no pictures, and the skin address changes straight away")
xbmcaddon.SETTINGS["show_badges"] = True
badges.sync_badges()
ok(icons() == ["tvshow_1.png"], "and back on again")
shutil.rmtree(store.BADGE_DIR, ignore_errors=True)
runq("action=menu", select=[[l for l, _ in main.menu_entries()].index("Refresh the boxset badges")])
ok(os.path.exists(os.path.join(rev_path(), "tvshow_1.png")), "choosing 'Refresh the boxset badges' in the menu rebuilds the pictures")
ok("Refresh the boxset badges" in [l for l, _ in main.menu_entries()], "'Refresh the boxset badges' is in the Boxsets menu")

print("== badge service")
w = service.Watcher()
w.onNotification("xbmc", "VideoLibrary.OnScanFinished", "{}")
ok(w.badge_debounce.pending and w.debounce.pending, "a library scan refreshes badges and home rows")
w = service.Watcher(); w.onNotification("xbmc", "Player.OnStop", "{}")
ok(w.debounce.pending and not w.badge_debounce.pending, "playback stopping refreshes the rows but not the badges")
w = service.Watcher(); w.onNotification("xbmc", "VideoLibrary.OnUpdate", "{}")
ok(not w.badge_debounce.pending, "a watched-state change does not rebuild badges")
w = service.Watcher(); w.onSettingsChanged()
ok(w.badge_debounce.pending, "changing a setting (e.g. show_badges) refreshes badges")
shutil.rmtree(store.BADGE_DIR, ignore_errors=True)
xbmcgui.Window(10000).setProperty(skinpatch.BADGE_REV_PROPERTY, "")
service.run()
ok(os.path.exists(os.path.join(rev_path(), "tvshow_1.png")) and xbmcgui.Window(10000).getProperty(skinpatch.BADGE_REV_PROPERTY) != "", "the service writes the pictures and tells the skin which folder to read when it starts")

print("== badges in the skin (synthetic skin files)")
xdir = os.path.join(ROOT, "badge-skin")
shutil.copytree(os.path.join(HERE, "fixtures", "xml"), xdir)
ok(not skinpatch.has_badges(xdir), "no badges before patching")
placed = skinpatch.patch_badges(xdir)
ok(placed == 6 and skinpatch.has_badges(xdir), "badges placed over every poster image and every roomy list row (%d)" % placed)
ok(skinpatch.patch_badges(xdir) == 0, "patching twice places nothing more")
ok('<include file="Includes_TvBoxsets.xml" />' in open(os.path.join(xdir, "Includes.xml"), encoding="utf-8").read(), "include file registered in Includes.xml")
for f in os.listdir(xdir):
    ET.parse(os.path.join(xdir, f))
ok(True, "every patched file is still well-formed XML")
inc = ET.parse(os.path.join(xdir, "Includes_TvBoxsets.xml")).getroot()
tex = inc.find(".//texture").text
ok(tex == skinpatch.BADGE_DIR_SPECIAL + "/$INFO[ListItem.DBType]_$INFO[ListItem.DBID].png" and "Property(tvboxsets_badge_rev)" in tex, "badge picture is chosen by the item's type and library id, from the folder number the add-on publishes")
vis = inc.find(".//visible").text
ok("tvshow" in vis and "movie" in vis and "DBID" in vis, "badge only shows for library shows and movies")
def badge_params(fname):
    root = ET.parse(os.path.join(xdir, fname)).getroot()
    return [{p.get("name"): p.get("value") for p in i.findall("param")} for i in root.iter("include") if i.get("content") == "TvBoxsetsBadge"]
def pill_params(fname):
    root = ET.parse(os.path.join(xdir, fname)).getroot()
    return [{p.get("name"): p.get("value") for p in i.findall("param")} for i in root.iter("include") if i.get("content") == "TvBoxsetsNameBadge"]
ok(pill_params("View_51_Poster.xml") == [{"left": "14", "top": "14", "width": "456", "height": "44"}], "big poster: name pill 10 in from its corner, across the poster, height capped at 44")
ok(pill_params("View_54_InfoWall.xml") == [{"left": "25", "top": "0", "width": "270", "height": "32"}], "tile poster (negative offset handled): pill scales with the poster")
ok(pill_params("DialogVideoInfo.xml") == [{"left": "30", "top": "30", "width": "166", "height": "26"}] and len(pill_params("DialogVideoInfo.xml")) == 1, "small poster gets the minimum height; one with a percentage position is skipped")
ok(open(os.path.join(xdir, "View_51_Poster.xml"), "rb").read().count(b"\r\n") > 5 and b"TvBoxsetsNameBadge" in open(os.path.join(xdir, "View_51_Poster.xml"), "rb").read() and b"\n" not in open(os.path.join(xdir, "View_51_Poster.xml"), "rb").read().replace(b"\r\n", b""), "files that use Windows line endings keep them")
xml_clone = os.path.join(ROOT, "home/addons/skin.estuary.boxsets/xml")
ok(skinpatch.has_badges(xml_clone) and main.skin_current(), "a freshly built skin copy has the widget and the badges")
ok(not any("Update" in l for l, _ in main.menu_entries()), "so the menu has no update entry")
os.remove(os.path.join(xml_clone, "Includes_TvBoxsets.xml"))
ok(not main.skin_current() and any("home widget and library badges" in l for l, _ in main.menu_entries()), "an older skin copy (no badges) is offered the update")
xbmc.SKIN = "skin.estuary"; xbmc.BUILTINS.clear()
runq("action=install_skin", yesno=[False])
ok(main.skin_current() and os.path.exists(os.path.join(xml_clone, "Includes_TvBoxsets.xml")), "running the update adds the badges to the existing skin copy")
ok(os.path.exists(os.path.join(rev_path(), "tvshow_1.png")), "and writes the badge pictures")


print("== badges in list rows")
def rows(fname, include):
    root = ET.parse(os.path.join(xdir, fname)).getroot()
    return [{p.get("name"): p.get("value") for p in i.findall("param")} for i in root.iter("include") if i.get("content") == include]
ok(rows("View_55_WideList.xml", "TvBoxsetsRowBadge") == [{"left": "70", "size": "28"}] * 2, "wide list: a small badge between the watched icon and the title, in both row layouts")
ok(rows("View_504_MediaList.xml", "TvBoxsetsBadge") == [{"left": "70", "top": "19", "size": "28"}], "media list (icon positioned by 'top'): uses the plain badge, lined up with the icon")
ok(rows("View_50_List.xml", "TvBoxsetsRowBadge") == [] and b"TvBoxsets" not in open(os.path.join(xdir, "View_50_List.xml"), "rb").read(), "a row with no room before the title is left alone")
inc = ET.parse(os.path.join(xdir, "Includes_TvBoxsets.xml")).getroot()
rb = [i for i in inc.iter("include") if i.get("name") == "TvBoxsetsRowBadge"][0]
mt = [i for i in inc.iter("include") if i.get("name") == "TvBoxsetsMovieTag"][0]
ok("boxset_movie" in mt.find(".//visible").text and any(c.text == "MOVIE" for c in mt.iter("label")), "movie tag include is only visible on items the add-on marks as movies")
pv = open(os.path.join(xdir, "View_54_InfoWall.xml"), encoding="utf-8").read()
ok(pv.count('content="TvBoxsetsMovieTag"') >= 1 and pv.count('content="TvBoxsetsMovieTag"') == pv.count('content="TvBoxsetsNameBadge"'), "every poster gets a movie tag next to its name badge")
skinpatch.patch_badges(xdir)
ok(open(os.path.join(xdir, "View_54_InfoWall.xml"), encoding="utf-8").read() == pv, "patching again leaves the movie tags unchanged (no duplicates)")
ok(rb.find(".//centertop").text == "50%" and "DBID" in rb.find(".//texture").text, "row badge is vertically centred and uses the same per-item picture")
text = open(os.path.join(xdir, "Includes_TvBoxsets.xml"), encoding="utf-8").read().replace("tvboxsets-badge v5", "tvboxsets-badge v1")
open(os.path.join(xdir, "Includes_TvBoxsets.xml"), "w", encoding="utf-8").write(text)
ok(not skinpatch.has_badges(xdir), "a skin copy made with badge version 1 is not counted as current")
skinpatch.patch_badges(xdir)
ok(skinpatch.has_badges(xdir) and "TvBoxsetsRowBadge" in open(os.path.join(xdir, "Includes_TvBoxsets.xml"), encoding="utf-8").read(), "patching upgrades it in place (no duplicate badges)")
ok(skinpatch.patch_badges(xdir) == 0 and rows("View_55_WideList.xml", "TvBoxsetsRowBadge") == [{"left": "70", "size": "28"}] * 2, "and a second run still places nothing more")

print("== tags in step with boxsets (info dialog 'Tags' row)")
xbmc.LIB[0]["tag"] = ["Franchise", "MyOwn"]; xbmc.LIB[1]["tag"] = []; xbmc.LIB[2]["tag"] = ["Boxset: Stale"]
xbmc.MOVIES[0]["tag"] = []; xbmc.MOVIES[1]["tag"] = []
store.save({"t1": box("Saga3", [A, B, {"title": "Film Two", "year": 2015, "type": "movie"}])})
xbmcaddon.SETTINGS["tag_prefix"] = "Boxset:"
xbmc.RPC_LOG.clear()
ok(tagsync.sync(quiet=True) == 4, "quiet sync writes the changes (3 items tagged + 1 stale tag removed)")
tags = {i["tvshowid"]: i["tag"] for i in xbmc.LIB}
ok(tags[1] == ["Franchise", "MyOwn", "Boxset: Saga3"] and tags[2] == ["Boxset: Saga3"] and tags[3] == [], "tags written; your own tags kept; stale boxset tag removed")
ok(xbmc.MOVIES[1]["tag"] == ["Boxset: Saga3"], "movies get the tag too")
gets = [p for m, p in xbmc.RPC_LOG if m in ("VideoLibrary.GetTVShows", "VideoLibrary.GetMovies")]
ok(all("art" not in p["properties"] for p in gets), "tag sync asks for the light set of fields")
xbmc.RPC_LOG.clear()
ok(tagsync.sync(quiet=True) == 0 and not [1 for m, p in xbmc.RPC_LOG if m.startswith("VideoLibrary.Set")], "nothing to change the second time")
xbmcaddon.SETTINGS["tag_prefix"] = ""
ok(tagsync.sync(quiet=True) is None, "an empty prefix is skipped silently in the background")
xbmcaddon.SETTINGS["tag_prefix"] = "Boxset:"
runq("action=menu", select=[[l for l, _ in main.menu_entries()].index("Remove boxset tags from Kodi...")], yesno=[False])
ok(xbmc.LIB[0]["tag"] == ["Franchise", "MyOwn", "Boxset: Saga3"], "'Remove boxset tags' does nothing if you say no")
runq("action=menu", select=[[l for l, _ in main.menu_entries()].index("Remove boxset tags from Kodi...")], yesno=[True])
ok(xbmc.LIB[0]["tag"] == ["Franchise", "MyOwn"] and xbmc.LIB[1]["tag"] == [] and xbmc.MOVIES[1]["tag"] == [], "...and removes only the boxset tags when you say yes")
ok(store.load()["t1"]["shows"], "boxsets themselves are untouched by removing tags")

print("== automatic tag sync (service)")
w = service.Watcher()
w.onNotification("xbmc", "VideoLibrary.OnScanFinished", "{}")
ok(w.tag_debounce.pending and w.tag_debounce.quiet == 2.5, "a library scan queues a tag sync (waits 2.5 quiet seconds, so quick edits are batched)")
w = service.Watcher(); w.onNotification("xbmc", "VideoLibrary.OnUpdate", "{}")
ok(not w.tag_debounce.pending, "our own tag writes (OnUpdate events) can't trigger another sync: no loop")
w = service.Watcher(); w.onSettingsChanged()
ok(w.tag_debounce.pending, "changing a setting queues a tag sync")
xbmcaddon.SETTINGS["auto_tags"] = False
xbmc.RPC_LOG.clear(); service.run()
ok(not [1 for m, p in xbmc.RPC_LOG if m.startswith("VideoLibrary.Set")], "service leaves your tags alone while the setting is off (default)")
xbmcaddon.SETTINGS["auto_tags"] = True
xbmc.RPC_LOG.clear(); service.run()
ok([1 for m, p in xbmc.RPC_LOG if m == "VideoLibrary.SetTVShowDetails"] and xbmc.LIB[0]["tag"][-1] == "Boxset: Saga3", "with the setting on, the service writes the tags at startup")
xbmcaddon.SETTINGS["auto_tags"] = False
ok(any(x.get("id") == "auto_tags" and x.findtext("default") == "true" for x in ET.parse(os.path.join(ADDON, "resources/settings.xml")).getroot().iter("setting")), "the setting exists and is on by default")

print("== diagnostics shows the badge status")
runq("action=diagnostics", select=[0])
text = [v for k, v in D.LOG if k == "textviewer"][0]
ok("Library badges in the skin copy: yes" in text and "Badge pictures: folder r" in text, "report says whether the skin copy has the badges and which picture folder is live")


print("== name label pictures (pure-Python renderer)")
import ast, struct, zlib as _zlib  # noqa: E402
atlas = labelimg.load_atlas(os.path.join(ADDON, "resources", "glyphs.json.z"))
STDLIB = {"base64", "json", "math", "struct", "unicodedata", "zlib"}
mods = {n.names[0].name.split(".")[0] for n in ast.walk(ast.parse(open(os.path.join(ADDON, "labelimg.py")).read())) if isinstance(n, ast.Import)}
ok(mods <= STDLIB, "labelimg uses only the standard library (Kodi's Python has no image library): %s" % sorted(mods))
ok(all(ord(c) in atlas.glyphs for c in "ABCxyz09 +&-:'.,!?()"), "plain ASCII is in the letter table")
ok(labelimg._glyph(atlas, "é") is atlas.glyphs[ord("é")] and labelimg._glyph(atlas, "\u2013") is atlas.glyphs[0x2013], "accents and dashes are in the table")
ok(labelimg._glyph(atlas, "\u65e5") is atlas.glyphs[ord("?")], "a letter that isn't in the table is drawn as '?'")
ok(labelimg.label_text(["Marvel"]) == "Marvel" and labelimg.label_text(["b", "A"]) == "A +1" and labelimg.label_text(["x", "y", "z", "x"]) == "x +2" and labelimg.label_text([]) == "", "label text: first name, then '+N' for the others")
wide = labelimg.text_width(atlas, "A very long boxset name that cannot possibly fit")
cut = labelimg.fit_text(atlas, "A very long boxset name that cannot possibly fit", 180)
ok(labelimg.text_width(atlas, cut) <= 180 and cut.endswith("\u2026") and labelimg.fit_text(atlas, "Short", 180) == "Short", "long names are shortened with an ellipsis; short ones are untouched")

def read_png(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, size = 8, b"", None
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        assert struct.unpack(">I", data[pos + 8 + n:pos + 12 + n])[0] == _zlib.crc32(kind + body) & 0xFFFFFFFF, "bad CRC"
        if kind == b"IHDR":
            size = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    w, h = size[0], size[1]
    raw = _zlib.decompress(idat)
    rows = [raw[y * (1 + w * 4) + 1:(y + 1) * (1 + w * 4)] for y in range(h)]
    return w, h, size[2:5], rows
png, pw, ph = labelimg.render_label(atlas, "Marvel")
w, h, fmt, rows = read_png(png)
ok((w, h) == (pw, ph) and fmt == (8, 6, 0) and all(len(r) == w * 4 for r in rows), "label is a valid 8-bit RGBA PNG whose size matches (%dx%d)" % (w, h))
ok(rows[0][3] == 0 and rows[h // 2][(w // 2) * 4 + 3] > 200, "the pill's corners are transparent and its middle is solid")
light = sum(1 for r in rows for x in range(0, w * 4, 4) if r[x] > 200 and r[x + 1] > 200 and r[x + 3] > 200)
ok(light > 150, "the name is drawn in light pixels (%d)" % light)
ok(labelimg.render_label(atlas, "Marvel Cinematic Universe")[1] > pw and labelimg.render_label(atlas, "x" * 200, 380)[1] <= 380, "longer names make a wider label, up to the limit")
ok(png == labelimg.render_label(atlas, "Marvel")[0], "drawing the same text twice gives identical bytes")

print("== label pictures in the numbered folders")
lb = os.path.join(ROOT, "label-unit")
wanted = {("tvshow", 1): ["Marvel"], ("tvshow", 2): ["Marvel", "Avengers"], ("movie", 10): ["Marvel"]}
rev, changed, items = badges.sync_files(wanted, lb, on_src, atlas)
rd = lambda n, r=None: open(os.path.join(lb, "r%d" % (r or badges.current_rev(lb)), n), "rb").read()  # noqa: E731
ok(changed and items == 3, "three items get pictures")
ok(rd("tvshow_1.png") == open(on_src, "rb").read() and rd("tvshow_1_name.png") == labelimg.render_label(atlas, "Marvel")[0], "icon file is the badge; name file is the 'Marvel' label")
ok(rd("tvshow_1_name.png") == rd("movie_10_name.png") and rd("tvshow_2_name.png") == labelimg.render_label(atlas, "Avengers +1")[0], "items in the same boxsets share a label; one in two boxsets reads 'Avengers +1'")
cached = sorted(os.listdir(os.path.join(lb, "_labels")))
ok(len(cached) == 2, "each distinct label is drawn once and kept (2 labels for 3 items)")
rev2 = badges.sync_files(wanted, lb, on_src, atlas)
ok(rev2 == (rev, False, 3) and sorted(os.listdir(os.path.join(lb, "_labels"))) == cached, "a second sync changes nothing")
wanted2 = {("tvshow", 1): ["Marvel Studios"], ("tvshow", 2): ["Marvel", "Avengers"], ("movie", 10): ["Marvel"]}
rev3, changed3, _ = badges.sync_files(wanted2, lb, on_src, atlas)
ok(changed3 and rev3 == rev + 1 and rd("tvshow_1_name.png") == labelimg.render_label(atlas, "Marvel Studios")[0], "renaming a boxset gives a new folder with the new label")
ok(rd("movie_10_name.png", rev3) == labelimg.render_label(atlas, "Marvel")[0], "the other labels are carried over unchanged")
leftover = sorted(os.listdir(os.path.join(lb, "_labels")))
ok(len(leftover) == 3, "the cache holds exactly the labels in use now (Marvel Studios, Avengers +1, Marvel): %d" % len(leftover))
rev4, _, _ = badges.sync_files({("tvshow", 2): ["Avengers"]}, lb, on_src, atlas, show_names=False)
ok(rd("tvshow_2_name.png", rev4) == open(on_src, "rb").read() and sorted(os.listdir(os.path.join(lb, "_labels"))) == [], "with names switched off the poster picture is the plain round icon, and unused labels are cleared from the cache")
legacy = os.path.join(ROOT, "label-legacy")
os.makedirs(legacy)
for n in ("tvshow_1.png", "tvshow_9.png", "movie_3_name.png"):
    shutil.copy(on_src, os.path.join(legacy, n))      # flat files left by 0.9 - 0.11.0
badges.sync_files({("tvshow", 1): ["Marvel"]}, legacy, on_src, atlas)
ok(sorted(n for n in os.listdir(legacy) if n.endswith(".png")) == ["_icon.png"] and os.path.isdir(os.path.join(legacy, "r1")), "an older badge folder is upgraded: flat files that could show stale labels are removed")

store.save({"k1": box("Kept", [A]), "k2": box("Auto", [A, B])})
shutil.rmtree(store.BADGE_DIR, ignore_errors=True)
xbmcaddon.SETTINGS["show_names"] = True
badges.sync_badges()
ok(open(os.path.join(rev_path(), "tvshow_1_name.png"), "rb").read() == labelimg.render_label(atlas, "Auto +1")[0] and open(os.path.join(rev_path(), "tvshow_2_name.png"), "rb").read() == labelimg.render_label(atlas, "Auto")[0], "end to end: Alpha is in two boxsets ('Auto +1'), Beta in one ('Auto')")
xbmcaddon.SETTINGS["show_names"] = False
badges.sync_badges()
ok(open(os.path.join(rev_path(), "tvshow_1_name.png"), "rb").read() == open(on_src, "rb").read(), "the 'show names' setting off gives the plain icon")
xbmcaddon.SETTINGS["show_names"] = True
badges.sync_badges()

print("== the skin shows the name label on posters")
inc = ET.parse(os.path.join(xml_clone, "Includes_TvBoxsets.xml")).getroot()
pill = [i for i in inc.iter("include") if i.get("name") == "TvBoxsetsNameBadge"][0]
ok(pill.find(".//texture").text.endswith("$INFO[ListItem.DBType]_$INFO[ListItem.DBID]_name.png") and pill.find(".//aspectratio").get("align") == "left", "pill include reads <type>_<id>_name.png and stays anchored to the left")
ok({p.get("name") for p in pill.findall("param")} == {"left", "top", "width", "height"}, "pill include takes left/top/width/height")
text = open(os.path.join(xdir, "View_51_Poster.xml"), encoding="utf-8", newline="").read()
text = text.replace("TvBoxsetsNameBadge", "TvBoxsetsBadge")
with open(os.path.join(xdir, "View_51_Poster.xml"), "w", encoding="utf-8", newline="") as f:
    f.write(text)
inc_text = open(os.path.join(xdir, "Includes_TvBoxsets.xml"), encoding="utf-8").read().replace("tvboxsets-badge v5", "tvboxsets-badge v2")
open(os.path.join(xdir, "Includes_TvBoxsets.xml"), "w", encoding="utf-8").write(inc_text)
ok(not skinpatch.has_badges(xdir), "a skin copy from the previous version (round badges on posters) counts as out of date")
skinpatch.patch_badges(xdir)
ok(skinpatch.has_badges(xdir) and len(pill_params("View_51_Poster.xml")) == 1 and b"content=\"TvBoxsetsBadge\"" not in open(os.path.join(xdir, "View_51_Poster.xml"), "rb").read(), "upgrading swaps the round badge for the name pill (no duplicates left behind)")

print("== tag auto-write is on by default")
store.save({"d1": box("DefaultOn", [A])})
xbmc.LIB[0]["tag"] = ["MyOwn"]
saved_setting = xbmcaddon.SETTINGS.pop("auto_tags")      # no stored value: the add-on's built-in default applies
xbmc.RPC_LOG.clear(); service.run()
xbmcaddon.SETTINGS["auto_tags"] = saved_setting
ok(xbmc.LIB[0]["tag"] == ["MyOwn", "Boxset: DefaultOn"], "with no stored setting the service writes the boxset tag (default on)")
store.save({"d1": box("DefaultOn", [A, B])})
before_mtime = service._mtime()
w = service.Watcher()
w.tag_debounce.quiet = 0.0
w.tag_debounce.event()
ok(w.tag_debounce.due() and service.Debouncer(quiet=2.5).quiet == 2.5, "a boxset edit is picked up after 2.5 quiet seconds")

print("== packaging: icon, settings, strings, licence headers")
import re, subprocess, hashlib, zipfile  # noqa: E402
ok(open(os.path.join(ADDON, "icon.png"), "rb").read(8) == b"\x89PNG\r\n\x1a\n", "icon.png is a PNG")
ok(open(os.path.join(ADDON, "fanart.jpg"), "rb").read(2) == b"\xff\xd8", "fanart.jpg is a JPEG")
meta = ET.parse(os.path.join(ADDON, "addon.xml")).getroot().find("extension[@point='xbmc.addon.metadata']")
ok(meta.findtext("assets/icon") == "icon.png" and meta.findtext("assets/fanart") == "fanart.jpg", "addon.xml references icon + fanart")
ok(meta.findtext("news"), "addon.xml has a changelog (<news>)")
ok(ET.parse(os.path.join(ADDON, "addon.xml")).getroot().get("provider-name") == "Frecklesnoot", "add-on author is Frecklesnoot")
po = open(os.path.join(ADDON, "resources/language/resource.language.en_gb/strings.po"), encoding="utf-8").read()
defined = set(re.findall(r'msgctxt "#(\d+)"', po))
settings = ET.parse(os.path.join(ADDON, "resources/settings.xml")).getroot()
used = {e.get(a) for e in settings.iter() for a in ("label", "help") if e.get(a)}
ok(used and used <= defined, "every settings label/help id exists in strings.po (%d ids)" % len(used))
ok({s.get("id") for s in settings.iter("setting") if s.get("type") != "action"} == set(xbmcaddon.SETTINGS), "settings.xml ids match what the add-on reads")
btn = [x for x in settings.iter("setting") if x.get("type") == "action"]
ok(len(btn) == 1 and "action=menu" in btn[0].findtext("data"), "settings has a button that opens the Boxsets menu")
for f in sorted(glob.glob(os.path.join(ADDON, "*.py"))):
    ok("SPDX-License-Identifier: GPL-2.0-or-later" in open(f, encoding="utf-8").read(), "licence header: " + os.path.basename(f))

print("== GitHub files (tests, releases, release notes)")
REPO = os.path.abspath(os.path.join(HERE, ".."))
import re as _re, subprocess as _sp  # noqa: E402
sys.path.insert(0, os.path.join(REPO, "tools"))
import release_notes  # noqa: E402
changelog = open(os.path.join(REPO, "CHANGELOG.md"), encoding="utf-8").read()
version = ET.parse(os.path.join(ADDON, "addon.xml")).getroot().get("version")
body = release_notes.section(changelog, version)
ok(body and len(body.strip()) > 40, "CHANGELOG.md has an entry for the add-on's current version (%s)" % version)
news = ET.parse(os.path.join(ADDON, "addon.xml")).getroot().find(".//news").text
ok(("v%s" % version) in news, "the add-on's own changelog text (<news>) mentions this version too")
ok(release_notes.section(changelog, "0.0.0") is None and release_notes.section("## 1.0 (x)\nA\n## 0.9\nB\n", "1.0").strip() == "A", "release_notes finds a version's section and stops at the next one")
res = _sp.run([sys.executable, os.path.join(REPO, "tools", "release_notes.py"), version], capture_output=True, text=True)
ok(res.returncode == 0 and "SHA256SUMS" in res.stdout and res.stdout.strip().startswith("-"), "release_notes.py prints the notes plus a how-to-verify footer")
res = _sp.run([sys.executable, os.path.join(REPO, "tools", "release_notes.py"), "0.0.0"], capture_output=True, text=True)
ok(res.returncode != 0, "a release for a version with no changelog entry is refused")
try:
    import yaml
except ImportError:
    yaml = None
for name in ("ci.yml", "release.yml"):
    path = os.path.join(REPO, ".github", "workflows", name)
    ok(os.path.exists(path), ".github/workflows/%s exists" % name)
if yaml:
    ci = yaml.safe_load(open(os.path.join(REPO, ".github", "workflows", "ci.yml")))
    rel = yaml.safe_load(open(os.path.join(REPO, ".github", "workflows", "release.yml")))
    steps = lambda wf, job: [s.get("run", "") + s.get("uses", "") for s in wf["jobs"][job]["steps"]]  # noqa: E731
    ok(any("tests/run_tests.py" in s for s in steps(ci, "test")) and any("build_zip.py" in s for s in steps(ci, "test")), "CI runs the tests and builds the zip")
    ok(rel[True]["push"]["tags"] == ["v*"] and rel["permissions"] == {"contents": "write"}, "release runs only for v* tags and only asks to write releases")
    rsteps = steps(rel, "release")
    ok(next(i for i, s in enumerate(rsteps) if "run_tests" in s) < next(i for i, s in enumerate(rsteps) if "build_zip" in s) < next(i for i, s in enumerate(rsteps) if "gh release create" in s), "release order: tests, then build, then publish")
    ok(all(("actions/" in u) for u in [s["uses"] for s in rel["jobs"]["release"]["steps"] if "uses" in s]), "the release job only uses GitHub's own 'actions/' helpers (no third-party code)")
    check = [s["run"] for s in rel["jobs"]["release"]["steps"] if "does not match" in s.get("run", "")][0]
    publish = [s["run"] for s in rel["jobs"]["release"]["steps"] if "gh release" in s.get("run", "")][0]
    ok("workflow_dispatch" in rel[True] and rel[True]["workflow_dispatch"]["inputs"]["tag"]["required"], "the release can also be run by hand for an existing tag (Actions > Release > Run workflow)")
    ok(rel["env"]["TAG"] == "${{ github.event.inputs.tag || github.ref_name }}", "the tag comes from the pushed tag, or from the hand-run box")
    if shutil.which("sh"):
        env_ok = dict(os.environ, TAG="v" + version)
        env_bad = dict(os.environ, TAG="v0.0.1")
        ok(_sp.run(["sh", "-c", check], cwd=REPO, env=env_ok, capture_output=True).returncode == 0 and _sp.run(["sh", "-c", check], cwd=REPO, env=env_bad, capture_output=True).returncode != 0, "the tag-must-match-addon.xml check passes for v%s and fails for a wrong tag" % version)
        # run the publish step against a pretend `gh`, once for a new release and once for one that already exists
        shim = os.path.join(ROOT, "gh-shim"); work = os.path.join(ROOT, "gh-work")
        os.makedirs(shim); os.makedirs(os.path.join(work, "dist"))
        for n in ("a.zip", "SHA256SUMS"):
            open(os.path.join(work, "dist", n), "w").write("x")
        open(os.path.join(work, "release-notes.md"), "w").write("notes")
        open(os.path.join(shim, "gh"), "w").write('#!/bin/sh\necho "$@" >> "$GH_LOG"\nif [ "$1 $2" = "release view" ]; then [ "$GH_EXISTS" = "1" ]; exit $?; fi\nexit 0\n')
        os.chmod(os.path.join(shim, "gh"), 0o755)
        def publish_calls(exists):
            log = os.path.join(ROOT, "gh-%s.log" % exists)
            _sp.run(["sh", "-c", publish], cwd=work, capture_output=True, check=True,
                    env=dict(os.environ, TAG="v" + version, GH_LOG=log, GH_EXISTS=str(exists), PATH=shim + os.pathsep + os.environ["PATH"]))
            return open(log).read().splitlines()
        new_calls = publish_calls(0)
        ok(len(new_calls) == 2 and new_calls[1].startswith("release create v%s " % version) and "dist/a.zip" in new_calls[1] and "--notes-file release-notes.md" in new_calls[1], "a new tag: the release is created with the zip, the checksums and the notes")
        old_calls = publish_calls(1)
        ok(len(old_calls) == 3 and old_calls[1].startswith("release upload v%s " % version) and old_calls[1].endswith("--clobber") and old_calls[2].startswith("release edit v%s " % version), "a release that already exists (published on the web page): the files are added to it, not 'create' again, which would fail")
ok(os.path.exists(os.path.join(REPO, ".github", "ISSUE_TEMPLATE", "bug_report.md")) and "Diagnostics report" in open(os.path.join(REPO, ".github", "ISSUE_TEMPLATE", "bug_report.md")).read(), "bug reports ask for a diagnostics report")
ok("Don't trust a zip? Check it" in open(os.path.join(REPO, "README.md"), encoding="utf-8").read(), "README explains how to verify a download")
meta = ET.parse(os.path.join(ADDON, "addon.xml")).getroot().find("extension[@point='xbmc.addon.metadata']")
src_url = meta.findtext("source")
ok(_re.match(r"^https://github\.com/[\w-]+/kodi-tv-boxsets$", src_url or "") and meta.findtext("website") == src_url, "the add-on's information page links to the GitHub repository (%s)" % src_url)
readme_text = open(os.path.join(REPO, "README.md"), encoding="utf-8").read()
ok(src_url + "/actions/workflows/ci.yml/badge.svg" in readme_text and src_url + "/releases" in readme_text, "README shows the tests badge and links to the releases")
ok("`LICENSE` file" in readme_text and "add the full licence text" not in readme_text, "README points at the LICENSE file")

print("== packaging: reproducible zip + repository")

TOOLS = os.path.abspath(os.path.join(HERE, "..", "tools"))
sys.path.insert(0, TOOLS)
import build_zip  # noqa: E402
bad_src = os.path.join(ROOT, "bad-addon", "plugin.video.tvboxsets")
shutil.copytree(ADDON, bad_src)
with open(os.path.join(bad_src, "addon.xml"), "a") as f:
    f.write("<unclosed>")
try:
    build_zip.build_zip(bad_src, os.path.join(ROOT, "bad-out"))
    refused = False
except SystemExit as exc:
    refused = "addon.xml" in str(exc)
ok(refused and not os.path.exists(os.path.join(ROOT, "bad-out")), "the build refuses to package an add-on whose XML is broken")
out1, ver, _ = build_zip.build_zip(ADDON, os.path.join(ROOT, "z1"))
out2, _, _ = build_zip.build_zip(ADDON, os.path.join(ROOT, "z2"))
sha = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest()
ok(sha(out1) == sha(out2), "same source builds a byte-identical zip")
repo = os.path.join(ROOT, "repo")
res = subprocess.run([sys.executable, os.path.join(TOOLS, "make_repo.py"), "--base-url", "https://example.com/kodi", "--out", repo],
                     capture_output=True, text=True)
ok(res.returncode == 0, "make_repo.py runs: " + res.stderr[-200:])
index = open(os.path.join(repo, "addons.xml"), encoding="utf-8").read()
ok(open(os.path.join(repo, "addons.xml.md5")).read() == hashlib.md5(index.encode("utf-8")).hexdigest(), "addons.xml.md5 matches addons.xml")
ids = [a.get("id") for a in ET.fromstring(index).findall("addon")]
ok(ids == ["plugin.video.tvboxsets", "repository.tvboxsets"], "addons.xml lists the add-on and the repository add-on")
rz = zipfile.ZipFile(os.path.join(repo, "repository.tvboxsets-1.0.0.zip"))
rxml = rz.read("repository.tvboxsets/addon.xml").decode()
ok('provider-name="Frecklesnoot"' in rxml, "repository add-on author is Frecklesnoot")
ok("https://example.com/kodi/addons.xml" in rxml and "https://example.com/kodi/zips/" in rxml, "repository add-on points at the base URL")
ok(os.path.exists(os.path.join(repo, "zips/plugin.video.tvboxsets/plugin.video.tvboxsets-%s.zip" % ver)), "add-on zip is where Kodi expects it")
ok(set(zipfile.ZipFile(os.path.join(repo, "zips/plugin.video.tvboxsets/plugin.video.tvboxsets-%s.zip" % ver)).namelist())
   == set(zipfile.ZipFile(out1).namelist()), "repo copy has the same files as the plain build")
idx = open(os.path.join(repo, "index.html"), encoding="utf-8").read()
ok("repository.tvboxsets-1.0.0.zip" in idx, "repository folder has a landing page linking the install zip")
ok(src_url in idx, "the landing page links to the source code")
bad = subprocess.run([sys.executable, os.path.join(TOOLS, "make_repo.py"), "--base-url", "example.com", "--out", repo + "2"],
                     capture_output=True, text=True)
ok(bad.returncode != 0, "make_repo.py rejects a base URL without http(s)://")

# --- repository served from GitHub Pages: the release zip is published byte for byte ---
rel_zip = os.path.join(ROOT, "rel", "plugin.video.tvboxsets-%s.zip" % ver)
os.makedirs(os.path.dirname(rel_zip), exist_ok=True)
shutil.copy(out1, rel_zip)
pages = os.path.join(ROOT, "pages")
res = subprocess.run([sys.executable, os.path.join(TOOLS, "make_repo.py"), "--addon-zip", rel_zip, "--repo-version", "1.2.0",
                      "--base-url", "https://someone.github.io/kodi-tv-boxsets/", "--out", pages], capture_output=True, text=True)
ok(res.returncode == 0, "make_repo.py --addon-zip runs: " + res.stderr[-200:])
served = os.path.join(pages, "zips/plugin.video.tvboxsets/plugin.video.tvboxsets-%s.zip" % ver)
ok(open(served, "rb").read() == open(rel_zip, "rb").read(), "the repository serves the release zip byte for byte")
ok(os.path.exists(os.path.join(pages, ".nojekyll")), "the Pages site has .nojekyll")
ok(os.path.exists(os.path.join(pages, "repository.tvboxsets-1.2.0.zip")), "repository add-on zip carries the requested version")
ok("https://someone.github.io/kodi-tv-boxsets/addons.xml" in zipfile.ZipFile(os.path.join(pages, "repository.tvboxsets-1.2.0.zip")).read("repository.tvboxsets/addon.xml").decode(),
   "repository add-on points at GitHub Pages")
hand = os.path.join(ROOT, "hand")
res = subprocess.run([sys.executable, os.path.join(TOOLS, "make_repo.py"), "--repo-version", "1.2.0",
                      "--base-url", "https://old.example.com/", "--repo-url", "https://new.example.com/x/", "--out", hand], capture_output=True, text=True)
hx = zipfile.ZipFile(os.path.join(hand, "repository.tvboxsets-1.2.0.zip")).read("repository.tvboxsets/addon.xml").decode()
ok(res.returncode == 0 and "https://new.example.com/x/addons.xml" in hx and "old.example.com" not in hx,
   "--repo-url sends the repository add-on to another address (hand-over site)")
wrong = os.path.join(ROOT, "rel", "plugin.video.tvboxsets-9.9.9.zip")
with zipfile.ZipFile(wrong, "w") as z:
    z.writestr("plugin.video.tvboxsets/addon.xml", '<addon id="plugin.video.tvboxsets" version="9.9.9"/>')
bad2 = subprocess.run([sys.executable, os.path.join(TOOLS, "make_repo.py"), "--addon-zip", wrong, "--base-url", "https://a.example/", "--out", repo + "3"],
                      capture_output=True, text=True)
ok(bad2.returncode != 0 and not os.path.exists(os.path.join(repo + "3", "addons.xml")), "an --addon-zip of another version is refused")
rel = open(os.path.join(REPO, ".github", "workflows", "release.yml")).read()
ok("tools/make_repo.py" in rel and "gh-pages" in rel and "--addon-zip" in rel and "site/repository.tvboxsets-" in rel,
   "release workflow builds the repository and publishes it to gh-pages")
ok('REPO_VERSION: "1.2.0"' in rel, "release workflow sets the repository add-on version")

print("\nALL {} CHECKS PASSED".format(CHECKS[0]))
