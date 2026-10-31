# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Clone the installed Estuary skin and add a 'Boxsets' main menu item to it.

Pure Python (no Kodi imports) so it can be tested on its own.
"""

import os
import re
import shutil
from xml.sax.saxutils import escape

SKIN_ID = "skin.estuary.boxsets"
SKIN_NAME = "Estuary (Boxsets)"
PLUGIN_PATH = "plugin://plugin.video.tvboxsets/"
MENU_ID = "99000"  # any value Estuary doesn't already use for a menu section


def _read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def patch_addon_xml(path):
    """Give the copy its own add-on id and name so it sits beside Estuary."""
    text = _read(path)
    text, n_id = re.subn(r'(<addon\b[^>]*?\sid=")skin\.estuary(")',
                         r"\g<1>" + SKIN_ID + r"\g<2>", text, count=1)
    text, n_name = re.subn(r'(<addon\b[^>]*?\sname=")[^"]*(")',
                           r"\g<1>" + SKIN_NAME + r"\g<2>", text, count=1)
    if not n_id or not n_name:
        raise RuntimeError("Could not recognise Estuary's addon.xml")
    _write(path, text)


def patch_home_xml(path):
    """Insert a 'Boxsets' item straight after the TV Shows main menu item."""
    text = _read(path)

    # Locate the existing TV Shows item (by its menu id, falling back to its target).
    pos = text.find('<property name="menu_id">$NUMBER[6000]</property>')
    if pos == -1:
        pos = text.find("videodb://tvshows")
    if pos == -1:
        raise RuntimeError("Could not find the TV Shows item in Home.xml")

    start = max(text.rfind("<item>", 0, pos), text.rfind("<item ", 0, pos))
    end_tag = text.find("</item>", pos)
    if start == -1 or end_tag == -1:
        raise RuntimeError("Could not isolate the TV Shows item in Home.xml")
    end = end_tag + len("</item>")
    block = text[start:end]

    # Build the new item from a copy of the TV Shows one, so it inherits its icon.
    new = block
    new = re.sub(r"\s*<onclick[^>]*>.*?</onclick>", "", new, flags=re.S)
    new = re.sub(r"\s*<visible[^>]*>.*?</visible>", "", new, flags=re.S)
    new = re.sub(
        r"<label>.*?</label>",
        "<label>Boxsets</label>\n"
        "<onclick>ActivateWindow(Videos,{},return)</onclick>".format(PLUGIN_PATH),
        new, count=1, flags=re.S)
    new = re.sub(r'(<property name="menu_id">).*?(</property>)',
                 r"\g<1>$NUMBER[" + MENU_ID + r"]\g<2>", new, count=1, flags=re.S)
    new = re.sub(r'(<property name="id">).*?(</property>)',
                 r"\g<1>tvboxsets\g<2>", new, count=1, flags=re.S)

    if "tvboxsets" not in new and "Boxsets" not in new:
        raise RuntimeError("Home.xml item could not be rewritten")

    _write(path, text[:end] + "\n" + new + text[end:])


WIDGET_ID = "tvboxsets"          # matches the menu item's "id" property
# Skin rows fed by an add-on only reload when their address changes. The add-on bumps this
# Home window property whenever boxsets (or watched state) change, and the rows include it in
# their address, so Kodi reloads them straight away instead of at the next restart.
RELOAD_PROPERTY = "tvboxsets_reload"
_RELOAD = "&reload=$INFO[Window(Home).Property({})]".format(RELOAD_PROPERTY)
WIDGET_PATH = PLUGIN_PATH + "?action=widget" + _RELOAD
WIDGET_CONTINUE_PATH = PLUGIN_PATH + "?action=widget&filter=in_progress" + _RELOAD
WIDGET_NEXT_PATH = PLUGIN_PATH + "?action=widget&filter=next_up" + _RELOAD
WIDGET_MARKER = "tvboxsets-widget v4"   # bump when the widget block changes


def has_widget(path):
    """True if the current (v2) widget block is in Home.xml."""
    try:
        return WIDGET_MARKER in _read(path)
    except OSError:
        return False


def _group_span(text, group_id):
    """(start, end, indent) of `<control type="group" id="...">...</control>`, or None.

    Works because Estuary indents nested controls deeper than the group's own closing tag.
    """
    m = re.search(r'^([ \t]*)<control type="group" id="{}">'.format(group_id), text, re.M)
    if not m:
        return None
    indent = m.group(1)
    close = re.compile(r"^" + re.escape(indent) + r"</control>", re.M).search(text, m.end())
    if not close:
        return None
    return m.start(), close.end(), indent


def _widget_block(indent, nl):
    lines = [
        '<control type="group" id="{mid}">',
        '\t<!-- {marker} -->',
        '\t<visible>String.IsEqual(Container(9000).ListItem.Property(id),{wid})</visible>',
        '\t<include content="Visible_Right_Delayed">',
        '\t\t<param name="id" value="{wid}"/>',
        '\t</include>',
        '\t<control type="grouplist" id="{gl}">',
        '\t\t<include>WidgetGroupListCommon</include>',
        '\t\t<pagecontrol>{sb}</pagecontrol>',
        '\t\t<include content="WidgetListPoster">',
        '\t\t\t<param name="content_path" value="{path}"/>',
        '\t\t\t<param name="widget_header" value="Boxsets"/>',
        '\t\t\t<param name="widget_target" value="videos"/>',
        '\t\t\t<param name="list_id" value="{lid}"/>',
        '\t\t</include>',
        '\t\t<include content="WidgetListPoster">',
        '\t\t\t<param name="content_path" value="{cpath}"/>',
        '\t\t\t<param name="widget_header" value="Continue watching"/>',
        '\t\t\t<param name="widget_target" value="videos"/>',
        '\t\t\t<param name="list_id" value="{lid2}"/>',
        '\t\t</include>',
        '\t\t<include content="WidgetListPoster">',
        '\t\t\t<param name="content_path" value="{npath}"/>',
        '\t\t\t<param name="widget_header" value="Next up (watch order)"/>',
        '\t\t\t<param name="widget_target" value="videos"/>',
        '\t\t\t<param name="list_id" value="{lid3}"/>',
        '\t\t</include>',
        '\t</control>',
        '\t<include content="WidgetScrollbar" condition="Skin.HasSetting(touchmode)">',
        '\t\t<param name="scrollbar_id" value="{sb}"/>',
        '\t</include>',
        '</control>',
    ]
    return nl.join(indent + ln.format(
        mid=MENU_ID, wid=WIDGET_ID, marker=WIDGET_MARKER, gl=int(MENU_ID) + 1,
        sb=int(MENU_ID) + 10, lid=int(MENU_ID) + 100, lid2=int(MENU_ID) + 101, lid3=int(MENU_ID) + 102,
        npath=escape(WIDGET_NEXT_PATH, {'"': "&quot;"}),
        path=escape(WIDGET_PATH, {'"': "&quot;"}), cpath=escape(WIDGET_CONTINUE_PATH, {'"': "&quot;"}))
        for ln in lines)


def patch_widget(path):
    """Add (or upgrade) the widget rows shown when 'Boxsets' is highlighted.

    Estuary shows one widget group per main menu item: the group is visible when the
    highlighted item's "id" property matches, and the group's control id must equal
    the item's "menu_id" so pressing right moves focus into it.

    Returns True if Home.xml was changed. An older Boxsets widget block is replaced.
    """
    text = _read(path)
    if WIDGET_MARKER in text:
        return False  # already current
    nl = "\r\n" if "\r\n" in text else "\n"

    old = _group_span(text, MENU_ID)
    if old:  # upgrade an earlier version of our own block in place
        start, end, indent = old
        block = _widget_block(indent, nl)
        _write(path, text[:start] + block + text[end:])
        return True

    tv = _group_span(text, "6000")
    if not tv:
        raise RuntimeError("Could not find the TV Shows widget group in Home.xml")
    _, end, indent = tv
    _write(path, text[:end] + nl + _widget_block(indent, nl) + text[end:])
    return True


# --------------------------------------------------------------------------
# Hide the "Categories" rows on the home screen (a setting of this add-on)
# --------------------------------------------------------------------------

HIDE_CATEGORIES_PROPERTY = "tvboxsets_hide_categories"  # Home window property, set by the service
_HIDE_FLAG = "String.IsEqual(Window(Home).Property({}),true)".format(HIDE_CATEGORIES_PROPERTY)
_CATEGORY_KINDS = "movies|tvshows|musicvideos"   # these have a menu click that must keep opening the titles
# Every home-screen "Categories" row Estuary lets you switch off. (The rows for the Videos and Pictures
# menus are their only content, so they stay.)
_ROW_KINDS = "movies|tvshows|musicvideos|music|addons|tv|radio"
# The row of category tiles: <include content="WidgetListCategories" condition="... + !Skin.HasSetting(home_no_X_categories_widget)">
_CATEGORY_WIDGET = re.compile(
    r'(<include content="WidgetListCategories" condition="[^"]*!Skin\.HasSetting\(home_no_(?:' + _ROW_KINDS
    + r')_categories_widget\))(")')
CATEGORIES_MARKER = "tvboxsets-categories v2"   # bump when the Home.xml changes below change
# Estuary's menu click: with that row hidden (and "flatten" off) it opens the category list instead of the titles.
_CATEGORY_CLICK = re.compile(
    r'^([ \t]*<onclick condition="[^"]*Skin\.HasSetting\(home_no_(?:' + _CATEGORY_KINDS
    + r')_categories_widget\)[^"]*!System\.GetBool\(myvideos\.flatten\)">ActivateWindow\(Videos,videodb://[a-z]+/),return\)</onclick>',
    re.M)
# Music videos have a single unconditional click that opens the library's top level.
_MUSICVIDEO_CLICK = re.compile(
    r'^([ \t]*)<onclick>ActivateWindow\(Videos,musicvideos,return\)</onclick>[ \t]*(\r?\n)', re.M)
_MV_HIDDEN = "Skin.HasSetting(home_no_musicvideos_categories_widget) | " + _HIDE_FLAG

# Version 1 of this patch (0.15.x) paired each click with a flag test; undone before the current patch is applied.
_V1_PAIR = re.compile(
    r'^([ \t]*)<onclick condition="([^"]*) \+ !' + re.escape(_HIDE_FLAG) + r'">(ActivateWindow\(Videos,videodb://[a-z]+/,return\))</onclick>[ \t]*(\r?\n)'
    r'[ \t]*<onclick condition="[^"]*">ActivateWindow\(Videos,videodb://[a-z]+/titles/,return\)</onclick>[ \t]*\r?\n', re.M)
_V1_MUSICVIDEO = re.compile(
    r'^([ \t]*)<onclick condition="!' + re.escape(_HIDE_FLAG) + r'">ActivateWindow\(Videos,musicvideos,return\)</onclick>[ \t]*(\r?\n)'
    r'[ \t]*<onclick condition="' + re.escape(_HIDE_FLAG) + r'">ActivateWindow\(Videos,videodb://musicvideos/titles/,return\)</onclick>[ \t]*\r?\n', re.M)
_V2_MUSICVIDEO = re.compile(
    r'^([ \t]*)<onclick condition="!' + re.escape("Skin.HasSetting(home_no_musicvideos_categories_widget)") + r' \+ !' + re.escape(_HIDE_FLAG)
    + r'">ActivateWindow\(Videos,musicvideos,return\)</onclick>[ \t]*(\r?\n)'
    r'[ \t]*<onclick condition="' + re.escape(_MV_HIDDEN) + r'">ActivateWindow\(Videos,videodb://musicvideos/titles/,return\)</onclick>[ \t]*\r?\n', re.M)


def has_categories(path):
    """True if Home.xml honours the hide-categories setting and opens the titles (or has nothing to patch)."""
    try:
        text = _read(path)
    except OSError:
        return False
    if CATEGORIES_MARKER in text:
        return True
    return HIDE_CATEGORIES_PROPERTY not in text and not _CATEGORY_WIDGET.search(text)


def _unpatch_categories(text):
    """Back to Estuary's original lines (undo any earlier version of this patch)."""
    text = re.sub(r"[ \t]*<!-- tvboxsets-categories v\d+ -->[ \t]*\r?\n?", "", text)
    text = _V1_PAIR.sub(lambda m: '{}<onclick condition="{}">{}</onclick>{}'.format(m.group(1), m.group(2), m.group(3), m.group(4)), text)
    text = _V1_MUSICVIDEO.sub(lambda m: "{}<onclick>ActivateWindow(Videos,musicvideos,return)</onclick>{}".format(m.group(1), m.group(2)), text)
    text = _V2_MUSICVIDEO.sub(lambda m: "{}<onclick>ActivateWindow(Videos,musicvideos,return)</onclick>{}".format(m.group(1), m.group(2)), text)
    return text.replace(" + !" + _HIDE_FLAG, "")  # the Categories rows


