#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pre-render the letters used on boxset name labels:  python3 tools/make_font.py  (needs Pillow)

Kodi's built-in Python has no image library, so the add-on cannot render a font itself. This
tool rasterises each letter once (smooth, anti-aliased) into a compact table that the add-on's
plain-Python renderer (labelimg.py) assembles into label pictures.

Letters: ASCII, Latin-1 and Latin Extended-A (U+0020-U+017F) plus dashes, curly quotes, bullet and ellipsis. Anything else
is drawn as '?' (or as its plain-letter equivalent, e.g. e-acute -> e).

Font: DejaVu Sans Bold (Bitstream Vera licence: free to use, modify and redistribute with its
copyright notice; see docs/font-notice.txt). Output: plugin.video.tvboxsets/resources/glyphs.json.z
"""
import base64
import json
import os
import zlib

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SIZE = 26                       # pixel size of the pre-rendered letters
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugin.video.tvboxsets", "resources")
CODEPOINTS = (list(range(0x20, 0x7F)) + list(range(0xA0, 0x180))
              + [0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026])


def main():
    font = ImageFont.truetype(FONT, SIZE)
    ascent, descent = font.getmetrics()
    glyphs = {}
    for cp in CODEPOINTS:
        ch = chr(cp)
        advance = int(round(font.getlength(ch)))
        bbox = font.getbbox(ch, anchor="ls")  # relative to the baseline origin
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w <= 0 or h <= 0:  # space and friends
            glyphs[cp] = [advance, 0, 0, 0, 0, ""]
            continue
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).text((-bbox[0], -bbox[1]), ch, font=font, fill=255, anchor="ls")
        glyphs[cp] = [advance, bbox[0], bbox[1], w, h, base64.b64encode(mask.tobytes()).decode("ascii")]

    badge = Image.open(os.path.join(OUT, "badge.png")).convert("RGBA").resize((SIZE + 6, SIZE + 6), Image.LANCZOS)
    atlas = {"size": SIZE, "ascent": ascent, "descent": descent, "glyphs": glyphs,
             "icon": {"w": badge.width, "h": badge.height, "data": base64.b64encode(badge.tobytes()).decode("ascii")}}
    raw = json.dumps(atlas, separators=(",", ":")).encode("utf-8")
    with open(os.path.join(OUT, "glyphs.json.z"), "wb") as f:
        f.write(zlib.compress(raw, 9))
    print("wrote glyphs.json.z: {} letters, {} bytes".format(len(glyphs), os.path.getsize(os.path.join(OUT, "glyphs.json.z"))))


if __name__ == "__main__":
    main()
