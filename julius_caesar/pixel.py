"""Low-level pixel-art helpers: palette, fonts, sprites, easing, shapes."""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# Base resolution; the final frame is scaled x4 to 1080x1920.
W, H, SCALE = 270, 480, 4
FPS = 30


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# Sweetie-16 plus a few Roman extras.
P = {k: hexc(v) for k, v in dict(
    ink="1a1c2c", plum="5d275d", red="b13e53", orange="ef7d57",
    yellow="ffcd75", lime="a7f070", green="38b764", teal="257179",
    navy="29366f", blue="3b5dc9", sky="41a6f6", cyan="73eff7",
    white="f4f4f4", silver="94b0c2", slate="566c86", dslate="333c57",
    gold="f4b41b", dgold="a86a1f", wine="7a1f2e", skin="f2c79b",
    tan="c98d5a", brown="8a4e2b", dbrown="4a2a1a", sand="e8c170",
    dsand="c48d4f", forest="1f4a3a", marble="e4dcc8", black="0e0f18",
    night="141627", purple="8e3a8e", pink="f59ab0", grass="5a8a3a",
    dgrass="3d6230", stone="8d8a80", dstone="5e5b55",
).items()}

FONT_DIR = os.path.join(HERE, "assets", "fonts")
_fonts = {}


def font(name, size):
    key = (name, size)
    if key not in _fonts:
        fn = {"title": "PressStart2P.woff", "cap": "VT323.woff",
              "label": "Silkscreen.woff"}[name]
        _fonts[key] = ImageFont.truetype(os.path.join(FONT_DIR, fn), size)
    return _fonts[key]


def draw(img):
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    return d


# ---------------------------------------------------------------- easing

def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = clamp(x)
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def prog(t, start, dur):
    """0..1 progress of an animation that starts at `start` and lasts `dur`."""
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


def lerp(a, b, x):
    return a + (b - a) * x


def mix(c1, c2, x):
    return tuple(int(round(lerp(a, b, clamp(x)))) for a, b in zip(c1, c2))


def blink(t, rate=2.0):
    return int(t * rate * 2) % 2 == 0


# ---------------------------------------------------------------- text

def text_size(s, kind="label", size=8, spacing=1):
    f = font(kind, size)
    w = sum(f.getlength(ch) + spacing for ch in s) - spacing
    asc, desc = f.getmetrics()
    return int(math.ceil(w)), asc


def text(img, x, y, s, color, kind="label", size=8, spacing=1, shadow=None,
         anchor="l", outline=None):
    """Draw pixel text with optional 1px drop shadow/outline.

    anchor: 'l' left, 'c' centered on x, 'r' right-aligned at x.
    Returns the drawn width.
    """
    f = font(kind, size)
    w, _ = text_size(s, kind, size, spacing)
    if anchor == "c":
        x = x - w // 2
    elif anchor == "r":
        x = x - w
    d = draw(img)
    # Silkscreen/Pixelify have a top bearing; normalise so y is the cap top.
    oy = -f.getbbox("H")[1]

    def run(cx, cy, col):
        for ch in s:
            d.text((cx, cy + oy), ch, font=f, fill=col)
            cx += f.getlength(ch) + spacing

    if outline:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1),
                       (-1, 1), (1, -1)):
            run(x + dx, y + dy, outline)
    if shadow:
        run(x + 1, y + 1, shadow)
    run(x, y, color)
    return w


# ---------------------------------------------------------------- sprites

