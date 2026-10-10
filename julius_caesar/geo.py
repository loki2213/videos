"""Hand-traced, simplified coastlines of the Roman world (lon, lat) and a
pixel map renderer. Accurate enough for a stylised campaign map."""
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from pixel import P

MED = [(-5.6, 36.1), (-4.4, 36.7), (-2.0, 36.8), (-0.8, 37.6), (-0.5, 38.3),
       (0.2, 38.8), (-0.3, 39.5), (0.5, 40.5), (1.2, 41.1), (2.2, 41.4),
       (3.2, 42.0), (3.1, 42.5), (3.0, 43.2), (4.0, 43.5), (4.8, 43.4),
       (5.4, 43.2), (6.6, 43.1), (7.3, 43.7), (8.0, 43.9), (8.9, 44.4),
       (9.8, 44.1), (10.3, 43.5), (11.0, 42.6), (12.2, 41.7), (13.0, 41.2),
       (14.2, 40.8), (15.0, 40.3), (15.7, 40.0), (15.8, 39.0), (15.7, 38.0),
       (16.1, 38.0), (16.6, 38.4), (17.1, 39.0), (16.6, 39.7), (17.0, 40.4),
       (17.9, 40.0), (18.4, 39.8), (18.5, 40.2), (17.9, 40.7), (16.9, 41.1),
       (16.0, 41.4), (16.1, 41.9), (15.2, 42.0), (14.2, 42.4), (13.6, 43.5),
       (12.6, 44.0), (12.3, 44.4), (12.3, 45.2), (13.1, 45.7), (13.8, 45.6),
       (13.6, 45.1), (13.9, 44.8), (14.4, 45.3), (15.0, 44.6), (15.9, 43.6),
       (17.5, 43.0), (18.5, 42.4), (19.3, 41.9), (19.5, 41.3), (19.4, 40.5),
       (20.0, 39.7), (20.7, 38.9), (21.1, 38.3), (21.6, 37.6), (21.7, 36.8),
       (22.4, 36.4), (22.8, 37.0), (23.2, 36.4), (22.9, 37.5), (23.6, 38.0),
       (24.0, 37.7), (24.0, 38.3), (22.9, 38.9), (22.9, 40.6), (23.9, 40.2),
       (24.4, 40.9), (26.0, 40.8), (26.2, 40.3), (26.2, 39.5), (26.8, 39.0),
       (26.9, 38.4), (27.3, 37.9), (27.3, 37.0), (28.0, 36.7), (29.1, 36.6),
       (30.5, 36.3), (30.6, 36.8), (31.5, 36.6), (32.5, 36.1), (33.5, 36.2),
       (34.6, 36.8), (35.9, 36.8), (35.8, 35.9), (35.9, 34.5), (35.5, 33.9),
       (35.2, 33.0), (34.6, 31.9), (34.2, 31.3), (33.0, 31.1), (32.3, 31.3),
       (31.0, 31.6), (30.0, 31.5), (29.9, 31.2), (28.0, 31.0), (25.2, 31.6),
       (23.0, 32.6), (21.0, 32.9), (20.1, 32.0), (20.0, 31.0), (19.0, 30.3),
       (17.0, 31.0), (15.4, 31.9), (15.2, 32.4), (13.1, 32.9), (11.2, 33.2),
       (10.1, 33.7), (10.9, 35.2), (11.1, 36.8), (10.3, 36.9), (10.2, 37.3),
       (9.8, 37.3), (8.6, 36.9), (7.0, 37.1), (5.1, 36.7), (3.0, 36.8),
       (1.0, 36.5), (-0.6, 35.8), (-2.0, 35.1), (-3.9, 35.2), (-5.3, 35.9)]

ATLANTIC = [(-30, 20), (-10, 20), (-10, 29), (-9.6, 30.4), (-9.2, 32.5),
            (-6.8, 34.0), (-5.9, 35.8), (-5.6, 36.0), (-6.3, 36.5),
            (-7.4, 37.2), (-8.9, 37.0), (-8.8, 38.5), (-9.5, 38.8),
            (-8.9, 40.2), (-8.8, 42.2), (-9.3, 43.0), (-8.0, 43.7),
            (-5.8, 43.6), (-3.8, 43.4), (-1.8, 43.4), (-1.3, 44.6),
            (-1.2, 46.2), (-2.2, 47.1), (-4.5, 47.8), (-4.8, 48.4),
            (-3.0, 48.8), (-1.6, 48.6), (-1.6, 49.6), (-0.2, 49.3),
            (0.2, 49.7), (1.6, 50.4), (2.5, 51.1), (3.6, 51.4), (4.2, 52.0),
            (4.7, 52.9), (5.5, 53.4), (7.0, 53.5), (8.6, 53.9), (8.7, 55.0),
            (8.3, 56.5), (10.5, 57.7), (12.0, 60.0), (-30, 60.0)]

