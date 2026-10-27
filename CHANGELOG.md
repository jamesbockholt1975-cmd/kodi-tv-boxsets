# Changelog

## 0.12.1 (alpha)
- **Fix: no `[Movie]` label on movies inside a boxset (0.12.0).** Estuary draws a movie's title field, not the
  list label, so the label was never seen. The title now carries `[Movie]` as well, and the real title is
  kept in the list item property `boxset_title`, which the right-click scripts (Move, Place, Remove) read,
  so they keep finding the right entry.
- Tests: 381 checks.

## 0.12.0 (alpha)
- **Movies are labelled inside a boxset.** In a boxset's list a movie now shows `[Movie]` after its title (in
  light blue), including movies that are not in the library at the moment. Only the label changes: the
  movie's title, artwork and info are untouched, so the right-click menu and Kodi's own info keep working.
- **Place a movie (or any item) after another one.** New right-click entry inside a boxset, "Place after
  another item...": pick the show (or "[At the start]") and the item moves straight after it, for example a
  film right after the series it belongs to. It uses the manual viewing order, like Move up/down, and does
  not change what is in the boxset. The order dialog ("Change show order") also marks movies with `[Movie]`.
- Tests: 379 checks.

## 0.11.3 (alpha)
- **Updates now come from GitHub.** Publishing a release (pushing a `v...` tag) now also builds the Kodi
  repository and publishes it with GitHub Pages (the `gh-pages` branch), serving the *same* zip that is
  attached to the release, byte for byte, so its checksum matches `SHA256SUMS`. People install the
  repository add-on once and Kodi then offers every new release by itself.
- `tools/make_repo.py`: `--addon-zip` (publish a zip that is already built, refused if it is another
  version), `--repo-url` (address written into the repository add-on, for a hand-over site), and a
  `.nojekyll` file for GitHub Pages.
- Repository add-on 1.2.0 points at GitHub Pages. The old Netlify site gets one last update that offers
  it, so existing users move over.
- Tests: 368 checks.

## 0.11.2 (alpha)
- Source and release links: the add-on's information page in Kodi now shows the GitHub repository as its
  website and source; the README has a tests badge and links; the repository's landing page links to the
  source. No change to how the add-on works.
- Release workflow: also works when the release was already created on the GitHub web page (it adds the
  zip and checksums to it instead of failing), and can be run by hand for an existing tag (Actions >
  Release > Run workflow). Tested with a pretend `gh` for both cases.
- Tests: 359 checks.

## 0.11.1 (alpha)
- **Fix: stale labels.** Put a show in the wrong boxset, take it out again, and the poster kept showing
  the wrong boxset's label. The picture file on disk was being updated correctly; but Kodi keeps a picture
  it has already drawn for as long as its address stays the same, and the address never changed. Pictures
  now live in a numbered folder (`badges/r<N>/`), every change builds a complete new folder, and the skin's
  picture path includes the number (published by the add-on in the Home-window property
  `tvboxsets_badge_rev`). When the number changes every visible badge reloads at once. Items that are in no
  boxset have no file at all (no more transparent placeholders). Folder numbers are never reused, even if
  the state file is damaged. Older folders and the flat pictures from 0.9 - 0.11.0 are removed. Identical
  pictures are hard-linked (or copied) from one stored copy; each distinct label is drawn once and cached.
- Skin badge include is now version 4: existing skin copies must be updated once more (Boxsets menu >
  "Update ...: add the home widget and library badges").
- The build script now refuses to package an add-on with broken XML (a stray `<name>` in the changelog text
  of 0.11.0 once produced a bad package).
- Diagnostics shows the live picture folder number.
- GitHub: the tests run on every change, and a published release has its zip built from the tagged source
  by GitHub, with a `SHA256SUMS` file (`.github/workflows/`). `tools/release_notes.py` prints a version's
  changelog section for the release page. A test now fails if the add-on version has no changelog entry.
- Tests: 351 checks.

## 0.11.0 (alpha)
- **Boxset tags are written automatically.** "Keep Kodi tags in step with my boxsets" is now **on by
  default**: add a show or movie to a boxset and the `Boxset: <name>` tag is written a few seconds later
  (the service waits 2.5 quiet seconds, so a run of quick edits is batched). Anyone who had never changed
  the setting gets the new default; turn it off in the add-on settings if you would rather not, and
  "Remove boxset tags from Kodi..." undoes it.
- **Boxset name labels on posters.** The badge on a poster is now a small pill with the badge icon and the
  boxset name ("Marvel"; "Marvel +1" when the item is in several boxsets; long names end in an ellipsis).
  List rows keep the small round icon (no room for text). New setting "Show the boxset name next to the
  badge" (on); off gives the plain round icon again.
