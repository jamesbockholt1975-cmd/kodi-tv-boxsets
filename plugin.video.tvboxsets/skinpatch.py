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
WIDGET_MARKER = "tvboxsets-widget v3"   # bump when the widget block changes


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
        '\t</control>',
        '\t<include content="WidgetScrollbar" condition="Skin.HasSetting(touchmode)">',
        '\t\t<param name="scrollbar_id" value="{sb}"/>',
        '\t</include>',
        '</control>',
    ]
    return nl.join(indent + ln.format(
        mid=MENU_ID, wid=WIDGET_ID, marker=WIDGET_MARKER, gl=int(MENU_ID) + 1,
        sb=int(MENU_ID) + 10, lid=int(MENU_ID) + 100, lid2=int(MENU_ID) + 101,
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
# Library badges: a small boxset icon on posters of items that are in a boxset
# --------------------------------------------------------------------------

BADGE_FILE = "Includes_TvBoxsets.xml"
BADGE_MARKER = "tvboxsets-badge v4"
BADGE_REV_PROPERTY = "tvboxsets_badge_rev"  # the add-on sets this to the current picture folder number
BADGE_DIR_SPECIAL = ("special://profile/addon_data/plugin.video.tvboxsets/badges/"
                     "r$INFO[Window(Home).Property(" + BADGE_REV_PROPERTY + ")]")

# Views whose poster artwork gets a badge (found in Estuary's own files).
BADGE_VIEW_FILES = ("View_50_List.xml", "View_51_Poster.xml", "View_53_Shift.xml",
                    "View_54_InfoWall.xml", "DialogVideoInfo.xml")
# Row layouts (small watched icon, then the title): the badge goes in the gap between them.
ROW_VIEW_FILES = ("View_55_WideList.xml", "View_504_MediaList.xml")
ROW_BADGE_SIZE = 28
_POSTER_TEXTURE = re.compile(r"Art\(poster\)|PosterThumbVar|ShiftThumbVar")
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
            text, count = _place_rows(text, nl)
        if text != original:  # rewriting an already-patched file gives the same text: nothing changes
            _write(path, text)
            placed += count
    return placed


_OUR_INCLUDE = re.compile(r'\r?\n[ \t]*<include content="TvBoxsets(?:Name|Row)?Badge">.*?</include>', re.S)


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
        if left is None or top is None or width is None:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        indent = re.match(r"[ \t]*", text[line_start:m.start()]).group(0)
        height = max(26, min(44, round(width * 0.11)))
        out.append(text[last:m.end()] + nl + _snippet(
            indent, nl, "TvBoxsetsNameBadge", left=left + 10, top=top + 10,
            width=max(60, width - 20), height=height))
        last = m.end()
        count += 1
    return ("".join(out) + text[last:]) if out else text, count


def _place_rows(text, nl):
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