def patch_categories(path):
    """Let the add-on's setting hide the Categories rows, and make clicking Movies / TV shows /
    Music videos open the titles whenever their row is hidden (by this setting or by Estuary's own
    switch). Returns True if Home.xml was changed."""
    original = _read(path)
    if CATEGORIES_MARKER in original:
        return False
    text = _unpatch_categories(original) if HIDE_CATEGORIES_PROPERTY in original else original
    nl = "\r\n" if "\r\n" in text else "\n"
    first = []

    def row(m):
        extra = " + !" + _HIDE_FLAG
        if not first:  # the version marker, as an XML comment just before the first row
            first.append(1)
            line_start = m.string.rfind("\n", 0, m.start()) + 1
            indent = re.match(r"[ \t]*", m.string[line_start:m.start()]).group(0)
            return "<!-- {} -->{}{}{}{}".format(CATEGORIES_MARKER, nl, indent, m.group(1), extra + m.group(2))
        return m.group(1) + extra + m.group(2)
    changed = _CATEGORY_WIDGET.sub(row, text)
    changed = _CATEGORY_CLICK.sub(lambda m: m.group(1) + "titles/,return)</onclick>", changed)
    changed = _MUSICVIDEO_CLICK.sub(lambda m: (
        '{i}<onclick condition="!Skin.HasSetting(home_no_musicvideos_categories_widget) + !{f}">'
        "ActivateWindow(Videos,musicvideos,return)</onclick>{nl}"
        '{i}<onclick condition="{h}">ActivateWindow(Videos,videodb://musicvideos/titles/,return)</onclick>{nl}'
    ).format(i=m.group(1), f=_HIDE_FLAG, h=_MV_HIDDEN, nl=m.group(2)), changed)
    if changed == original:
        return False
    _write(path, changed)
    return True


