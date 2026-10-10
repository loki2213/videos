"""Procedural chiptune score + synthesized SFX + narration mix."""
import os

import numpy as np
import soundfile as sf

SR = 24000
BPM = 100
BEAT = 60 / BPM

# Per-scene music intensity: 0 sombre pad, 1 light, 2 driving, 3 battle.
INTENSITY = {
    "hook": 2, "origins": 1, "sulla": 1, "pirates": 1, "ladder": 1,
    "triumvirate": 2, "deal": 1, "consul": 1, "gaul": 2, "alesia": 3,
    "legions": 2, "collapse": 1, "ultimatum": 2, "rubicon": 3, "italy": 2,
    "spain": 2, "dyrrhachium": 2, "pharsalus": 3, "egypt": 0, "epilogue": 2,
    "ides": 0, "outro": 2,
}

# (scene, cue word or seconds, sound)
SFX = [
    ("hook", "Cross", "boom"), ("hook", "How", "chime"),
    ("origins", "Venus", "chime"), ("sulla", "refused", "blip"),
    ("sulla", "pardon", "stamp"), ("pirates", "50", "coins"),
    ("pirates", "crucified", "boom"), ("ladder", "Pontifex", "chime"),
    ("triumvirate", "Pompey", "blip"), ("triumvirate", "Crassus", "blip"),
    ("triumvirate", "First", "boom"), ("deal", "married", "chime"),
    ("consul", "laws", "stamp"), ("consul", "Julius", "blip"),
    ("gaul", "Rhine", "blip"), ("gaul", "Britain", "whoosh"),
    ("alesia", "surrendered", "stamp"), ("alesia", "conquered", "chime"),
    ("legions", "Senate", "boom"), ("collapse", "Julia", "blip"),
    ("collapse", "Crassus", "boom"), ("ultimatum", "public", "stamp"),
    ("ultimatum", "vetoed", "stamp"), ("rubicon", "crossed", "splash"),
    ("rubicon", "Alea", "dice"), ("rubicon", "die", "boom"),
    ("italy", "foot", "stamp"), ("italy", "pardoning", "chime"),
    ("spain", "surrendered", "stamp"), ("dyrrhachium", "beat", "boom"),
    ("pharsalus", "Pharsalus", "boom"), ("pharsalus", "charged", "rumble"),
    ("pharsalus", "hidden", "clash"), ("pharsalus", "collapsed", "boom"),
    ("egypt", "stabbed", "stab"), ("egypt", "wept", "chime"),
    ("epilogue", "came", "chime"), ("epilogue", "dictator", "boom"),
    ("ides", "stabbed", "stab"), ("ides", "23", "stab"),
    ("ides", "foot", "boom"), ("outro", "One", "blip"),
    ("outro", "Five", "blip"), ("outro", "Republic", "boom"),
]


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def pulse(freq, dur, duty=0.5, amp=0.2, decay=0.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ph = (t * freq) % 1.0
    w = np.where(ph < duty, 1.0, -1.0) * amp
    env = np.ones(n)
    a = min(n, int(0.004 * SR))
    env[:a] = np.linspace(0, 1, a)
    r = min(n, int(0.02 * SR))
    env[n - r:] *= np.linspace(1, 0, r)
    if decay:
        env *= np.exp(-t * decay)
    return w * env


def tri(freq, dur, amp=0.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ph = (t * freq) % 1.0
    w = (4 * np.abs(ph - 0.5) - 1) * amp
    env = np.minimum(1, np.minimum(t / 0.05, (dur - t) / 0.08).clip(0))
    return w * env


def noise(dur, amp=0.2, decay=20.0, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    return rng.uniform(-1, 1, n) * amp * np.exp(-t * decay)


def kick(amp=0.5):
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    f = 120 * np.exp(-t * 25) + 45
    ph = np.cumsum(f) / SR
    return np.sin(2 * np.pi * ph) * amp * np.exp(-t * 14)


def lowpass(x, a=0.25):
    y = np.empty_like(x)
    acc = 0.0
    # vectorised one-pole via cumulative trick is overkill; chunked loop
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y


def add(buf, x, t):
    i = int(t * SR)
    if i >= len(buf) or i + len(x) <= 0:
        return
    j = min(len(buf), i + len(x))
    s = max(0, i)
    buf[s:j] += x[s - i:j - i]


# chords: (root midi, chord tones as semitone offsets)
PROG = [(50, (0, 3, 7)), (46, (0, 4, 7)), (48, (0, 4, 7)), (45, (0, 4, 7))]
SAD = [(50, (0, 3, 7)), (43, (0, 3, 7)), (46, (0, 4, 7)), (45, (0, 4, 7))]


def music(tl):
    total = tl.total + 1.0
    buf = np.zeros(int(total * SR))
    bar = 4 * BEAT
    nbars = int(total / bar) + 1

    def intensity_at(t):
        i, it = tl.at(t)
        return INTENSITY.get(it["id"], 1)

    for b in range(nbars):
        t0 = b * bar
        inten = intensity_at(t0 + 0.01)
        prog = SAD if inten == 0 else PROG
        root, tones = prog[b % 4]
        # pad (triangle chord)
        for k in tones:
            add(buf, tri(midi(root + 12 + k), bar, 0.035), t0)
        if inten >= 1:
            # bass eighths
            for e in range(8):
                n = root - 12 + (12 if e % 4 == 3 else 0)
                add(buf, pulse(midi(n), BEAT / 2 * 0.9, 0.25, 0.05), t0 + e *
                    BEAT / 2)
            # arpeggio 16ths
            arp = [tones[i % 3] + 12 * (i // 3 % 2) for i in range(16)]
            for s, k in enumerate(arp):
                add(buf, pulse(midi(root + 24 + k), BEAT / 4 * 0.8, 0.125,
                               0.022, decay=8), t0 + s * BEAT / 4)
        if inten >= 2:
            for q in range(4):
                if q % 2 == 0:
                    add(buf, kick(0.22), t0 + q * BEAT)
                else:
                    add(buf, noise(0.12, 0.08, 30, seed=b * 4 + q), t0 +
                        q * BEAT)
            for e in range(8):
                add(buf, noise(0.03, 0.02, 80, seed=b * 8 + e), t0 + e *
                    BEAT / 2)
        if inten >= 3:
            # march snare rolls + lead fanfare
            for s in range(16):
                if s % 4 in (1, 2, 3) and s >= 12:
                    add(buf, noise(0.06, 0.05, 45, seed=900 + b * 16 + s),
                        t0 + s * BEAT / 4)
            mel = [7, 7, 12, 10, 7, 5, 3, 5] if b % 2 == 0 else \
                  [3, 5, 7, 3, 2, 3, 5, 2]
            for e, k in enumerate(mel):
                add(buf, pulse(midi(root + 24 + k), BEAT / 2 * 0.85, 0.5,
                               0.028), t0 + e * BEAT / 2)
        if inten == 0:
            # sparse sad bell melody
            for e, k in enumerate((7, None, 3, None, 2, None, 0, None)):
                if k is not None:
                    add(buf, pulse(midi(root + 24 + k), BEAT * 0.95, 0.5,
                                   0.025, decay=3), t0 + e * BEAT / 2)
    buf = lowpass(buf, 0.35)
    return buf


def mixs(*arrs):
    n = max(len(a) for a in arrs)
    out = np.zeros(n)
    for a in arrs:
        out[:len(a)] += a
    return out


def sfx(kind, seed=0):
    if kind == "boom":
        return mixs(kick(0.6), noise(0.5, 0.15, 7, seed))
    if kind == "stamp":
        return mixs(kick(0.45), noise(0.08, 0.3, 50, seed))
    if kind == "chime":
        out = np.zeros(int(0.8 * SR))
        for i, n in enumerate((86, 90, 93, 98)):
            x = pulse(midi(n), 0.5, 0.5, 0.05, decay=6)
            add(out, x, i * 0.06)
        return out
    if kind == "blip":
        return np.concatenate([pulse(midi(84), 0.05, 0.5, 0.06),
                               pulse(midi(91), 0.07, 0.5, 0.06, decay=20)])
    if kind == "coins":
        out = np.zeros(int(1.0 * SR))
        rng = np.random.default_rng(seed)
        for i in range(12):
            add(out, pulse(midi(rng.integers(95, 103)), 0.06, 0.5, 0.04,
                           decay=40), i * 0.06 + rng.random() * 0.02)
        return out
    if kind == "splash":
        x = noise(1.2, 0.25, 3, seed)
        return lowpass(x, 0.15) * 1.6
    if kind == "dice":
        out = np.zeros(int(0.9 * SR))
        for i in range(7):
            add(out, noise(0.03, 0.25, 90, seed + i), i * 0.09 + i * i * 0.004)
        return out
    if kind == "clash":
        out = np.zeros(int(0.8 * SR))
        for i in range(4):
            add(out, mixs(pulse(midi(100 + i), 0.15, 0.5, 0.05, decay=25),
                          noise(0.15, 0.12, 30, seed + i)), i * 0.15)
        return out
    if kind == "stab":
        return mixs(noise(0.12, 0.25, 35, seed),
                    pulse(midi(40), 0.12, 0.5, 0.08, decay=30))
    if kind == "rumble":
        return lowpass(noise(1.6, 0.4, 1.5, seed), 0.05) * 2
    if kind == "whoosh":
        x = noise(0.5, 0.2, 0.0, seed)
        env = np.sin(np.linspace(0, np.pi, len(x)))
        return lowpass(x * env, 0.1) * 1.5
    raise KeyError(kind)


def build(tl, path):
    from render import Ctx
    music_buf = music(tl)
    total = len(music_buf)
    voice = np.zeros(total)
    fx = np.zeros(total)
    for it in tl.items:
        x, sr = sf.read(os.path.join(tl.audio_dir, it["id"] + ".wav"))
        assert sr == SR, sr
        add(voice, x, it["start"] + 0.25)
        if it["start"] > 0:
            add(fx, sfx("whoosh", seed=int(it["start"])) * 0.35,
                it["start"] - 0.15)
    items = {it["id"]: it for it in tl.items}
    for k, (sid, cue, kind) in enumerate(SFX):
        it = items[sid]
        t = cue if isinstance(cue, float) else Ctx(it).at(cue)
        add(fx, sfx(kind, seed=k) * 0.8, it["start"] + t)
    # duck music under the voice
    env = np.abs(voice)
    win = int(0.25 * SR)
    kern = np.ones(win) / win
    env = np.convolve(env, kern, mode="same")
    duck = 1.0 - 0.6 * np.clip(env / 0.03, 0, 1)
    # fade out at the very end
    fade = np.ones(total)
    n = int(2.0 * SR)
    end = int(tl.total * SR)
    fade[end - n:end] = np.linspace(1, 0, n)
    fade[end:] = 0
    mixb = voice * 1.0 + music_buf * duck * 0.45 * fade + fx * 0.5
    mixb = np.tanh(mixb * 1.2) / 1.2
    sf.write(path, mixb[:int(tl.total * SR)].astype(np.float32), SR)
