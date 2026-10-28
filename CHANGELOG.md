# Changelog

## 0.21.2 (alpha)
- **Fix: "Operating system: Busy" in the diagnostics report.** Kodi fills that label in lazily; the report now
  falls back to Python's own description when Kodi says Busy.
- **Release page and README now say which file to install.** Using GitHub's automatic *Source code (zip)* /
  *Download ZIP* gives Kodi's "invalid structure" error (the add-on sits inside an extra folder). The release
  notes and README now tell people to use `plugin.video.tvboxsets-<version>.zip` or
  `repository.tvboxsets-<version>.zip` from the Assets list.
- Tests: 562 checks.

## 0.21.1 (alpha)
- **Boxset name on its poster.** Views such as InfoWall draw no title under a poster, so in the Boxsets list
  (and the home screen Boxsets row) you could not tell which boxset a tile was. Each boxset tile now carries
  its name, and the Estuary (Boxsets) copy draws it as a dark label in the top-left corner of the poster, the
  same place and style as the boxset-name labels on items inside a boxset. The Next up row's tiles show the
  boxset they come from the same way. Needs the skin update once (badge include version 6).
- Tests: 560 checks.

## 0.21.0 (alpha)
- **More smart-boxset rules.** The Smart rules editor gained **Unwatched only** (a movie not yet played, or a
  show with episodes left), **Added in the last N days** and **Rating at least** (5 to 9). They combine
  (AND) with genre, tag, studio, years and title, and count as rules on their own. Studio already existed.
  They are evaluated live when a boxset is shown; the Kodi tags and library menu entries follow at the next
  sync (when boxsets change or Kodi starts).
- **Boxset poster collage.** Set boxset artwork > Poster > **Make a collage from the posters inside this
  boxset** builds one 2:3 poster from up to six items (2 side by side, 3 as one tall plus two, 4 as 2x2,
  6 as 3x2) and sets it as the boxset's poster; making it again replaces the old file, and Automatic puts the
  first item's poster back. Needs Pillow, which Kodi supplies as the optional add-on
  **Python Imaging Library** (`script.module.pil`); without it a message says what to install and nothing
  else changes.
- CI installs Pillow so the collage tests run there too.
- Tests: 556 checks.

## 0.20.1 (alpha)
- **Fix: no export in the Boxsets menu.** Import a watch order file was there but export was only a
  right-click entry inside a watch order. Added **Export a watch order file...** to the Boxsets menu: it lists
  the boxsets that have a watch order and saves the one you pick.
- Tests: 528 checks.

## 0.20.0 (alpha)
- **Boxsets in any skin.** Boxsets menu > **Add boxsets to Kodi's library menu (other skins)...** writes Kodi
  library nodes: a "TV Boxsets" folder under Videos > Library with one entry per boxset and media type
  (TV shows, movies), each a filter on the boxset's Kodi tag. Skins that don't have the Estuary (Boxsets)
  home rows can then browse boxsets from their normal Videos menu. If you have no custom library folder yet,
  Kodi's built-in nodes are copied into your profile first (unchanged), since Kodi uses a custom folder
  instead of the built-in one. The entries follow your boxsets automatically (the service refreshes them
  when boxsets change); **Remove boxsets from Kodi's library menu...** deletes only the add-on's own folder.
  Needs the boxset tags (and a tag prefix); restart Kodi once after adding.
- Tests: 526 checks.

## 0.19.0 (alpha)
- **Share a watch order.** Inside a watch order, right-click > **Export this watch order to a file...** saves
  a small `.json` file (name, then each season, episode range or movie with title, year and the IMDb / TMDB /
  TVDB ids Kodi knows). No paths, artwork or watched state are in it. **Boxsets menu > Import a watch order
  file...** reads one: it matches every entry to your library by id first, then title and year, then a unique
  title, and puts the order into a new boxset (or one you pick, asking before it replaces an existing order).
  Entries you don't have yet are kept, show as "not in library", and are listed in a summary.
- Tests: 511 checks.

## 0.18.1 (alpha)
- **Clearer removing inside the watch order.** The only remove entry there was labelled "Remove from this
  boxset" although it took the entry out of the watch order only. Now there are two, named for what they do:
  **Remove from the watch order** (just that entry; the show or movie stays in the boxset) and
  **Remove from this boxset** (takes the show or movie out of the boxset, after asking; its seasons and
  episodes then leave the watch order view too).
- Tests: 491 checks.

## 0.18.0 (alpha)
- **Create boxsets from Kodi movie sets.** New entry in the Boxsets menu. It lists the movie sets in your
  Kodi library (with how many movies each has, and which already exist as a boxset), you tick the ones you
  want, and each becomes a boxset of those movies, using the set's poster and fanart unless the boxset
  already has its own. A set with the same name as an existing boxset extends it instead of making a
  duplicate; nothing is added twice. Kodi's sets are not changed. Once a set is a boxset you can add the
  matching TV shows to it and give it a watch order.
- Tests: 489 checks.

## 0.17.0 (alpha)
- **Next up (watch order) row on the home screen.** A third row under Boxsets, next to "Continue watching":
  one tile per boxset that has a watch order, showing the next unwatched episode (or movie) in that order,
  labelled with the boxset's name and ready to play with one click. It follows the order you arranged:
  seasons, crossover episodes and movies. Boxsets without a watch order have no tile (use **Fill the watch
  order from this boxset**). The row refreshes when you watch something or edit a boxset.
- **Play all unwatched (queue).** New right-click entry on a boxset (in the list and inside it) and inside the
  watch order: queues every unwatched episode and movie, in the watch order if the boxset has one (inside the
  watch order always), otherwise in the boxset's own order, and asks whether to **play them now** (replaces the
  video queue and starts at the first item) or **add them to the end of the queue**. Specials are only queued
  when a watch-order entry asks for them.
