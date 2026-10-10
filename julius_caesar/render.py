"""Render the Julius Caesar TikTok video (full-screen pixel art, on-screen
story text, music + SFX, no narration).

Usage:
  python render.py OUT.mp4 [--workers N] [--range START:END]
  python render.py SHEET.png --still SCENE:T [SCENE:T ...] [--scale S]
"""
import argparse
import math
import os
import subprocess
import tempfile
from multiprocessing import Pool

import numpy as np
from PIL import Image

import captions
import scenes
from pixel import (BAYER4, FPS, H, P, SCALE, W, clamp, ease, frame, rect,
                   text, text_size)
from script import SCENES

PRE = 0.7             # establishing time before a scene's first caption
TAIL = 1.1            # hold after the last caption
EXTRA_TAIL = {"hook": 0.6, "rubicon": 2.0, "pharsalus": 1.0, "alesia": 0.6,
              "egypt": 1.0, "ides": 1.5, "outro": 3.4, "gaul": 0.8,
              "triumvirate": 0.6, "epilogue": 0.6}
TRANS = 0.45          # dither transition between scenes

CAP_Y = 322           # top of the caption box (base pixels)
CAP_CX = 128          # caption centre, nudged left of TikTok's button rail

CHAPTERS = [
    ("hook", "PROLOGUE"), ("origins", "I. THE RISE"),
    ("triumvirate", "II. THE TRIUMVIRATE"), ("collapse", "III. THE RUBICON"),
    ("italy", "IV. CIVIL WAR"), ("epilogue", "V. THE END"),
]

YEAR_MIN, YEAR_MAX = -100, -44


class Timeline:
    def __init__(self):
        self.items = []
        t = 0.0
        chapter = ""
        chap = dict(CHAPTERS)
        for sc in SCENES:
            sid = sc["id"]
            chapter = chap.get(sid, chapter)
            words, end = captions.word_timings(sc["text"], PRE)
            dur = end + TAIL + EXTRA_TAIL.get(sid, 0.0)
            self.items.append(dict(id=sid, start=t, dur=dur, year=sc["year"],
                                   chapter=chapter, words=words,
                                   pages=captions.pages(words)))
            t += dur
        self.total = t

    def at(self, t):
        for i, it in enumerate(self.items):
            if t < it["start"] + it["dur"] or i == len(self.items) - 1:
                return i, it
        return len(self.items) - 1, self.items[-1]


class Ctx:
    """Per-scene context handed to scene draw functions."""

    def __init__(self, item):
        self.item = item
        self.dur = item["dur"]
        self.words = item["words"]
        self.year = item["year"]

    def at(self, word, n=1, end=False):
        """Scene-local time when the n-th occurrence of `word` is read."""
        k = 0
        key = word.lower()
        for w, a, b in self.words:
            c = captions.core(w)
            if c == key or c == key + "'s":
                k += 1
                if k == n:
                    return b if end else a
        raise KeyError(f"{word!r} not in scene {self.item['id']}")


# ---------------------------------------------------------------- overlays

def shade_band(img, y0, y1, level=0.6):
    """Darken a horizontal band with an ordered-dither pattern so text on
    top stays legible over any art."""
    a = np.array(img)
    h = y1 - y0
    yy, xx = np.mgrid[0:h, 0:W]
    # fade the shading in/out at the band edges
    edge = np.minimum(yy + 1, h - yy) / 6.0
    lv = np.clip(edge, 0, 1) * level
    m = BAYER4[yy % 4, xx % 4] < lv
    sub = a[y0:y1]
    sub[m, :3] = (sub[m, :3] * 0.25).astype(np.uint8)
    img.paste(Image.fromarray(a, img.mode))


