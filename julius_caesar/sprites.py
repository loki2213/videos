"""Procedural pixel-art sprites: figures, horses, ships, buildings, icons and
profile portraits. Everything is drawn with hard-edged primitives so the
result stays pixel-crisp."""
import math

from PIL import Image, ImageDraw

from pixel import P, circle, comp, line, poly, rect, spr

# ---------------------------------------------------------------- figures

OUTFITS = {
    # tunic, armour, helmet, crest, shield, cloak
    "legion": dict(tunic=P["red"], armor=P["silver"], helm=P["silver"],
                   crest=P["red"], shield=P["red"], trim=P["gold"]),
    "pompeian": dict(tunic=P["blue"], armor=P["silver"], helm=P["silver"],
                     crest=P["navy"], shield=P["blue"], trim=P["white"]),
    "gaul": dict(tunic=P["green"], pants=P["blue"], hair=P["orange"],
                 shield=P["teal"], trim=P["yellow"]),
    "pirate": dict(tunic=P["slate"], pants=P["dbrown"], hair=P["ink"],
                   band=P["red"]),
    "senator": dict(toga=P["white"], shade=P["silver"], stripe=P["purple"],
                    hair=P["silver"]),
    "caesar": dict(toga=P["white"], shade=P["silver"], stripe=P["purple"],
                   hair=P["brown"], laurel=P["green"]),
    "dictator": dict(toga=P["purple"], shade=P["plum"], stripe=P["gold"],
                     hair=P["brown"], laurel=P["lime"]),
    "general": dict(tunic=P["red"], armor=P["gold"], cloak=P["wine"],
                    hair=P["brown"], laurel=P["green"]),
    "pompey": dict(tunic=P["blue"], armor=P["gold"], cloak=P["navy"],
                   hair=P["dbrown"]),
    "egypt": dict(kilt=P["white"], hair=P["ink"], skin=P["tan"]),
    "civil": dict(tunic=P["dsand"], hair=P["dbrown"]),
}