- How: Kodi's built-in Python has no image library, so the letters are pre-rendered once from DejaVu Sans
  Bold into `resources/glyphs.json.z` (`tools/make_font.py`, Pillow, build time only) and a plain-Python
  renderer (`labelimg.py`, standard library only) assembles each label as a PNG. Latin letters (ASCII,
  Latin-1, Latin Extended-A, common punctuation) are supported; anything else shows as `?`.
- The `badges` folder now holds two files per item (`tvshow_12.png` icon, `tvshow_12_name.png` label) and a
  `state.json` remembering what each file holds, so only changed files are rewritten. Older folders are
  upgraded automatically.
- Skin: badge include version 3 (`TvBoxsetsNameBadge`). Patching now strips and re-places our own
  placements, so upgrading an older skin copy replaces round badges with labels instead of duplicating them.
  Tested on a copy of a real Estuary skin folder (14 placements in 7 files, all still well-formed,
  idempotent, an old-style patch replaced cleanly). Existing skin copies: Boxsets menu > "Update ...".
- DejaVu font credit in `docs/font-notice.txt`.
- Tests: 326 checks.

## 0.10.0 (alpha)
- **Which boxsets an item is in, in the video info dialog.** Estuary's info dialog already has a
  "Tags" row, so no skin change is needed: once an item carries a tag such as "Boxset: Marvel" the
  dialog shows it. New setting **Keep Kodi tags in step with my boxsets** (off by default, because it
  writes to the Kodi library) lets the background service keep those tags current: it waits for a
  quiet moment after a boxset change, a library scan/clean/removal, a setting change or startup.
  Only tags starting with the prefix (default "Boxset:") are ever added or removed. The Tools
  action ("Write boxsets to Kodi tags") does the same on demand.
- **Boxsets menu > "Remove boxset tags from Kodi..."**: takes every boxset tag off every item (asks first;
  your boxsets and your own tags are untouched).
- Tag work moved into `tagsync.py` and now asks Kodi for the light set of fields (no artwork/plots).
- **Badges in list rows.** The wide list and media list rows get a small badge between the watched icon
  and the title. The plain List view's rows have no room, but that view already shows the badge on its
  preview poster. Badge include is now version 2: existing skin copies are offered "Update ...: add the
  home widget and library badges" in the Boxsets menu. Tested on a copy of a real Estuary skin folder: 14
  placements in 7 files, every file still well-formed, idempotent.
- Tests: 296 checks.

## 0.9.0 (alpha)
- **Boxset badge in the library.** A small stacked-cards icon on the poster of every TV show and
  movie that is in a boxset, in the Estuary (Boxsets) skin copy. Shown in the Poster, Wall,
  InfoWall, Shift and List views and in the video info dialog (not in the banner/fan-art views; the
  wide list rows were added in 0.10.0). The home screen's poster-style widgets share the Poster/Wall
  tile layout, so they show it too.