def hud(img, it, year_now):
    shade_band(img, 34, 100, 0.85)
    text(img, W // 2, 40, "JULIUS CAESAR", P["yellow"], "title", 8,
         anchor="c", shadow=P["wine"])
    text(img, W // 2, 50, "THE ROAD TO THE RUBICON", P["silver"], "label", 8,
         anchor="c", spacing=0)
    text(img, 8, 68, it["chapter"], P["gold"], "label", 8, spacing=0,
         shadow=P["black"])
    ys = f"{int(round(-year_now))} BC"
    text(img, W - 8, 62, ys, P["white"], "title", 16, anchor="r",
         shadow=P["red"])
    x0, x1, by = 10, W - 10, 84
    rect(img, x0, by, x1 - x0, 3, P["dslate"])
    frac = (year_now - YEAR_MIN) / (YEAR_MAX - YEAR_MIN)
    mx = x0 + (x1 - x0) * clamp(frac)
    rect(img, x0, by, int(mx - x0), 3, P["red"])
    for yy in (-100, -90, -80, -70, -60, -50):
        tx = x0 + (x1 - x0) * (yy - YEAR_MIN) / (YEAR_MAX - YEAR_MIN)
        rect(img, int(tx), by + 4, 1, 2, P["slate"])
        text(img, int(tx), by + 7, str(-yy), P["silver"], "label", 8,
             anchor="c", spacing=0)
    for sc in SCENES:
        tx = x0 + (x1 - x0) * (sc["year"] - YEAR_MIN) / (YEAR_MAX - YEAR_MIN)
        c = P["yellow"] if sc["year"] <= year_now + 0.01 else P["slate"]
        img.putpixel((int(tx), by - 2), c)
    rect(img, int(mx) - 1, by - 3, 3, 9, P["yellow"])
    rect(img, int(mx), by - 4, 1, 11, P["white"])


def draw_captions(img, it, local):
    pgs = it["pages"]
    cur = None
    for i, pg in enumerate(pgs):
        nxt = pgs[i + 1]["start"] if i + 1 < len(pgs) else \
            min(it["dur"] - 0.3, pg["end"] + 1.2)
        if pg["start"] - 0.1 <= local < nxt:
            cur = pg
    if cur is None:
        return
    lh = 20
    n = len(cur["lines"])
    bh = n * lh + 8
    bw = max(text_size(" ".join(w for w, _, _ in ln), "cap",
                       captions.CAP_SIZE)[0] for ln in cur["lines"]) + 16
    k = ease(clamp((local - cur["start"] + 0.1) / 0.18))
    bw2 = max(4, int(bw * k))
    x0 = CAP_CX - bw2 // 2
    rect(img, x0, CAP_Y, bw2, bh, P["ink"])
    frame(img, x0, CAP_Y, bw2, bh, P["gold"])
    frame(img, x0 + 1, CAP_Y + 1, bw2 - 2, bh - 2, P["dgold"])
    if k < 1:
        return
    # quick typewriter reveal of the whole page
    shown = int((local - cur["start"] - 0.08) * 70)
    sp = text_size(" ", "cap", captions.CAP_SIZE)[0] + 1
    for li, ln in enumerate(cur["lines"]):
        s = " ".join(w for w, _, _ in ln)
        lw, _ = text_size(s, "cap", captions.CAP_SIZE)
        x = CAP_CX - lw // 2
        y = CAP_Y + 4 + li * lh
        for w, a, b in ln:
            if shown <= 0:
                return
            vis = w[:shown]
            col = P["yellow"] if captions.is_key(w) else P["white"]
            text(img, x, y, vis, col, "cap", captions.CAP_SIZE,
                 outline=P["black"])
            shown -= len(w) + 1
            x += text_size(w, "cap", captions.CAP_SIZE)[0] + sp


def dither_wipe(a, b, x):
    """Ordered-dither cross transition from image a to b (0..1)."""
    if x <= 0:
        return a
    if x >= 1:
        return b
    aa = np.asarray(a)
    bb = np.asarray(b)
    h, w = aa.shape[:2]
    big = np.kron(BAYER4, np.ones((2, 2)))
    yy, xx = np.mgrid[0:h, 0:w]
    m = big[yy % 8, xx % 8] < x
    out = np.where(m[..., None], bb, aa)
    return Image.fromarray(out.astype(np.uint8), a.mode)


