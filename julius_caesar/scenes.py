"""Scene animations. Each scene_<id>(panel, t, ctx) draws one frame of the
270x216 story panel at scene-local time t. ctx.at(word) gives the time a
narration word is spoken so visual beats land on the voice-over.
Optional year_<id>(t, ctx) animates the HUD year."""
import math
import random
from functools import lru_cache

from PIL import Image

import geo
from pixel import (BAYER4, P, bar, circle, clamp, comp, darken, dashed_path,
                   dither_mask, ease, ease_back, ease_out, frame, lerp, line,
                   mix, poly, prog, rect, shake, stamp, text, text_size,
                   tint_overlay, vgrad)
from sprites import (BAG, BROKEN_HEART, COIN, CROSS, DAGGER, EAGLE, FASCES,
                     FLAG_R, HEART, LAUREL, PLOW, SCROLL, SILVER_COIN, SKULL,
                     TENT, cypress, die_face, figure, horse_rider, house,
                     mountains, palm, portrait_card, ship, small_boat, stars,
                     temple, torch, tree)

PW, PH = 270, 216

# ================================================================ helpers


def typed(s, t, start, cps=30):
    n = int(max(0.0, (t - start) * cps))
    return s[:n]


def tag(img, s, t, start=0.0, x=5, y=5, col=None, right=False):
    """Typewriter location/date tag in a framed box."""
    s2 = typed(s, t, start)
    if not s2:
        return
    w, _ = text_size(s, "label", 8, 0)
    w2, _ = text_size(s2, "label", 8, 0)
    if right:
        x = PW - w - 7
    rect(img, x - 3, y - 3, w + 6, 11, P["ink"])
    frame(img, x - 3, y - 3, w + 6, 11, P["dgold"])
    text(img, x, y, s2, col or P["yellow"], "label", 8, spacing=0)


def label_layer(s, fg, bg=None, border=None, kind="label", size=8, pad=2,
                outline=None):
    sp = 0 if kind == "label" else 1
    w, _ = text_size(s, kind, size, sp)
    h = {("label", 8): 5, ("label", 16): 11}.get((kind, size), size)
    if kind == "cap":
        h = 11
    ow = 1 if outline else 0
    L = Image.new("RGBA", (w + 2 * pad + 2 + 2 * ow, h + 2 * pad + 2 + 2 * ow),
                  (0, 0, 0, 0))
    if bg:
        rect(L, 0, 0, L.width, L.height, bg)
    if border:
        frame(L, 0, 0, L.width, L.height, border)
    text(L, pad + 1 + ow, pad + 1 + ow, s, fg, kind, size, spacing=sp,
         outline=outline)
    return L


_LCACHE = {}


def lbl(img, cx, cy, s, fg=None, bg=None, border=None, kind="label", size=8,
        t=1.0, anchor="c", pad=2, outline=None):
    """Label that pops in (t = 0..1 progress) centred at (cx, cy)."""
    if t <= 0:
        return
    key = (s, fg, bg, border, kind, size, pad, outline)
    if key not in _LCACHE:
        _LCACHE[key] = label_layer(s, fg or P["white"], bg, border, kind,
                                   size, pad, outline)
    L = _LCACHE[key]
    if anchor == "l":
        cx = cx + L.width // 2
    elif anchor == "r":
        cx = cx - L.width // 2
    pop(img, L, cx, cy, t)


def pop(img, layer, cx, cy, t):
    if t <= 0:
        return
    k = ease_back(t)
    if k < 0.08:
        return
    if abs(k - 1) < 0.02:
        comp(img, layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))
        return
    w = max(1, int(layer.width * k))
    h = max(1, int(layer.height * k))
    comp(img, layer.resize((w, h), Image.NEAREST),
         (int(cx - w / 2), int(cy - h / 2)))


@lru_cache(maxsize=128)
def card_layer(who, scale=2, label=True, mood=None, gray=False, name=None,
               border=None):
    w = 32 * scale + 4
    h = w + (9 if label else 0)
    L = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    portrait_card(L, 0, 0, who, scale=scale, label=label, mood=mood,
                  gray=gray, name=name, border=border)
    return L


def card(img, x, y, who, t=1.0, scale=2, **kw):
    """Portrait card with top-left at (x, y), popping in."""
    L = card_layer(who, scale, **kw)
    pop(img, L, x + L.width / 2, y + L.height / 2, t)
    return L.width, L.height


def wrap(s, max_w, kind="label", size=8):
    words, lines, cur = s.split(), [], ""
    for w in words:
        nxt = (cur + " " + w).strip()
        if text_size(nxt, kind, size, 0)[0] > max_w and cur:
            lines.append(cur)
            cur = w
        else:
            cur = nxt
    if cur:
        lines.append(cur)
    return lines


def textbox(img, x, y, w, lines, t=1.0, fg=None, bg=None, border=None,
            lh=8, start_col=None, cps=40, t0=0.0):
    """Box with typed multi-line text. t is scene time, t0 when it starts."""
    if t < t0:
        return
    h = len(lines) * lh + 6
    k = ease_out(prog(t, t0, 0.2))
    rect(img, x, y, w, int(h * k), bg or P["ink"])
    frame(img, x, y, w, int(h * k), border or P["dgold"])
    if k < 1:
        return
    n = int((t - t0 - 0.2) * cps)
    for i, ln in enumerate(lines):
        if n <= 0:
            break
        col = fg or P["white"]
        if start_col and i == 0:
            col = start_col
        text(img, x + 4, y + 4 + i * lh, ln[:n], col, "label", 8, spacing=0)
        n -= len(ln)


def arrow_head(img, x, y, ang, col, size=3):
    a1 = ang + math.radians(150)
    a2 = ang - math.radians(150)
    poly(img, [(x + math.cos(ang) * 1, y + math.sin(ang) * 1),
               (x + math.cos(a1) * size, y + math.sin(a1) * size),
               (x + math.cos(a2) * size, y + math.sin(a2) * size)], col)


def route(img, pts, p, col, dash=3, gap=2, head=True, t=0.0, width=1):
    """Animated dashed route with arrow head. p = reveal progress."""
    if p <= 0:
        return None
    hx, hy = dashed_path(img, pts, col, p, dash, gap, offset=-t * 8)
    if width > 1:
        dashed_path(img, [(x + 1, y) for x, y in pts], col, p, dash, gap,
                    offset=-t * 8)
    if head:
        # direction from the point slightly behind
        L = 0.0
        segs = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            d = math.hypot(x1 - x0, y1 - y0)
            segs.append((x0, y0, x1, y1, d))
            L += d
        target = L * clamp(p)
        acc = 0.0
        ang = 0.0
        for x0, y0, x1, y1, d in segs:
            if acc + d >= target - 1e-6:
                ang = math.atan2(y1 - y0, x1 - x0)
                break
            acc += d
        arrow_head(img, hx, hy, ang, col, 4)
    return hx, hy


def bezier(p0, p1, p2, n=24):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1])
            for u in (i / n for i in range(n + 1))]


def pin(img, x, y, col, t, label=None, below=False, lab_col=None, dx=0):
    if t <= 0:
        return
    k = ease_back(t)
    drop = int((1 - ease_out(t)) * 10)
    x, y = int(x), int(y) - drop
    circle(img, x, y - 4, 2, col, outline=P["ink"])
    line(img, x, y - 2, x, y, P["ink"])
    img.putpixel((x - 1, y - 5), P["white"]) if 0 < x < PW and 5 < y < PH \
        else None
    if label and t > 0.3:
        ly = y + 6 if below else y - 13
        lbl(img, x + dx, ly, label, lab_col or P["white"], P["ink"], None,
            t=clamp((t - 0.3) / 0.5))


def flash(img, t, at, dur=0.15, col=None):
    if at <= t < at + dur:
        tint_overlay(img, col or P["white"], 0.6 * (1 - (t - at) / dur))


def fade_in_black(img, t, dur=0.25):
    if t < dur:
        darken(img, 1 - t / dur)


def sparkle(img, x, y, t, seed=0, col=None):
    ph = (t * 3 + seed * 0.37) % 1.0
    r = int(ph * 4)
    c = col or P["yellow"]
    for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
        xx, yy = int(x + dx), int(y + dy)
        if 0 <= xx < PW and 0 <= yy < PH:
            img.putpixel((xx, yy), c)


def sky(img, stops, h):
    vgrad(img, 0, 0, PW, h, stops)


def ground(img, y, c1, c2, h=None):
    h = h or PH - y
    rect(img, 0, y, PW, h, c1)
    m = dither_mask(PW, h, 0.18)
    import numpy as np
    a = np.array(img)
    a[y:y + h][m] = (*c2, 255)
    img.paste(Image.fromarray(a, img.mode))


def rome_skyline(img, base, t, col=None, lit=False):
    """Distant Rome: hills, temples, houses, cypresses."""
    hill = col or P["grass"]
    poly(img, [(0, base), (0, base - 10), (40, base - 22), (90, base - 16),
               (140, base - 30), (200, base - 18), (270, base - 26),
               (270, base)], hill)
    temple(img, 120, base - 26, w=40, h=28)
    temple(img, 214, base - 22, w=28, h=20, cols=4)
    for i, hx in enumerate((20, 52, 70, 170, 186, 246)):
        house(img, hx, base - 12 - (i % 2) * 3, w=12, h=8)
    for cx in (8, 46, 96, 165, 205, 262):
        cypress(img, cx, base - 10, 16)
    rect(img, 0, base, PW, PH - base, P["dgrass"])


def river_x(y, top=130, xl=(150, 120), xr=(162, 205)):
    f = (y - top) / (PH - top)
    return lerp(xl[0], xl[1], f), lerp(xr[0], xr[1], f)


def river_scene(img, t, dawn=0.0, moon=True):
    """Side view of the Rubicon: legion on the near bank (left), Italy on
    the far bank (right). River runs from the horizon toward the viewer."""
    top = mix(P["night"], P["navy"], dawn)
    mid = mix(P["navy"], P["plum"], dawn)
    hor = mix(P["plum"], P["orange"], dawn)
    sky(img, [top, mid, hor], 130)
    if dawn < 0.7:
        stars(img, PW, 90, t, n=int(50 * (1 - dawn)))
    if moon:
        circle(img, 222, 30, 9, P["marble"])
        circle(img, 226, 27, 9, top) if dawn < 0.2 else None
    poly(img, [(0, 130), (0, 112), (40, 104), (90, 114), (130, 100),
               (180, 110), (230, 98), (270, 108), (270, 130)], P["dslate"])
    poly(img, [(0, 130), (0, 122), (60, 116), (120, 124), (170, 118),
               (220, 124), (270, 116), (270, 130)], P["forest"])
    ground(img, 130, P["dgrass"], P["forest"])
    # river
    pts = [(150, 130), (162, 130), (205, PH), (120, PH)]
    poly(img, pts, P["navy"])
    for k in range(14):
        yy = 130 + ((k * 7 + t * 14) % (PH - 130))
        a, b = river_x(yy)
        span = b - a
        x0 = a + span * ((k * 0.37) % 0.7)
        line(img, x0, yy, x0 + max(2, span * 0.18), yy, P["blue"])
        if k % 3 == 0:
            img.putpixel((int(x0 + 1), int(yy)), P["sky"])
    # banks
    for yy in range(130, PH):
        a, b = river_x(yy)
        img.putpixel((int(a), yy), P["dbrown"])
        img.putpixel((int(b), yy), P["dbrown"])