class Sprite:
    """Sprite parsed from a list of strings; '.' is transparent."""

    def __init__(self, rows, pal):
        h = len(rows)
        w = max(len(r) for r in rows)
        arr = np.zeros((h, w, 4), np.uint8)
        for y, r in enumerate(rows):
            for x, ch in enumerate(r):
                if ch in (".", " "):
                    continue
                c = pal[ch]
                c = P[c] if isinstance(c, str) else c
                arr[y, x] = (*c, 255)
        self.arr = arr
        self.w, self.h = w, h
        self._img = Image.fromarray(arr, "RGBA")
        self._cache = {}

    def image(self, flip=False, scale=1, tint=None):
        key = (flip, scale, tint)
        if key not in self._cache:
            im = self._img
            if tint is not None:
                a = self.arr.copy()
                m = a[..., 3] > 0
                a[m, :3] = tint
                im = Image.fromarray(a, "RGBA")
            if flip:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            if scale != 1:
                im = im.resize((self.w * scale, self.h * scale), Image.NEAREST)
            self._cache[key] = im
        return self._cache[key]

    def blit(self, img, x, y, flip=False, scale=1, tint=None, anchor="tl"):
        im = self.image(flip, scale, tint)
        x, y = int(round(x)), int(round(y))
        if anchor == "bc":       # bottom-centre (feet)
            x -= im.width // 2
            y -= im.height
        elif anchor == "c":
            x -= im.width // 2
            y -= im.height // 2
        comp(img, im, (x, y))


def comp(img, im, xy):
    """alpha_composite that tolerates negative / out-of-bounds offsets."""
    x, y = int(xy[0]), int(xy[1])
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(img.width, x + im.width), min(img.height, y + im.height)
    if x1 <= x0 or y1 <= y0:
        return
    if (x0, y0, x1, y1) != (x, y, x + im.width, y + im.height):
        im = im.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    if img.mode == "RGBA":
        img.alpha_composite(im, (x0, y0))
    else:
        img.paste(im, (x0, y0), im)


def spr(art, pal):
    rows = [r for r in art.strip("\n").split("\n")]
    rows = [r.strip() for r in rows]
    return Sprite(rows, pal)


# ---------------------------------------------------------------- shapes

def rect(img, x, y, w, h, color):
    if w <= 0 or h <= 0:
        return
    draw(img).rectangle([int(x), int(y), int(x + w - 1), int(y + h - 1)],
                        fill=color)


def frame(img, x, y, w, h, color):
    if w < 1 or h < 1:
        return
    draw(img).rectangle([int(x), int(y), int(x + w - 1), int(y + h - 1)],
                        outline=color)


def line(img, x0, y0, x1, y1, color, width=1):
    draw(img).line([int(x0), int(y0), int(x1), int(y1)], fill=color,
                   width=width)


def dashed_path(img, pts, color, progress=1.0, dash=3, gap=2, offset=0.0):
    """Draw a dashed polyline revealed up to `progress` (0..1) of its length.
    Returns the (x, y) of the head."""
    seg = []
    total = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        seg.append((x0, y0, x1, y1, L))
        total += L
    lim = total * clamp(progress)
    d = draw(img)
    acc = 0.0
    head = pts[0]
    for x0, y0, x1, y1, L in seg:
        if L == 0:
            continue
        s = 0.0
        while s < L and acc + s < lim:
            ph = (acc + s + offset) % (dash + gap)
            if ph < dash:
                px = x0 + (x1 - x0) * s / L
                py = y0 + (y1 - y0) * s / L
                d.point((int(round(px)), int(round(py))), fill=color)
                head = (px, py)
            s += 0.5
        acc += L
    return head


def circle(img, cx, cy, r, color, outline=None):
    draw(img).ellipse([int(cx - r), int(cy - r), int(cx + r), int(cy + r)],
                      fill=color, outline=outline)


def poly(img, pts, color, outline=None):
    draw(img).polygon([(int(round(x)), int(round(y))) for x, y in pts],
                      fill=color, outline=outline)


BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9],
                   [15, 7, 13, 5]]) / 16.0


def dither_mask(w, h, level, ox=0, oy=0):
    """Boolean mask, True where a pixel is 'on' for an ordered-dither level."""
    yy, xx = np.mgrid[0:h, 0:w]
    return BAYER4[(yy + oy) % 4, (xx + ox) % 4] < level


