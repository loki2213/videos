"""Estimate per-word timings from the narration audio and lay out captions.

Kokoro gives no timestamps, so words are distributed over the speech using
character weights, with phrase boundaries snapped to detected pauses."""
import re

import numpy as np

from pixel import text_size

OVERRIDE = re.compile(r"\{([^|}]+)\|[^}]+\}")


def display_text(s):
    return OVERRIDE.sub(r"\1", s)


def _weight(w):
    core = re.sub(r"[^\w']", "", w)
    n = len(core)
    if any(ch.isdigit() for ch in core):
        n = max(n * 2.4, 6)      # "22,000" is spoken as several words
    if core.upper() in ("BC",) or w.startswith("B.C"):
        n = 4
    return n + 1.2


def _pauses(x, sr, thresh=0.015, min_gap=0.08):
    win = int(sr * 0.01)
    n = len(x) // win
    loud = np.abs(x[:n * win]).reshape(n, win).max(1) > thresh
    idx = np.flatnonzero(loud)
    if len(idx) == 0:
        return 0.0, len(x) / sr, []
    first, last = idx[0], idx[-1]
    gaps, run = [], None
    for i in range(first, last + 1):
        if not loud[i]:
            run = i if run is None else run
        elif run is not None:
            if (i - run) * 0.01 >= min_gap:
                gaps.append((run * 0.01, i * 0.01))
            run = None
    return first * 0.01, (last + 1) * 0.01, gaps


def word_timings(text, samples, sr):
    words = display_text(text).split()
    s0, s1, gaps = _pauses(samples, sr)
    # phrases split after punctuation
    phrases, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[,.;:?!]$", w) and not re.match(r"^B\.C\.?$", w):
            phrases.append(cur)
            cur = []
    if cur:
        phrases.append(cur)
    wts = [sum(_weight(w) for w in p) for p in phrases]
    total = sum(wts)
    # expected boundary times, snapped to nearest pause
    bounds = []
    acc = 0.0
    used = set()
    last_t = s0
    for i, wt in enumerate(wts[:-1]):
        acc += wt
        e = s0 + (s1 - s0) * acc / total
        best = None
        for j, (g0, g1) in enumerate(gaps):
            if j in used or g0 < last_t:
                continue
            dd = abs((g0 + g1) / 2 - e)
            if dd < 0.9 and (best is None or dd < best[0]):
                best = (dd, j)
        if best:
            used.add(best[1])
            g0, g1 = gaps[best[1]]
            bounds.append((g0, g1))
            last_t = g1
        else:
            bounds.append((e, e))
            last_t = e
    out = []
    starts = [s0] + [b[1] for b in bounds]
    ends = [b[0] for b in bounds] + [s1]
    for p, a, b in zip(phrases, starts, ends):
        pw = [_weight(w) for w in p]
        tot = sum(pw)
        t = a
        for w, k in zip(p, pw):
            d = (b - a) * k / tot
            out.append((w, t, t + d))
            t += d
    return out


def pages(timed, max_w=246, max_lines=2):
    """Group timed words into caption pages of up to two lines.
    Returns list of dict(lines=[[(word, s, e), ...], ...], start, end)."""
    res = []
    lines, line = [], []

    def lw(ws):
        return text_size(" ".join(w for w, _, _ in ws), "cap", 20)[0]

    def flush():
        nonlocal lines, line
        if line:
            lines.append(line)
        if lines:
            res.append(dict(lines=lines))
        lines, line = [], []

    for i, item in enumerate(timed):
        if line and lw(line + [item]) > max_w:
            lines.append(line)
            line = []
            if len(lines) >= max_lines:
                res.append(dict(lines=lines))
                lines = []
        line.append(item)
        w = item[0]
        n_words = sum(len(x) for x in lines) + len(line)
        if re.search(r"[.?!:]$", w) and not re.match(r"^B\.C\.?$", w) \
                and n_words >= 3:
            flush()
    flush()
    for k, pg in enumerate(res):
        pg["start"] = pg["lines"][0][0][1]
        pg["end"] = pg["lines"][-1][-1][2]
    return res