def splash(img, x, y, t, seed=0):
    rnd = random.Random(seed)
    for i in range(6):
        ph = (t * 2.5 + rnd.random()) % 1.0
        dx = (rnd.random() - 0.5) * 10
        px = x + dx * ph
        py = y - 6 * math.sin(ph * math.pi)
        if 0 <= px < PW and 0 <= py < PH:
            img.putpixel((int(px), int(py)), P["cyan"] if i % 2 else P["white"])


def cohort(img, x, y, w, h, col, dark, t=0.0, seed=0, cav=False):
    rect(img, x, y, w, h, dark)
    rect(img, x + 1, y + 1, w - 2, h - 2, col)
    for yy in range(int(y) + 2, int(y + h) - 1, 2):
        for xx in range(int(x) + 2, int(x + w) - 1, 2):
            if 0 <= xx < PW and 0 <= yy < PH and (xx + yy + seed) % 4 == 0:
                img.putpixel((xx, yy), P["white"] if not cav else P["sand"])


# ================================================================ scenes

def scene_hook(img, t, ctx):
    river_scene(img, t, dawn=0.0)
    # legion waiting on the near bank
    for row, yy in enumerate((168, 182, 200)):
        for i in range(5):
            x = 14 + i * 14 + (row % 2) * 7
            figure(img, x, yy, "legion", facing=1)
        torch(img, 10 + row * 24, yy - 16, t, seed=row)
    horse_rider(img, 100, 198, t * 0.3, rider="general")
    # signpost on the far bank
    rect(img, 224, 160, 2, 16, P["dbrown"])
    rect(img, 212, 154, 28, 8, P["sand"])
    text(img, 226, 156, "ITALIA", P["dbrown"], "label", 8, anchor="c",
         spacing=0)
    tag(img, "JANUARY, 49 BC", t, 0.15)
    t_cross = ctx.at("Cross")
    t_stay = ctx.at("Stay")
    t_how = ctx.at("How")
    if t < t_how:
        if t > t_cross:
            p = ease_out(prog(t, t_cross, 0.6))
            route(img, [(120, 186), (170, 176), (214, 182)], p, P["red"], t=t)
            lbl(img, 205, 116, "CROSS = TREASON", P["white"], P["red"],
                P["wine"], t=prog(t, t_cross, 0.35))
        if t > t_stay:
            lbl(img, 62, 116, "STAY = RUIN", P["ink"], P["silver"],
                P["slate"], t=prog(t, t_stay, 0.35))
    else:
        k = prog(t, t_how, 0.4)
        darken(img, 0.55 * k)
        LAUREL.blit(img, 135, 52, scale=3, anchor="c") if k > 0.3 else None
        lbl(img, 135, 86, "JULIUS CAESAR", P["yellow"], None, None, "title",
            16, t=prog(t, t_how + 0.1, 0.4), outline=P["ink"])
        lbl(img, 135, 108, "THE ROAD TO THE RUBICON", P["white"], P["red"],
            P["wine"], t=prog(t, t_how + 0.5, 0.4), pad=3)
        for i in range(5):
            sparkle(img, 60 + i * 38, 70 + (i % 2) * 34, t, i)
    fade_in_black(img, t, 0.2)


def scene_origins(img, t, ctx):
    sky(img, [P["sky"], P["cyan"], P["white"]], 180)
    circle(img, 236, 26, 10, P["yellow"])
    rome_skyline(img, 200, t)
    tag(img, "ROME, 100 BC", t, 0.1, right=True)
    # Venus -> Caesar lineage
    t_v = ctx.at("Venus")
    t_c = 0.25
    card(img, 10, 78, "caesar", prog(t, t_c, 0.4), 2)
    lbl(img, 44, 166, "BORN 100 BC", P["white"], P["red"], None,
        t=prog(t, ctx.at("100"), 0.3))
    t_desc = ctx.at("claimed")
    if t > t_desc:
        card(img, 20, 10, "venus", prog(t, t_desc, 0.35), 1)
        p = prog(t, t_desc + 0.2, 0.5)
        dashed_path(img, [(38, 58), (38, 76)], P["pink"], p)
        lbl(img, 100, 26, "DESCENDED FROM", P["white"], P["ink"], None,
            t=prog(t, t_desc + 0.1, 0.3))
        lbl(img, 100, 36, "A GODDESS?", P["pink"], P["ink"], None,
            t=prog(t, t_v, 0.3))
        for i in range(3):
            sparkle(img, 22 + i * 14, 12 + (i % 2) * 30, t, i, P["pink"])
    t_m = ctx.at("money")
    if t > t_m - 0.3:
        p = prog(t, t_m - 0.3, 0.5)
        rect(img, 84, 100, 86, 36, P["ink"])
        frame(img, 84, 100, 86, 36, P["dgold"])
        text(img, 88, 104, "WEALTH", P["white"], "label", 8, spacing=0)
        bar(img, 124, 104, 42, 5, 0.18 * p, P["gold"], P["dslate"])
        text(img, 88, 114, "POWER", P["white"], "label", 8, spacing=0)
        bar(img, 124, 114, 42, 5, 0.22 * p, P["red"], P["dslate"])
        text(img, 88, 124, "PEDIGREE", P["white"], "label", 8, spacing=0)
        bar(img, 124, 124, 42, 5, 1.0 * p, P["purple"], P["dslate"])
    t_a = ctx.at("aunt")
    if t > t_a:
        card(img, 202, 60, "marius", prog(t, t_a + 0.2, 0.35), 1)
        HEART.blit(img, 186, 76) if t > t_a + 0.4 else None
        dashed_path(img, [(80, 90), (186, 80)], P["pink"],
                    prog(t, t_a, 0.4))
        lbl(img, 220, 114, "UNCLE MARIUS", P["yellow"], P["ink"], None,
            t=prog(t, ctx.at("Marius"), 0.3))
        lbl(img, 220, 124, "POPULIST GENERAL", P["white"], P["red"], None,
            t=prog(t, ctx.at("populist"), 0.3))


def scene_sulla(img, t, ctx):
    sky(img, [P["wine"], P["red"], P["orange"]], 216)
    rome_skyline(img, 214, t, col=P["wine"])
    darken(img, 0.25)
    card(img, 8, 8, "sulla", prog(t, 0.1, 0.35), 2, mood="angry")
    lbl(img, 42, 92, "DICTATOR", P["white"], P["red"], P["wine"],
        t=prog(t, ctx.at("Sulla"), 0.3))
    # proscription list
    tl = 0.4
    h = int(96 * ease_out(prog(t, tl, 0.6)))
    if h > 4:
        rect(img, 96, 8, 166, h, P["marble"])
        frame(img, 96, 8, 166, h, P["dsand"])
        rect(img, 94, 6, 170, 4, P["dsand"])
        rect(img, 94, 6 + h, 170, 4, P["dsand"])
        if h > 20:
            text(img, 179, 14, "PROSCRIBED", P["wine"], "label", 8,
                 anchor="c", spacing=0)
        rnd = random.Random(4)
        for i in range(8):
            yy = 26 + i * 9
            if yy + 4 > 8 + h:
                break
            ln = rnd.randint(50, 130)
            for k in range(0, ln, 4):
                rect(img, 106 + k, yy + 1, 3, 2, P["slate"])
            cut = prog(t, tl + 0.5 + i * 0.25, 0.25)
            if cut > 0:
                line(img, 104, yy + 2, 104 + (ln + 4) * cut, yy + 2, P["red"])
    t_d = ctx.at("divorce")
    if t > t_d - 0.2:
        rect(img, 96, 112, 166, 26, P["ink"])
        frame(img, 96, 112, 166, 26, P["red"])
        text(img, 102, 116, "SULLA'S ORDER:", P["red"], "label", 8, spacing=0)
        text(img, 102, 126, typed("DIVORCE CORNELIA", t, t_d), P["white"],
             "label", 8, spacing=0)
    t_r = ctx.at("refused")
    if t > ctx.at("Caesar") - 0.1:
        card(img, 8, 112, "caesar", prog(t, ctx.at("Caesar") - 0.1, 0.35), 1)
    if t > t_r:
        L = label_layer("NO.", P["ink"], P["white"], P["ink"], "title", 8, 3)
        pop(img, L, 66, 124, prog(t, t_r, 0.3))
        poly(img, [(50, 126), (56, 122), (56, 130)], P["white"]) \
            if t > t_r + 0.15 else None
    t_h = ctx.at("hid")
    if t > t_h:
        # flight into the hills at night
        k = prog(t, t_h, 0.3)
        rect(img, 0, 160, PW, 56, P["night"])
        stars(img, PW, 20, t, n=10) if False else None
        poly(img, [(0, 216), (0, 186), (50, 172), (110, 184), (170, 166),
                   (230, 180), (270, 170), (270, 216)], P["forest"])
        for bx in (40, 120, 200):
            circle(img, bx, 196, 6, P["dgrass"])
        x = lerp(10, 250, prog(t, t_h, 2.2))
        figure(img, x, 206, "caesar", walk=t * 3)
        lbl(img, 80, 166, "ON THE RUN, SICK WITH FEVER", P["silver"], P["ink"],
            None, t=k)
    t_p = ctx.at("pardon")
    if t > t_p:
        stamp(img, 200, 188, "PARDONED", P["lime"], prog(t, t_p, 0.4), 8)