BLACK_SEA = [(29.1, 41.2), (28.0, 41.6), (28.0, 42.7), (27.9, 43.2),
             (28.6, 44.3), (29.6, 45.2), (30.6, 46.5), (31.7, 46.6),
             (33.0, 46.0), (32.5, 45.4), (33.5, 44.5), (34.5, 44.5),
             (35.5, 45.1), (36.5, 45.3), (38.0, 47.0), (39.5, 47.0),
             (38.5, 46.0), (37.5, 45.0), (38.5, 44.3), (40.0, 43.4),
             (41.6, 41.6), (40.0, 41.0), (38.0, 40.9), (36.0, 41.7),
             (35.0, 42.0), (33.5, 42.0), (32.0, 41.6), (31.0, 41.1),
             (30.0, 41.2)]

MARMARA = [(26.2, 40.3), (27.0, 40.9), (28.9, 41.0), (29.1, 41.2),
           (29.9, 40.7), (28.0, 40.4), (26.6, 40.1)]

ISLANDS = {
    "britain": [(-5.7, 50.0), (-4.2, 50.4), (-3.0, 50.7), (-1.5, 50.7),
                (0.3, 50.8), (1.4, 51.2), (0.9, 51.6), (1.7, 52.5),
                (0.4, 52.9), (0.1, 53.6), (-0.4, 54.3), (-1.5, 55.0),
                (-2.0, 56.0), (-3.0, 58.6), (-5.0, 58.6), (-5.7, 56.5),
                (-4.9, 55.5), (-3.0, 55.0), (-3.4, 54.4), (-3.0, 53.6),
                (-4.6, 53.3), (-4.2, 52.8), (-4.1, 52.3), (-5.2, 51.7),
                (-4.0, 51.6), (-3.0, 51.4), (-4.5, 51.1)],
    "ireland": [(-6.0, 52.2), (-6.0, 53.5), (-6.2, 54.5), (-5.6, 55.2),
                (-8.0, 55.2), (-10.0, 54.2), (-9.9, 53.2), (-10.3, 52.0),
                (-9.6, 51.5), (-8.0, 51.8), (-6.4, 52.2)],
    "sicily": [(12.4, 37.8), (13.4, 38.2), (14.5, 38.05), (15.6, 38.3),
               (15.1, 37.5), (15.2, 36.7), (14.4, 36.8), (12.6, 37.6)],
    "sardinia": [(8.4, 39.0), (9.0, 39.1), (9.6, 39.2), (9.8, 40.5),
                 (9.5, 41.2), (8.2, 40.9), (8.4, 40.0)],
    "corsica": [(8.6, 41.4), (9.4, 41.4), (9.5, 42.5), (9.4, 43.0),
                (8.6, 42.4)],
    "crete": [(23.5, 35.3), (24.5, 35.6), (26.3, 35.3), (26.1, 35.0),
              (24.7, 35.0), (23.5, 35.2)],
    "cyprus": [(32.3, 34.7), (33.0, 34.6), (34.0, 35.0), (34.6, 35.7),
               (33.0, 35.4), (32.3, 35.1)],
    "mallorca": [(2.4, 39.6), (3.4, 39.9), (3.2, 39.3), (2.7, 39.5)],
    "euboea": [(22.8, 38.9), (23.5, 38.7), (24.5, 38.0), (24.2, 38.2),
               (23.2, 38.6)],
}

RIVERS = {
    "rhine": [(9.5, 47.6), (7.6, 47.6), (8.2, 48.9), (8.3, 50.0),
              (7.6, 50.4), (6.9, 50.9), (6.2, 51.8), (4.3, 51.9)],
    "rhone": [(6.1, 46.2), (5.2, 45.8), (4.8, 45.7), (4.8, 44.5),
              (4.7, 43.5)],
    "loire": [(4.0, 45.5), (3.2, 47.0), (1.5, 47.5), (0.0, 47.3),
              (-2.0, 47.3)],
    "seine": [(4.5, 47.8), (2.4, 48.8), (1.0, 49.2), (0.3, 49.5)],
    "po": [(7.5, 45.0), (9.0, 45.1), (10.5, 45.0), (11.8, 45.0),
           (12.4, 44.9)],
    "nile": [(31.2, 29.0), (31.2, 30.1), (30.6, 31.0), (31.0, 31.5)],
    "ebro": [(-3.0, 43.0), (-1.0, 41.8), (0.5, 41.0), (0.8, 40.7)],
    "rubicon": [(12.0, 44.0), (12.25, 44.1), (12.40, 44.16)],
}

