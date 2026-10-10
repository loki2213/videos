"""Reading-paced word timings and caption page layout for the on-screen
story text (the video has no narration)."""
import re

from pixel import text_size

CPS = 18.0            # reading speed, characters per second
COMMA_PAUSE = 0.2
STOP_PAUSE = 0.5
MIN_WORD = 0.2
CAP_SIZE = 20
LINE_W = 214
MAX_LINES = 3

KEY_WORDS = {
    "caesar", "pompey", "crassus", "julia", "marius", "sulla", "venus",
    "bibulus", "vercingetorix", "antony", "cleopatra", "rome", "gaul",
    "rubicon", "italy", "greece", "spain", "egypt", "alesia", "carrhae",
    "dyrrhachium", "thessaly", "pharsalus", "zela", "thapsus", "munda",
    "rhine", "britain", "alps", "senate", "triumvirate", "pontifex",
    "maximus", "alea", "iacta", "est", "ides", "republic", "thirteenth",
}


def core(w):
    return w.lower().strip(".,;:?!'\"")


def is_key(w):
    c = core(w)
    if c.endswith("'s"):
        c = c[:-2]
    return c in KEY_WORDS or any(ch.isdigit() for ch in c)


def word_timings(text, start):
    """Assign each word a reading slot. Returns ([(word, a, b)], end)."""
    out = []
    t = start
    for w in text.split():
        if w == "||":           # dramatic pause marker, not displayed
            t += 1.6
            continue
        d = max(MIN_WORD, (len(w) + 1) / CPS)
        if any(ch.isdigit() for ch in w):
            d += 0.15
        out.append((w, t, t + d))
        t += d
        if re.search(r"[.?!:]$", w):
            t += STOP_PAUSE
        elif re.search(r"[,;]$", w):
            t += COMMA_PAUSE
    return out, t


def pages(timed, max_w=LINE_W, max_lines=MAX_LINES):
    """Group timed words into caption pages, breaking at sentence ends when
    possible. Returns list of dict(lines=[[(word, s, e), ...]], start)."""
    res = []
    lines, line = [], []

    def lw(ws):
        return text_size(" ".join(w for w, _, _ in ws), "cap", CAP_SIZE)[0]

    def flush():
        nonlocal lines, line
        if line:
            lines.append(line)
        if lines:
            res.append(dict(lines=lines))
        lines, line = [], []

    for item in timed:
        if line and lw(line + [item]) > max_w:
            lines.append(line)
            line = []
            if len(lines) >= max_lines:
                res.append(dict(lines=lines))
                lines = []
        line.append(item)
        n_words = sum(len(x) for x in lines) + len(line)
        if re.search(r"[.?!]$", item[0]) and n_words >= 4:
            flush()
    flush()
    for pg in res:
        pg["start"] = pg["lines"][0][0][1]
        pg["end"] = pg["lines"][-1][-1][2]
    return res