def scene_pirates(img, t, ctx):
    sky(img, [P["plum"], P["red"], P["orange"], P["yellow"]], 130)
    circle(img, 200, 130, 16, P["yellow"])
    rect(img, 0, 128, PW, 88, P["navy"])
    for k in range(40):
        yy = 130 + (k * 37) % 86
        xx = (k * 53 + t * (8 + yy * 0.05)) % (PW + 20) - 10
        line(img, xx, yy, xx + 4 + (yy - 128) // 12, yy,
             P["blue"] if k % 3 else P["orange"])
    t_hunt = ctx.at("hunted")
    flee = ease(prog(t, t_hunt, 2.0)) * 60
    ship(img, 150 + flee, 172, t, sail=P["ink"], hull=P["dbrown"],
         flag=P["red"], scale=2)
    # ransom box
    rect(img, 6, 6, 128, 58, P["ink"])
    frame(img, 6, 6, 128, 58, P["dgold"])
    text(img, 12, 11, "RANSOM DEMAND", P["yellow"], "label", 8, spacing=0)
    t20 = ctx.at("20")
    t50 = ctx.at("50")
    if t > t20:
        text(img, 12, 24, "20 TALENTS", P["white"], "title", 8)
        if t > ctx.at("insulted"):
            line(img, 10, 27, 10 + 86 * prog(t, ctx.at("insulted"), 0.3), 27,
                 P["red"], 2)
    if t > t50:
        k = ease_back(prog(t, t50, 0.35))
        if k > 0.1:
            L = label_layer("50 TALENTS", P["yellow"], None, None, "title", 8, 0)
            pop(img, L, 56, 41, prog(t, t50, 0.35))
        text(img, 12, 53, "1 TALENT = ~26 KG SILVER", P["silver"], "label", 8,
             spacing=0) if t > t50 + 0.4 else None
    # coin pile
    n = int(clamp((t - t20) / 0.04, 0, 20)) + int(clamp((t - t50) / 0.03, 0, 30))
    for i in range(n):
        cx = 140 + (i % 6) * 9 + (i // 6 % 2) * 4
        cy = 54 - (i // 6) * 4
        SILVER_COIN.blit(img, cx, cy)
    if t > t_hunt:
        x = lerp(-60, 90, ease_out(prog(t, t_hunt, 2.0)))
        ship(img, x, 178, t + 1, sail=P["red"], flag=P["gold"], scale=2)
        lbl(img, x, 112, "ROMAN FLEET", P["white"], P["red"], None,
            t=prog(t, t_hunt + 0.3, 0.3))
    t_cr = ctx.at("crucified")
    if t > t_cr:
        k = prog(t, t_cr, 0.4)
        darken(img, 0.5 * k)
        poly(img, [(212, 216), (220, 150), (240, 140), (270, 136), (270, 216)],
             P["black"])
        for i, cx in enumerate((232, 246, 260)):
            if t > t_cr + i * 0.2:
                CROSS.blit(img, cx - 2, 128 + (i % 2) * 2, scale=2,
                           tint=P["black"])
        lbl(img, 160, 120, "PROMISE KEPT", P["white"], P["red"], P["wine"],
            t=prog(t, ctx.at("promised"), 0.3))


def scene_ladder(img, t, ctx):
    vgrad(img, 0, 0, PW, PH, [P["dslate"], P["slate"], P["dslate"]])
    for cx in (6, 264):
        rect(img, cx - 4, 0, 8, PH, P["marble"])
        line(img, cx + 2, 0, cx + 2, PH, P["stone"])
    steps = [("QUAESTOR", "69 BC"), ("AEDILE", "65 BC"), ("PONTIFEX", "63 BC"),
             ("PRAETOR", "62 BC"), ("CONSUL", "59 BC")]
    sx0, sw, sh, base = 50, 42, 24, 206
    for i, (nm, yr) in enumerate(steps):
        x = sx0 + i * sw
        y = base - (i + 1) * sh
        rect(img, x, y, PW - x - 10, sh, P["marble"])
        rect(img, x, y, PW - x - 10, 2, P["white"])
        line(img, x, y, x, y + sh, P["stone"])
        dim = i == 4
        col = P["slate"] if dim else P["ink"]
        text(img, x + sw // 2, y + 6, nm, col, "label", 8, anchor="c",
             spacing=0)
        text(img, x + sw // 2, y + 14, yr, P["red"] if not dim else P["slate"],
             "label", 8, anchor="c", spacing=0)
    rect(img, 10, base, PW - 20, PH - base, P["marble"])
    # Caesar hopping up to step 3
    t_pm = ctx.at("Pontifex")
    hops = [0.6, 1.8, t_pm - 0.3]
    pos = 0
    for k, th in enumerate(hops):
        if t >= th:
            pos = k + 1
    xs = [sx0 - 14] + [sx0 + i * sw + sw // 2 for i in range(5)]
    ys = [base] + [base - (i + 1) * sh for i in range(5)]
    cx, cy = xs[pos], ys[pos]
    if pos < 3:
        th = hops[pos]
        if t > th - 0.35:
            f = prog(t, th - 0.35, 0.35)
            cx = lerp(xs[pos], xs[pos + 1], f)
            cy = lerp(ys[pos], ys[pos + 1], f) - math.sin(f * math.pi) * 10
    figure(img, cx, cy, "caesar", walk=t * 2 if pos < 3 else None, scale=2)
    # debt meter
    t_b = ctx.at("borrowed")
    t_dt = ctx.at("debt")
    rect(img, 16, 22, 16, 150, P["ink"])
    frame(img, 15, 21, 18, 152, P["dgold"])
    text(img, 24, 12, "DEBT", P["red"], "label", 8, anchor="c", spacing=0)
    f = clamp(0.1 + 0.5 * prog(t, t_b - 0.3, 1.0) + 0.5 * prog(t, t_dt - 0.4,
                                                               0.8), 0, 1.0)
    hh = int(146 * f)
    rect(img, 18, 24 + 146 - hh, 12, hh, P["red"])
    if f >= 0.99 and int(t * 4) % 2 == 0:
        lbl(img, 24, 12, "MAX!", P["white"], P["red"], None)
    if t > t_b - 0.3:
        for i in range(6):
            ph = (t * 1.2 + i / 6) % 1.0
            x = lerp(40, cx, ph)
            y = lerp(20, cy - 20, ph) - math.sin(ph * math.pi) * 20
            COIN.blit(img, x, y)
    if t > t_pm:
        p = prog(t, t_pm, 0.4)
        rect(img, 80, 14, 168, 34, P["ink"]) if p > 0.3 else None
        frame(img, 80, 14, 168, 34, P["gold"]) if p > 0.3 else None
        lbl(img, 164, 24, "PONTIFEX MAXIMUS", P["yellow"], None, None,
            "title", 8, t=p)
        lbl(img, 164, 38, "ROME'S CHIEF PRIEST", P["white"], None, None,
            t=prog(t, ctx.at("chief"), 0.3))
        for i in range(4):
            sparkle(img, 90 + i * 50, 16 + (i % 2) * 30, t, i)


def year_ladder(t, ctx):
    t_pm = ctx.at("Pontifex")
    return -69 + 6 * prog(t, 0.3, t_pm - 0.3)



# ---------------------------------------------------------------- triumvirate

TRI = {"caesar": (101, 4), "pompey": (14, 110), "crassus": (184, 110)}
TRI_C = {k: (x + 36, y + 36) for k, (x, y) in TRI.items()}


def plum_bg(img, t):
    vgrad(img, 0, 0, PW, PH, [P["ink"], P["plum"], P["ink"]])
    for y in range(4, PH, 12):
        for x in range((y // 12) % 2 * 6, PW, 12):
            img.putpixel((x, y), P["purple"])


def tri_lines(img, t, p=1.0, broken=(), col=None):
    col = col or (P["yellow"] if int(t * 6) % 2 else P["gold"])
    pairs = [("caesar", "pompey"), ("caesar", "crassus"),
             ("pompey", "crassus")]
    for a, b in pairs:
        if (a, b) in broken:
            continue
        (x0, y0), (x1, y1) = TRI_C[a], TRI_C[b]
        line(img, x0, y0, lerp(x0, x1, p), lerp(y0, y1, p), col, 2)


def scene_triumvirate(img, t, ctx):
    plum_bg(img, t)
    t_p, t_c, t_f = ctx.at("Pompey"), ctx.at("Crassus"), ctx.at("First")
    if t > t_f:
        tri_lines(img, t, ease_out(prog(t, t_f, 0.5)))
    card(img, *TRI["caesar"], "caesar", prog(t, 0.2, 0.35))
    if t > 0.5:
        lbl(img, 222, 24, "CAESAR", P["yellow"], None, None, "title", 8,
            t=prog(t, 0.5, 0.3))
        lbl(img, 222, 38, "THE POLITICIAN", P["white"], P["red"], None,
            t=prog(t, 0.7, 0.3))
        lbl(img, 222, 50, "AMBITION 10/10", P["white"], P["ink"], None,
            t=prog(t, 0.9, 0.3))
    card(img, *TRI["pompey"], "pompey", prog(t, t_p, 0.35))
    if t > t_p:
        lbl(img, 50, 202, "ARMY 10/10", P["white"], P["blue"], None,
            t=prog(t, ctx.at("famous"), 0.3))
        lbl(img, 50, 100, "THE GENERAL", P["white"], P["blue"], None,
            t=prog(t, t_p + 0.3, 0.3))
    card(img, *TRI["crassus"], "crassus", prog(t, t_c, 0.35))
    if t > t_c:
        lbl(img, 220, 202, "WEALTH 10/10", P["ink"], P["gold"], None,
            t=prog(t, ctx.at("richest"), 0.3))
        lbl(img, 220, 100, "THE BANKER", P["ink"], P["gold"], None,
            t=prog(t, t_c + 0.3, 0.3))
    if t > t_f:
        rect(img, 70, 128, 130, 34, P["ink"]) if t > t_f + 0.2 else None
        frame(img, 70, 128, 130, 34, P["gold"]) if t > t_f + 0.2 else None
        lbl(img, 135, 138, "FIRST", P["yellow"], None, None, "title", 8,
            t=prog(t, t_f, 0.3))
        lbl(img, 135, 151, "TRIUMVIRATE", P["yellow"], None, None, "title", 8,
            t=prog(t, t_f + 0.15, 0.3))
        lbl(img, 135, 170, "60 BC - A SECRET PACT", P["white"], P["red"], None,
            t=prog(t, t_f + 0.4, 0.3))
        for i in range(5):
            sparkle(img, 75 + i * 30, 126 + (i % 2) * 38, t, i)
    t_s = ctx.at("secret")
    if t_s < t < t_p:
        lbl(img, 135, 140, "TOP SECRET", P["red"], P["ink"], P["red"], "title",
            8, t=prog(t, t_s, 0.3))


def scene_deal(img, t, ctx):
    plum_bg(img, t)
    tri_lines(img, t)
    for k in TRI:
        card(img, *TRI[k], k)
    t_p, t_c = ctx.at("Pompey"), ctx.at("Crassus")
    t_cs = ctx.at("Caesar")
    t_m = ctx.at("married")
    if t > t_p:
        p = prog(t, t_p, 0.35)
        PLOW.blit(img, 92, 168, scale=2) if p > 0.5 else None
        lbl(img, 50, 202, "LAND FOR VETERANS", P["white"], P["blue"], None,
            t=p)
    if t > t_c:
        p = prog(t, t_c, 0.35)
        BAG.blit(img, 160, 168, scale=2) if p > 0.5 else None
        lbl(img, 220, 202, "TAX DEAL FOR ALLIES", P["ink"], P["gold"], None,
            t=p)
    if t > t_cs:
        p = prog(t, t_cs, 0.35)
        FASCES.blit(img, 186, 20, scale=2) if p > 0.5 else None
        lbl(img, 222, 50, "CONSULSHIP", P["white"], P["red"], None, t=p)
        lbl(img, 222, 62, "+ A PROVINCE", P["white"], P["ink"], None,
            t=prog(t, t_cs + 0.3, 0.3))
    if t > t_m - 0.2:
        card(img, 20, 10, "julia", prog(t, t_m - 0.2, 0.35), 1)
        p = prog(t, t_m + 0.1, 0.5)
        dashed_path(img, [(38, 56), (44, 108)], P["pink"], p)
        HEART.blit(img, 44, 76, scale=2) if p > 0.6 else None
        lbl(img, 78, 70, "WED 59 BC", P["white"], P["red"], None,
            t=prog(t, t_m + 0.4, 0.3))
        dashed_path(img, [(57, 30), (100, 30)], P["silver"],
                    prog(t, ctx.at("daughter"), 0.4))
        lbl(img, 78, 22, "DAUGHTER", P["silver"], P["ink"], None,
            t=prog(t, ctx.at("daughter"), 0.3))


def scene_consul(img, t, ctx):
    sky(img, [P["sky"], P["cyan"]], 120)
    temple(img, 70, 140, w=130, h=90, cols=8)
    rect(img, 0, 140, PW, 76, P["stone"])
    for x in range(0, PW, 12):
        line(img, x, 140, x - 20, 216, P["dstone"])
    # rostra
    rect(img, 108, 168, 54, 14, P["marble"])
    rect(img, 108, 168, 54, 2, P["white"])
    t_b = ctx.at("Bibulus")
    raise_ = int(t * 2) % 2 == 0 and t < t_b
    figure(img, 135, 168, "caesar", pose="raise" if raise_ else None)
    # crowd of Pompey's veterans and citizens
    rnd = random.Random(2)
    for i in range(14):
        x = 10 + i * 18 + rnd.randint(-3, 3)
        y = 196 + (i % 2) * 12
        kind = "legion" if i % 3 == 0 else "civil"
        pose = "raise" if (int(t * 3) + i) % 4 == 0 else None
        figure(img, x, y, kind, facing=1 if x < 135 else -1, pose=pose)
    # laws passed list
    laws = ["LAND FOR VETERANS", "POMPEY'S EAST DEALS", "TAX RELIEF"]
    t_l = ctx.at("laws")
    if t > t_l - 0.3:
        rect(img, 6, 6, 118, 42, P["ink"])
        frame(img, 6, 6, 118, 42, P["dgold"])
        text(img, 10, 10, "LAWS PASSED 59 BC", P["yellow"], "label", 8,
             spacing=0)
        for i, lw in enumerate(laws):
            ti = t_l + i * 0.45
            if t > ti:
                text(img, 10, 21 + i * 9, lw, P["white"], "label", 8,
                     spacing=0)
                lbl(img, 118, 23 + i * 9, "OK", P["ink"], P["lime"], None,
                    t=prog(t, ti + 0.15, 0.25))
    if t > ctx.at("brazenly"):
        lbl(img, 135, 156, "BY FORCE!", P["white"], P["red"], None,
            t=prog(t, ctx.at("brazenly"), 0.3))
    # Bibulus goes home
    if t > t_b - 0.2:
        house(img, 228, 196, w=30, h=22)
        card(img, 220, 8, "bibulus", prog(t, t_b - 0.2, 0.35), 1)
        x = lerp(196, 243, prog(t, t_b, 1.2))
        if t < t_b + 1.2:
            figure(img, x, 196, "senator", walk=t * 2)
        else:
            rect(img, 241, 186, 5, 10, P["dbrown"])
            lbl(img, 243, 170, "ZZZ", P["white"], P["ink"], None,
                t=prog(t, t_b + 1.2, 0.3))
        lbl(img, 200, 62, "HID AT HOME", P["white"], P["ink"], None,
            t=prog(t, ctx.at("home"), 0.3))
    t_j = ctx.at("Julius")
    if t > t_j - 0.5:
        p = prog(t, t_j - 0.5, 0.35)
        darken(img, 0.5 * p)
        L = Image.new("RGBA", (190, 52), (0, 0, 0, 0))
        rect(L, 0, 0, 190, 52, P["marble"])
        frame(L, 0, 0, 190, 52, P["stone"])
        frame(L, 2, 2, 186, 48, P["dstone"])
        text(L, 95, 8, "CONSULS OF 59 BC", P["dstone"], "label", 8,
             anchor="c", spacing=0)
        text(L, 95, 22, "JULIUS", P["red"], "title", 8, anchor="c")
        text(L, 95, 35, "& CAESAR", P["red"], "title", 8, anchor="c")
        pop(img, L, 135, 110, p)


# ---------------------------------------------------------------- Gaul

GAUL_VIEW = geo.View.centered(3.0, 48.6, 13.5)


@lru_cache(maxsize=4)
def _gaul_masks(vkey):
    v = geo.View(*vkey)
    import numpy as np
    gaul = geo.region_mask(v, [geo.GAUL])
    prov = geo.region_mask(v, [geo.NARBONENSIS, geo.CISALPINA])
    gx, gy = v.xy(*geo.PLACES["geneva"])
    yy, xx = np.mgrid[0:v.h, 0:v.w]
    dist = np.hypot(xx - gx, (yy - gy) * 1.1)
    return gaul, prov, dist


def map_base(view, t, rivers=(), alps=True, pyrenees=False):
    img = geo.render_map(view, t).convert("RGBA")
    geo.draw_rivers(img, view, rivers)
    if alps:
        geo.draw_mountains(img, view, geo.ALPS)
    if pyrenees:
        geo.draw_mountains(img, view, geo.PYRENEES)
    return img


def place(view, name):
    return view.xy(*geo.PLACES[name])


def scene_gaul(img, t, ctx):
    v = GAUL_VIEW
    m = map_base(v, t, ("rhine", "rhone", "loire", "seine", "po"),
                 pyrenees=True)
    gaul, prov, dist = _gaul_masks(v.key())
    geo.overlay_region(m, prov, P["red"], 1)
    r = 260 * ease(prog(t, 0.6, ctx.dur - 1.6))
    geo.overlay_region(m, gaul & (dist < r), P["red"], 2)
    comp(img, m, (0, 0))
    gx, gy = place(v, "geneva")
    lbl(img, gx + 30, gy + 30, "ROMAN PROVINCE", P["white"], P["wine"], None,
        t=prog(t, 0.3, 0.3))
    lbl(img, 120, 112, "GAUL", P["white"], None, None, "title", 8,
        outline=P["ink"], t=prog(t, ctx.at("Gaul"), 0.3))
    ax, ay = v.xy(9.5, 46.2)
    lbl(img, ax + 10, ay + 10, "ALPS", P["white"], P["ink"], None,
        t=prog(t, ctx.at("Alps"), 0.3))
    # year counter
    yr = int(round(58 - 7 * clamp(prog(t, 0.6, ctx.dur - 1.6))))
    rect(img, 4, 4, 64, 22, P["ink"])
    frame(img, 4, 4, 64, 22, P["dgold"])
    text(img, 36, 8, "CONQUEST", P["silver"], "label", 8, anchor="c",
         spacing=0)
    text(img, 36, 16, f"{yr} BC", P["yellow"], "title", 8, anchor="c")
    t_r = ctx.at("Rhine")
    if t > t_r - 0.2:
        bx, by = place(v, "rhine_bridge")
        p = prog(t, t_r - 0.2, 0.4)
        for i in range(int(7 * p)):
            rect(img, bx - 4 + i, by - 1, 1, 3, P["brown"])
        rect(img, bx - 4, by - 2, int(8 * p), 1, P["sand"])
        lbl(img, bx + 26, by - 12, "BRIDGE: ~10 DAYS", P["white"], P["ink"],
            P["sky"], t=prog(t, ctx.at("ten"), 0.3))
        lbl(img, bx + 26, by - 2, "55 BC", P["yellow"], P["ink"], None,
            t=prog(t, ctx.at("ten"), 0.3))
    t_b = ctx.at("Britain")
    if t > t_b - 0.3:
        a = v.xy(2.0, 50.6)
        b = v.xy(0.2, 51.5)
        pts = bezier(a, ((a[0] + b[0]) / 2 + 4, a[1] - 14), b)
        route(img, pts, ease_out(prog(t, t_b - 0.3, 0.6)), P["red"], t=t)
        lbl(img, b[0] - 22, b[1] - 18, "BRITAIN", P["white"], P["red"], None,
            t=prog(t, t_b, 0.3))
        lbl(img, b[0] - 22, b[1] - 8, "55 & 54 BC", P["yellow"], P["ink"],
            None, t=prog(t, ctx.at("twice"), 0.3))


def year_gaul(t, ctx):
    return -58 + 7 * clamp(prog(t, 0.6, ctx.dur - 1.6))


def scene_alesia(img, t, ctx):
    import numpy as np
    rect(img, 0, 0, PW, PH, P["grass"])
    m = dither_mask(PW, PH, 0.25)
    a = np.array(img)
    a[m] = (*P["dgrass"], 255)
    img.paste(Image.fromarray(a, "RGBA"))
    cx, cy = 135, 116
    # rivers
    for off in (-34, 34):
        pts = [(0, cy + off + math.sin(i / 20) * 4) for i in range(0, 270, 6)]
        pts = [(i, cy + off + math.sin(i / 22.0) * 5) for i in range(0, 271, 5)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            line(img, x0, y0, x1, y1, P["sky"], 2)
    # oppidum on its hill
    draw_e = lambda rx, ry, col: poly(img, [(cx + rx * math.cos(u / 20 * 6.283),
                                             cy + ry * math.sin(u / 20 * 6.283))
                                            for u in range(20)], col)
    draw_e(30, 20, P["dsand"])
    draw_e(26, 16, P["sand"])
    for i in range(7):
        hx = cx - 20 + (i % 4) * 12
        hy = cy - 6 + (i // 4) * 10
        poly(img, [(hx - 3, hy + 2), (hx + 3, hy + 2), (hx, hy - 3)],
             P["brown"])
    rnd = random.Random(5)
    for i in range(24):
        ang = rnd.random() * 6.283
        rr = rnd.random()
        x = cx + math.cos(ang) * 22 * rr
        y = cy + math.sin(ang) * 13 * rr
        img.putpixel((int(x), int(y)), P["green"] if i % 2 else P["orange"])
    tag(img, "ALESIA, 52 BC", t, 0.1)
    t_tr = ctx.at("trapped")
    lbl(img, cx, cy + 26, "~80,000 GAULS", P["white"], P["green"], None,
        t=prog(t, t_tr, 0.3))

    def ring(rx, ry, p, col):
        n = 72
        pts = [(cx + rx * math.cos(-math.pi / 2 + u / n * 6.283),
                cy + ry * math.sin(-math.pi / 2 + u / n * 6.283))
               for u in range(n + 1)]
        route(img, pts, p, col, dash=4, gap=1, head=False, t=0, width=2)
        if 0 < p < 1:
            k = int(p * n)
            figure(img, pts[k][0], pts[k][1] + 6, "legion")

    t_two = ctx.at("two")
    t_in = ctx.at("in")
    t_out = ctx.at("out")
    ring(52, 40, ease(prog(t, t_two - 0.2, max(0.4, t_in - t_two + 0.4))),
         P["red"])
    if t > t_in - 0.2:
        lbl(img, cx, cy - 46, "INNER WALL ~16 KM", P["white"], P["wine"], None,
            t=prog(t, t_in - 0.2, 0.3))
    ring(100, 84, ease(prog(t, t_in, max(0.5, t_out - t_in + 0.5))), P["red"])
    if t > t_out - 0.2:
        lbl(img, cx, 14, "OUTER WALL ~21 KM", P["white"], P["wine"], None,
            t=prog(t, t_out - 0.2, 0.3))
        # relief army pushing in from outside
        for i, (sx, sy) in enumerate(((10, 30), (258, 40), (20, 200),
                                      (250, 196), (135, 214))):
            ph = prog(t, t_out + i * 0.1, 0.8)
            bounce = math.sin(max(0, t - t_out - 0.8) * 6) * 2 if ph >= 1 else 0
            ang = math.atan2(sy - cy, sx - cx)
            ex = cx + math.cos(ang) * 112
            ey = cy + math.sin(ang) * 96
            x = lerp(sx, ex, ph) + bounce
            y = lerp(sy, ey, ph)
            for k in range(5):
                figure(img, x + (k - 2) * 4, y + (k % 2) * 3, "gaul",
                       facing=1 if sx < cx else -1, walk=t * 2 + k * 0.2)
        lbl(img, 46, 190, "RELIEF ARMY", P["white"], P["green"], None,
            t=prog(t, t_out + 0.3, 0.3))
    t_s = ctx.at("surrendered")
    if t > t_s - 0.3:
        p = prog(t, t_s - 0.3, 0.35)
        darken(img, 0.55 * p)
        card(img, 101, 40, "verc", p, 2, label=False)
        lbl(img, 137, 34, "VERCINGETORIX", P["yellow"], P["ink"], None, t=p)
        stamp(img, 137, 128, "SURRENDERED", P["red"], prog(t, t_s, 0.4), 8)
    t_c = ctx.at("conquered")
    if t > t_c - 0.3:
        lbl(img, 137, 160, "GAUL CONQUERED", P["yellow"], P["ink"], P["gold"],
            "title", 8, t=prog(t, t_c - 0.3, 0.35), pad=4)


def scene_legions(img, t, ctx):
    vgrad(img, 0, 0, PW, PH, [P["ink"], P["dslate"], P["slate"]])
    card(img, 8, 6, "caesar", prog(t, 0.1, 0.3))
    t_r, t_p, t_l = ctx.at("rich"), ctx.at("popular"), ctx.at("legions")
    rows = [("WEALTH", t_r, P["gold"]), ("POPULARITY", t_p, P["lime"])]
    for i, (nm, tt, col) in enumerate(rows):
        y = 12 + i * 20
        if t > tt - 0.2:
            text(img, 88, y, nm, P["white"], "label", 8, spacing=0)
            bar(img, 88, y + 8, 170, 6, ease_out(prog(t, tt - 0.2, 0.7)), col,
                P["ink"], P["dslate"])
    if t > t_l - 0.3:
        text(img, 88, 52, "LOYAL LEGIONS", P["white"], "label", 8, spacing=0)
        n = int(clamp((t - t_l + 0.3) / 0.08, 0, 10))
        for i in range(n):
            EAGLE.blit(img, 88 + i * 17, 62)
    # the Senate trembles
    t_s = ctx.at("Senate")
    base = 212
    rect(img, 0, base - 2, PW, 8, P["marble"])
    sx, sy = shake(t, t_s, 1.5, 2)
    temple(img, 70 + sx, base - 2 + sy, w=130, h=100, cols=8)
    for i in range(7):
        x = 82 + i * 18
        jit = (int(t * 20) + i) % 2 if t > t_s else 0
        figure(img, x + jit, base - 2, "senator",
               facing=1 if i % 2 else -1, pose="raise" if t > t_s else None)
    if t > t_s:
        lbl(img, 135, 100, "THE SENATE", P["white"], P["red"], P["wine"],
            "title", 8, t=prog(t, t_s, 0.3))
        for i in range(4):
            lbl(img, 90 + i * 30, 120 + (i % 2) * 8, "!", P["yellow"], None,
                None, "title", 8, t=prog(t, t_s + 0.1 * i, 0.3),
                outline=P["ink"])


def scene_collapse(img, t, ctx):
    plum_bg(img, t)
    t_j, t_c = ctx.at("Julia"), ctx.at("Crassus")
    t_p = ctx.at("Pompey")
    broken = []
    if t > t_c + 0.6:
        broken += [("caesar", "crassus"), ("pompey", "crassus")]
    if t > t_p + 0.4:
        broken += [("caesar", "pompey")]
    tri_lines(img, t, 1.0, broken, col=P["dgold"])
    # Julia
    jg = t > t_j + 0.5
    card(img, 20, 10, "julia", 1.0, 1, gray=jg)
    if t > t_j:
        lbl(img, 38, 64, "DIED 54 BC", P["white"], P["ink"], None,
            t=prog(t, t_j + 0.3, 0.3))
        hx, hy = (TRI_C["caesar"][0] + TRI_C["pompey"][0]) / 2, \
                 (TRI_C["caesar"][1] + TRI_C["pompey"][1]) / 2
        (BROKEN_HEART if t > t_j + 0.5 else HEART).blit(
            img, hx, hy, scale=2, anchor="c")
    # Pompey slides toward the Senate
    px, py = TRI["pompey"]
    if t > t_p:
        f = ease(prog(t, t_p, 0.8))
        px = lerp(px, 6, f)
        py = lerp(py, 128, f)
        lbl(img, 120, 206, "-> CAESAR'S ENEMIES", P["white"], P["blue"], None,
            t=prog(t, t_p + 0.5, 0.3))
    card(img, int(px), int(py), "pompey", 1.0)
    card(img, *TRI["caesar"], "caesar", 1.0)
    cg = t > t_c + 0.6
    cxp, cyp = TRI["crassus"]
    card(img, cxp, cyp, "crassus", 1.0, gray=cg)
    if t > t_c:
        rnd = random.Random(9)
        for i in range(30):
            st = t_c + rnd.random() * 0.9
            ph = (t - st) / 0.4
            if 0 <= ph <= 1:
                x = cxp + 10 + rnd.random() * 60 - 30 * (1 - ph)
                y = cyp - 20 + ph * 60
                line(img, x, y, x + 3, y + 3, P["ink"])
                img.putpixel((int(x + 3), int(y + 3)), P["white"])
        if cg:
            SKULL.blit(img, cxp + 36, cyp + 30, scale=2, anchor="c")
        lbl(img, cxp + 36, 100, "KILLED AT CARRHAE", P["white"], P["red"],
            None, t=prog(t, ctx.at("Carrhae"), 0.3))
        lbl(img, cxp + 36, 202, "53 BC", P["yellow"], P["ink"], None,
            t=prog(t, ctx.at("53"), 0.3))
    if t > t_p + 0.4:
        mx = (TRI_C["caesar"][0] + 50) / 2
        flash(img, t, t_p + 0.4, 0.2, P["red"])


def year_collapse(t, ctx):
    return -54 + prog(t, ctx.at("53"), 0.4)


def senate_bg(img, t, tint=None):
    vgrad(img, 0, 0, PW, PH, [P["wine"], P["plum"], P["ink"]])
    for x in range(14, PW, 48):
        rect(img, x - 5, 0, 10, 170, P["marble"])
        line(img, x + 3, 0, x + 3, 170, P["stone"])
        rect(img, x - 7, 0, 14, 4, P["marble"])
        rect(img, x - 7, 166, 14, 4, P["marble"])
    rect(img, 0, 170, PW, 46, P["dstone"])
    for x in range(0, PW, 16):
        rect(img, x, 170 + (x // 16 % 2) * 23, 16, 23, P["stone"])


def scene_ultimatum(img, t, ctx):
    senate_bg(img, t)
    for row, yy in enumerate((190, 210)):
        for i in range(9):
            x = 12 + i * 30 + row * 15
            figure(img, x, yy, "senator", facing=1 if x < 135 else -1,
                   pose="raise" if (int(t * 2) + i + row) % 5 == 0 else None)
    t_pl = 0.2
    t_j = ctx.at("January")
    if t < t_j:
        textbox(img, 40, 30, 190, ["THE OPTIMATES' PLAN:",
                                   "1. STRIP CAESAR OF HIS ARMY",
                                   "2. PROSECUTE HIM",
                                   "3. END HIS CAREER"],
                t, start_col=P["yellow"], lh=10, t0=t_pl, cps=45)
    else:
        h = int(110 * ease_out(prog(t, t_j, 0.5)))
        rect(img, 50, 16, 170, h, P["marble"])
        frame(img, 50, 16, 170, h, P["dsand"])
        rect(img, 46, 12, 178, 6, P["dsand"])
        rect(img, 46, 14 + h, 178, 6, P["dsand"])
        lines = [("DECREE OF THE SENATE", P["wine"]), ("JANUARY 49 BC", P["slate"]),
                 ("", None), ("CAESAR MUST", P["ink"]),
                 ("DISBAND HIS LEGIONS", P["ink"]), ("- OR BE DECLARED -", P["red"]),
                 ("A PUBLIC ENEMY", P["red"])]
        for i, (ln, col) in enumerate(lines):
            yy = 24 + i * 12
            if yy + 6 < 16 + h and ln:
                text(img, 135, yy, ln, col, "label", 8, anchor="c", spacing=0)
        t_pe = ctx.at("public")
        if t > t_pe:
            stamp(img, 204, 30, "SPQR", P["red"], prog(t, t_pe, 0.35), 8)
    t_a = ctx.at("Antony")
    if t > t_a - 0.2:
        card(img, 4, 108, "antony", prog(t, t_a - 0.2, 0.35), 1,
             name="ANTONY")
        lbl(img, 72, 116, "TRIBUNE", P["white"], P["red"], None,
            t=prog(t, t_a, 0.3))
        stamp(img, 72, 136, "VETO!", P["yellow"], prog(t, ctx.at("vetoed"),
                                                        0.35), 8)
    t_f = ctx.at("fled")
    if t > t_f:
        x = lerp(40, 300, ease(prog(t, t_f, 1.4)))
        figure(img, x, 172, "general", walk=t * 3, scale=2)
        lbl(img, 210, 150, "-> TO CAESAR", P["white"], P["red"], None,
            t=prog(t, t_f + 0.2, 0.3))


def scene_rubicon(img, t, ctx):
    t_cr = ctx.at("crossed")
    t_al = ctx.at("Alea")
    river_scene(img, t, dawn=0.35, moon=False)
    # signs
    rect(img, 224, 160, 2, 16, P["dbrown"])
    rect(img, 212, 154, 28, 8, P["sand"])
    text(img, 226, 156, "ITALIA", P["dbrown"], "label", 8, anchor="c",
         spacing=0)
    t_r = ctx.at("Rubicon")
    if t < t_al - 0.3:
        lbl(img, 156, 122, "RUBICON", P["cyan"], P["ink"], None,
            t=prog(t, t_r, 0.3))
    # crossing
    hx = lerp(100, 236, ease(prog(t, t_cr - 0.2, 3.0)))
    hy = 198

    def wade_for(x, y):
        a, b = river_x(y)
        return (a + 2 < x < b - 2), (a, b)

    soldiers = []
    for row, yy in enumerate((168, 182, 200)):
        for i in range(5):
            x0 = 14 + i * 14 + (row % 2) * 7
            delay = 0.5 + (4 - i) * 0.12 + row * 0.2
            x = x0 + 130 * ease(prog(t, t_cr + delay, 3.4))
            soldiers.append((yy, x, row, i))
    for yy, x, row, i in sorted(soldiers):
        inw, _ = wade_for(x, yy)
        moving = t_cr + 0.5 < t < t_cr + 4.5
        figure(img, x, yy, "legion", walk=t * 1.8 + i * 0.3 if moving else None,
               wade=5 if inw else 0)
        if inw:
            splash(img, x, yy - 4, t, i + row * 5)
    inw, _ = wade_for(hx, hy)
    horse_rider(img, hx, hy, t * (1 if t > t_cr else 0.3), rider="general",
                wade=7 if inw else 0)
    if inw:
        splash(img, hx, hy - 6, t, 99)
    # eagle of the XIII
    t_13 = ctx.at("Thirteenth")
    ex = 60 + 130 * ease(prog(t, t_cr + 0.6, 3.4))
    if t > t_13 - 0.2:
        EAGLE.blit(img, ex, 162, anchor="bc")
        lbl(img, ex, 136, "LEGIO XIII", P["yellow"], P["ink"], None,
            t=prog(t, t_13 - 0.2, 0.3))
    t_law = ctx.at("forbade")
    if t_law - 0.2 < t < t_al:
        rect(img, 30, 14, 210, 40, P["ink"])
        frame(img, 30, 14, 210, 40, P["red"])
        text(img, 135, 19, "ROMAN LAW", P["red"], "label", 8, anchor="c",
             spacing=0)
        text(img, 135, 30, typed("NO GENERAL MAY LEAD AN ARMY", t, t_law),
             P["white"], "label", 8, anchor="c", spacing=0)
        text(img, 135, 40, typed("INTO ITALY. PENALTY: DEATH.", t, t_law + 0.9),
             P["white"], "label", 8, anchor="c", spacing=0)
    if t > t_al - 0.3:
        p = prog(t, t_al - 0.3, 0.4)
        darken(img, 0.6 * p)
        # tumbling die
        fall = ease_out(prog(t, t_al - 0.3, 0.8))
        dy = lerp(-20, 64, fall)
        face = 6 if fall >= 1 else 1 + int(t * 14) % 6
        die_face(img, 135, dy, face, scale=3)
        lbl(img, 135, 110, "ALEA IACTA EST", P["yellow"], None, None, "title",
            16, t=prog(t, t_al, 0.4), outline=P["ink"])
        t_d = ctx.at("die")
        lbl(img, 135, 132, "THE DIE IS CAST", P["white"], P["red"], P["wine"],
            "title", 8, t=prog(t, t_d - 0.1, 0.4), pad=3)
        lbl(img, 135, 150, "10 JANUARY 49 BC", P["silver"], None, None,
            t=prog(t, t_d + 0.6, 0.3))
        for i in range(6):
            sparkle(img, 40 + i * 38, 96 + (i % 2) * 44, t, i)



# ---------------------------------------------------------------- civil war

ITALY_VIEW = geo.View.centered(14.6, 42.2, 25)


def scene_italy(img, t, ctx):
    v = ITALY_VIEW
    m = map_base(v, t, ("po", "rubicon"))
    comp(img, m, (0, 0))
    P_ = {k: place(v, k) for k in ("rubicon", "ariminum", "rome", "corfinium",
                                   "brundisium", "dyrrhachium")}
    pin(img, *P_["rome"], P["yellow"], prog(t, 0.2, 0.4), "ROMA", below=True)
    pin(img, *P_["rubicon"], P["cyan"], prog(t, 0.3, 0.4), "RUBICON")
    t_bo = ctx.at("boasted")
    t_fo = ctx.at("foot")
    t_fl = ctx.at("fled")
    t_gr = ctx.at("Greece")
    t_mo = ctx.at("months")
    t_pa = ctx.at("pardoning")
    # Caesar's march down the Adriatic coast
    c_pts = [P_["rubicon"], P_["ariminum"], v.xy(13.5, 43.6), P_["corfinium"],
             v.xy(15.5, 41.5), P_["brundisium"]]
    route(img, c_pts, ease(prog(t, 0.5, t_mo - 0.2)), P["red"], t=t, width=2)
    # Pompey flees Rome -> Brundisium -> Greece
    if t > t_fl - 0.2:
        p_pts = [P_["rome"], v.xy(14.8, 41.1), v.xy(16.5, 40.9),
                 P_["brundisium"]]
        route(img, p_pts, ease(prog(t, t_fl - 0.2, 1.0)), P["sky"], t=t)
    if t > t_gr - 0.4:
        a, b = P_["brundisium"], P_["dyrrhachium"]
        pts = bezier(a, ((a[0] + b[0]) / 2, a[1] - 20), b)
        hd = route(img, pts, ease(prog(t, t_gr - 0.4, 1.2)), P["sky"], t=t)
        if hd:
            ship(img, hd[0], hd[1] + 4, t, sail=P["sky"], oars=False)
        lbl(img, b[0] - 4, b[1] - 34, "POMPEY -> GREECE", P["white"],
            P["blue"], None, t=prog(t, t_gr, 0.3))
    # the foot stamp joke
    if t_bo - 0.2 < t < t_fl + 0.3:
        card(img, 6, 120, "pompey", prog(t, t_bo - 0.2, 0.35), 1)
        if t > t_fo - 0.3:
            k = prog(t, t_fo - 0.3, 0.3)
            lbl(img, 84, 132, "*STOMP*", P["ink"], P["white"], P["ink"],
                "title", 8, t=k, pad=3)
            lbl(img, 84, 150, "LEGIONS: 0", P["white"], P["red"], None,
                t=prog(t, t_fo + 0.4, 0.3))
    # day counter
    days = int(1 + 64 * clamp(prog(t, 0.5, t_mo - 0.2)))
    rect(img, 182, 4, 84, 24, P["ink"])
    frame(img, 182, 4, 84, 24, P["dgold"])
    text(img, 224, 8, "CAESAR'S MARCH", P["silver"], "label", 8, anchor="c",
         spacing=0)
    text(img, 224, 17, f"DAY {days}", P["yellow"], "title", 8, anchor="c")
    if t > t_pa - 0.2:
        cx, cy = P_["corfinium"]
        LAUREL.blit(img, cx, cy - 18, scale=2, anchor="c")
        lbl(img, cx - 2, cy - 34, "CLEMENCY", P["ink"], P["lime"], None,
            t=prog(t, t_pa - 0.2, 0.3))
        lbl(img, 135, 204, "ENEMIES PARDONED, NOT KILLED", P["white"], P["ink"],
            P["lime"], t=prog(t, t_pa, 0.3))


SPAIN_VIEW = geo.View.centered(4.5, 42.4, 12.5)


def scene_spain(img, t, ctx):
    v = SPAIN_VIEW
    comp(img, map_base(v, t, ("rhone", "ebro", "po"), pyrenees=True), (0, 0))
    pts = [place(v, "rome"), place(v, "ariminum"), v.xy(9.0, 44.5),
           v.xy(7.3, 43.7), place(v, "massilia"), v.xy(3.1, 43.2),
           v.xy(2.4, 42.3), place(v, "ilerda")]
    t_sp = ctx.at("Spain")
    route(img, pts, ease(prog(t, 0.2, 2.6)), P["red"], t=t, width=2)
    pin(img, *place(v, "rome"), P["yellow"], prog(t, 0.1, 0.4), "ROMA",
        below=True)
    pin(img, *place(v, "massilia"), P["sky"], prog(t, 1.4, 0.4),
        "MASSILIA (SIEGE)", below=False)
    ix, iy = place(v, "ilerda")
    t_su = ctx.at("surrendered")
    for i in range(4):
        x = ix - 18 + (i % 2) * 8
        y = iy + 4 + (i // 2) * 8
        cohort(img, x, y, 7, 5, P["white"] if t > t_su else P["blue"],
               P["slate"] if t > t_su else P["navy"])
    pin(img, ix, iy, P["red"], prog(t, 2.6, 0.4), "ILERDA, AUG 49 BC",
        below=True)
    lbl(img, 135, 9, "SPAIN", P["yellow"], None, None, "title", 8,
        outline=P["ink"], t=prog(t, t_sp, 0.3))
    t_a = ctx.at("army")
    t_th = ctx.at("then")
    if t > t_a - 0.2:
        rect(img, 30, 150, 210, 40, P["ink"])
        frame(img, 30, 150, 210, 40, P["dgold"])
        text(img, 135, 155, typed('"FIRST, AN ARMY WITHOUT A LEADER...', t,
                                  t_a - 0.2, 26), P["white"], "label", 8,
             anchor="c", spacing=0)
        text(img, 135, 166, typed('...THEN A LEADER WITHOUT AN ARMY."', t,
                                  t_th, 26), P["yellow"], "label", 8,
             anchor="c", spacing=0)
        text(img, 135, 178, "- CAESAR", P["silver"], "label", 8, anchor="c",
             spacing=0) if t > t_th + 0.8 else None
    if t > t_su:
        lbl(img, ix + 4, iy - 30, "SURRENDER!", P["ink"], P["white"], P["ink"],
            "title", 8, t=prog(t, t_su, 0.3))


GREECE_VIEW = geo.View.centered(20.4, 40.4, 30)


def scene_dyrrhachium(img, t, ctx):
    v = GREECE_VIEW
    comp(img, map_base(v, t, (), alps=False), (0, 0))
    bx, by = place(v, "brundisium")
    dx, dy = place(v, "dyrrhachium")
    px_, py_ = place(v, "pharsalus")
    t_b = ctx.at("beat")
    # crossing in winter, Jan 48
    land = v.xy(19.5, 40.6)
    pts = bezier((bx, by), ((bx + land[0]) / 2, by + 16), land)
    hd = route(img, pts, ease(prog(t, 0.1, 1.2)), P["red"], t=t)
    if hd and t < 1.6:
        ship(img, hd[0], hd[1] + 4, t, sail=P["red"], oars=False)
    if t < t_b:
        lbl(img, (bx + land[0]) / 2, by + 34, "CAESAR CROSSES, JAN 48",
            P["white"], P["red"], None, t=prog(t, 0.4, 0.3))
    pin(img, dx, dy, P["sky"], prog(t, 0.3, 0.4), "DYRRHACHIUM")
    t_b = ctx.at("beat")
    # siege lines around Pompey's camp
    cx, cy = dx + 4, dy + 10
    n = 30
    arc = [(cx + 24 * math.cos(a), cy + 20 * math.sin(a))
           for a in (math.radians(-80 + 200 * i / n) for i in range(n + 1))]
    route(img, arc, ease(prog(t, 0.8, t_b - 0.8)), P["red"], head=False,
          dash=3, gap=1, width=2)
    for i in range(3):
        cohort(img, cx - 6 + (i % 2) * 6, cy - 4 + i * 4, 6, 4, P["blue"],
               P["navy"])
    if t > t_b:
        a = (cx + 8, cy + 18)
        b = (cx + 40, cy + 46)
        route(img, [a, b], ease_out(prog(t, t_b, 0.5)), P["sky"], t=t, width=2)
        k = prog(t, t_b + 0.3, 0.3)
        if k > 0:
            for d in range(-4, 5):
                img.putpixel((int(cx + 30 + d), int(cy + 26 + d)), P["red"])
                img.putpixel((int(cx + 30 + d), int(cy + 26 - d)), P["red"])
            lbl(img, cx + 48, cy + 20, "CAESAR BEATEN", P["white"], P["red"],
                None, t=k)
    t_e = ctx.at("enemy")
    if t > t_e - 0.2:
        lines = ['"THE ENEMY WOULD HAVE WON',
                 'TODAY, IF THEY HAD A COMMANDER',
                 'WHO KNEW HOW TO WIN."', '- CAESAR, VIA PLUTARCH']
        textbox(img, 6, 164, 172, lines, t, t0=t_e - 0.2, cps=40, lh=9)
    t_f = ctx.at("finish")
    if t > t_f:
        route(img, [(cx, cy), v.xy(21.0, 40.0), (px_, py_)],
              ease(prog(t, t_f, 1.6)), P["red"], t=t)
        pin(img, px_, py_, P["red"], prog(t, t_f + 1.2, 0.4), "THESSALY",
            below=False)


def scene_pharsalus(img, t, ctx):
    import numpy as np
    rect(img, 0, 0, PW, PH, P["grass"])
    m = dither_mask(PW, PH, 0.2)
    a = np.array(img)
    a[m] = (*P["dgrass"], 255)
    img.paste(Image.fromarray(a, "RGBA"))
    # river Enipeus on the left
    for y in range(0, PH, 2):
        x = 10 + math.sin(y / 18) * 4
        rect(img, x, y, 6, 2, P["blue"])
        if (y + int(t * 10)) % 12 == 0:
            img.putpixel((int(x + 2), y), P["cyan"])
    # camps
    for i in range(4):
        TENT.blit(img, 100 + i * 14, 32)
    FLAG_R.blit(img, 156, 26, tint=P["blue"]) if True else None
    for i in range(3):
        TENT.blit(img, 110 + i * 14, 200)
    t_ph = ctx.at("Pharsalus")
    t_22 = ctx.at("22,000")
    t_45 = ctx.at("45,000")
    t_cav = ctx.at("cavalry")
    t_hid = ctx.at("hidden")
    t_br = ctx.at("broke")
    t_col = ctx.at("collapsed")
    # Pompey's infantry
    adv = ease(prog(t, t_col - 0.8, 1.0)) * 18
    rout = prog(t, t_col - 0.2, 1.2)
    rnd = random.Random(3)
    for ln in range(3):
        for i in range(10):
            x = 26 + i * 17
            y = 66 + ln * 12
            if rout > 0:
                for k in range(5):
                    sx = x + rnd.random() * 14
                    sy = y - rout * (30 + rnd.random() * 50)
                    sx += (rnd.random() - 0.5) * rout * 40
                    if 0 <= sx < PW and 0 <= sy < PH:
                        rect(img, sx, sy, 2, 2, P["blue"])
            else:
                cohort(img, x, y, 14, 8, P["blue"], P["navy"], seed=i + ln)
    # Pompey's cavalry: 7 squadrons on his left (viewer's right)
    for i in range(7):
        x0 = 200 + (i % 3) * 22
        y0 = 58 + (i // 3) * 13
        charge = ease(prog(t, t_cav, 1.4))
        x1 = 206 + (i % 3) * 20
        y1 = 128 + (i // 3) * 12
        x = lerp(x0, x1, charge)
        y = lerp(y0, y1, charge)
        flee = ease_out(prog(t, t_br, 1.2))
        x = lerp(x, 280 + i * 6, flee)
        y = lerp(y, -30 + i * 8, flee)
        if t > t_hid + 0.4 and flee < 0.1:
            x += math.sin(t * 30 + i) * 1
        cohort(img, x, y, 18, 9, P["navy"], P["ink"], seed=i, cav=True)
    # Caesar's infantry (three lines)
    for ln in range(3):
        for i in range(8):
            x = 40 + i * 19
            y = 140 + ln * 12 - adv * (1 if ln < 2 else 0.5)
            cohort(img, x, y, 15, 8, P["red"], P["wine"], seed=i + ln)
    # Caesar's small cavalry, pushed back
    back = ease(prog(t, t_cav + 0.6, 0.8)) * 26
    cohort(img, 210, 150 + back, 16, 8, P["orange"], P["wine"], cav=True)
    # hidden fourth line
    rev = prog(t, t_hid, 0.3)
    push = ease(prog(t, t_hid + 0.3, 0.9))
    for i in range(6):
        x = 196 + (i % 3) * 22
        y = 180 + (i // 3) * 11 - push * 26
        if rev <= 0:
            if t > t_cav:
                frame(img, x, y, 15, 8, P["wine"])
        else:
            cohort(img, x, y, 15, 8, P["red"], P["yellow"], seed=i)
    if t > t_hid:
        flash(img, t, t_hid, 0.15, P["yellow"])
        lbl(img, 214, 206, "HIDDEN 4TH LINE", P["ink"], P["yellow"], None,
            t=prog(t, t_hid, 0.3))
        if t_hid + 0.5 < t < t_br + 0.6:
            rnd2 = random.Random(int(t * 12))
            for k in range(10):
                x = 200 + rnd2.random() * 66
                y = 140 + rnd2.random() * 24
                img.putpixel((int(x), int(y)), P["white"] if k % 2 else
                             P["yellow"])
    if t > t_cav:
        lbl(img, 230, 46, "7,000 CAVALRY", P["white"], P["navy"], None,
            t=prog(t, t_cav, 0.3)) if t < t_br else None
    # title + army sizes
    if t < t_22:
        lbl(img, 135, 112, "PHARSALUS", P["yellow"], P["ink"], P["gold"],
            "title", 16, t=prog(t, t_ph - 0.2, 0.35), pad=4)
        lbl(img, 135, 132, "9 AUGUST 48 BC", P["white"], P["ink"], None,
            t=prog(t, t_ph + 0.2, 0.3))
    else:
        rect(img, 26, 2, 218, 24, P["ink"])
        frame(img, 26, 2, 218, 24, P["dgold"])
        text(img, 30, 6, "CAESAR", P["red"], "label", 8, spacing=0)
        bar(img, 70, 6, 120, 5, (22 / 45) * ease_out(prog(t, t_22, 0.5)),
            P["red"], P["dslate"])
        text(img, 194, 6, "22,000", P["white"], "label", 8, spacing=0)
        if t > t_45 - 0.1:
            text(img, 30, 16, "POMPEY", P["sky"], "label", 8, spacing=0)
            bar(img, 70, 16, 120, 5, ease_out(prog(t, t_45 - 0.1, 0.5)),
                P["blue"], P["dslate"])
            text(img, 194, 16, "45,000", P["white"], "label", 8, spacing=0)
    if t > t_col:
        lbl(img, 135, 112, "DECISIVE VICTORY", P["yellow"], P["ink"],
            P["gold"], "title", 8, t=prog(t, t_col + 0.3, 0.35), pad=4)


def scene_egypt(img, t, ctx):
    sky(img, [P["orange"], P["yellow"], P["sand"]], 130)
    circle(img, 60, 120, 14, P["white"])
    rect(img, 0, 128, PW, 88, P["teal"])
    for k in range(30):
        yy = 130 + (k * 29) % 86
        xx = (k * 47 + t * 10) % (PW + 20) - 10
        line(img, xx, yy, xx + 5, yy, P["cyan"])
    poly(img, [(150, 216), (190, 140), (270, 132), (270, 216)], P["sand"])
    poly(img, [(150, 216), (190, 140), (196, 140), (160, 216)], P["dsand"])
    # Egyptian pylon / fort at Pelusium
    rect(img, 226, 96, 34, 40, P["dsand"])
    poly(img, [(222, 136), (230, 92), (256, 92), (264, 136)], P["sand"])
    rect(img, 238, 116, 10, 20, P["dbrown"])
    for i in range(3):
        line(img, 228, 100 + i * 4, 258, 100 + i * 4, P["dsand"])
    palm(img, 204, 160, 28, t)
    palm(img, 214, 150, 22, t + 1)
    for i in range(4):
        figure(img, 200 + i * 14, 182 + (i % 2) * 8, "egypt", facing=-1)
    tag(img, "PELUSIUM, EGYPT, 28 SEP 48 BC", t, 0.1)
    t_s = ctx.at("stabbed")
    t_c = ctx.at("Caesar")
    t_h = ctx.at("head")
    t_w = ctx.at("wept")
    card(img, 214, 16, "ptolemy", prog(t, ctx.at("boy"), 0.35), 1,
         label=False)
    lbl(img, 232, 60, "PTOLEMY XIII", P["white"], P["ink"], None,
        t=prog(t, ctx.at("boy") + 0.2, 0.3))
    lbl(img, 232, 69, "AGE ~13", P["silver"], P["ink"], None,
        t=prog(t, ctx.at("boy") + 0.4, 0.3))
    bx = lerp(30, 150, ease_out(prog(t, 0.1, t_s - 0.2)))
    fell = t > t_s + 0.2
    people = [("pompey", -4, "fall" if fell else None),
              ("egypt", 6, "stab" if t > t_s - 0.1 else None)]
    small_boat(img, bx, 166, t, people=people)
    if t_s < t < t_h - 0.4:
        flash(img, t, t_s, 0.12, P["red"])
        DAGGER.blit(img, bx + 6, 136, scale=2)
        lbl(img, bx - 10, 124, "POMPEY MURDERED", P["white"], P["red"], None,
            t=prog(t, t_s + 0.2, 0.3))
    if t > t_c - 0.2:
        x = lerp(-50, 50, ease_out(prog(t, t_c - 0.2, 1.2)))
        ship(img, x, 196, t, sail=P["red"], flag=P["gold"], scale=2)
    if t > t_h - 0.4:
        p = prog(t, t_h - 0.4, 0.4)
        darken(img, 0.6 * p)
        card(img, 40, 40, "caesar", p, 2, mood="sad" if t > t_w else None)
        # the offering: a covered basket
        k = prog(t, t_h - 0.2, 0.4)
        if k > 0:
            figure(img, 190, 150, "egypt", facing=-1, scale=2)
            rect(img, 150, 120, 22, 12, P["dsand"])
            rect(img, 148, 116, 26, 5, P["marble"])
            lbl(img, 162, 104, "POMPEY'S HEAD", P["white"], P["ink"], P["red"],
                t=k)
            lbl(img, 162, 142, "+ HIS SIGNET RING", P["yellow"], P["ink"],
                None, t=prog(t, t_h + 0.3, 0.3))
        if t > t_w:
            lbl(img, 76, 30, "CAESAR WEPT", P["cyan"], P["ink"], None,
                t=prog(t, t_w, 0.3))
            for i in range(3):
                ph = (t * 1.5 + i / 3) % 1.0
                img.putpixel((40 + 2 + 41, int(40 + 2 + 26 + ph * 14)),
                             P["cyan"])


MED_VIEW = geo.View(-10.0, 56.4, 7.73)


def scene_epilogue(img, t, ctx):
    v = MED_VIEW
    comp(img, map_base(v, t, ("nile", "rhine", "po")), (0, 0))
    stops = [("alexandria", "Egypt", "ALEXANDRIA 48-47", P["yellow"]),
             ("zela", "Zela", "ZELA 47", P["red"]),
             ("thapsus", "Thapsus", "THAPSUS 46", P["red"]),
             ("munda", "Munda", "MUNDA 45", P["red"])]
    prev = place(v, "pharsalus")
    for i, (pl, w, lab, col) in enumerate(stops):
        tw = ctx.at(w)
        xy = place(v, pl)
        if t > tw - 0.5:
            route(img, [prev, xy], ease(prog(t, tw - 0.5, 0.5)), P["red"], t=t)
        pin(img, *xy, col, prog(t, tw, 0.4), lab, below=pl in ("alexandria",
                                                              "thapsus"),
            dx=-14 if pl == "zela" else 0)
        prev = xy
    t_e = ctx.at("Cleopatra")
    if t > t_e - 0.2:
        card(img, 214, 148, "cleo", prog(t, t_e - 0.2, 0.35), 1,
             label=False)
        lbl(img, 232, 192, "CLEOPATRA", P["white"], P["purple"], None,
            t=prog(t, t_e, 0.3))
    t_z = ctx.at("came")
    if t > t_z - 0.2 and t < ctx.at("dictator") - 0.4:
        lbl(img, 190, 66, "VENI, VIDI, VICI", P["yellow"], P["ink"], P["gold"],
            "title", 8, t=prog(t, t_z - 0.2, 0.35), pad=3)
    t_d = ctx.at("dictator")
    if t > t_d - 0.4:
        p = prog(t, t_d - 0.4, 0.4)
        darken(img, 0.6 * p)
        LAUREL.blit(img, 135, 26, scale=3, anchor="c") if p > 0.5 else None
        card(img, 101, 42, "caesar", p, 2)
        lbl(img, 137, 140, "DICTATOR PERPETUO", P["yellow"], P["ink"],
            P["gold"], "title", 8, t=prog(t, t_d, 0.35), pad=4)
        lbl(img, 137, 158, "DICTATOR FOR LIFE, 44 BC", P["white"], P["red"],
            None, t=prog(t, t_d + 0.3, 0.3))


def year_epilogue(t, ctx):
    y = -48
    for w, yr in (("Zela", -47), ("Thapsus", -46), ("Munda", -45),
                  ("dictator", -44)):
        y += prog(t, ctx.at(w) - 0.2, 0.4) * 1
    return y


def scene_ides(img, t, ctx):
    vgrad(img, 0, 0, PW, PH, [P["dslate"], P["plum"], P["ink"]])
    for x in range(20, PW, 46):
        rect(img, x - 6, 0, 12, 160, P["marble"])
        line(img, x + 4, 0, x + 4, 160, P["stone"])
    rect(img, 0, 160, PW, 56, P["dstone"])
    for x in range(0, PW, 18):
        for y in range(160, PH, 14):
            if (x // 18 + y // 14) % 2:
                rect(img, x, y, 18, 14, P["stone"])
    # statue of Pompey
    rect(img, 210, 150, 40, 30, P["marble"])
    rect(img, 206, 148, 48, 4, P["white"])
    figure(img, 230, 148, "pompey", facing=-1, scale=3, tint=P["marble"])
    lbl(img, 230, 186, "POMPEY", P["dstone"], P["marble"], None)
    t_s = ctx.at("stabbed")
    t_23 = ctx.at("23")
    t_f = ctx.at("foot")
    cx = lerp(120, 186, ease(prog(t, t_23 + 0.3, t_f - t_23)))
    # conspirators close in
    close = ease(prog(t, ctx.at("senators") - 0.3, 1.0))
    for i in range(6):
        side = -1 if i < 3 else 1
        k = i % 3
        x0 = 135 + side * (150 + k * 20)
        x1 = cx + side * (22 + k * 16) - (8 if side > 0 else 0)
        x = lerp(x0, x1, close)
        stab = t > t_s and int(t * 8 + i) % 2 == 0
        figure(img, x, 198 + (k % 2) * 6, "senator", facing=-side,
               pose="stab" if stab else None, scale=2)
    fallen = t > t_f
    if not fallen:
        figure(img, cx, 196, "dictator", facing=1, scale=2)
    else:
        figure(img, 196, 198, "dictator", facing=1, scale=2, pose="fall")
    if t > t_s:
        if int(t * 8) % 2 == 0 and t < t_f:
            tint_overlay(img, P["red"], 0.15)
        n = int(1 + 22 * clamp(prog(t, t_s, t_23 - t_s + 0.3)))
        rect(img, 6, 22, 92, 26, P["ink"])
        frame(img, 6, 22, 92, 26, P["red"])
        text(img, 52, 26, "STAB WOUNDS", P["silver"], "label", 8, anchor="c",
             spacing=0)
        text(img, 52, 36, str(n), P["red"], "title", 8, anchor="c")
        lbl(img, 160, 60, "BRUTUS & CASSIUS", P["white"], P["ink"], None,
            t=prog(t, t_s + 0.3, 0.3))
        lbl(img, 160, 70, "+ ~60 CONSPIRATORS", P["silver"], P["ink"], None,
            t=prog(t, t_s + 0.5, 0.3))
    tag(img, "IDES OF MARCH, 15 MARCH 44 BC", t, 0.1)
    if not fallen:
        lbl(img, cx, 146, "CAESAR", P["yellow"], P["ink"], None,
            t=prog(t, 0.3, 0.3))
    if t > t_f:
        tint_overlay(img, P["wine"], 0.35 * prog(t, t_f, 0.6))
        lbl(img, 135, 112, "AT THE FEET OF POMPEY", P["white"], P["ink"],
            P["red"], t=prog(t, t_f + 0.2, 0.35))


def scene_outro(img, t, ctx):
    vgrad(img, 0, 0, PW, PH, [P["black"], P["night"], P["navy"]])
    stars(img, PW, PH, t, 60, seed=3)
    t1, t2, t3 = ctx.at("One"), ctx.at("Five"), ctx.at("Republic")
    tiles = [(t1, "1", "RIVER CROSSED", "RUBICON, 49 BC", P["sky"]),
             (t2, "5", "YEARS OF CIVIL WAR", "49 - 45 BC", P["red"]),
             (t3, "500", "YEAR-OLD REPUBLIC", "ENDED: EMPIRE, 27 BC", P["gold"])]
    end_t = ctx.dur - 2.4
    for i, (tt, big, l1, l2, col) in enumerate(tiles):
        if t < tt - 0.1 or t > end_t:
            continue
        y = 16 + i * 64
        k = ease_out(prog(t, tt - 0.1, 0.35))
        x = lerp(-260, 10, k)
        rect(img, x, y, 250, 54, P["ink"])
        frame(img, x, y, 250, 54, col)
        text(img, x + 40, y + 14, big, col, "title", 16, anchor="c")
        text(img, x + 80, y + 14, l1, P["white"], "title", 8)
        text(img, x + 80, y + 30, l2, P["silver"], "label", 8, spacing=0)
    if t > end_t:
        p = prog(t, end_t, 0.4)
        die_face(img, 135, 40, 6, scale=3)
        lbl(img, 135, 86, "ALEA IACTA EST", P["yellow"], None, None, "title",
            16, t=p, outline=P["ink"])
        lbl(img, 135, 112, "THE DIE IS CAST", P["white"], P["red"], P["wine"],
            "title", 8, t=prog(t, end_t + 0.3, 0.35), pad=3)
        lbl(img, 135, 150, "FOLLOW FOR MORE", P["white"], None, None, "title",
            8, t=prog(t, end_t + 0.8, 0.35))
        lbl(img, 135, 164, "PIXEL HISTORY", P["yellow"], None, None, "title",
            8, t=prog(t, end_t + 1.0, 0.35))
        for i in range(6):
            sparkle(img, 30 + i * 42, 60 + (i % 2) * 70, t, i)