ALPS = [(6.9, 44.3), (7.0, 45.2), (7.6, 45.9), (8.5, 46.4), (9.5, 46.5),
        (10.5, 46.6), (11.6, 46.7), (12.8, 46.5), (13.8, 46.4)]
PYRENEES = [(-1.4, 43.0), (0.0, 42.8), (1.2, 42.6), (2.4, 42.5)]

PLACES = {
    "rome": (12.5, 41.9), "rubicon": (12.4, 44.15), "ariminum": (12.57, 44.06),
    "ravenna": (12.2, 44.4), "brundisium": (17.94, 40.64),
    "corfinium": (13.84, 42.12),
    "dyrrhachium": (19.45, 41.32), "pharsalus": (22.38, 39.30),
    "alexandria": (29.9, 31.2), "pelusium": (32.55, 31.04),
    "zela": (35.9, 40.3), "thapsus": (11.05, 35.6), "munda": (-4.8, 37.4),
    "ilerda": (0.62, 41.62), "massilia": (5.37, 43.3), "alesia": (4.5, 47.54),
    "geneva": (6.1, 46.2), "bibracte": (4.04, 46.92),
    "rhine_bridge": (7.4, 50.4), "deal": (1.4, 51.22),
    "portus_itius": (1.6, 50.75), "lesbos": (26.3, 39.1),
    "utica": (10.06, 37.05), "athens": (23.7, 38.0), "carthage": (10.3, 36.85),
}

GAUL = [(-1.8, 43.4), (0.0, 43.0), (1.3, 43.3), (1.6, 43.7), (3.4, 44.1),
        (4.6, 44.8), (5.6, 45.4), (6.1, 46.2), (7.0, 46.6), (7.6, 47.6),
        (8.2, 48.9), (8.3, 50.0), (7.6, 50.4), (6.9, 50.9), (6.2, 51.8),
        (4.3, 51.9), (3.0, 51.6), (1.5, 50.6), (-1.0, 49.9), (-6.0, 48.6),
        (-6.0, 44.2), (-1.8, 43.7)]

NARBONENSIS = [(3.1, 42.4), (2.0, 42.6), (1.3, 43.3), (1.6, 43.7),
               (3.4, 44.1), (4.6, 44.8), (5.6, 45.4), (6.1, 46.2),
               (7.0, 45.9), (6.9, 44.3), (7.6, 43.6), (7.6, 42.0),
               (3.4, 41.8)]

CISALPINA = [(6.9, 44.3), (7.0, 45.2), (7.6, 45.9), (8.5, 46.4),
             (9.5, 46.5), (10.5, 46.6), (11.6, 46.7), (12.8, 46.5),
             (13.8, 46.4), (13.9, 45.6), (12.5, 45.0), (12.4, 44.16),
             (12.0, 44.0), (11.0, 44.0), (10.0, 44.1), (8.0, 44.2)]


class View:
    """Equirectangular view: top-left at (lon0, lat1), `ppd` pixels per
    degree of latitude, panel size w x h."""

    def __init__(self, lon0, lat1, ppd, w=270, h=216):
        self.lon0, self.lat1, self.ppd = lon0, lat1, ppd
        self.w, self.h = w, h
        self.kx = ppd * math.cos(math.radians(42))

    def xy(self, lon, lat):
        return ((lon - self.lon0) * self.kx, (self.lat1 - lat) * self.ppd)

    def pts(self, ll):
        return [self.xy(*p) for p in ll]

    def key(self):
        return (round(self.lon0, 3), round(self.lat1, 3), round(self.ppd, 3),
                self.w, self.h)

    @staticmethod
    def centered(lon, lat, ppd, w=270, h=216):
        kx = ppd * math.cos(math.radians(42))
        return View(lon - w / 2 / kx, lat + h / 2 / ppd, ppd, w, h)


def lerp_view(a, b, x):
    """Interpolate views in log-zoom space around their centres."""
    ca = (a.lon0 + a.w / 2 / a.kx, a.lat1 - a.h / 2 / a.ppd)
    cb = (b.lon0 + b.w / 2 / b.kx, b.lat1 - b.h / 2 / b.ppd)
    z = math.exp(math.log(a.ppd) + (math.log(b.ppd) - math.log(a.ppd)) * x)
    lon = ca[0] + (cb[0] - ca[0]) * x
    lat = ca[1] + (cb[1] - ca[1]) * x
    return View.centered(lon, lat, z, a.w, a.h)


def _poly_mask(view, polys, ss=1):
    im = Image.new("L", (view.w * ss, view.h * ss), 0)
    d = ImageDraw.Draw(im)
    for pl in polys:
        d.polygon([(x * ss, y * ss) for x, y in view.pts(pl)], fill=255)
    if ss > 1:
        im = im.resize((view.w, view.h), Image.BOX)
    return np.asarray(im) > 127


