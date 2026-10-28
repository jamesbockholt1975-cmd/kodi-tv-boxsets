# TV Boxsets for Kodi

[![Tests](https://github.com/jamesbockholt1975-cmd/kodi-tv-boxsets/actions/workflows/ci.yml/badge.svg)](https://github.com/jamesbockholt1975-cmd/kodi-tv-boxsets/actions/workflows/ci.yml)
**Source:** https://github.com/jamesbockholt1975-cmd/kodi-tv-boxsets · **Releases (zips with checksums):** https://github.com/jamesbockholt1975-cmd/kodi-tv-boxsets/releases


Kodi has "Sets" for movies but nothing equivalent for TV shows. **TV Boxsets** is a
Kodi add-on (Python 3) that lets you group TV shows from your library into boxsets and
browse them with artwork in Kodi's native views, with an optional home screen menu item
and widget for the default **Estuary** skin.

> **Status: work in progress.** Only tested on **Kodi 22 RC1**. Other versions and
> platforms are untested. Back up your setup before trying it.

## Features

- Create boxsets, add and remove shows, rename, delete.
- Right-click any library TV show or movie: **Boxsets...** (see which boxsets it is in, tick to add or remove).
- Right-click inside a boxset: **Move up / Move down**, **Play all unwatched (queue)**, **Place after another item** (put a movie right after its show), **Watch order** (a separate sequence of seasons, crossover episodes and movies, so one show can come back later), **Remove from this boxset**, **Play next
  unwatched episode**, **Add shows / movies**, and the **Boxsets menu** (create, backup, tags,
  skin setup, diagnostics). The lists themselves show only boxsets and shows.
- Custom poster, fanart, banner, clear logo and landscape art per boxset; manual or A-Z order;
  sort boxsets by name, progress or recent change.
- **Smart boxsets** (rules add matching items automatically) and **mixed boxsets** (TV shows and
  movies together).
- A small **badge on posters and list rows** of library items that are in a boxset, with the **boxset name**
  on posters (Estuary (Boxsets) skin copy).
- **Boxset tags** ("Boxset: Marvel") written automatically (can be switched off), shown in the info dialog's Tags row.
- Mark a whole boxset watched/unwatched; write boxsets to Kodi tags for other skins to use.
- Watched progress, **Play next unwatched episode**, greyed-out entries for shows that
  have left the library.
- Create boxsets from Kodi tags or movie sets.
- Smart boxset rules: genre, tag, studio, years, title, unwatched only, recently added, rating at least.
- Boxset poster collage built from the items inside (needs the optional Python Imaging Library add-on).
- Boxsets in other skins: Boxsets menu > Add boxsets to Kodi's library menu (Kodi library nodes built from the tags).
- Share a watch order as a small file: export it from the watch order view, import someone else's from the Boxsets menu.
- Automatic daily backups, export, import (merge or replace) and restore.
- Estuary integration: a **Boxsets** main menu item and a widget row (see below).
- Support tools: a **diagnostics report** for bug reports, add-on **settings**, and a
  versioned data file that upgrades safely.

## Install

**Best: through the repository, so Kodi updates it for you.**

1. Download `repository.tvboxsets-<version>.zip` from the
   [releases page](https://github.com/jamesbockholt1975-cmd/kodi-tv-boxsets/releases) (or from
   https://jamesbockholt1975-cmd.github.io/kodi-tv-boxsets/).
2. In Kodi: **Settings > Add-ons > Install from zip file** (enable *Unknown sources* first) and choose it.
3. **Add-ons > Install from repository > TV Boxsets Repository > Video add-ons > TV Boxsets > Install.**
4. Restart Kodi so the right-click menu entries load. New releases are then offered by Kodi itself.

**Or by hand:** download `plugin.video.tvboxsets-<version>.zip` from the releases page and use
**Install from zip file**. Releases are built by GitHub from the tagged source, with `SHA256SUMS`.

For the home screen item, open the add-on and choose **Add 'Boxsets' to the home screen
(Estuary)**. That builds a modified copy of Estuary called *Estuary (Boxsets)*; your normal
Estuary is left untouched.

## Repository layout

```
plugin.video.tvboxsets/   the add-on
  addon.xml               manifest (plugin source + two context-menu items)
  main.py                 plugin entry point: views, actions, tools, skin setup
  store.py                shared storage, automatic backups, merge helpers
  skinpatch.py            clones Estuary and patches Home.xml (no Kodi imports)
  context.py              context item: add the focused library show to a boxset
  context_remove.py       context item: remove the focused show from a boxset
  library.py              library lookups, smart matches, ordering, membership (shared)
  badges.py               keeps the badge and name-label picture files in step with the boxsets
  labelimg.py             draws the name labels (standard library only)
  libnodes.py             writes/removes the "TV Boxsets" Kodi library nodes (other skins)
  collage.py              builds a poster collage from the items' posters (Pillow)
  tagsync.py              writes/removes the prefixed boxset tags in the Kodi library
  ctxutil.py, ctx_*.py    small right-click scripts used while browsing inside a boxset
  diagnostics.py          builds the diagnostics report text (no Kodi imports)
  rules.py                smart-boxset rule matching and descriptions (no Kodi imports)
  resources/              settings.xml and the English strings file
  icon.png, fanart.jpg    add-on artwork
tests/
  run_tests.py            feature tests against stand-in Kodi modules
  kodi_mocks/             fake xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon
  fixtures/Home.xml       simplified stand-in for Estuary's Home.xml (not Estuary's file)
tools/build_zip.py        builds dist/plugin.video.tvboxsets-<version>.zip
tools/make_repo.py        builds a Kodi repository folder you can host on any web server
tools/make_art.py         redraws icon.png, fanart.jpg and the badge pictures (needs Pillow)
tools/make_font.py        pre-renders the letters used on name labels (needs Pillow + DejaVu Sans Bold)
docs/hosting-a-repository.md   plain-language steps for hosting updates without GitHub
docs/other-skins.md       using the add-on with skins that have their own menu editors
```

## Tests

```
python3 tests/run_tests.py
```

No Kodi needed. The tests run the add-on's real code against stand-in Kodi modules in a
temporary folder and cover the views, storage, backups, tag import, ordering, artwork,
play-next, the context menus and the skin patching. They **cannot** show how Kodi
renders anything, so they are no substitute for testing in Kodi.

## Build a zip

```
python3 tools/build_zip.py
```

## Getting updates to testers (no GitHub needed)

A Kodi repository is just a folder of static files. `tools/make_repo.py` builds it for any
web address you choose; upload the folder and testers install one small repository zip, after
which Kodi installs new versions by itself. See `docs/hosting-a-repository.md`.

## Reporting a problem

In the add-on go to **Tools > Create a diagnostics report**, save it, and attach it to your
post. It lists versions, checks and counts only (no show or boxset names). For deeper
problems, switch on *Write extra detail to the Kodi log* in the add-on settings first.

## How it works

- Boxsets are directory items listed with `setContent('tvshows')`, so the skin uses its
  native poster and list views. Shows inside a boxset link to Kodi's own library node
  (`videodb://tvshows/titles/<id>/`), so seasons, episodes and playback are untouched.
- Entries are stored in `boxsets.json` (add-on userdata) by **title and year** (movies are keyed
  separately), not library ID, so boxsets survive a library clean or rebuild. The file is
  versioned (currently format 3). Smart boxsets store their rules and are filled from the
  library each time they are shown.
- Library data comes from JSON-RPC (`VideoLibrary.GetTVShows`, `GetTVShowDetails`,
  `GetEpisodes`, `GetTags`, `Player.Open`).
- Estuary integration: `skinpatch.py` copies the installed `skin.estuary` to
  `special://home/addons/skin.estuary.boxsets`, changes the id and name in `addon.xml`,
  inserts a menu item after the TV Shows item in `xml/Home.xml` (cloned from it), and adds
  a widget group whose control id equals the item's `menu_id`. If Estuary's `Home.xml`
  changes shape, the build stops with an error and cleans up after itself.
- This repository contains **no Estuary code**; the copy is made at runtime from the
  user's own installed skin.

## Don't trust a zip? Check it

- **Read the code.** It is all plain Python and XML in `plugin.video.tvboxsets/`; nothing is compiled or
  hidden, and there is no code in the zip that is not in this repository.
- **Tests run in public.** The *Tests* workflow runs `tests/run_tests.py` on every change, on GitHub's own
  computers (see the Actions tab). A green tick on a commit means the tests passed.
- **Releases are built here.** When a version tag (such as `v0.11.2`) is pushed or a release is published, the *Release* workflow runs the tests, builds
  the zip from that tagged source with `tools/build_zip.py`, and attaches the zip and a `SHA256SUMS` file to
  the release. You can compare a download with it:
  - Windows (PowerShell): `Get-FileHash plugin.video.tvboxsets-<version>.zip -Algorithm SHA256`
  - Linux / macOS: `sha256sum plugin.video.tvboxsets-<version>.zip`
- **Build it yourself.** `python3 tools/build_zip.py` makes the same zip from the source (files are added in
  a fixed order with fixed dates). Unzip both and compare the folders; they should be identical.
- **What the add-on can touch.** It reads your Kodi video library through Kodi's own interface, keeps its data in
  its own userdata folder, and (only when you choose to) writes tags and watched state to the library and adds
  a skin copy under `addons/`. It makes no network requests of its own.

## Using other skins

See `docs/other-skins.md`: the add-on works as a plain plugin path, so skins with their own
menu or widget editors don't need the Estuary skin copy at all.

## Known limitations

- The home screen integration is Estuary-only and depends on `Home.xml`'s structure.
- The skin copy does not get Estuary updates; the add-on detects them and offers a rebuild.
- Boxsets live in the add-on's own file, not Kodi's video database, so other add-ons and
  skins cannot see them.
- No automatic poster collage (Kodi's bundled Python has no image library).

## Feedback welcome

Open questions: is there a cleaner way to add a main menu item to Estuary without cloning
the skin? Should boxsets live in Kodi's database (tags or a new set type)? Reports from
other Kodi versions and platforms are especially useful; please include relevant
`kodi.log` lines (the add-on logs with the prefix `[TV Boxsets]`).

## Licence

GPL-2.0-or-later: see the `LICENSE` file, and the SPDX line at the top of each source file.
Copyright (C) 2026 Frecklesnoot.

## Credits

Boxset name labels use letter shapes pre-rendered from DejaVu Sans Bold (Bitstream Vera licence; see
`docs/font-notice.txt`).

## About

Developed with the help of an AI assistant (Claude, by Anthropic), then tested against
simulated Kodi modules and by the author on Kodi 22 RC1.