def vgrad(img, x, y, w, h, stops, dither=True):
    """Vertical gradient through colour stops, with ordered dithering so it
    stays in a limited palette look."""
    arr = np.array(img)
    n = len(stops) - 1
    for j in range(h):
        f = j / max(1, h - 1) * n
        i = min(int(f), n - 1)
        frac = f - i
        if dither:
            row = np.where(BAYER4[j % 4, np.arange(w) % 4] < frac,
                           1, 0)
            c0 = np.array(stops[i])
            c1 = np.array(stops[i + 1])
            arr[y + j, x:x + w, :3] = np.where(row[:, None] == 1, c1, c0)
        else:
            arr[y + j, x:x + w, :3] = mix(stops[i], stops[i + 1], frac)
    img.paste(Image.fromarray(arr, img.mode))


def darken(img, amount, box=None):
    """Blend the image (or box) toward black."""
    arr = np.asarray(img).astype(np.float32)
    if box:
        x, y, w, h = box
        arr[y:y + h, x:x + w, :3] *= (1 - amount)
    else:
        arr[..., :3] *= (1 - amount)
    img.paste(Image.fromarray(arr.astype(np.uint8), img.mode))


def tint_overlay(img, color, amount):
    arr = np.asarray(img).astype(np.float32)
    arr[..., :3] = arr[..., :3] * (1 - amount) + np.array(color) * amount
    img.paste(Image.fromarray(arr.astype(np.uint8), img.mode))


def bar(img, x, y, w, h, frac, color, bg=None, border=None):
    if bg:
        rect(img, x, y, w, h, bg)
    rect(img, x, y, int(round(w * clamp(frac))), h, color)
    if border:
        frame(img, x - 1, y - 1, w + 2, h + 2, border)


def popup_scale(t, start, dur=0.35):
    """Return 0..~1.1 scale value for a pop-in animation."""
    return ease_back(prog(t, start, dur))


def badge(img, cx, cy, s, fg, bg, border, t=1.0, kind="label", size=8,
          pad=3):
    """Centered label box that pops in. t is 0..1 progress."""
    if t <= 0:
        return
    w, h = text_size(s, kind, size)
    if kind == "title":
        h = size
    elif kind == "label":
        h = 5 if size == 8 else 11
    bw, bh = w + pad * 2, h + pad * 2
    k = ease_back(t)
    sw, sh = max(1, int(bw * k)), max(1, int(bh * k))
    rect(img, cx - sw // 2, cy - sh // 2, sw, sh, bg)
    frame(img, cx - sw // 2, cy - sh // 2, sw, sh, border)
    if t > 0.6:
        text(img, cx, cy - h // 2, s, fg, kind, size, anchor="c")


def stamp(img, cx, cy, s, color, t, size=16, kind="title", angle_bg=None):
    """Rubber-stamp effect: slams down from big to normal size."""
    if t <= 0:
        return
    k = 1 + 1.5 * (1 - ease_out(min(1, t * 2)))
    w, _ = text_size(s, kind, size)
    h = size
    pad = 4
    layer = Image.new("RGBA", (w + pad * 2 + 2, h + pad * 2 + 2), (0, 0, 0, 0))
    frame(layer, 0, 0, layer.width, layer.height, color)
    frame(layer, 1, 1, layer.width - 2, layer.height - 2, color)
    text(layer, pad + 1, pad + 1, s, color, kind, size)
    if k != 1:
        layer = layer.resize((int(layer.width * k), int(layer.height * k)),
                             Image.NEAREST)
    comp(img, layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


def shake(t, start, dur=0.3, amp=2, seed=0):
    if not (start <= t < start + dur):
        return 0, 0
    k = 1 - (t - start) / dur
    i = int(t * 60) + seed
    return (int(amp * k * math.sin(i * 7.3)), int(amp * k * math.cos(i * 5.1)))