@lru_cache(maxsize=64)
def land_mask(vkey):
    view = View(vkey[0], vkey[1], vkey[2], vkey[3], vkey[4])
    water = _poly_mask(view, [MED, ATLANTIC, BLACK_SEA, MARMARA])
    isl = _poly_mask(view, list(ISLANDS.values()))
    return (~water) | isl


def region_mask(view, polys):
    return _poly_mask(view, polys) & land_mask(view.key())


@lru_cache(maxsize=64)
def _base_map(vkey):
    view = View(*vkey)
    land = land_mask(vkey)
    h, w = land.shape
    arr = np.zeros((h, w, 3), np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    # water: two-tone dither with depth (distance to coast)
    dist = distance_steps(land, 6)
    sea = np.array(P["navy"])
    shallow = np.array(P["blue"])
    arr[:] = sea
    arr[(dist == 1) & ~land] = shallow
    arr[(dist == 2) & ~land & ((xx + yy) % 2 == 0)] = shallow
    # land: sand/grass dither; north is greener
    lat = view.lat1 - yy / view.ppd
    from pixel import BAYER4
    green = BAYER4[yy % 4, xx % 4] < np.clip((lat - 41.0) / 5.0, 0, 1)
    base = np.where(green[..., None], np.array(P["grass"]),
                    np.array(P["dsand"]))
    alt = np.where(green[..., None], np.array(P["dgrass"]),
                   np.array(P["sand"]))
    noise = ((xx * 7 + yy * 13) % 11 == 0) | ((xx * 3 + yy * 5) % 17 == 0)
    landcol = np.where(noise[..., None], alt, base)
    arr[land] = landcol[land]
    # coast outline
    coast = land & (dist_inner(land) == 1)
    arr[coast] = arr[coast] // 2 + 20
    return arr


def distance_steps(land, n):
    """For water pixels: number of 4-neighbour steps to the nearest land
    (1..n), 0 beyond n or on land."""
    dist = np.zeros(land.shape, np.uint8)
    cur = land.copy()
    for i in range(1, n + 1):
        grown = cur.copy()
        grown[1:, :] |= cur[:-1, :]
        grown[:-1, :] |= cur[1:, :]
        grown[:, 1:] |= cur[:, :-1]
        grown[:, :-1] |= cur[:, 1:]
        ring = grown & ~cur
        dist[ring] = i
        cur = grown
    return dist


def dist_inner(land):
    """1 where a land pixel touches water (4-neighbourhood)."""
    m = np.zeros_like(land, np.uint8)
    w = ~land
    nb = np.zeros_like(land)
    nb[1:, :] |= w[:-1, :]
    nb[:-1, :] |= w[1:, :]
    nb[:, 1:] |= w[:, :-1]
    nb[:, :-1] |= w[:, 1:]
    m[land & nb] = 1
    return m


def render_map(view, t=0.0, waves=True):
    """Return an RGB PIL image of the map for this view."""
    arr = _base_map(view.key()).copy()
    land = land_mask(view.key())
    if waves:
        h, w = land.shape
        yy, xx = np.mgrid[0:h, 0:w]
        ph = ((xx + int(t * 6)) // 3 + yy * 5) % 23
        wv = (ph == 0) & (yy % 4 == 0) & ~land
        arr[wv] = np.array(P["sky"])
    return Image.fromarray(arr, "RGB")


def draw_rivers(img, view, names, color=None):
    d = ImageDraw.Draw(img)
    for n in names:
        pts = view.pts(RIVERS[n])
        d.line([(int(x), int(y)) for x, y in pts], fill=color or P["sky"],
               width=1)


def draw_mountains(img, view, chain, color=None, snow=None, size=None):
    d = ImageDraw.Draw(img)
    s = size or max(2, int(view.ppd / 4))
    for lon, lat in chain:
        x, y = view.xy(lon, lat)
        d.polygon([(x - s, y + s // 2), (x, y - s), (x + s, y + s // 2)],
                  fill=color or P["stone"])
        d.polygon([(x - s // 3, y - s * 2 // 3), (x, y - s),
                   (x + s // 3, y - s * 2 // 3)], fill=snow or P["white"])


def overlay_region(img, mask, color, alpha_pattern=2, t=0.0):
    """Hatch-fill a region mask with a colour (pixel-art transparency)."""
    arr = np.array(img)
    h, w = mask.shape
    yy, xx = np.mgrid[0:h, 0:w]
    if alpha_pattern == 1:
        pat = np.ones_like(mask)
    else:
        pat = ((xx + yy) % alpha_pattern == 0)
    m = mask & pat
    arr[m, :3] = np.array(color)
    # border
    edge = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0) &
                    np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
    arr[edge, :3] = np.array(color)
    img.paste(Image.fromarray(arr, img.mode))