# --------------------------------------------------------------------------
# Library badges: a small boxset icon on posters of items that are in a boxset
# --------------------------------------------------------------------------

BADGE_FILE = "Includes_TvBoxsets.xml"
# Bump this whenever the include or where it is placed changes: it is how the Boxsets menu knows a skin copy
# needs "Update ... add the home widget and library badges".
BADGE_MARKER = "tvboxsets-badge v8"
BADGE_REV_PROPERTY = "tvboxsets_badge_rev"  # the add-on sets this to the current picture folder number
BADGE_DIR_SPECIAL = ("special://profile/addon_data/plugin.video.tvboxsets/badges/"
                     "r$INFO[Window(Home).Property(" + BADGE_REV_PROPERTY + ")]")

# Views whose poster artwork gets a badge (found in Estuary's own files).
BADGE_VIEW_FILES = ("View_50_List.xml", "View_51_Poster.xml", "View_53_Shift.xml",
                    "View_54_InfoWall.xml", "View_501_Banner.xml", "View_502_FanArt.xml", "DialogVideoInfo.xml")
# Row layouts (small watched icon, then the title): the badge goes in the gap between them.
ROW_VIEW_FILES = ("View_55_WideList.xml", "View_504_MediaList.xml")
ROW_BADGE_SIZE = 28
ROW_NAME_FILES = ("View_55_WideList.xml",)   # rows wide enough for the boxset-name label as well
ROW_NAME_WIDTH, ROW_NAME_HEIGHT, ROW_NAME_RESERVE = 360, 28, 230   # label size; room kept for the right-hand text
ROW_HEIGHT = 75                                                      # Estuary's list_item_height (1080p)
SCREEN_WIDTH = 1920
_POSTER_TEXTURE = re.compile(r"Art\(poster\)|PosterThumbVar|ShiftThumbVar|InfoWallThumbVar|BannerArtVar|FanartImageVar")
_IMAGE_CONTROL = re.compile(r'<control type="image"[^>]*>(.*?)</control>', re.S)