# ---------------------------------------------------------------- frame

def render_scene(item, local):
    full = Image.new("RGBA", (W, H), P["ink"] + (255,))
    ctx = Ctx(item)
    layer = scenes.begin(full)
    getattr(scenes, "scene_" + item["id"])(layer, local, ctx)
    scenes.flush()
    return full, ctx


def year_of(item, local):
    fn = getattr(scenes, "year_" + item["id"], None)
    return fn(local, Ctx(item)) if fn else item["year"]


def render_frame(tl, t):
    i, it = tl.at(t)
    local = t - it["start"]
    img, ctx = render_scene(it, local)
    if i > 0 and local < TRANS:
        prev = tl.items[i - 1]
        pimg, _ = render_scene(prev, prev["dur"] + local)
        img = dither_wipe(pimg, img, local / TRANS)
    year_now = year_of(it, local)
    if i > 0 and local < 0.8:
        prev = tl.items[i - 1]
        py = year_of(prev, prev["dur"])
        year_now = py + (year_now - py) * ease(local / 0.8)
    hud(img, it, year_now)
    draw_captions(img, it, local)
    return img.convert("RGB")


def upscale(img, s=SCALE):
    a = np.asarray(img)
    return np.repeat(np.repeat(a, s, 0), s, 1)


# ---------------------------------------------------------------- workers

_TL = None


def _init():
    global _TL
    _TL = Timeline()


def _render_chunk(args):
    f0, f1, path, scale = args
    w, h = W * scale, H * scale
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-tune", "animation", "-pix_fmt", "yuv420p", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        try:
            im = render_frame(_TL, f / FPS)
        except Exception as e:
            raise RuntimeError(f"frame {f} (t={f / FPS:.2f}s): {e!r}") from e
        p.stdin.write(upscale(im, scale).tobytes())
    p.stdin.close()
    p.wait()
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--still", nargs="*", help="scene:t pairs -> PNG sheet")
    ap.add_argument("--scale", type=int, default=SCALE)
    ap.add_argument("--range", help="start:end seconds (preview)")
    args = ap.parse_args()
    tl = Timeline()
    print(f"total duration {tl.total:.2f}s")
    if args.still:
        ims = []
        for spec in args.still:
            sid, tt = spec.split(":")
            it = next(x for x in tl.items if x["id"] == sid)
            ims.append(render_frame(tl, it["start"] + float(tt)))
        sheet = Image.new("RGB", (W * len(ims) + 4 * (len(ims) - 1), H),
                          (255, 255, 255))
        for k, im in enumerate(ims):
            sheet.paste(im, (k * (W + 4), 0))
        sheet = sheet.resize((sheet.width * args.scale,
                              sheet.height * args.scale), Image.NEAREST)
        sheet.save(args.out)
        return
    t0, t1 = 0.0, tl.total
    if args.range:
        a, b = args.range.split(":")
        t0, t1 = float(a), float(b)
    nfr0, nfr1 = int(round(t0 * FPS)), int(math.ceil(t1 * FPS))
    tmp = tempfile.mkdtemp(prefix="jc_")
    n = args.workers
    step = math.ceil((nfr1 - nfr0) / n)
    chunks = [(nfr0 + k * step, min(nfr1, nfr0 + (k + 1) * step),
               os.path.join(tmp, f"part{k:02d}.mp4"), args.scale)
              for k in range(n) if nfr0 + k * step < nfr1]
    with Pool(n, initializer=_init) as pool:
        parts = pool.map(_render_chunk, chunks)
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    import audio
    wav = os.path.join(tmp, "mix.wav")
    audio.build(tl, wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
           "-i", lst, "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", wav,
           "-map", "0:v", "-map", "1:a", "-c:v", "copy",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
           "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", args.out]
    subprocess.run(cmd, check=True)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