- The boxset tile's right-click menu also gained **Watch order (seasons and movies)...**.
- Needs the skin update once (the widget block is version 4).
- Tests: 480 checks.

## 0.16.1 (alpha)
- **Fix: Movies / TV shows / Music videos opened the category list.** Estuary sends the click to the category
  list whenever that Categories row is hidden with its own skin switch (Settings > Home screen). 0.15.x only
  corrected the click when this add-on's "Hide the Categories rows" setting was on, so hiding the row with the
  skin switch still gave the category list. In the Estuary (Boxsets) copy the click now opens the titles
  whenever the row is hidden, by either switch. Music videos: titles when its row is hidden, the usual screen
  otherwise.
- A Home.xml patched by 0.15.x is recognised as out of date and upgraded in place (no duplicate lines); run
  the skin update once.
- Tests: 464 checks.

## 0.16.0 (alpha)
- **Full information page inside a boxset.** Shows and movies in a boxset (and in its watch order) used to
  carry only a few fields (plot, year, genres), so their information page looked thin. They now carry what
  Kodi has for the item: cast (with roles), ratings and votes, your rating, content certificate, studio,
  premiere date, runtime, original and sort title, IMDb/unique ids, date added, tags, and for movies tagline,
  plot outline, director, writer, country, trailer, set and top-250. The full record is asked for one item at
  a time for what is on screen (a cast list for the whole library would be far too heavy).
- Needs no skin update.
- Tests: 459 checks.

## 0.15.1 (alpha)
- **New setting: hide the Categories rows.** Settings > "Hide the Categories rows on the home screen" removes
  the row of category tiles shown on the home screen under **Movies, TV shows, Music videos, Music, Add-ons,
  TV and Radio** (all seven rows Estuary lets you switch off; the Videos and Pictures menus keep theirs, as
  they hold nothing else). Checked against a real Estuary Home.xml: 7 rows. Clicking those menu items still opens the titles straight
  away, whatever Estuary's own "categories widget" switch says (Estuary otherwise opens the category list
  once that row is hidden). Takes effect straight away; no restart.
- How: the Estuary (Boxsets) copy's Home.xml now checks a Home window property
  (`tvboxsets_hide_categories`, set by the add-on's service from the setting) on those rows and on the
  Movies / TV shows / Music videos menu clicks. The Genres and Studios rows are untouched. A copy built before this version counts as out
  of date: run the skin update once. Only the Estuary (Boxsets) copy is affected, never your normal Estuary.
- Diagnostics report shows whether the copy has it and the setting's value.
- Tests: 454 checks.

## 0.14.0 (alpha)
- **Crossover episodes in the watch order.** A watch-order entry can now be a single episode or a run of
  episodes of a season, not only a whole season or a movie. New right-click entry inside the watch order:
  **Add episodes (crossovers)...** - pick the show, the season and the episodes (consecutive ones become one
  entry). If the season is already in the order (as a whole season, or in parts), its entry is **split in
  place** around the new one: `Show A S3 up to E7`, `S3E8-E9` (the crossover), `S3E10+`, so no episode is
  listed twice. A crossover at the very start or end of a season leaves no empty part.
- A single episode plays directly; a run of several is a folder listing its episodes (each playable). Parts show
  their own progress. Play next unwatched episode, Move up/down, Place after and Remove all work on parts.
- Adding seasons or "Fill the watch order from this boxset" skip a season that already has any entry, so
  splitting never produces a duplicate whole season.
- Stored as optional `first` / `last` on the entry in `boxsets.json` (a missing `first` means "from the
  start", a missing `last` "to the end"). Whole-season entries from 0.13.0 are unchanged. No skin update.
- Tests: 441 checks.

## 0.13.0 (alpha)
- **Watch order (cross-show support).** Each boxset can have a watch order: whole seasons of its shows and its
  movies in a sequence you choose, so one show can come back later (Show A S1, Show B S1, a film, Show A S2).
  Right-click inside a boxset > **Watch order (seasons and movies)...** opens it. Inside it:
  **Add seasons and movies to the watch order...** (pick from a list), **Fill the watch order from this
  boxset** (everything, in the boxset's order), **Move up / Move down**, **Place after another item...**,
  **Remove from this boxset** (here it removes the entry from the watch order only) and **Play next unwatched
  episode** (plays the first unwatched episode of the first season in the order that has one, or the first
  unwatched movie). A season opens Kodi's own season screen; a movie plays and carries the MOVIE tag.
- The boxset's ordinary order and membership are never changed by the watch order. Seasons of a show that
  leaves the boxset drop out of the view (and come back if it returns). Seasons Kodi doesn't have show as
  "not in library". Stored as `watch` in `boxsets.json` (format 3, no migration); backups and merges carry it.
- Needs no skin update.
- Tests: 423 checks.

## 0.12.2 (alpha)
- **Fix: the movie marker now shows in InfoWall / Poster / Wall views.** Estuary draws no title under a poster
  in those views (only the picture), so a `[Movie]` text label could not appear there. Movies in a boxset are
  now marked with a blue **MOVIE** tag in the top-right corner of the poster, drawn by the skin copy (same
  mechanism as the boxset-name pills; badge include version 5). List views still show `[Movie]` after the
  title. Needs the skin update once (Boxsets menu > "Update 'Estuary (Boxsets)'...").
- The add-on marks movies for the skin with the list item property `boxset_movie`.
- Checked against a real copy of Estuary's view files: 14 placements, all files valid XML, safe to run twice.
- Tests: 385 checks.

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