- How it works: Kodi can't tell a skin "is this item in a boxset?" for every poster on screen, but a
  skin can show a picture whose file name contains the item's library id. The background service keeps
  a folder of tiny files (`tvshow_12.png`, `movie_7.png` in the add-on's userdata `badges` folder):
  the badge picture while an item is in a boxset, a 1x1 transparent picture otherwise. Files are
  overwritten, never deleted, so Kodi's picture cache notices the change. It refreshes when the
  boxsets file changes, after a library scan/clean/removal, when settings change, and at startup.
- The skin patch (`skinpatch.patch_badges`) adds `Includes_TvBoxsets.xml` and places the badge
  include after each poster image in five of Estuary's view files. Missing/unrecognised files are
  skipped. Tested on a copy of a real Estuary skin folder (8 placements in 5 files, all files still
  well-formed, idempotent).
- Existing skin copies get it through the Boxsets menu entry "Update ...: add the home widget and
  library badges" (also upgrades the widget). New settings: "Show a badge on library items".
- Boxsets menu > "Refresh the boxset badges". Diagnostics now reports whether the skin copy has the badges.
- Tests: 273 checks.

## 0.8.0 (alpha)
- **Right-click any library TV show or movie > "Boxsets..."**: shows every boxset with a tick
  against the ones the item is already in (hand-picked or matched by smart rules). Tick or
  untick to add/remove in one go, or start a new boxset. Replaces "Add to TV show boxset" /
  "Add movie to boxset".
- **Continue watching** row now shows the show (or movie) to carry on with, with the boxset
  name on the second line, instead of the boxset itself. The partly-watched show is preferred,
  otherwise the first unwatched one in viewing order; a show in several boxsets appears once.
- **Move up / Move down** in the right-click menu inside a boxset sets a viewing order, for
  normal and smart boxsets and for movies. The order is stored separately from membership
  (`order`), so smart boxsets keep filling themselves. "Change show order" now uses it too.
- **Cleaner lists:** the "+ Create new boxset", "+ Create new smart boxset", Tools, skin-setup
  and "Add shows/movies", "Play next" rows are gone from the boxset list and from inside a
  boxset. They moved into a **Boxsets menu** (right-click any boxset, or the add-on's settings
  > Open the Boxsets menu) and into the right-click menu inside a boxset. Empty lists show a
  single "create your first boxset" / "add shows" row so there is always a way in.
- New shared modules `library.py` and `ctxutil.py`; six small right-click scripts.
- Tests: 236 checks.

## 0.7.1 (alpha)
- **Fix:** the home screen Boxsets / Continue watching rows did not update after creating a
  boxset or adding/removing shows until Kodi was restarted. Rows fed by an add-on only reload
  when their address changes, so the rows now carry a `reload` value taken from a Home-window
  property (`tvboxsets_reload`) that the add-on changes on every save.
- New background service: also refreshes the rows when playback stops or the library updates, so
  watched progress stays current (events are batched into one refresh).
- Widget block is now v3. Existing skin copies upgrade in place via the add-on's
  "Update ... add the Boxsets home widget" item. A service is only started by Kodi at startup,
  so restart Kodi once after updating.
- Tools > "Refresh the home screen rows" as a manual fallback.
- Tests: 182 checks.

## 0.7.0 (alpha)
- **Smart boxsets:** rules (genre, tag, studio, year range, title) add matching items
  automatically; hand-picked extras and exclusions are supported.
- **Mixed boxsets:** movies can be in a boxset alongside TV shows. Right-click a library movie
  to add it; movies play from the boxset; progress counts movies too.
- **Mark everything as watched / unwatched** for a whole boxset.
- **Write boxsets to Kodi tags** (one-way, with a configurable prefix so your own tags are never
  touched). "Create boxsets from tags" now covers movies and strips the prefix.
- Five artwork types per boxset: poster, fanart, banner, clear logo, landscape.
- **Sort boxsets** by name, in-progress first, or recently changed (setting).
- **Continue watching** row on the home screen widget (widget block v2; use the add-on's
  "Update ... add the Boxsets home widget" item to upgrade an existing skin copy).
- Data file is now format 3 (a copy of the previous file is kept as `pre-format3-boxsets.json`).
- Movies are only fetched from the library when something needs them.
- `docs/other-skins.md`: using the add-on with skins that have their own menu editors.
- Tests: 163 checks.
- Not included yet: a combined cross-show watch order (interleaving episodes of different
  shows).

## 0.6.1 (alpha)
- Author (provider name) set to Frecklesnoot in the add-on and the repository add-on.

## 0.6.0 (alpha)
- **Diagnostics report** (Tools): Kodi/OS/add-on versions, skin copy checks, counts and the
  add-on's recent log lines. Contains no show or boxset names; file paths are scrubbed.
- **Add-on settings:** number of automatic backups to keep, show/hide missing shows, extra logging.
- **Versioned data file:** `boxsets.json` is now format 2. Old files are read as before and
  upgraded on the next save, with a permanent copy of the old file kept in `backups/`. If a
  file was written by a *newer* add-on, this one refuses to touch it.
- Icon and fanart (drawn by `tools/make_art.py`), English strings file, changelog in `addon.xml`.
- `tools/make_repo.py` builds a Kodi repository that can be hosted on any plain web server,
  so testers get updates automatically (no GitHub needed).
- Tests: 96 checks (was 51).

## 0.5.0
- Watched progress on boxset tiles and shows (episode counts and watched flag).
- Custom poster and fanart per boxset (image file, or artwork from a show).
- Manual show ordering, and "Play next unwatched episode" for a boxset.
- Shows that leave the library appear greyed out as "(not in library)" and return on their own.
- Lookup falls back to a unique title match when a show's year changes.
- Create boxsets from Kodi tags.
- Automatic daily backups, plus export, import (merge or replace) and restore.
- Detects Estuary updates and can rebuild the Boxsets skin safely, keeping skin settings.
- New skin copies start with the user's existing Estuary skin settings.
- Test-suite and build script added.

## 0.4.1
- "Remove from this boxset" is now a proper context-menu item, shown only inside a boxset.

## 0.4.0
- Home screen widget row of boxsets when "Boxsets" is highlighted in the Estuary copy.
- Widget-only view of boxsets (no create/setup rows).

## 0.3.0
- Context-menu item "Add to TV show boxset" on library TV shows.
- Shared storage module used by the browser and the context menu.

## 0.2.1
- Enables the cloned skin through JSON-RPC and offers to switch to it.

## 0.2.0
- Builds a modified copy of Estuary with a "Boxsets" main menu item.

## 0.1.0
- First version: create boxsets, add and remove shows, browse them with artwork.
