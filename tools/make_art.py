#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Draw the add-on icon and fanart:  python3 tools/make_art.py   (needs Pillow)

Writes plugin.video.tvboxsets/icon.png (512x512) and fanart.jpg (1920x1080).
The artwork is an original abstract stack of posters; it does not use Kodi's logo.
"""
import os

from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugin.video.tvboxsets")
BG_TOP, BG_BOTTOM = (13, 27, 45), (7, 14, 24)
POSTERS = [(30, 111, 146), (18, 160, 199), (240, 244, 248)]  # back -> front


def gradient(size):
    w, h = size
    img = Image.new("RGB", size)
    px = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        px.line([(0, y), (w, y)], fill=tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3)))
    return img


def poster_stack(size, alpha=255):
    """Three fanned poster rectangles on a transparent layer."""
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    pw, ph = int(w * 0.40), int(h * 0.62)
    cx, cy = w // 2, int(h * 0.52)
    for i, colour in enumerate(POSTERS):
        poster = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(poster)
        d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=int(pw * 0.07), fill=colour + (alpha,))
        if i == len(POSTERS) - 1:  # front poster: a simple play triangle
            tri = [(pw * 0.38, ph * 0.38), (pw * 0.38, ph * 0.62), (pw * 0.66, ph * 0.50)]
            d.polygon(tri, fill=(13, 27, 45, alpha))
        angle = (i - 1) * 9
        poster = poster.rotate(-angle, expand=True, resample=Image.BICUBIC)
        shadow = Image.new("RGBA", poster.size, (0, 0, 0, 0))
        shadow.paste((0, 0, 0, 110), mask=poster.split()[3])
        shadow = shadow.filter(ImageFilter.GaussianBlur(max(w // 60, 3)))
        dx = (i - 1) * int(w * 0.11)
        pos = (cx - poster.width // 2 + dx, cy - poster.height // 2 - (i == 2) * int(h * 0.02))
        layer.alpha_composite(shadow, (pos[0] + max(w // 100, 2), pos[1] + max(h // 100, 2)))
        layer.alpha_composite(poster, pos)
    return layer


def badge(size=128):
    """Small round badge with the poster-stack glyph, for items that are in a boxset."""
    scale = 4  # draw big, then shrink for smooth edges
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, big - 1, big - 1], fill=(13, 27, 45, 235))
    d.ellipse([big * 0.04, big * 0.04, big * 0.96, big * 0.96], outline=(18, 160, 199, 255), width=max(big // 28, 2))
    pw, ph = int(big * 0.26), int(big * 0.38)
    cx, cy = big // 2, big // 2
    for i, colour in enumerate(POSTERS):
        poster = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        ImageDraw.Draw(poster).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=int(pw * 0.14), fill=colour + (255,))
        poster = poster.rotate(-(i - 1) * 12, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(poster, (cx - poster.width // 2 + (i - 1) * int(big * 0.10),
                                     cy - poster.height // 2 + (i == 2) * 0))
    return img.resize((size, size), Image.LANCZOS)


def main():
    res = os.path.join(OUT, "resources")
    os.makedirs(res, exist_ok=True)
    badge().save(os.path.join(res, "badge.png"), optimize=True)
    Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(os.path.join(res, "badge_off.png"))
    icon = gradient((512, 512)).convert("RGBA")
    icon.alpha_composite(poster_stack((512, 512)))
    icon.convert("RGB").save(os.path.join(OUT, "icon.png"), optimize=True)

    fan = gradient((1920, 1080)).convert("RGBA")
    big = poster_stack((1080, 1080))
    # fade the whole stack at once so the posters hide each other instead of showing through
    big.putalpha(big.getchannel("A").point(lambda a: int(a * 0.30)))
    fan.alpha_composite(big, (1920 - 1080 - 60, 0))
    fan.convert("RGB").save(os.path.join(OUT, "fanart.jpg"), quality=88)
    print("wrote icon.png, fanart.jpg, resources/badge.png and resources/badge_off.png")


if __name__ == "__main__":
    main()
