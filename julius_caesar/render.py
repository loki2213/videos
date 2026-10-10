"""Render the Julius Caesar TikTok video.

Usage:
  python render.py AUDIO_DIR OUT.mp4 [--workers N] [--still SCENE:T OUT.png]
                   [--preview-scale S]

AUDIO_DIR is the output of tts.py (per-scene WAVs + timing.json).
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image

import captions
import scenes
from pixel import (FPS, H, P, SCALE, W, clamp, ease, frame, line, mix, rect,
                   text, text_size, vgrad, BAYER4)
from script import SCENES

PRE = 0.25            # silence before each scene's narration
TAIL = 0.45           # default silence after
EXTRA_TAIL = {"hook": 0.25, "rubicon": 1.1, "pharsalus": 0.2, "ides": 0.9,
              "outro": 2.6, "alesia": 0.2, "egypt": 0.4}
TRANS = 0.3           # dither transition between scenes (inside panel)

PANEL_Y = 104
PANEL_H = 216
CAP_Y = 330

CHAPTERS = [
    ("hook", "PROLOGUE"), ("origins", "I. THE RISE"),
    ("triumvirate", "II. THE TRIUMVIRATE"), ("collapse", "III. THE RUBICON"),
    ("italy", "IV. CIVIL WAR"), ("epilogue", "V. THE END"),
]

YEAR_MIN, YEAR_MAX = -100, -44


class Timeline:
    def __init__(self, audio_dir):
        self.audio_dir = audio_dir
        with open(os.path.join(audio_dir, "timing.json")) as f:
            timing = json.load(f)
        self.items = []
        t = 0.0
        chapter = ""
        chap = dict(CHAPTERS)
        for sc in SCENES:
            sid = sc["id"]
            chapter = chap.get(sid, chapter)
            speech = timing[sid]
            dur = PRE + speech + TAIL + EXTRA_TAIL.get(sid, 0.0)
            x, sr = sf.read(os.path.join(audio_dir, sid + ".wav"))
            words = captions.word_timings(sc["text"], x, sr)
            words = [(w, a + PRE, b + PRE) for w, a, b in words]
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
        """Scene-local time when the n-th occurrence of `word` is spoken."""
        k = 0
        key = word.lower()
        for w, a, b in self.words:
            core = w.lower().strip(".,;:?!'\"")
            if core == key or core.startswith(key):
                k += 1
                if k == n:
                    return b if end else a
        raise KeyError(f"{word!r} not in scene {self.item['id']}")


# ---------------------------------------------------------------- chrome

_BG = None


def background(img, t):
    global _BG
    if _BG is None:
        _BG = Image.new("RGBA", (W, H))
        vgrad(_BG, 0, 0, W, H, [P["black"], P["night"], P["dslate"],
                                P["night"], P["black"]])
        # greek key bands
        for y0 in (PANEL_Y - 4, PANEL_Y + PANEL_H + 1):
            rect(_BG, 0, y0, W, 3, P["dgold"])
            for x in range(0, W, 6):
                _BG.putpixel((x, y0 + 1), P["gold"])
                _BG.putpixel((x + 1, y0 + 1), P["gold"])
                _BG.putpixel((x + 3, y0), P["yellow"])
    img.paste(_BG)
    # marching silhouettes at the bottom (decorative)
    from sprites import figure
    gy = 446
    rect(img, 0, gy, W, H - gy, P["black"])
    off = (t * 9) % 26
    for i in range(-1, 12):
        figure(img, int(i * 26 + off), gy, "legion", walk=t * 1.6 + i * 0.13,
               tint=P["dslate"])
    rect(img, 0, gy, W, 1, P["dslate"])


def hud(img, t, it, local, year_now):
    text(img, W // 2, 44, "JULIUS CAESAR", P["yellow"], "title", 8,
         anchor="c", shadow=P["wine"])
    text(img, W // 2, 54, "THE ROAD TO THE RUBICON", P["silver"], "label", 8,
         anchor="c", spacing=0)
    # chapter ribbon
    ch = it["chapter"]
    text(img, 8, 70, ch, P["gold"], "label", 8, spacing=0,
         shadow=P["black"])
    # year
    y = int(round(-year_now))
    ys = f"{y} BC"
    text(img, W - 8, 64, ys, P["white"], "title", 16, anchor="r",
         shadow=P["red"])
    # timeline bar
    x0, x1, by = 10, W - 10, 86
    rect(img, x0, by, x1 - x0, 3, P["dslate"])
    frac = (year_now - YEAR_MIN) / (YEAR_MAX - YEAR_MIN)
    mx = x0 + (x1 - x0) * clamp(frac)
    rect(img, x0, by, int(mx - x0), 3, P["red"])
    for yy in (-100, -90, -80, -70, -60, -50):
        tx = x0 + (x1 - x0) * (yy - YEAR_MIN) / (YEAR_MAX - YEAR_MIN)
        rect(img, int(tx), by + 4, 1, 2, P["slate"])
        text(img, int(tx), by + 7, str(-yy), P["slate"], "label", 8,
             anchor="c", spacing=0)
    for sc in SCENES:
        tx = x0 + (x1 - x0) * (sc["year"] - YEAR_MIN) / (YEAR_MAX - YEAR_MIN)
        c = P["yellow"] if sc["year"] <= year_now + 0.01 else P["slate"]
        img.putpixel((int(tx), by - 2), c)
    # marker
    rect(img, int(mx) - 1, by - 3, 3, 9, P["yellow"])
    rect(img, int(mx), by - 4, 1, 11, P["white"])


def draw_captions(img, it, local):
    pgs = it["pages"]
    cur = None
    for i, pg in enumerate(pgs):
        nxt = pgs[i + 1]["start"] if i + 1 < len(pgs) else \
            min(it["dur"], pg["end"] + 0.8)
        if pg["start"] - 0.05 <= local < nxt:
            cur = pg
    if cur is None:
        return
    lh = 20
    n = len(cur["lines"])
    y0 = CAP_Y + (2 - n) * lh // 2
    # backing plate
    rect(img, 4, CAP_Y - 4, W - 8, 2 * lh + 6, P["black"])
    frame(img, 4, CAP_Y - 4, W - 8, 2 * lh + 6, P["dslate"])
    for li, ln in enumerate(cur["lines"]):
        s = " ".join(w for w, _, _ in ln)
        lw, _ = text_size(s, "cap", 20)
        x = (W - lw) // 2
        y = y0 + li * lh
        for w, a, b in ln:
            if a <= local < b + 0.05:
                col = P["yellow"]
            elif local >= b:
                col = P["white"]
            else:
                col = P["silver"]
            ww = text(img, x, y, w, col, "cap", 20, outline=P["ink"])
            x += ww + text_size(" ", "cap", 20)[0] + 1


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

def render_panel(item, local):
    panel = Image.new("RGBA", (W, PANEL_H), P["ink"] + (255,))
    ctx = Ctx(item)
    fn = getattr(scenes, "scene_" + item["id"])
    fn(panel, local, ctx)
    return panel, ctx


def render_frame(tl, t):
    i, it = tl.at(t)
    local = t - it["start"]
    img = Image.new("RGBA", (W, H), P["black"] + (255,))
    background(img, t)
    panel, ctx = render_panel(it, local)
    # transition from previous scene
    if i > 0 and local < TRANS:
        prev = tl.items[i - 1]
        ppanel, _ = render_panel(prev, prev["dur"] + local)
        panel = dither_wipe(ppanel, panel, local / TRANS)
    img.alpha_composite(panel, (0, PANEL_Y))
    # year: scenes may animate ctx.year; ease between scenes
    year_now = ctx.year
    if i > 0 and local < 0.6:
        prev = tl.items[i - 1]
        pctx = Ctx(prev)
        try:
            render_year = getattr(scenes, "year_" + prev["id"])
            py = render_year(prev["dur"], pctx)
        except AttributeError:
            py = prev["year"]
        yfn = getattr(scenes, "year_" + it["id"], None)
        cy = yfn(local, ctx) if yfn else it["year"]
        year_now = py + (cy - py) * ease(local / 0.6)
    else:
        yfn = getattr(scenes, "year_" + it["id"], None)
        if yfn:
            year_now = yfn(local, ctx)
    hud(img, t, it, local, year_now)
    draw_captions(img, it, local)
    return img.convert("RGB")


def upscale(img, s=SCALE):
    a = np.asarray(img)
    return np.repeat(np.repeat(a, s, 0), s, 1)


# ---------------------------------------------------------------- workers

_TL = None


def _init(audio_dir):
    global _TL
    _TL = Timeline(audio_dir)


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


def build_audio(tl, path):
    import audio
    audio.build(tl, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio_dir")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--still", nargs="*", help="scene:t pairs -> PNG sheet")
    ap.add_argument("--scale", type=int, default=SCALE)
    ap.add_argument("--range", help="start:end seconds (preview)")
    args = ap.parse_args()
    tl = Timeline(args.audio_dir)
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
    with Pool(n, initializer=_init, initargs=(args.audio_dir,)) as pool:
        parts = pool.map(_render_chunk, chunks)
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    wav = os.path.join(tmp, "mix.wav")
    build_audio(tl, wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
           "-i", lst, "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", wav,
           "-map", "0:v", "-map", "1:a", "-c:v", "copy",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac",
           "-b:a", "192k", "-shortest", "-movflags", "+faststart", args.out]
    subprocess.run(cmd, check=True)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
