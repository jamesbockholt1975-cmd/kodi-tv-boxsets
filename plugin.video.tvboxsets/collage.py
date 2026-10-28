# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Make a boxset poster out of the posters of the shows and movies inside it.

Needs Pillow (Kodi's `script.module.pil`, installed on request: it is an optional dependency). Without it
nothing else in the add-on is affected; the menu entry just explains what is missing.
"""

import io
from urllib.parse import unquote

SIZE = (600, 900)          # a normal 2:3 poster
GAP = 6
BACKGROUND = (13, 27, 45)
MAX_ITEMS = 6


class Unavailable(Exception):
    """Pillow is not installed."""


def source_path(url):
    """The real file or web address behind a Kodi art URL (they are often wrapped as image://...)."""
    if not url:
        return ""
    if url.startswith("image://"):
        inner = unquote(url[len("image://"):])
        if inner.endswith("/"):
            inner = inner[:-1]
        if "@" in inner.split("/")[0] and not inner.startswith(("http", "smb", "nfs", "special", "/")):
            return ""  # image://video@... : a frame grabbed from a file, not a picture we can read
        return inner
    return url


def layout(count, size=SIZE, gap=GAP):
    """Cells [(x, y, w, h)] for `count` posters: 1 whole, 2 side by side, 3 one tall + two, 4-5 2x2, 6 3x2."""
    w, h = size
    if count <= 1:
        return [(0, 0, w, h)]
    if count == 2:
        cw = (w - gap) // 2
        return [(0, 0, cw, h), (cw + gap, 0, w - cw - gap, h)]
    if count == 3:
        cw, ch = (w - gap) // 2, (h - gap) // 2
        return [(0, 0, cw, h), (cw + gap, 0, w - cw - gap, ch), (cw + gap, ch + gap, w - cw - gap, h - ch - gap)]
    if count < 6:
        count = 4
        cols, rows = 2, 2
    else:
        count, cols, rows = 6, 3, 2
    cw, ch = (w - gap * (cols - 1)) // cols, (h - gap * (rows - 1)) // rows
    return [(c * (cw + gap), r * (ch + gap), cw if c < cols - 1 else w - c * (cw + gap),
             ch if r < rows - 1 else h - r * (ch + gap)) for r in range(rows) for c in range(cols)][:count]


def build(images, size=SIZE):
    """PNG bytes: the `images` (raw file bytes of posters, best first) arranged on one poster."""
    try:
        from PIL import Image
    except ImportError:
        raise Unavailable()
    pics = []
    for raw in images[:MAX_ITEMS]:
        try:
            pics.append(Image.open(io.BytesIO(bytes(raw))).convert("RGB"))
        except Exception:  # noqa: BLE001 - a poster that can't be decoded is skipped
            continue
    if not pics:
        return None
    canvas = Image.new("RGB", size, BACKGROUND)
    for pic, (x, y, w, h) in zip(pics, layout(len(pics), size)):
        scale = max(w / pic.width, h / pic.height)  # fill the cell, cropping the overflow
        resized = pic.resize((max(1, round(pic.width * scale)), max(1, round(pic.height * scale))), Image.LANCZOS)
        left, top = (resized.width - w) // 2, (resized.height - h) // 2
        canvas.paste(resized.crop((left, top, left + w, top + h)), (x, y))
    out = io.BytesIO()
    canvas.save(out, "PNG", optimize=True)
    return out.getvalue()