def figure(img, x, y, kind="legion", facing=1, walk=None, pose=None,
           scale=1, skin=None, wade=0, tint=None):
    """Draw a ~9x18px figure with its feet at (x, y).

    walk: phase in cycles (float) or None for standing.
    pose: None, 'raise' (arm up), 'stab', 'point', 'fall' (lying down),
          'kneel'.
    wade: number of bottom rows hidden (standing in water).
    """
    o = OUTFITS[kind]
    sk = skin or o.get("skin", P["skin"])
    c = Image.new("RGBA", (22, 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    cx, fy = 10, 27   # centre column, feet row

    def px(xx, yy, col):
        d.point((xx, yy), fill=col)

    def r(x0, y0, x1, y1, col):
        d.rectangle([x0, y0, x1, y1], fill=col)

    toga = "toga" in o
    sw = 0.0
    if walk is not None:
        sw = math.sin(walk * 2 * math.pi)
    # legs
    if pose == "kneel":
        r(cx - 1, fy - 3, cx + 2, fy - 2, P["dbrown"] if not toga else o["toga"])
        r(cx + 2, fy - 2, cx + 3, fy, sk)
        r(cx - 2, fy - 1, cx + 0, fy, P["dbrown"])
    elif not toga:
        legc = o.get("pants", sk)
        for k, side in ((1, -1), (-1, 1)):
            dx = int(round(1.6 * sw * k))
            x0 = cx + (0 if side < 0 else 1)
            d.line([x0, fy - 5, x0 + dx, fy - 1], fill=legc)
            d.line([x0 + dx, fy, x0 + dx + 1, fy], fill=P["dbrown"])
    else:
        dx = int(round(1.0 * sw))
        r(cx - 2, fy - 7, cx + 2, fy - 1, o["toga"])
        px(cx - 2 + max(0, dx), fy, P["dbrown"])
        px(cx + 1 + min(0, dx), fy, P["dbrown"])
        px(cx + 2 + min(0, dx), fy, P["dbrown"])
        d.line([cx - 1, fy - 6, cx - 1, fy - 1], fill=o["shade"])
    body_top = fy - 13 if pose != "kneel" else fy - 10
    # torso
    if toga:
        r(cx - 2, body_top, cx + 2, fy - 6, o["toga"])
        d.line([cx - 2, body_top, cx + 2, body_top + 4], fill=o["shade"])
        d.line([cx - 2, body_top + 1, cx - 2, fy - 6], fill=o["shade"])
        if o.get("stripe"):
            d.line([cx + 1, body_top, cx + 2, body_top], fill=o["stripe"])
            d.line([cx - 2, fy - 7, cx + 2, fy - 7], fill=o["stripe"])
    elif kind == "egypt":
        r(cx - 1, body_top, cx + 2, fy - 7, sk)
        r(cx - 2, fy - 7, cx + 2, fy - 5, o["kilt"])
    else:
        r(cx - 2, body_top, cx + 2, fy - 6, o["tunic"])
        if "armor" in o:
            r(cx - 2, body_top + 1, cx + 2, body_top + 4, o["armor"])
            d.line([cx - 2, body_top + 2, cx + 2, body_top + 2],
                   fill=P["slate"] if o["armor"] == P["silver"] else P["dgold"])
            d.line([cx - 2, body_top + 5, cx + 2, body_top + 5],
                   fill=P["dbrown"])
    # cloak
    if "cloak" in o:
        flap = int(round(1 + 1.0 * abs(sw)))
        poly_pts = [(cx - 2, body_top), (cx - 2 - flap, fy - 4),
                    (cx - 1, fy - 5), (cx - 1, body_top)]
        d.polygon(poly_pts, fill=o["cloak"])
    # head
    hy = body_top - 5
    r(cx - 1, hy, cx + 2, hy + 4, sk)
    px(cx + 3, hy + 2, sk)                          # nose
    px(cx + 1, hy + 1, P["ink"])                    # eye
    hair = o.get("hair")
    if "helm" in o:
        r(cx - 2, hy - 1, cx + 2, hy, o["helm"])
        r(cx - 2, hy + 1, cx - 1, hy + 3, o["helm"])
        d.line([cx - 1, hy - 2, cx + 1, hy - 2], fill=o["crest"])
        d.line([cx, hy - 3, cx, hy - 3], fill=o["crest"])
    elif kind == "egypt":
        r(cx - 2, hy - 1, cx + 1, hy, hair)
        r(cx - 2, hy + 1, cx - 1, hy + 4, hair)
    elif hair:
        r(cx - 2, hy - 1, cx + 1, hy, hair)
        r(cx - 2, hy + 1, cx - 2, hy + 2, hair)
        if kind == "gaul":
            r(cx - 3, hy, cx - 2, hy + 4, hair)
            px(cx + 2, hy + 3, hair)  # moustache
            px(cx + 3, hy + 3, hair)
        if o.get("laurel"):
            px(cx - 2, hy, o["laurel"])
            px(cx, hy - 1, o["laurel"])
            px(cx + 2, hy, o["laurel"])
    if kind == "pirate":
        r(cx - 2, hy - 1, cx + 2, hy, o["band"])
        px(cx - 3, hy + 1, o["band"])
    # arms + gear
    ay = body_top + 1
    if pose == "raise":
        d.line([cx + 2, ay, cx + 4, ay - 4], fill=sk)
    elif pose == "point":
        d.line([cx + 2, ay + 1, cx + 6, ay + 1], fill=sk)
    elif pose == "stab":
        d.line([cx + 2, ay, cx + 4, ay - 2], fill=sk)
        d.line([cx + 4, ay - 3, cx + 6, ay - 5], fill=P["white"])
    elif pose in (None, "kneel"):
        d.line([cx + 1, ay + 1, cx + 2, ay + 4], fill=sk)
    if "shield" in o and kind in ("legion", "pompeian"):
        sy = body_top
        r(cx + 2, sy, cx + 4, sy + 8, o["shield"])
        d.line([cx + 4, sy, cx + 4, sy + 8], fill=P["wine"]
               if kind == "legion" else P["navy"])
        px(cx + 3, sy + 4, o["trim"])
        # pilum held behind
        d.line([cx - 3, body_top - 9, cx - 3, fy - 2], fill=P["brown"])
        d.line([cx - 3, body_top - 11, cx - 3, body_top - 9], fill=P["white"])
    elif kind == "gaul":
        r(cx + 2, body_top, cx + 4, body_top + 7, o["shield"])
        px(cx + 3, body_top + 3, o["trim"])
        d.line([cx - 3, body_top - 8, cx - 3, fy - 2], fill=P["brown"])
        px(cx - 3, body_top - 9, P["white"])
    if wade:
        d.rectangle([0, fy - wade + 1, 21, 29], fill=(0, 0, 0, 0))
    if pose == "fall":
        c = c.rotate(-90 * facing, expand=True)
    if tint is not None:
        import numpy as np
        a = np.array(c)
        m = a[..., 3] > 0
        a[m, :3] = tint
        c = Image.fromarray(a, "RGBA")
    if facing < 0:
        c = c.transpose(Image.FLIP_LEFT_RIGHT)
    if scale != 1:
        c = c.resize((c.width * scale, c.height * scale), Image.NEAREST)
    if pose == "fall":
        comp(img, c, (int(x - c.width // 2),
                                int(y - c.height + 6 * scale)))
    else:
        comp(img, c, (int(x - 10 * scale), int(y - 27 * scale)))


def horse_rider(img, x, y, t=0.0, gallop=False, facing=1, rider="general",
                scale=1, horse=None, wade=0):
    """Horse with rider, feet at (x, y). t drives the leg cycle."""
    hc = horse or P["brown"]
    dk = P["dbrown"]
    c = Image.new("RGBA", (34, 34), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    gy = 31
    bob = int(round(math.sin(t * 2 * math.pi * (3 if gallop else 2)) * 0.6))
    by = gy - 12 + bob
    # legs
    ph = t * (3 if gallop else 2)
    for i, lx in enumerate((9, 12, 20, 23)):
        a = math.sin((ph + i * 0.25 + (0.5 if i % 2 else 0)) * 2 * math.pi)
        fx = lx + int(round(a * (2.5 if gallop else 1.5)))
        d.line([lx, by + 5, fx, gy - 1], fill=hc if i % 2 else dk)
        d.point((fx, gy), fill=P["ink"])
    # body
    d.ellipse([7, by - 1, 25, by + 6], fill=hc)
    d.line([9, by + 6, 23, by + 6], fill=dk)
    # neck/head
    d.polygon([(19, by + 2), (21, by - 4), (24, by - 7), (26, by - 6),
               (24, by - 1), (23, by + 3)], fill=hc)
    d.polygon([(24, by - 8), (27, by - 8), (31, by - 4), (31, by - 2),
               (28, by - 2), (25, by - 5)], fill=hc)
    d.point((25, by - 9), fill=hc)
    d.point((27, by - 6), fill=P["ink"])
    d.point((31, by - 2), fill=dk)
    d.line([20, by - 3, 24, by - 8], fill=dk)  # mane
    # tail
    sw = int(round(math.sin(t * 6) * 1))
    d.line([7, by, 4, by + 6 + sw], fill=dk)
    d.line([6, by + 1, 3, by + 7 + sw], fill=dk)
    # saddle cloth
    d.rectangle([13, by - 1, 18, by + 3], fill=P["red"] if rider != "pompey"
                else P["blue"])
    d.line([13, by + 3, 18, by + 3], fill=P["gold"])
    # rider
    o = OUTFITS[rider]
    rx, ry = 16, by - 1
    d.rectangle([rx - 1, ry - 7, rx + 2, ry - 1], fill=o["tunic"])
    d.rectangle([rx - 1, ry - 6, rx + 2, ry - 4], fill=o["armor"])
    d.line([rx + 1, ry, rx + 3, ry + 3], fill=P["skin"])
    cl = int(round(2 + abs(math.sin(t * 5)) * 2))
    d.polygon([(rx - 1, ry - 7), (rx - 3 - cl, ry - 1), (rx - 2 - cl, ry + 2),
               (rx, ry - 2)], fill=o["cloak"])
    d.rectangle([rx - 1, ry - 12, rx + 2, ry - 8], fill=P["skin"])
    d.point((rx + 3, ry - 10), fill=P["skin"])
    d.point((rx + 1, ry - 11), fill=P["ink"])
    d.rectangle([rx - 2, ry - 13, rx + 1, ry - 12], fill=o["hair"])
    d.point((rx - 2, ry - 11), fill=o["hair"])
    if o.get("laurel"):
        for p in ((rx - 2, ry - 12), (rx, ry - 13), (rx + 2, ry - 12)):
            d.point(p, fill=o["laurel"])
    d.line([rx + 2, ry - 6, rx + 5, ry - 4], fill=P["skin"])  # arm/rein
    if wade:
        d.rectangle([0, gy - wade + 1, 33, 33], fill=(0, 0, 0, 0))
    if facing < 0:
        c = c.transpose(Image.FLIP_LEFT_RIGHT)
    if scale != 1:
        c = c.resize((c.width * scale, c.height * scale), Image.NEAREST)
    comp(img, c, (int(x - 17 * scale), int(y - 31 * scale)))


# ---------------------------------------------------------------- ships

def ship(img, x, y, t=0.0, facing=1, sail=None, hull=None, oars=True,
         scale=1, flag=None):
    """Galley with water line at y, centred on x."""
    sail = sail or P["white"]
    hull = hull or P["brown"]
    c = Image.new("RGBA", (44, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    wl = 26
    bob = int(round(math.sin(t * 2.2) * 1))
    hy = wl - 4 + bob
    d.polygon([(4, hy), (40, hy), (36, hy + 5), (8, hy + 5)], fill=hull)
    d.line([4, hy, 1, hy - 4], fill=hull)          # stern
    d.line([40, hy, 43, hy - 2], fill=hull)        # prow ram
    d.line([8, hy + 1, 36, hy + 1], fill=P["dbrown"])
    for i in range(8, 38, 4):
        d.point((i, hy + 2), fill=P["ink"])
    if oars:
        for i in range(10, 36, 4):
            a = math.sin(t * 6 + i * 0.3)
            d.line([i, hy + 3, i - 2 + int(a * 2), wl + 2], fill=P["dsand"])
    d.line([22, hy - 18, 22, hy], fill=P["dbrown"])  # mast
    d.line([14, hy - 17, 30, hy - 17], fill=P["dbrown"])
    billow = int(round(math.sin(t * 1.5)))
    d.polygon([(14, hy - 16), (30, hy - 16), (31 + billow, hy - 8),
               (30, hy - 4), (14, hy - 4), (15 + billow, hy - 10)], fill=sail)
    if flag:
        d.polygon([(22, hy - 22), (26, hy - 21), (22, hy - 19)], fill=flag)
        d.line([22, hy - 22, 22, hy - 18], fill=P["dbrown"])
    if facing < 0:
        c = c.transpose(Image.FLIP_LEFT_RIGHT)
    if scale != 1:
        c = c.resize((c.width * scale, c.height * scale), Image.NEAREST)
    comp(img, c, (int(x - 22 * scale), int(y - wl * scale)))


def small_boat(img, x, y, t=0.0, facing=1, people=()):
    c = Image.new("RGBA", (30, 26), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    bob = int(round(math.sin(t * 2.5)))
    hy = 20 + bob
    d.polygon([(2, hy), (27, hy), (24, hy + 4), (5, hy + 4)], fill=P["brown"])
    d.line([2, hy, 0, hy - 2], fill=P["brown"])
    d.line([5, hy + 4, 24, hy + 4], fill=P["dbrown"])
    if facing < 0:
        c = c.transpose(Image.FLIP_LEFT_RIGHT)
    comp(img, c, (int(x - 15), int(y - 22)))
    for i, (kind, dx, pose) in enumerate(people):
        figure(img, x + dx, y - 2 + bob, kind, facing=facing, pose=pose,
               wade=0)


# ---------------------------------------------------------------- scenery

def temple(img, x, y, w=40, h=30, col=None, roof=None, cols=6):
    """Classical temple with base at y, left edge x."""
    col = col or P["marble"]
    roof = roof or P["red"]
    sh = P["stone"]
    rect(img, x - 2, y - 3, w + 4, 3, sh)
    rect(img, x, y - 5, w, 2, col)
    ped = max(5, w // 6)
    ch = h - 9 - ped
    step = (w - 4) / (cols - 1)
    for i in range(cols):
        cx = int(x + 2 + i * step)
        rect(img, cx - 1, y - 5 - ch, 3, ch, col)
        line(img, cx + 1, y - 5 - ch, cx + 1, y - 6, sh)
    rect(img, x - 1, y - 7 - ch, w + 2, 2, col)
    rect(img, x - 1, y - 5 - ch, w + 2, 1, sh)
    poly(img, [(x - 3, y - 7 - ch), (x + w + 2, y - 7 - ch),
               (x + w // 2, y - 7 - ch - ped)], roof)
    poly(img, [(x + 4, y - 8 - ch), (x + w - 5, y - 8 - ch),
               (x + w // 2, y - 7 - ch - ped + 3)], col)


def house(img, x, y, w=14, h=10, wall=None, roof=None, door=True):
    wall = wall or P["sand"]
    roof = roof or P["red"]
    rect(img, x, y - h, w, h, wall)
    poly(img, [(x - 2, y - h), (x + w + 1, y - h), (x + w // 2, y - h - 5)],
         roof)
    if door:
        rect(img, x + w // 2 - 1, y - 5, 3, 5, P["dbrown"])
    rect(img, x + 2, y - h + 2, 2, 2, P["dbrown"])
    if w > 10:
        rect(img, x + w - 4, y - h + 2, 2, 2, P["dbrown"])


def palm(img, x, y, h=22, t=0.0):
    sway = math.sin(t * 1.3 + x) * 1.0
    for i in range(h):
        bx = x + int(round(math.sin(i / h * 1.2) * 2 + sway * i / h))
        img.putpixel((bx, y - i), P["brown"] if i % 3 else P["dbrown"]) \
            if 0 <= bx < img.width and 0 <= y - i < img.height else None
    tx = x + int(round(math.sin(1.2) * 2 + sway))
    ty = y - h
    for ang in (-150, -110, -60, -20, 10, -180):
        a = math.radians(ang + sway * 4)
        for k in range(1, 9):
            px_ = tx + int(round(math.cos(a) * k))
            py_ = ty + int(round(math.sin(a) * k + 0.08 * k * k))
            if 0 <= px_ < img.width and 0 <= py_ < img.height:
                img.putpixel((px_, py_), P["green"] if k < 6 else P["teal"])


def tree(img, x, y, h=14, col=None):
    col = col or P["green"]
    rect(img, x - 1, y - 5, 2, 5, P["dbrown"])
    circle(img, x, y - h + 5, 5, col)
    circle(img, x - 3, y - h + 8, 3, col)
    circle(img, x + 3, y - h + 8, 3, col)
    img.putpixel((int(x - 2), int(y - h + 3)), P["lime"]) \
        if 0 <= x - 2 < img.width and 0 <= y - h + 3 < img.height else None


def cypress(img, x, y, h=18):
    poly(img, [(x - 3, y - 2), (x + 3, y - 2), (x, y - h)], P["forest"])
    poly(img, [(x - 1, y - 4), (x + 2, y - 4), (x, y - h + 3)], P["teal"])
    rect(img, x, y - 2, 1, 2, P["dbrown"])


def mountains(img, base_y, peaks, col, snow=None):
    for (px_, ph, pw) in peaks:
        poly(img, [(px_ - pw, base_y), (px_, base_y - ph), (px_ + pw, base_y)],
             col)
        if snow:
            poly(img, [(px_ - pw * 0.25, base_y - ph * 0.75),
                       (px_, base_y - ph),
                       (px_ + pw * 0.25, base_y - ph * 0.75)], snow)


def torch(img, x, y, t, seed=0):
    rect(img, x, y, 1, 7, P["dbrown"])
    f = int(t * 12 + seed) % 3
    flame = [P["yellow"], P["orange"], P["red"]]
    img.putpixel((x, y - 1), flame[0])
    img.putpixel((x, y - 2 - (f == 1)), flame[1])
    if f != 2:
        img.putpixel((x + (1 if f == 0 else -1), y - 2), flame[2])


def stars(img, w, h, t, n=40, seed=1, color=None):
    import random
    rnd = random.Random(seed)
    for i in range(n):
        x, y = rnd.randrange(w), rnd.randrange(h)
        ph = rnd.random() * 6
        if math.sin(t * 2 + ph) > -0.6:
            img.putpixel((x, y), color or (P["white"] if i % 3 else P["silver"]))


# ---------------------------------------------------------------- icons

COIN = spr("""
..yyyy..
.yggggy.
yggyyggy
ygyyyygd
ygyyyygd
yggyyggd
.dggggd.
..dddd..
""", {"y": "yellow", "g": "gold", "d": "dgold"})

SILVER_COIN = spr("""
..wwww..
.wssssw.
wsswwssw
swwwwwsd
swwwwwsd
wsswwssd
.dssssd.
..dddd..
""", {"w": "white", "s": "silver", "d": "slate"})

HEART = spr("""
.rr.rr.
rpprrrr
rprrrrr
.rrrrr.
..rrr..
...r...
""", {"r": "red", "p": "pink"})

BROKEN_HEART = spr("""
.rr..rr.
rprr.rrr
rrr.rrrr
.rr.rrr.
..r.rr..
....r...
""", {"r": "red", "p": "pink"})

DAGGER = spr("""
......w
.....ws
....ws.
...ws..
.gws...
..g....
.b.g...
b......
""", {"w": "white", "s": "silver", "g": "gold", "b": "brown"})

SKULL = spr("""
.wwww.
wwwwww
wkwwkw
wwwwww
.wkkw.
.w..w.
""", {"w": "white", "k": "ink"})

EAGLE = spr("""
y.......y
yy.yyy.yy
.yyyyyyy.
..yyyyy..
...yky...
....y....
...ddd...
....b....
....b....
...rrr...
...ryr...
...rrr...
....b....
....b....
....b....
....b....
""", {"y": "gold", "d": "dgold", "k": "ink", "b": "brown", "r": "red"})

FASCES = spr("""
s.......
ss......
sbbb....
.bbbb...
.rbbbb..
..bbbbb.
...brbb.
....bbbb
.....bbb
......bb
""", {"s": "silver", "b": "dsand", "r": "red"})

SCROLL = spr("""
.dddddddddddd.
dmmmmmmmmmmmmd
.wwwwwwwwwwww.
.wkkkkkk.kkkw.
.wwwwwwwwwwww.
.wkkkk.kkkkkw.
.wwwwwwwwwwww.
.wkkkkkkk.kkw.
.wwwwwwwwwwww.
.wkkk.kkkkkkw.
.wwwwwwwwwwww.
dmmmmmmmmmmmmd
.dddddddddddd.
""", {"d": "dsand", "m": "sand", "w": "marble", "k": "slate"})

LAUREL = spr("""
..g.......g..
.gl.......lg.
gl.........lg
g...........g
gl.........lg
.gl.......lg.
..ggl...lgg..
....gg.gg....
""", {"g": "green", "l": "lime"})

BAG = spr("""
...bb...
..b..b..
...bb...
..dddd..
.dsssdd.
dsss$sdd
dsssssdd
.dddddd.
""", {"b": "brown", "d": "dbrown", "s": "dsand", "$": "yellow"})

PLOW = spr("""
gggggggg
gglggggg
gggggglg
dddddddd
.bbbb...
....bbb.
.....bs.
""", {"g": "green", "l": "lime", "d": "dgrass", "b": "brown", "s": "silver"})

CROSS = spr("""
..b..
bbbbb
..b..
..b..
..b..
..b..
""", {"b": "dbrown"})

FLAG_R = spr("""
bggg
brrr
brrr
brrr
b...
b...
b...
""", {"b": "dbrown", "g": "gold", "r": "red"})

TENT = spr("""
....w....
...wsw...
..wssw...
.wsssw...
wsssddw..
wwwwwwww.
""", {"w": "marble", "s": "sand", "d": "dbrown"})

DIE = spr("""
kkkkkkkkk
kwwwwwwwk
kwkwwwkwk
kwwwwwwwk
kwwwkwwwk
kwwwwwwwk
kwkwwwkwk
kwwwwwwwk
kkkkkkkkk
""", {"k": "ink", "w": "white"})


def die_face(img, x, y, n, scale=2):
    c = Image.new("RGBA", (9, 9), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 8, 8], fill=P["white"], outline=P["ink"])
    pips = {1: [(4, 4)], 2: [(2, 2), (6, 6)], 3: [(2, 2), (4, 4), (6, 6)],
            4: [(2, 2), (6, 2), (2, 6), (6, 6)],
            5: [(2, 2), (6, 2), (4, 4), (2, 6), (6, 6)],
            6: [(2, 2), (6, 2), (2, 4), (6, 4), (2, 6), (6, 6)]}[n]
    for p in pips:
        d.point(p, fill=P["red"])
    c = c.resize((9 * scale, 9 * scale), Image.NEAREST)
    comp(img, c, (int(x - 9 * scale / 2), int(y - 9 * scale / 2)))


# ---------------------------------------------------------------- portraits

PEOPLE = {
    "caesar": dict(hair=P["brown"], style="thin", laurel=True, garb="red",
                   name="CAESAR", face="lean"),
    "pompey": dict(hair=P["dbrown"], style="anastole", garb="blue",
                   name="POMPEY", face="round"),
    "crassus": dict(hair=P["silver"], style="bald", garb="gold",
                    name="CRASSUS", face="old"),
    "sulla": dict(hair=P["orange"], style="short", garb="purple",
                  name="SULLA", face="blotch"),
    "marius": dict(hair=P["silver"], style="short", garb="red",
                   name="MARIUS", face="old"),
    "julia": dict(hair=P["dbrown"], style="bun", garb="pink", name="JULIA",
                  face="young"),
    "verc": dict(hair=P["orange"], style="long", garb="green",
                 name="VERCINGETORIX", face="moustache"),
    "bibulus": dict(hair=P["silver"], style="short", garb="white",
                    name="BIBULUS", face="old"),
    "ptolemy": dict(hair=P["ink"], style="nemes", garb="egypt",
                    name="PTOLEMY XIII", face="young"),
    "cleo": dict(hair=P["ink"], style="melon", garb="egypt",
                 name="CLEOPATRA", face="young"),
    "antony": dict(hair=P["ink"], style="curly", garb="red",
                   name="MARK ANTONY", face="lean"),
    "venus": dict(hair=P["yellow"], style="bun", garb="pink", name="VENUS",
                  face="young"),
}

GARB = {
    "red": (P["red"], P["wine"], P["white"]),
    "blue": (P["blue"], P["navy"], P["white"]),
    "gold": (P["white"], P["silver"], P["gold"]),
    "purple": (P["white"], P["silver"], P["purple"]),
    "pink": (P["pink"], P["red"], P["white"]),
    "green": (P["green"], P["teal"], P["orange"]),
    "white": (P["white"], P["silver"], P["purple"]),
    "egypt": (P["white"], P["silver"], P["gold"]),
}


def portrait(who, mood=None):
    """Return a 32x32 RGBA profile bust (facing right)."""
    pp = PEOPLE[who]
    c = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    sk, skd = P["skin"], P["tan"]
    hair = pp["hair"]
    face = pp["face"]
    g1, g2, g3 = GARB[pp["garb"]]
    # shoulders / garment
    d.polygon([(4, 31), (6, 25), (12, 22), (20, 22), (26, 25), (28, 31)],
              fill=g1)
    d.line([(12, 22), (17, 31)], fill=g2)
    d.line([(20, 23), (22, 31)], fill=g2)
    d.line([(6, 26), (11, 31)], fill=g3)
    if pp["garb"] == "red":   # cloak clasp
        d.point((19, 24), fill=P["gold"])
        d.point((20, 24), fill=P["gold"])
    # neck
    d.rectangle([13, 18, 18, 23], fill=sk)
    d.line([(13, 19), (13, 23)], fill=skd)
    if face == "moustache":
        d.line([(12, 22), (19, 22)], fill=P["gold"])  # torc
        d.point((19, 21), fill=P["gold"])
    # head profile
    jaw = 1 if face == "round" else 0
    head = [(9, 13), (9, 9), (11, 6), (14, 4), (18, 4), (21, 6), (22, 9),
            (22, 11), (24, 14), (22, 15), (22, 16), (23, 17), (22, 18),
            (21 + jaw, 20), (18, 21 + jaw), (14, 20), (11, 17)]
    if face == "young":
        head = [(p[0], p[1]) for p in head]
        head[8] = (23, 14)
    d.polygon(head, fill=sk)
    # shading at back of jaw
    d.line([(12, 17), (15, 20)], fill=skd)
    # ear
    d.rectangle([13, 11, 14, 14], fill=skd)
    d.point((14, 12), fill=sk)
    # eye + brow
    d.point((20, 10), fill=P["ink"])
    d.point((19, 10), fill=P["white"])
    d.line([(18, 8), (21, 8)], fill=skd if face != "old" else P["slate"])
    # mouth
    d.point((22, 17), fill=P["red"] if face == "young" else skd)
    d.point((21, 17), fill=skd)
    if face == "old":
        d.point((18, 13), fill=skd)
        d.line([(19, 15), (20, 16)], fill=skd)
        d.point((16, 9), fill=skd)
    if face == "blotch":
        for p in ((17, 12), (19, 14), (16, 16), (20, 12), (18, 17), (15, 8)):
            d.point(p, fill=P["red"])
    if face == "moustache":
        d.line([(20, 16), (23, 16)], fill=hair)
        d.point((20, 17), fill=hair)
    if mood == "sad":
        d.point((20, 11), fill=P["cyan"])
        d.point((20, 12), fill=P["cyan"])
    if mood == "angry":
        d.line([(18, 7), (21, 9)], fill=P["ink"])
    # hair
    st = pp["style"]
    if st == "thin":
        d.polygon([(9, 13), (9, 9), (11, 6), (14, 4), (18, 4), (20, 6),
                   (16, 6), (12, 9), (11, 13)], fill=hair)
        d.line([(16, 5), (19, 6)], fill=hair)
    elif st == "anastole":
        d.polygon([(9, 14), (8, 9), (10, 5), (14, 2), (19, 2), (22, 3),
                   (21, 6), (18, 5), (16, 6), (13, 8), (12, 12), (11, 14)],
                  fill=hair)
        d.point((20, 3), fill=P["tan"])
    elif st == "bald":
        d.polygon([(9, 15), (9, 10), (11, 9), (12, 12), (11, 15)], fill=hair)
        d.point((15, 5), fill=P["white"])
    elif st == "short":
        d.polygon([(9, 13), (9, 9), (11, 5), (14, 3), (19, 3), (21, 5),
                   (18, 5), (13, 8), (11, 13)], fill=hair)
    elif st == "curly":
        d.polygon([(8, 14), (8, 8), (11, 4), (15, 2), (20, 3), (22, 6),
                   (18, 6), (13, 9), (12, 14)], fill=hair)
        for p in ((10, 6), (13, 4), (17, 3), (9, 10), (11, 8)):
            d.point(p, fill=P["dslate"])
    elif st == "bun":
        d.polygon([(9, 14), (9, 9), (11, 5), (14, 3), (19, 3), (22, 6),
                   (18, 6), (14, 8), (12, 14)], fill=hair)
        d.ellipse([5, 7, 10, 12], fill=hair)
        d.point((15, 16), fill=P["gold"])   # earring
        d.line([(12, 5), (18, 4)], fill=P["gold"])
    elif st == "long":
        d.polygon([(6, 22), (7, 9), (10, 4), (14, 2), (19, 2), (22, 5),
                   (18, 6), (14, 8), (12, 14), (12, 22)], fill=hair)
        d.line([(9, 8), (8, 18)], fill=P["dgold"])
    elif st == "nemes":
        d.polygon([(7, 22), (8, 8), (12, 3), (18, 3), (21, 5), (22, 8),
                   (18, 8), (14, 9), (13, 16), (12, 22)], fill=P["gold"])
        for yy in range(5, 22, 2):
            d.line([(8, yy), (13, yy)], fill=P["blue"])
        d.point((22, 7), fill=P["red"])   # uraeus
        d.point((22, 6), fill=P["gold"])
    elif st == "melon":
        d.polygon([(8, 15), (8, 8), (11, 4), (15, 2), (20, 3), (22, 6),
                   (17, 6), (13, 9), (12, 15)], fill=hair)
        for yy in (4, 7, 10):
            d.line([(9, yy + 2), (14, yy)], fill=P["dslate"])
        d.line([(12, 4), (21, 5)], fill=P["gold"])
        d.point((15, 16), fill=P["gold"])
    if pp.get("laurel"):
        for (lx, ly) in ((9, 11), (10, 9), (11, 7), (13, 5), (15, 4),
                         (17, 4), (19, 5)):
            d.point((lx, ly), fill=P["green"])
            d.point((lx + 1, ly - 1), fill=P["lime"])
        d.line([(8, 12), (6, 15)], fill=P["green"])
        d.line([(8, 13), (7, 16)], fill=P["lime"])
    return c


def portrait_card(img, x, y, who, scale=2, border=None, label=True,
                  mood=None, gray=False, bg=None, name=None):
    """Framed portrait card. (x, y) is the top-left. Returns (w, h)."""
    from pixel import frame as pframe, text
    s = 32 * scale
    bg = bg or P["dslate"]
    border = border or P["gold"]
    rect(img, x, y, s + 4, s + 4, border)
    rect(img, x + 1, y + 1, s + 2, s + 2, P["ink"])
    rect(img, x + 2, y + 2, s, s, bg)
    por = portrait(who, mood)
    if gray:
        import numpy as np
        a = np.array(por).astype(np.int32)
        g = (a[..., :3].mean(-1) * 0.8).astype(np.uint8)
        a[..., 0] = a[..., 1] = a[..., 2] = g
        por = Image.fromarray(a.astype(np.uint8), "RGBA")
    if scale != 1:
        por = por.resize((s, s), Image.NEAREST)
    comp(img, por, (x + 2, y + 2))
    h = s + 4
    if label:
        nm = name or PEOPLE[who]["name"]
        rect(img, x, y + s + 4, s + 4, 9, border)
        text(img, x + (s + 4) // 2, y + s + 6, nm, P["ink"], "label", 8,
             anchor="c", spacing=0)
        h += 9
    return s + 4, h
