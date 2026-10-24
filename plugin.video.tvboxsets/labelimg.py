# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Draw the boxset name labels shown on posters, using only the Python standard library.

Kodi's built-in Python has no image library, so letters are pre-rendered (tools/make_font.py,
DejaVu Sans Bold) into resources/glyphs.json.z and assembled here: a rounded dark pill with the
boxset badge icon on the left and the name in white. The result is a PNG (bytes).
"""

import base64
import json
import math
import struct
import unicodedata
import zlib

HEIGHT = 40               # pixel height of the pill
PAD_LEFT, ICON_GAP, PAD_RIGHT = 4, 8, 16
BORDER = 2.0
FILL, FILL_ALPHA = (13, 27, 45), 235 / 255.0
EDGE = (18, 160, 199)
TEXT = (240, 244, 248)
ELLIPSIS = "\u2026"


class Atlas:
    def __init__(self, raw):
        self.size, self.ascent, self.descent = raw["size"], raw["ascent"], raw["descent"]
        self.glyphs = {}
        for cp, (advance, xoff, yoff, w, h, data) in raw["glyphs"].items():
            self.glyphs[int(cp)] = (advance, xoff, yoff, w, h, base64.b64decode(data) if data else b"")
        icon = raw["icon"]
        self.icon = (icon["w"], icon["h"], base64.b64decode(icon["data"]))


def load_atlas(path):
    with open(path, "rb") as f:
        return Atlas(json.loads(zlib.decompress(f.read()).decode("utf-8")))


def _glyph(atlas, ch):
    """The pre-rendered letter for `ch`, falling back to its plain-letter form, then '?'."""
    cp = ord(ch)
    if cp in atlas.glyphs:
        return atlas.glyphs[cp]
    plain = unicodedata.normalize("NFKD", ch)[:1]
    if plain and ord(plain) in atlas.glyphs and ord(plain) < 0x80:
        return atlas.glyphs[ord(plain)]
    return atlas.glyphs[ord("?")]


def text_width(atlas, text):
    return sum(_glyph(atlas, ch)[0] for ch in text)


def fit_text(atlas, text, max_width):
    """Shorten `text` with an ellipsis until it is no wider than `max_width` pixels."""
    if text_width(atlas, text) <= max_width:
        return text
    room = max_width - text_width(atlas, ELLIPSIS)
    out = ""
    for ch in text:
        if text_width(atlas, out + ch) > room:
            break
        out += ch
    return out.rstrip() + ELLIPSIS


def label_text(names, limit=None):
    """'Marvel' for one boxset; 'Marvel +2' when the item is in three."""
    names = sorted(set(names), key=str.lower)
    if not names:
        return ""
    return names[0] + (" +{}".format(len(names) - 1) if len(names) > 1 else "")


def _clamp(v):
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def _over(dst, off, rgb, alpha):
    """Blend a colour with `alpha` (0..1) over the RGBA pixel at dst[off:off+4]."""
    da = dst[off + 3] / 255.0
    out_a = alpha + da * (1 - alpha)
    if out_a <= 0:
        return
    for i in range(3):
        dst[off + i] = int(round((rgb[i] * alpha + dst[off + i] * da * (1 - alpha)) / out_a))
    dst[off + 3] = int(round(out_a * 255))


def _png(width, height, rgba):
    rows = b"".join(b"\x00" + bytes(rgba[y * width * 4:(y + 1) * width * 4]) for y in range(height))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def render_label(atlas, text, max_width=380):
    """PNG bytes of the pill for `text`. Returns (png_bytes, width, height)."""
    icon_w, icon_h, icon_px = atlas.icon
    left = PAD_LEFT + icon_w + ICON_GAP
    text = fit_text(atlas, text, max(max_width - left - PAD_RIGHT, 20))
    width = left + text_width(atlas, text) + PAD_RIGHT
    height = HEIGHT
    buf = bytearray(width * height * 4)

    # rounded pill with an accent border, anti-aliased with a distance function
    r, hw, hh = height / 2.0, width / 2.0, height / 2.0
    for y in range(height):
        for x in range(width):
            px, py = x + 0.5 - hw, y + 0.5 - hh
            qx, qy = abs(px) - (hw - r), abs(py) - (hh - r)
            sd = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r
            shape, inner = _clamp(0.5 - sd), _clamp(0.5 - (sd + BORDER))
            a_fill, a_edge = inner * FILL_ALPHA, shape - inner
            alpha = a_fill + a_edge
            if alpha <= 0:
                continue
            off = (y * width + x) * 4
            for i in range(3):
                buf[off + i] = int(round((FILL[i] * a_fill + EDGE[i] * a_edge) / alpha))
            buf[off + 3] = int(round(min(alpha, 1.0) * 255))

    # the badge icon
    iy = (height - icon_h) // 2
    for y in range(icon_h):
        for x in range(icon_w):
            o = (y * icon_w + x) * 4
            a = icon_px[o + 3] / 255.0
            if a > 0:
                _over(buf, ((iy + y) * width + PAD_LEFT + x) * 4, icon_px[o:o + 3], a)

    # the name
    baseline = (height - (atlas.ascent + atlas.descent)) // 2 + atlas.ascent
    pen = left
    for ch in text:
        advance, xoff, yoff, w, h, mask = _glyph(atlas, ch)
        for gy in range(h):
            y = baseline + yoff + gy
            if not 0 <= y < height:
                continue
            for gx in range(w):
                a = mask[gy * w + gx]
                x = pen + xoff + gx
                if a and 0 <= x < width:
                    _over(buf, (y * width + x) * 4, TEXT, a / 255.0)
        pen += advance
    return _png(width, height, buf), width, height
