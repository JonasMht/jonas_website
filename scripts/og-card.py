#!/usr/bin/env python3
"""Render the Open Graph social card (1200x630) from the site's design tokens.

    python3 scripts/og-card.py

Writes assets/img/og-cover.jpg. Every string is measured and shrunk to fit its
column before drawing, so text can never clip off the canvas (the previous card
was generated from a throwaway heredoc and shipped "STRASBO" cut in half).

The hero photo lives only inside the old card, so it is extracted from there.
Point SRC at a real photo to re-source it.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets/img/og-station.jpg"  # only surviving copy of the photo
OUT = ROOT / "assets/img/og-cover.jpg"

W, H = 1200, 630

# design tokens, lifted verbatim from assets/css/main.css
BG = (12, 15, 20)  # --bg
ACCENT = (111, 168, 220)  # --accent
TEXT = (229, 234, 241)  # --text
DIM = (140, 151, 167)  # --dim
FAINT = (119, 131, 154)  # --faint, the a11y-corrected value (5.02:1 on --bg)

SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# square crop of the source photo (430x430 at 90,100): offset drops the wall
# clock in the top-left corner and centres the operator under the scanner arch
CROP = (110, 130, 510, 530)
PHOTO = 420
MARGIN = 60
PBOX = (MARGIN, (H - PHOTO) // 2, MARGIN + PHOTO, (H - PHOTO) // 2 + PHOTO)
TX = PBOX[2] + 56
TW = W - MARGIN - TX


def measure(text, font, tracking=0.0):
    """Width of `text` including inter-character tracking, in pixels."""
    if not tracking:
        return font.getlength(text)
    return sum(font.getlength(c) for c in text) + tracking * (len(text) - 1)


def fit(text, path, tracking, avail, hi, lo):
    """Largest font size in [lo, hi] whose tracked width fits `avail`."""
    for size in range(hi, lo - 1, -1):
        font = ImageFont.truetype(path, size)
        if measure(text, font, tracking * size) <= avail:
            return font, size
    return ImageFont.truetype(path, lo), lo


def draw_tracked(draw, xy, text, font, fill, tracking=0.0):
    x, y = xy
    if not tracking:
        draw.text((x, y), text, font=font, fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + tracking


def rounded(img, radius):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.size[0] - 1, img.size[1] - 1), radius, fill=255)
    return mask


def reticle(draw, box, arm=26, gap=9, weight=2):
    """The site's lock-on corner brackets — drawn *outside* the frame, matching
    `.card::after { inset: -7px }` in main.css. Drawn inside they read as
    crop marks sitting on the photo."""
    x0, y0, x1, y1 = box
    x0 -= gap
    y0 -= gap
    x1 += gap
    y1 += gap
    for cx, cy, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        draw.rectangle((min(cx, cx + dx * arm), min(cy, cy + dy * weight),
                        max(cx, cx + dx * arm), max(cy, cy + dy * weight)), fill=ACCENT)
        draw.rectangle((min(cx, cx + dx * weight), min(cy, cy + dy * arm),
                        max(cx, cx + dx * weight), max(cy, cy + dy * arm)), fill=ACCENT)


def main():
    # --- ground + the same soft accent bloom the body carries --------------
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.sqrt((xx - W * 0.82) ** 2 + (yy + 0.10 * H) ** 2)
    a = (np.clip(1 - dist / 1000.0, 0, 1) ** 1.5 * 0.05)[..., None]
    arr = np.array(Image.new("RGB", (W, H), BG), np.float32)
    arr += (np.array(ACCENT, np.float32) - arr) * a
    card = Image.fromarray(arr.astype(np.uint8))

    # --- photo -------------------------------------------------------------
    photo = Image.open(SRC).convert("RGB").crop(CROP).resize((PHOTO, PHOTO), Image.LANCZOS)
    card.paste(photo, PBOX[:2], rounded(photo, 14))

    draw = ImageDraw.Draw(card)
    reticle(draw, PBOX)

    # --- type block --------------------------------------------------------
    name, name_sz = fit("J.MEHTALI", SANS, 0.0, TW, 78, 40)
    sub, sub_sz = fit("// ICUBE · STRASBOURG", MONO, 0.02, TW, 40, 22)
    l1, l1_sz = fit("THERMAL ABLATION PLANNING", MONO, 0.14, TW, 23, 13)
    l2, l2_sz = fit("UNIVERSITY OF STRASBOURG", MONO, 0.14, TW, 23, 13)

    # vertical rhythm: name / sub / rule / two labels, centred as one block
    h_name = name_sz + 12
    h_sub = sub_sz + 26
    h_rule = 2 + 46
    h_l1 = l1_sz + 12
    h_l2 = l2_sz
    y = (H - (h_name + h_sub + h_rule + h_l1 + h_l2)) // 2

    draw.text((TX, y), "J.MEHTALI", font=name, fill=TEXT)
    y += h_name
    draw_tracked(draw, (TX, y), "// ICUBE · STRASBOURG", sub, ACCENT, 0.02 * sub_sz)
    y += h_sub
    draw.rectangle((TX, y, TX + 132, y + 2), fill=ACCENT)
    y += h_rule
    draw_tracked(draw, (TX, y), "THERMAL ABLATION PLANNING", l1, DIM, 0.14 * l1_sz)
    y += h_l1
    draw_tracked(draw, (TX, y), "UNIVERSITY OF STRASBOURG", l2, FAINT, 0.14 * l2_sz)

    card.save(OUT, quality=92, optimize=True, progressive=True)

    # --- report: any line wider than its column is a bug -------------------
    print(f"wrote {OUT.relative_to(ROOT)}  {card.size[0]}x{card.size[1]}")
    print(f"column {TW}px")
    for label, text, font, track, sz in (
        ("name", "J.MEHTALI", name, 0.0, name_sz),
        ("sub", "// ICUBE · STRASBOURG", sub, 0.02, sub_sz),
        ("label", "THERMAL ABLATION PLANNING", l1, 0.14, l1_sz),
        ("label", "UNIVERSITY OF STRASBOURG", l2, 0.14, l2_sz),
    ):
        w = measure(text, font, track * sz)
        flag = "OK " if w <= TW else "OVERFLOW"
        print(f"  {flag} {label:<5} {sz:>2}px  {w:6.1f}px  {text}")


if __name__ == "__main__":
    main()