BADGE_INCLUDE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<includes>
\t<!-- {marker} -->
\t<include name="TvBoxsetsBadge">
\t\t<param name="left">10</param>
\t\t<param name="top">10</param>
\t\t<param name="size">48</param>
\t\t<definition>
\t\t\t<control type="image">
\t\t\t\t<left>$PARAM[left]</left>
\t\t\t\t<top>$PARAM[top]</top>
\t\t\t\t<width>$PARAM[size]</width>
\t\t\t\t<height>$PARAM[size]</height>
\t\t\t\t<aspectratio>keep</aspectratio>
\t\t\t\t<texture background="true">{dir}/$INFO[ListItem.DBType]_$INFO[ListItem.DBID].png</texture>
\t\t\t\t<visible>[String.IsEqual(ListItem.DBType,tvshow) | String.IsEqual(ListItem.DBType,movie)] + !String.IsEmpty(ListItem.DBID)</visible>
\t\t\t</control>
\t\t</definition>
\t</include>
\t<include name="TvBoxsetsRowBadge">
\t\t<param name="left">70</param>
\t\t<param name="size">28</param>
\t\t<definition>
\t\t\t<control type="image">
\t\t\t\t<left>$PARAM[left]</left>
\t\t\t\t<centertop>50%</centertop>
\t\t\t\t<width>$PARAM[size]</width>
\t\t\t\t<height>$PARAM[size]</height>
\t\t\t\t<aspectratio>keep</aspectratio>
\t\t\t\t<texture background="true">{dir}/$INFO[ListItem.DBType]_$INFO[ListItem.DBID].png</texture>
\t\t\t\t<visible>[String.IsEqual(ListItem.DBType,tvshow) | String.IsEqual(ListItem.DBType,movie)] + !String.IsEmpty(ListItem.DBID)</visible>
\t\t\t</control>
\t\t</definition>
\t</include>
\t<include name="TvBoxsetsMovieTag">
\t\t<param name="left">10</param>
\t\t<param name="top">10</param>
\t\t<definition>
\t\t\t<control type="group">
\t\t\t\t<left>$PARAM[left]</left>
\t\t\t\t<top>$PARAM[top]</top>
\t\t\t\t<visible>String.IsEqual(ListItem.Property(boxset_movie),true)</visible>
\t\t\t\t<control type="image">
\t\t\t\t\t<width>84</width>
\t\t\t\t\t<height>28</height>
\t\t\t\t\t<texture colordiffuse="E61E88E5">colors/white.png</texture>
\t\t\t\t</control>
\t\t\t\t<control type="label">
\t\t\t\t\t<width>84</width>
\t\t\t\t\t<height>28</height>
\t\t\t\t\t<align>center</align>
\t\t\t\t\t<aligny>center</aligny>
\t\t\t\t\t<font>font12</font>
\t\t\t\t\t<textcolor>FFFFFFFF</textcolor>
\t\t\t\t\t<label>MOVIE</label>
\t\t\t\t</control>
\t\t\t</control>
\t\t</definition>
\t</include>
\t<include name="TvBoxsetsTileName">
\t\t<param name="left">10</param>
\t\t<param name="top">10</param>
\t\t<param name="width">200</param>
\t\t<param name="height">32</param>
\t\t<definition>
\t\t\t<control type="group">
\t\t\t\t<left>$PARAM[left]</left>
\t\t\t\t<top>$PARAM[top]</top>
\t\t\t\t<visible>!String.IsEmpty(ListItem.Property(boxset_tile))</visible>
\t\t\t\t<control type="image">
\t\t\t\t\t<width>$PARAM[width]</width>
\t\t\t\t\t<height>$PARAM[height]</height>
\t\t\t\t\t<texture colordiffuse="EB0D1B2D" border="6">colors/white.png</texture>
\t\t\t\t</control>
\t\t\t\t<control type="label">
\t\t\t\t\t<left>10</left>
\t\t\t\t\t<right>10</right>
\t\t\t\t\t<height>$PARAM[height]</height>
\t\t\t\t\t<aligny>center</aligny>
\t\t\t\t\t<font>font12</font>
\t\t\t\t\t<textcolor>FFF0F4F8</textcolor>
\t\t\t\t\t<label>$INFO[ListItem.Property(boxset_tile)]</label>
\t\t\t\t</control>
\t\t\t</control>
\t\t</definition>
\t</include>
\t<include name="TvBoxsetsNameBadge">
\t\t<param name="left">10</param>
\t\t<param name="top">10</param>
\t\t<param name="width">200</param>
\t\t<param name="height">32</param>
\t\t<definition>
\t\t\t<control type="image">
\t\t\t\t<left>$PARAM[left]</left>
\t\t\t\t<top>$PARAM[top]</top>
\t\t\t\t<width>$PARAM[width]</width>
\t\t\t\t<height>$PARAM[height]</height>
\t\t\t\t<aspectratio align="left">keep</aspectratio>
\t\t\t\t<texture background="true">{dir}/$INFO[ListItem.DBType]_$INFO[ListItem.DBID]_name.png</texture>
\t\t\t\t<visible>[String.IsEqual(ListItem.DBType,tvshow) | String.IsEqual(ListItem.DBType,movie)] + !String.IsEmpty(ListItem.DBID)</visible>
\t\t\t</control>
\t\t</definition>
\t</include>
</includes>
""".format(marker=BADGE_MARKER, dir=BADGE_DIR_SPECIAL)


def has_badges(xml_dir):
    """True if the badge include is installed and at least one view uses it."""
    try:
        if BADGE_MARKER not in _read(os.path.join(xml_dir, BADGE_FILE)):
            return False
        return any('content="TvBoxsets' in _read(os.path.join(xml_dir, f))
                   for f in BADGE_VIEW_FILES + ROW_VIEW_FILES if os.path.exists(os.path.join(xml_dir, f)))
    except OSError:
        return False


def _number(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _tag(block, name):
    m = re.search(r"<{0}>([^<]*)</{0}>".format(name), block)
    return m.group(1) if m else None


def patch_badges(xml_dir):
    """Add the badge include and place it over every poster image in the library views.

    Returns the number of badges placed (0 if already up to date). Skins differ, so any view
    file that is missing or has no recognisable poster image is simply skipped.
    """
    include_path = os.path.join(xml_dir, BADGE_FILE)
    _write(include_path, BADGE_INCLUDE_XML)

    includes_path = os.path.join(xml_dir, "Includes.xml")
    text = _read(includes_path)
    if BADGE_FILE not in text:
        m = re.search(r'^([ \t]*)<include file="Defaults.xml"\s*/>[ \t]*(\r?\n)', text, re.M)
        if not m:
            raise RuntimeError("Could not find where Includes.xml lists its include files")
        text = text[:m.end()] + '{}<include file="{}" />{}'.format(m.group(1), BADGE_FILE, m.group(2)) + text[m.end():]
        _write(includes_path, text)

    placed = 0
    for name in BADGE_VIEW_FILES + ROW_VIEW_FILES:
        path = os.path.join(xml_dir, name)
        if not os.path.exists(path):
            continue
        original = _read(path)
        text = _strip_placements(original)
        nl = "\r\n" if "\r\n" in text else "\n"
        if name in BADGE_VIEW_FILES:
            text, count = _place_posters(text, nl)
        else:
            text, count = _place_rows(text, nl, names=name in ROW_NAME_FILES)
        if text != original:  # rewriting an already-patched file gives the same text: nothing changes
            _write(path, text)
            placed += count
    return placed


_OUR_INCLUDE = re.compile(r'\r?\n[ \t]*<include content="TvBoxsets(?:(?:Name|Row)?Badge|MovieTag|TileName)">.*?</include>', re.S)


def _strip_placements(text):
    """Remove every badge placement we made earlier, so a patch can be redone from scratch."""
    return _OUR_INCLUDE.sub("", text)


def _snippet(indent, nl, include, **params):
    lines = [indent + '<include content="{}">'.format(include)]
    lines += [indent + '\t<param name="{}" value="{}" />'.format(k, v) for k, v in params.items()]
    lines.append(indent + "</include>")
    return nl.join(lines)


def _place_posters(text, nl):
    """A name pill in the top-left corner of every poster image (numeric position only)."""
    out, last, count = [], 0, 0
    for m in _IMAGE_CONTROL.finditer(text):
        tex = re.search(r"<texture[^>]*>([^<]*)</texture>", m.group(1))
        if not tex or not _POSTER_TEXTURE.search(tex.group(1)):
            continue
        left, top, width = (_number(_tag(m.group(1), t)) for t in ("left", "top", "width"))
        right = _number(_tag(m.group(1), "right"))
        if width is None and left is not None and right is not None:
            # Anchored on both sides (Fanart view): the width is the enclosing group's width minus both gaps
            outer = re.findall(r"<width>(\d+)</width>", text[max(0, m.start() - 1500):m.start()])
            if outer and int(outer[-1]) - left - right > 100:
                width = int(outer[-1]) - left - right
        if left is None or top is None or width is None:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        indent = re.match(r"[ \t]*", text[line_start:m.start()]).group(0)
        height = max(26, min(44, round(width * 0.11)))
        out.append(text[last:m.end()] + nl + _snippet(
            indent, nl, "TvBoxsetsNameBadge", left=left + 10, top=top + 10,
            width=max(60, width - 20), height=height))
        # the boxset's own name on its tile (the plugin sets boxset_tile on the boxset list and the Next up row)
        out[-1] += nl + _snippet(indent, nl, "TvBoxsetsTileName", left=left + 10, top=top + 10,
                                 width=max(60, width - 20), height=height)
        # a MOVIE tag in the top-right corner (the plugin sets the property only on movies in a boxset)
        out[-1] += nl + _snippet(indent, nl, "TvBoxsetsMovieTag", left=max(left, left + width - 94), top=top + 10)
        last = m.end()
        count += 1
    return ("".join(out) + text[last:]) if out else text, count


def _place_rows(text, nl, names=False):
    """A small round badge to the right of the watched icon, if there is room before the title."""
    out, last, count = [], 0, 0
    for m in _IMAGE_CONTROL.finditer(text):
        body = m.group(1)
        tex = re.search(r"<texture[^>]*>([^<]*)</texture>", body)
        if not tex or "ListWatchedIconVar" not in tex.group(1):
            continue
        left, width, top = (_number(_tag(body, t)) for t in ("left", "width", "top"))
        centered = (_tag(body, "centertop") or "").strip() == "50%"
        if left is None or width is None or (top is None and not centered):
            continue
        label = re.search(r'<control type="label"[^>]*>(.*?)</control>', text[m.end():m.end() + 900], re.S)
        label_left = _number(_tag(label.group(1), "left")) if label else None
        start = left + width + 3
        if label_left is None or label_left - start < ROW_BADGE_SIZE + 4:
            continue  # no room: this row would put the badge on top of the title
        line_start = text.rfind("\n", 0, m.start()) + 1
        indent = re.match(r"[ \t]*", text[line_start:m.start()]).group(0)
        if centered:
            snippet = _snippet(indent, nl, "TvBoxsetsRowBadge", left=start, size=ROW_BADGE_SIZE)
        else:
            snippet = _snippet(indent, nl, "TvBoxsetsBadge", left=start, top=top + 2, size=ROW_BADGE_SIZE)
        if names:
            # the boxset names, right-aligned to the left of the right-hand text (year, rating...)
            box = re.search(r'<control type="fixedlist"[^>]*>(.*?)</control>|<control type="list"[^>]*>(.*?)<', text, re.S)
            lst_left = _number(_tag(text[box.start():box.start() + 600], "left")) if box else None
            lst_right = _number(_tag(text[box.start():box.start() + 600], "right")) if box else None
            if lst_left is not None and lst_right is not None:
                row_width = SCREEN_WIDTH - lst_left - lst_right
                pill_left = row_width - ROW_NAME_RESERVE - ROW_NAME_WIDTH
                if pill_left > (label_left or 0) + 200:
                    snippet += nl + _snippet(indent, nl, "TvBoxsetsNameBadge", left=pill_left,
                                             top=(ROW_HEIGHT - ROW_NAME_HEIGHT) // 2,
                                             width=ROW_NAME_WIDTH, height=ROW_NAME_HEIGHT)
        out.append(text[last:m.end()] + nl + snippet)
        last = m.end()
        count += 1
    return ("".join(out) + text[last:]) if out else text, count


def build_skin(src, dst):
    """Copy skin folder `src` to `dst` and patch it. Cleans up on failure."""
    try:
        shutil.copytree(src, dst)
        patch_addon_xml(os.path.join(dst, "addon.xml"))
        patch_home_xml(os.path.join(dst, "xml", "Home.xml"))
        patch_widget(os.path.join(dst, "xml", "Home.xml"))
        patch_categories(os.path.join(dst, "xml", "Home.xml"))
        patch_badges(os.path.join(dst, "xml"))
    except Exception:
        shutil.rmtree(dst, ignore_errors=True)
        raise


def addon_version(path):
    try:
        text = _read(path)
    except OSError:
        return None
    m = re.search(r'<addon\b[^>]*?\sversion="([^"]*)"', text)
    return m.group(1) if m else None


def version_key(version):
    return [int(x) for x in re.findall(r"\d+", version or "")]


def seed_settings(src_file, dst_dir):
    """Give the copy the same skin settings Estuary has, unless it already has its own."""
    dst_file = os.path.join(dst_dir, "settings.xml")
    if os.path.isfile(src_file) and not os.path.exists(dst_file):
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        return True
    return False


def rebuild_skin(src, dst, tmp_root):
    """Rebuild the copy from the current Estuary, swapping it in only if the build works."""
    tmp = os.path.join(tmp_root, "tvboxsets_skin_build")
    old = os.path.join(tmp_root, "tvboxsets_skin_old")
    for path in (tmp, old):
        shutil.rmtree(path, ignore_errors=True)
    os.makedirs(tmp_root, exist_ok=True)
    build_skin(src, tmp)  # cleans up after itself if it fails; the old copy is untouched
    try:
        if os.path.isdir(dst):
            shutil.move(dst, old)
        shutil.move(tmp, dst)
    except Exception:
        if os.path.isdir(old) and not os.path.isdir(dst):
            shutil.move(old, dst)
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    shutil.rmtree(old, ignore_errors=True)
