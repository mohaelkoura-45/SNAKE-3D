
import array
import colorsys
import copy
import datetime
import json
import math
import os
import random
import sys
import threading
import time
from collections import deque

try:
    import pygame
except ImportError:  # pragma: no cover
    print("This game needs pygame.  Install it with:  pip install pygame")
    sys.exit(1)


# --------------------------------------------------------------------------- #
#  Constants
# --------------------------------------------------------------------------- #
N = 21                                   # board is N x N cells
UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
DIRS = (UP, DOWN, LEFT, RIGHT)
MAX_LEVEL = 10
DIFFS = ("Easy", "Normal", "Hard")
DMULT = (1.0, 1.5, 2.0)
BASE_SPEED = (6.0, 8.0, 10.0)
SCORE_FILE = os.path.join(os.path.expanduser("~"), ".snake3d_scores.json")
GY = -0.9                                # ground height (top of the island)
GROUND_HALF = 16                         # half-size of the floating island
MUSIC_VOL = 0.55

_L = (0.45, 0.85, 0.35)
_ln = math.sqrt(sum(v * v for v in _L))
LX, LY, LZ = (v / _ln for v in _L)
AMB, DIF = 0.50, 0.60

FOOD_COL = (235, 60, 60)
GOLD_COL = (255, 205, 40)
SLOW_COL = (70, 170, 255)
TEAL = (60, 150, 160)


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def opp(d):
    return (-d[0], -d[1])


def wx(g):
    return g - N / 2 + 0.5




# --------------------------------------------------------------------------- #
#  Extra constants
# --------------------------------------------------------------------------- #
VERSION = 2
_HOME = os.path.expanduser("~")
SAVE_FILE = os.path.join(_HOME, ".snake3d_save.json")
OLD_SCORE_FILE = SCORE_FILE               # v1 high-score file (imported once)
WHITE = (255, 255, 255)
COIN_COL = (255, 215, 60)
XP_COL = (120, 220, 255)


def slug(s):
    out = "".join(c.lower() if c.isalnum() else "_" for c in s)
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


# --------------------------------------------------------------------------- #
#  Characters  (cosmetics + a small perk each).  req: ("level", n) / ("ach", id)
# --------------------------------------------------------------------------- #
def _ch(name, head, b0, b1, acc, pat, hat, perk, price=0, req=None, **kw):
    d = dict(id=slug(name), name=name, head=head, b0=b0, b1=b1, acc=acc, pat=pat, hat=hat, perk=perk,
             price=price, req=req)
    d.update(kw)
    return d


CHARACTERS = [
    _ch("Emerald Viper", (120, 255, 150), (50, 200, 100), (20, 110, 70), (200, 255, 120), "gradient", None,
        "Balanced classic - no perks."),
    _ch("Frost Wyrm", (210, 240, 255), (90, 170, 240), (40, 80, 170), (230, 245, 255), "gradient", "crest",
        "Slow-motion lasts 10 seconds.", slow=10.0),
    _ch("Mystic Mamba", (235, 160, 255), (170, 80, 230), (80, 40, 140), (255, 150, 220), "spots", "wizard",
        "+15% score on everything.", score=1.15),
    _ch("Fire Drake", (255, 220, 120), (255, 120, 40), (150, 40, 20), (255, 230, 80), "stripes", "horns",
        "Combo timer lasts 6 seconds.", combo=6.0),
    _ch("Golden Cobra", (255, 235, 130), (240, 190, 50), (160, 110, 20), (120, 70, 10), "stripes", "crown",
        "Special fruit appears more often.", price=2500, bonus=1.8),
    _ch("Rainbow Racer", (255, 140, 180), (255, 255, 255), (255, 255, 255), (255, 255, 255), "rainbow", "party",
        "Starts with 4 lives.", price=3000, lives=4),
    _ch("Cyber Python", (130, 255, 255), (50, 80, 120), (25, 35, 60), (0, 255, 200), "checker", "antenna",
        "Pickups last much longer.", price=1500, blife=1.7),
    _ch("Shadow Ninja", (80, 80, 105), (55, 55, 75), (22, 22, 34), (230, 40, 60), "stripes", "headband",
        "Moves 8% slower - great control.", price=1500, speed=0.92),
    _ch("Pumpkin Imp", (255, 170, 60), (240, 130, 30), (130, 70, 20), (90, 170, 60), "stripes", "pumpkin",
        "+50% level-clear bonus.", price=1000, clear=1.5),
    _ch("Ghost Glider", (245, 248, 255), (205, 220, 245), (150, 170, 215), (255, 230, 120), "gradient", "halo",
        "Combo timer lasts 5.5 seconds.", price=2000, combo=5.5),
    # ---- new characters
    _ch("Cyber Snake", (0, 255, 220), (20, 40, 70), (10, 20, 40), (0, 255, 220), "checker", "antenna",
        "+10% coins from everything.", price=3500, req=("level", 8), coinx=1.1),
    _ch("Plasma Viper", (255, 120, 255), (150, 40, 220), (60, 20, 120), (255, 100, 255), "stripes", "crest",
        "Power-ups last 25% longer.", price=4000, req=("level", 10), pw=1.25),
    _ch("Shadow Serpent", (110, 90, 150), (45, 35, 70), (15, 10, 28), (170, 60, 255), "spots", "horns",
        "Ghost mode lasts 50% longer.", price=4500, req=("level", 12), gdur=1.5),
    _ch("Toxic Cobra", (190, 255, 60), (110, 200, 30), (40, 100, 20), (255, 255, 80), "spots", "crest",
        "+10% XP from everything.", price=3500, req=("level", 6), xpx=1.1),
    _ch("Crystal Dragon", (180, 250, 255), (110, 210, 245), (70, 120, 220), (255, 255, 255), "checker", "horns",
        "Each level starts with an 8s shield.", price=6000, req=("level", 15), startshield=8.0),
    _ch("Storm Snake", (200, 215, 255), (90, 100, 160), (40, 45, 90), (255, 240, 90), "stripes", "antenna",
        "Weak magnet pull is always on.", price=5000, req=("level", 14), magnet=2),
    _ch("Solar Serpent", (255, 240, 130), (255, 180, 40), (220, 90, 20), (255, 255, 200), "gradient", "halo",
        "Special fruit lasts longer.", price=6500, req=("level", 18), blife=1.5),
    _ch("Lunar Viper", (230, 235, 255), (150, 160, 215), (70, 75, 140), (255, 255, 210), "spots", "wizard",
        "Slow-motion lasts 9 seconds.", price=5500, req=("level", 16), slow=9.0),
    _ch("Void Snake", (150, 100, 255), (60, 30, 110), (15, 8, 35), (210, 120, 255), "gradient", "crown",
        "+15% XP, but 5% slower.", price=0, req=("level", 20), xpx=1.15, speed=0.95),
    _ch("Neon Cobra", (255, 90, 220), (40, 220, 255), (255, 60, 200), (255, 255, 120), "stripes", "party",
        "+5% score, combo lasts 5s.", price=10000, req=("level", 25), score=1.05, combo=5.0),
]
CHAR_IDX = {c["id"]: i for i, c in enumerate(CHARACTERS)}


def seg_color(look, i, n, t=0.0):
    t01 = i / max(1, n - 1)
    base = mix(look["b0"], look["b1"], t01)
    pat = look["pat"]
    if pat == "stripes":
        return look["acc"] if i % 4 == 2 else base
    if pat == "spots":
        return look["acc"] if i % 5 == 3 else base
    if pat == "checker":
        return shade(look["acc"], 0.55) if i % 2 else base
    if pat == "rainbow":
        r, g, b = colorsys.hsv_to_rgb((i * 0.07 + t * 0.15) % 1.0, 0.7, 1.0)
        return (int(r * 255), int(g * 255), int(b * 255))
    if pat == "flame":
        f = 0.5 + 0.5 * math.sin(t * 9 - i * 0.9)
        return mix(look["b1"], look["acc"], f * (1 - t01 * 0.5))
    if pat == "galaxy":
        return look["acc"] if (i * 7 + int(t * 3)) % 6 == 0 else base
    if pat == "glow":
        return mix(base, look["acc"], 0.3 + 0.3 * math.sin(t * 5 - i * 0.7))
    return shade(base, 0.9) if i % 2 else base


def draw_hat(R, look, hat, x, z, d, t):
    if not hat or hat == "none":
        return
    p = (-d[1], d[0])
    acc = look["acc"]
    if hat == "horns":
        for sg in (-1, 1):
            bx, bz = x - d[0] * 0.05 + p[0] * 0.3 * sg, z - d[1] * 0.05 + p[1] * 0.3 * sg
            R.box(bx, 0.92, bz, 0.07, 0.13, 0.07, (240, 232, 205), bias=0.5)
            R.box(bx + p[0] * 0.04 * sg, 1.12, bz + p[1] * 0.04 * sg, 0.045, 0.1, 0.045, (255, 250, 230), bias=0.5)
    elif hat == "crest":
        for k in range(3):
            o = 0.22 * k - 0.05
            R.box(x - d[0] * o, 0.9 + 0.05 * (2 - k), z - d[1] * o, 0.06, 0.12, 0.06, acc, bias=0.5)
    elif hat == "crown":
        R.box(x, 0.86, z, 0.38, 0.05, 0.38, (255, 215, 70), bias=0.5)
        for sx in (-1, 1):
            for sz in (-1, 1):
                R.box(x + 0.3 * sx, 1.0, z + 0.3 * sz, 0.06, 0.1, 0.06, (255, 215, 70), bias=0.5)
    elif hat in ("wizard", "party"):
        cx, cz = x - d[0] * 0.1, z - d[1] * 0.1
        if hat == "wizard":
            R.box(cx, 0.84, cz, 0.42, 0.03, 0.42, look["b1"], bias=0.5)
        for k, hw in enumerate((0.3, 0.23, 0.16, 0.09)):
            c = look["b1"] if hat == "wizard" else (acc if k % 2 == 0 else (255, 120, 170))
            R.box(cx, 0.97 + 0.2 * k, cz, hw, 0.1, hw, c, bias=0.5)
        R.box(cx, 1.82, cz, 0.06, 0.06, 0.06, (255, 235, 90), rot=t * 2, bias=0.5)
    elif hat == "antenna":
        ax, az = x - d[0] * 0.15, z - d[1] * 0.15
        R.box(ax, 1.0, az, 0.03, 0.2, 0.03, (90, 90, 100), bias=0.5)
        R.box(ax, 1.25, az, 0.07 + 0.02 * math.sin(t * 6), 0.07, 0.07, acc, rot=t * 3, bias=0.5)
    elif hat == "headband":
        R.box(x, 0.62, z, 0.5, 0.07, 0.5, acc, bias=0.5)
        for sg in (-1, 1):
            R.box(x - d[0] * 0.58 + p[0] * 0.1 * sg, 0.66, z - d[1] * 0.58 + p[1] * 0.1 * sg, 0.07, 0.04, 0.07, acc,
                  bias=0.5)
    elif hat == "halo":
        y = 1.2 + 0.05 * math.sin(t * 3)
        for sg in (-1, 1):
            R.box(x, y, z + 0.3 * sg, 0.3, 0.03, 0.04, acc, bias=0.5)
            R.box(x + 0.3 * sg, y, z, 0.04, 0.03, 0.3, acc, bias=0.5)
    elif hat == "pumpkin":
        R.box(x, 0.9, z, 0.05, 0.1, 0.05, (90, 170, 60), bias=0.5)
        R.box(x + 0.08, 0.98, z, 0.1, 0.02, 0.04, (90, 170, 60), bias=0.5)
    elif hat == "tophat":
        R.box(x, 0.84, z, 0.42, 0.03, 0.42, (30, 30, 40), bias=0.5)
        R.box(x, 1.15, z, 0.26, 0.3, 0.26, (35, 35, 48), bias=0.5)
        R.box(x, 0.97, z, 0.27, 0.05, 0.27, acc, bias=0.6)
    elif hat == "cap":
        R.box(x, 0.9, z, 0.45, 0.1, 0.45, acc, bias=0.5)
        R.box(x + d[0] * 0.4, 0.85, z + d[1] * 0.4, 0.25 + 0.15 * abs(d[0]), 0.03, 0.25 + 0.15 * abs(d[1]),
              shade(acc, 0.8), bias=0.6)
    elif hat == "cowboy":
        R.box(x, 0.84, z, 0.62, 0.03, 0.62, (140, 95, 55), bias=0.5)
        R.box(x, 1.0, z, 0.3, 0.17, 0.3, (155, 105, 60), bias=0.5)
    elif hat == "viking":
        R.box(x, 0.9, z, 0.5, 0.12, 0.5, (150, 150, 165), bias=0.5)
        for sg in (-1, 1):
            R.box(x + p[0] * 0.5 * sg, 1.05, z + p[1] * 0.5 * sg, 0.06, 0.2, 0.06, (245, 240, 220), bias=0.5)
    elif hat == "shades":
        R.box(x + d[0] * 0.3, 0.86, z + d[1] * 0.3, 0.06 + 0.4 * abs(p[0]), 0.07, 0.06 + 0.4 * abs(p[1]),
              (10, 10, 15), bias=4.0)
    elif hat == "flower":
        for sg in (-1, 1):
            R.box(x + 0.16 * sg, 0.86, z, 0.08, 0.04, 0.08, (255, 140, 190), rot=t, bias=0.5)
            R.box(x, 0.86, z + 0.16 * sg, 0.08, 0.04, 0.08, (255, 140, 190), rot=t, bias=0.5)
        R.box(x, 0.9, z, 0.07, 0.04, 0.07, (255, 220, 60), bias=0.6)


def draw_head_style(R, look, style, x, z, d):
    """Extra geometry for head styles (the base head box is drawn by the caller)."""
    p = (-d[1], d[0])
    if style == "viper":
        R.box(x + d[0] * 0.42, 0.36, z + d[1] * 0.42, 0.2 + 0.1 * abs(p[0]), 0.28, 0.2 + 0.1 * abs(p[1]),
              shade(look["head"], 0.95), edge=True)
    elif style == "bulldog":
        R.box(x + d[0] * 0.3, 0.2, z + d[1] * 0.3, 0.3 + 0.2 * abs(p[0]), 0.16, 0.3 + 0.2 * abs(p[1]),
              shade(look["head"], 0.85), edge=True)
    elif style == "robot":
        R.box(x + d[0] * 0.3, 0.72, z + d[1] * 0.3, 0.04 + 0.42 * abs(p[0]), 0.05, 0.04 + 0.42 * abs(p[1]),
              (255, 60, 60), bias=3.5)
    elif style == "dragon":
        R.box(x + d[0] * 0.45, 0.3, z + d[1] * 0.45, 0.18 + 0.08 * abs(p[0]), 0.2, 0.18 + 0.08 * abs(p[1]),
              shade(look["head"], 0.9), edge=True)
        for sg in (-1, 1):
            R.box(x + d[0] * 0.62 + p[0] * 0.07 * sg, 0.42, z + d[1] * 0.62 + p[1] * 0.07 * sg, 0.03, 0.03, 0.03,
                  (40, 20, 20), bias=3.5)


# --------------------------------------------------------------------------- #
#  Worlds  (sky, island, scenery, weather)
# --------------------------------------------------------------------------- #
def _world(name, fa, fb, wall, slab, ground, dirt, sky, body, stars, clouds, mount, scen, amb, lamp, skyline=False):
    return dict(name=name, fa=fa, fb=fb, wall=wall, slab=slab, ground=ground, dirt=dirt, sky=sky, body=body,
                stars=stars, clouds=clouds, mount=mount, scen=scen, amb=amb, lamp=lamp, skyline=skyline)


WORLDS = [
    _world("Meadow", (74, 160, 86), (66, 146, 78), (158, 134, 104), (96, 70, 48), (88, 170, 90), (110, 80, 52),
           ((70, 140, 230), (190, 230, 250)), ("sun", (255, 244, 180), (0.74, 0.2)), 0, (255, 255, 255),
           ((120, 160, 190), (90, 140, 110)),
           [("tree", 4, ((100, 70, 45), (52, 150, 70), (70, 175, 85))), ("flower", 5, None),
            ("rock", 1, ((130, 130, 135),))], "petals", (255, 220, 120)),
    _world("Desert", (222, 188, 120), (208, 174, 108), (178, 104, 70), (140, 98, 64), (232, 200, 140), (170, 120, 80),
           ((70, 130, 215), (250, 215, 160)), ("sun", (255, 250, 200), (0.7, 0.18)), 0, (255, 240, 220),
           ((215, 150, 100), (190, 120, 80)),
           [("cactus", 4, ((70, 150, 80),)), ("rock", 3, ((190, 130, 90),))], "dust", (255, 190, 90)),
    _world("Glacier", (178, 216, 240), (160, 202, 230), (96, 138, 196), (80, 110, 160), (225, 240, 250), (140, 175, 210),
           ((20, 40, 100), (150, 200, 235)), ("sun", (255, 255, 255), (0.25, 0.2)), 0, (235, 245, 255),
           ((170, 200, 230), (140, 175, 215)),
           [("pine", 5, ((90, 65, 45), (40, 110, 90), (245, 250, 255))), ("crystal", 3, ((150, 220, 255),))],
           "snow", (160, 230, 255)),
    _world("Volcano", (78, 56, 58), (66, 46, 48), (190, 70, 45), (40, 28, 28), (58, 40, 40), (35, 24, 24),
           ((24, 6, 10), (170, 50, 22)), ("sun", (255, 110, 50), (0.3, 0.25)), 0, (70, 45, 45),
           ((90, 40, 35), (60, 28, 28)),
           [("lava", 5, ((50, 38, 38), (255, 120, 30))), ("rock", 3, ((70, 55, 55),))], "embers", (255, 140, 40)),
    _world("Neon City", (30, 32, 62), (24, 26, 52), (230, 60, 200), (14, 14, 34), (18, 16, 40), (10, 10, 26),
           ((4, 4, 20), (60, 24, 110)), ("moon", (255, 150, 230), (0.28, 0.2)), 90, None,
           ((70, 30, 120), (46, 20, 90)),
           [("pylon", 6, ((0, 255, 230), (255, 60, 200), (120, 160, 255)))], "sparks", (0, 255, 230), True),
    _world("Moonlit Forest", (34, 80, 70), (28, 70, 62), (90, 80, 110), (40, 36, 56), (30, 70, 62), (30, 24, 40),
           ((4, 8, 30), (24, 60, 80)), ("moon", (235, 240, 255), (0.72, 0.2)), 110, (60, 80, 110),
           ((22, 44, 64), (14, 32, 48)),
           [("pine", 5, ((50, 38, 34), (24, 70, 60), None)), ("mushroom", 4, ((120, 255, 200), (255, 140, 220)))],
           "fireflies", (180, 255, 160)),
    _world("Candy Land", (255, 190, 214), (248, 170, 200), (120, 210, 190), (200, 120, 160), (255, 210, 230),
           (210, 130, 170), ((255, 170, 220), (255, 235, 250)), ("sun", (255, 250, 200), (0.7, 0.2)), 0, (255, 225, 240),
           ((255, 190, 225), (240, 160, 205)),
           [("lollipop", 4, ((255, 90, 140), (90, 200, 255), (255, 230, 90))),
            ("gumdrop", 4, ((255, 120, 120), (120, 230, 140), (160, 140, 255)))], "sprinkles", (255, 255, 150)),
    _world("Tropical Beach", (240, 222, 160), (228, 208, 146), (190, 140, 100), (150, 110, 70), (240, 225, 170),
           (180, 140, 90), ((20, 150, 230), (160, 235, 245)), ("sun", (255, 250, 210), (0.76, 0.18)), 0, (255, 255, 255),
           ((60, 170, 170), (40, 140, 130)),
           [("palm", 5, ((120, 90, 60), (50, 170, 80))), ("rock", 2, ((200, 180, 140),))], "bubbles", (255, 240, 150)),
    _world("Autumn Hills", (196, 130, 70), (182, 118, 62), (120, 84, 60), (84, 56, 40), (180, 120, 60), (100, 66, 40),
           ((90, 50, 110), (255, 170, 90)), ("sun", (255, 200, 120), (0.3, 0.3)), 0, (255, 190, 140),
           ((150, 70, 70), (110, 56, 60)),
           [("tree", 5, ((90, 60, 40), (210, 80, 40), (240, 160, 40))), ("pumpkin", 3, ((240, 130, 30), (70, 140, 60)))],
           "leaves", (255, 170, 60)),
    _world("Cosmos", (36, 40, 76), (30, 34, 66), (120, 140, 230), (30, 34, 60), (40, 44, 80), (22, 24, 48),
           ((2, 2, 12), (30, 16, 70)), ("planet", (120, 170, 255), (0.74, 0.28)), 160, None, None,
           [("asteroid", 6, ((110, 100, 120),)), ("crystal", 3, ((200, 150, 255),))], "stardust", (255, 200, 255)),
]


# ---- scenery objects: each returns (boxes, floating); boxes are (ox,oy,oz,hx,hy,hz,color,rot)
def sc_tree(rng, c):
    h, s = rng.uniform(0.7, 1.3), rng.uniform(0.8, 1.2)
    return [(0, h / 2, 0, .17 * s, h / 2, .17 * s, c[0], 0),
            (0, h + .4 * s, 0, .62 * s, .4 * s, .62 * s, c[1], rng.random()),
            (0, h + 1.05 * s, 0, .4 * s, .3 * s, .4 * s, c[2], rng.random())], False


def sc_pine(rng, c):
    s = rng.uniform(0.8, 1.2)
    b = [(0, .25, 0, .14, .25, .14, c[0], 0), (0, .75, 0, .75 * s, .25, .75 * s, c[1], 0),
         (0, 1.2, 0, .55 * s, .25, .55 * s, c[1], .4), (0, 1.65, 0, .32 * s, .25, .32 * s, c[1], .8)]
    if c[2]:
        b.append((0, 1.95, 0, .2 * s, .07, .2 * s, c[2], .8))
        b.append((0, 1.0, 0, .77 * s, .03, .77 * s, c[2], 0))
    return b, False


def sc_cactus(rng, c):
    h = rng.uniform(0.9, 1.6)
    return [(0, h / 2, 0, .2, h / 2, .2, c[0], 0), (.3, h * .5, 0, .18, .06, .1, c[0], 0),
            (.42, h * .5 + .2, 0, .09, .22, .09, c[0], 0)], False


def sc_rock(rng, c):
    s = rng.uniform(0.6, 1.3)
    return [(0, .2 * s, 0, .4 * s, .2 * s, .35 * s, c[0], rng.random()),
            (.3 * s, .12 * s, .2 * s, .25 * s, .12 * s, .22 * s, shade(c[0], .85), rng.random())], False


def sc_flower(rng, c):
    out = []
    for _ in range(2):
        ox, oz = rng.uniform(-.3, .3), rng.uniform(-.3, .3)
        col = rng.choice([(255, 90, 120), (255, 220, 80), (255, 255, 255), (180, 120, 255)])
        out += [(ox, .15, oz, .025, .15, .025, (60, 140, 60), 0), (ox, .34, oz, .11, .05, .11, col, rng.random()),
                (ox, .4, oz, .05, .03, .05, (255, 200, 60), 0)]
    return out, False


def sc_crystal(rng, c):
    h = rng.uniform(0.8, 1.7)
    return [(0, h / 2, 0, .2, h / 2, .2, c[0], .785), (.35, .4, .1, .12, .35, .12, shade(c[0], .9), .3)], False


def sc_lava(rng, c):
    s = rng.uniform(0.7, 1.2)
    r = rng.random()
    return [(0, .3, 0, .45 * s, .3, .4 * s, c[0], r), (0, .62, 0, .22 * s, .04, .2 * s, c[1], r)], False


def sc_pylon(rng, c):
    h, w, g = rng.uniform(1.5, 4.0), rng.uniform(.35, .7), rng.choice(c)
    return [(0, h / 2, 0, w, h / 2, w, (28, 26, 60), 0), (0, h * .35, 0, w + .01, .04, w + .01, g, 0),
            (0, h * .7, 0, w + .01, .04, w + .01, g, 0), (0, h + .05, 0, w * .9, .05, w * .9, g, 0)], False


def sc_mushroom(rng, c):
    s = rng.uniform(0.8, 1.5)
    return [(0, .2 * s, 0, .09 * s, .2 * s, .09 * s, (230, 230, 210), 0),
            (0, .45 * s, 0, .28 * s, .1 * s, .28 * s, rng.choice(c), rng.random())], False


def sc_lollipop(rng, c):
    r = rng.random() * 3
    return [(0, .5, 0, .03, .5, .03, (250, 250, 250), 0), (0, 1.15, 0, .32, .32, .06, rng.choice(c), r),
            (0, 1.15, 0, .2, .2, .07, (255, 255, 255), r)], False


def sc_gumdrop(rng, c):
    col, r = rng.choice(c), rng.random()
    return [(0, .2, 0, .3, .2, .3, col, r), (0, .45, 0, .18, .1, .18, col, r), (0, .58, 0, .06, .03, .06, (255, 255, 255), r)], False


def sc_palm(rng, c):
    b = [(.08 * k, .25 + .5 * k, 0, .13, .25, .13, c[0], 0) for k in range(4)]
    tx = .08 * 3
    b += [(tx, 2.05, 0, .75, .04, .16, c[1], k * .785) for k in range(4)]
    b += [(tx + .1, 1.9, .1, .08, .08, .08, (90, 60, 30), 0)]
    return b, False


def sc_pumpkin(rng, c):
    return [(0, .25, 0, .3, .25, .3, c[0], rng.random()), (0, .55, 0, .05, .08, .05, c[1], 0)], False


def sc_asteroid(rng, c):
    r = rng.random()
    return [(0, rng.uniform(1.8, 4.5), 0, .5, .4, .45, c[0], r),
            (.3, rng.uniform(2.0, 4.8), .1, .3, .25, .3, shade(c[0], .85), r + 1)], True


SCEN = dict(tree=sc_tree, pine=sc_pine, cactus=sc_cactus, rock=sc_rock, flower=sc_flower, crystal=sc_crystal,
            lava=sc_lava, pylon=sc_pylon, mushroom=sc_mushroom, lollipop=sc_lollipop, gumdrop=sc_gumdrop,
            palm=sc_palm, pumpkin=sc_pumpkin, asteroid=sc_asteroid)



# ---- new scenery kinds (for the 10 new worlds)
def sc_column(rng, c):
    h = rng.uniform(1.0, 2.4)
    return [(0, .12, 0, .38, .12, .38, c[0], 0), (0, h / 2 + .2, 0, .24, h / 2, .24, c[0], 0),
            (0, h + .45, 0, .34, .1, .34, shade(c[0], 1.1), 0)], False


def sc_ruin(rng, c):
    return [(0, .35, 0, .7, .35, .25, c[0], rng.random() * .3), (.2, .8, 0, .3, .12, .22, shade(c[0], .9), 0),
            (-.4, .2, .5, .25, .2, .25, shade(c[0], .8), rng.random())], False


def sc_coral(rng, c):
    col = rng.choice(c)
    return [(0, .35, 0, .12, .35, .12, col, 0), (.2, .55, 0, .1, .22, .1, col, 0), (-.2, .5, .05, .1, .25, .1, shade(col, .9), 0),
            (0, .78, 0, .16, .08, .16, shade(col, 1.15), 0)], False


def sc_kelp(rng, c):
    h = rng.uniform(1.2, 2.6)
    return [(0, h / 2, 0, .07, h / 2, .07, c[0], 0), (.12, h * .7, 0, .06, h * .3, .06, shade(c[0], .85), 0)], False


def sc_jelly(rng, c):
    col = rng.choice(c)
    y = rng.uniform(1.8, 3.8)
    return [(0, y, 0, .35, .22, .35, col, 0), (0, y - .45, 0, .05, .25, .05, shade(col, .8), 0),
            (.18, y - .4, .1, .04, .22, .04, shade(col, .8), 0)], True


def sc_spike(rng, c):
    h = rng.uniform(.8, 2.0)
    col = rng.choice(c)
    return [(0, h / 2, 0, .25, h / 2, .25, col, rng.random()), (0, h * .9, 0, .12, h * .35, .12, shade(col, 1.2), .6)], False


def sc_floatisle(rng, c):
    y = rng.uniform(1.5, 3.5)
    return [(0, y, 0, .9, .25, .9, c[0], 0), (0, y + .3, 0, .85, .08, .85, c[1], 0),
            (0, y + .7, 0, .25, .3, .25, (110, 80, 50), 0), (0, y + 1.2, 0, .5, .3, .5, c[1], .4)], True


def sc_barrel(rng, c):
    return [(0, .3, 0, .28, .3, .28, c[0], rng.random()), (0, .62, 0, .2, .03, .2, c[1], 0)], False


def sc_deadtree(rng, c):
    h = rng.uniform(1.0, 2.0)
    return [(0, h / 2, 0, .1, h / 2, .1, c[0], 0), (.3, h * .7, 0, .28, .04, .05, c[0], .3),
            (-.28, h * .85, 0, .25, .04, .05, c[0], -.3)], False


def sc_panel(rng, c):
    h = rng.uniform(.8, 2.2)
    return [(0, h / 2, 0, .45, h / 2, .3, c[0], rng.random() * .4), (0, h * .6, .31, .3, .05, .02, c[1], 0),
            (0, h + .1, 0, .12, .1, .12, c[1], 0)], False


def sc_satellite(rng, c):
    y = rng.uniform(2.0, 4.0)
    return [(0, y, 0, .25, .25, .25, c[0], 0), (.6, y, 0, .35, .03, .2, c[1], 0), (-.6, y, 0, .35, .03, .2, c[1], 0)], True


def sc_tesla(rng, c):
    return [(0, .2, 0, .3, .2, .3, c[0], 0), (0, .7, 0, .12, .3, .12, shade(c[0], 1.1), 0),
            (0, 1.15, 0, .22, .08, .22, c[1], rng.random()), (0, 1.35, 0, .1, .1, .1, c[1], rng.random())], False


def sc_dreamcloud(rng, c):
    y = rng.uniform(1.6, 3.6)
    col = rng.choice(c)
    return [(0, y, 0, .6, .2, .4, col, 0), (.35, y + .12, .1, .35, .2, .3, col, 0), (-.35, y + .08, 0, .3, .16, .3, col, 0)], True


def sc_star(rng, c):
    y = rng.uniform(2.0, 4.2)
    return [(0, y, 0, .2, .2, .06, c[0], 0), (0, y, 0, .2, .2, .06, c[0], .785)], True


SCEN.update(column=sc_column, ruin=sc_ruin, coral=sc_coral, kelp=sc_kelp, jelly=sc_jelly, spike=sc_spike,
            floatisle=sc_floatisle, barrel=sc_barrel, deadtree=sc_deadtree, panel=sc_panel, satellite=sc_satellite,
            tesla=sc_tesla, dreamcloud=sc_dreamcloud, star=sc_star)

WORLDS += [
    _world("Cyber City", (22, 30, 52), (18, 24, 44), (0, 180, 220), (10, 14, 30), (14, 20, 38), (8, 10, 24),
           ((2, 6, 28), (0, 90, 140)), ("moon", (120, 255, 255), (0.25, 0.22)), 70, None,
           ((20, 60, 110), (12, 40, 80)),
           [("pylon", 6, ((0, 255, 255), (255, 0, 180), (255, 230, 60))), ("satellite", 3, ((60, 70, 100), (0, 200, 255)))],
           "rain", (0, 255, 255), True),
    _world("Ancient Ruins", (170, 150, 110), (156, 138, 100), (150, 125, 90), (100, 80, 56), (150, 135, 95),
           (100, 80, 55), ((60, 110, 170), (240, 210, 150)), ("sun", (255, 235, 170), (0.7, 0.2)), 0, (250, 240, 215),
           ((190, 150, 110), (150, 120, 85)),
           [("column", 5, ((200, 190, 165),)), ("ruin", 4, ((170, 160, 135),)), ("rock", 2, ((150, 140, 120),))],
           "dust", (255, 200, 110)),
    _world("Deep Ocean", (30, 100, 140), (24, 88, 128), (60, 150, 170), (16, 50, 80), (24, 80, 120), (12, 40, 70),
           ((2, 20, 60), (20, 120, 170)), ("moon", (180, 240, 255), (0.3, 0.2)), 0, None, ((16, 70, 110), (10, 50, 90)),
           [("coral", 5, ((255, 110, 130), (255, 170, 80), (190, 110, 255))), ("kelp", 4, ((40, 160, 90),)),
            ("jelly", 3, ((255, 140, 230), (140, 230, 255)))], "bubbles", (140, 255, 255)),
    _world("Crystal Caverns", (60, 50, 100), (52, 42, 90), (140, 90, 220), (30, 24, 56), (50, 40, 84), (26, 20, 48),
           ((8, 4, 24), (60, 30, 100)), ("moon", (210, 180, 255), (0.7, 0.18)), 60, None, ((50, 36, 90), (34, 24, 68)),
           [("crystal", 6, ((200, 120, 255),)), ("spike", 4, ((150, 100, 230), (100, 200, 255))),
            ("mushroom", 2, ((130, 255, 220), (255, 150, 230)))], "sparks", (200, 140, 255)),
    _world("Sky Islands", (120, 200, 120), (108, 186, 110), (230, 230, 240), (140, 100, 70), (130, 205, 130),
           (150, 110, 80), ((60, 150, 240), (210, 240, 255)), ("sun", (255, 250, 200), (0.78, 0.18)), 0, (255, 255, 255),
           None, [("floatisle", 4, ((140, 105, 75), (100, 190, 100))), ("tree", 3, ((100, 70, 45), (60, 160, 80), (90, 190, 100))),
                  ("flower", 3, None)], "petals", (255, 255, 200)),
    _world("Toxic Wasteland", (92, 100, 52), (82, 90, 44), (120, 130, 60), (50, 56, 30), (84, 94, 44), (46, 50, 26),
           ((30, 40, 10), (150, 170, 40)), ("sun", (210, 255, 80), (0.3, 0.22)), 0, (90, 110, 40),
           ((70, 84, 30), (50, 64, 24)),
           [("barrel", 4, ((90, 220, 60), (210, 255, 80))), ("deadtree", 4, ((50, 42, 34),)),
            ("mushroom", 3, ((170, 255, 60), (255, 230, 60)))], "ash", (190, 255, 60)),
    _world("Space Station", (92, 98, 116), (82, 88, 106), (130, 150, 190), (50, 56, 74), (60, 66, 86), (36, 40, 56),
           ((2, 3, 14), (22, 28, 60)), ("planet", (90, 150, 240), (0.75, 0.3)), 140, None, None,
           [("panel", 5, ((120, 130, 150), (80, 220, 255))), ("satellite", 4, ((150, 160, 180), (90, 140, 255)))],
           "stardust", (120, 220, 255)),
    _world("Black Hole", (44, 30, 70), (36, 24, 60), (150, 80, 230), (18, 12, 34), (30, 20, 54), (14, 8, 28),
           ((0, 0, 6), (40, 8, 70)), ("planet", (30, 10, 50), (0.5, 0.3)), 180, None, None,
           [("asteroid", 6, ((70, 50, 100),)), ("crystal", 3, ((170, 90, 255),)), ("star", 2, ((255, 220, 120),))],
           "stardust", (200, 120, 255)),
    _world("Electric Grid", (40, 44, 58), (34, 38, 50), (255, 230, 60), (20, 22, 30), (30, 34, 46), (16, 18, 26),
           ((8, 10, 28), (60, 70, 130)), ("moon", (255, 255, 180), (0.72, 0.2)), 50, (50, 56, 90),
           ((46, 54, 92), (32, 38, 70)),
           [("tesla", 5, ((90, 96, 120), (120, 220, 255))), ("pylon", 4, ((255, 230, 60), (120, 200, 255)))],
           "rain", (255, 240, 110), True),
    _world("Dream World", (210, 170, 240), (198, 156, 232), (130, 190, 255), (150, 110, 190), (220, 180, 250),
           (160, 120, 200), ((120, 60, 200), (255, 190, 235)), ("moon", (255, 245, 210), (0.7, 0.2)), 90, (255, 215, 245),
           ((180, 120, 230), (150, 100, 210)),
           [("dreamcloud", 5, ((255, 235, 250), (210, 230, 255))), ("star", 3, ((255, 240, 140),)),
            ("lollipop", 2, ((255, 110, 200), (120, 200, 255), (255, 240, 120))),
            ("gumdrop", 2, ((200, 160, 255), (160, 255, 220)))], "sprinkles", (255, 220, 255)),
]
assert len(WORLDS) == 20
# per-world extras: weather list, favoured event, unique obstacle (name, colour), brightness, default music
_WX = {
    "Meadow":         (["petals"], "golden_rush", ("Boulder", (150, 150, 150)), 1.0, "dawn_drift"),
    "Desert":         (["dust"], "speed_storm", ("Tumbleweed", (190, 140, 70)), 1.05, "wanderers_road"),
    "Glacier":        (["snow"], "dark_mode", ("Ice Block", (160, 220, 255)), 1.0, "still_waters"),
    "Volcano":        (["embers", "ash"], "speed_storm", ("Lava Blob", (255, 90, 30)), 0.95, "dragon_rush"),
    "Neon City":      (["rain", "sparks"], "coin_rain", ("Drone", (255, 60, 220)), 0.9, "neon_chase"),
    "Moonlit Forest": (["fireflies"], "dark_mode", ("Shadow", (60, 40, 90)), 0.85, "moonlit_pond"),
    "Candy Land":     (["sprinkles"], "fruit_frenzy", ("Gumball", (255, 100, 150)), 1.05, "cloud_garden"),
    "Tropical Beach": (["bubbles"], "fruit_frenzy", ("Crab", (255, 120, 80)), 1.05, "lantern_glow"),
    "Autumn Hills":   (["leaves"], "golden_rush", ("Pumpkin", (240, 130, 30)), 0.98, "ancient_trails"),
    "Cosmos":         (["stardust"], "coin_rain", ("Comet", (200, 220, 255)), 0.9, "starfarer"),
    "Cyber City":     (["rain", "sparks"], "speed_storm", ("Security Bot", (0, 220, 255)), 0.9, "pulse_runner"),
    "Ancient Ruins":  (["dust"], "golden_rush", ("Golem", (170, 160, 130)), 1.0, "ancient_trails"),
    "Deep Ocean":     (["bubbles"], "dark_mode", ("Jellyfish", (255, 140, 230)), 0.85, "deep_expedition"),
    "Crystal Caverns": (["sparks"], "coin_rain", ("Crystal Golem", (200, 120, 255)), 0.88, "lantern_glow"),
    "Sky Islands":    (["petals"], "fruit_frenzy", ("Storm Cloud", (200, 205, 225)), 1.08, "skybound"),
    "Toxic Wasteland": (["ash"], "dark_mode", ("Toxic Blob", (160, 255, 60)), 0.9, "thunder_run"),
    "Space Station":  (["stardust"], "speed_storm", ("Repair Bot", (150, 160, 190)), 0.92, "starfarer"),
    "Black Hole":     (["stardust"], "dark_mode", ("Void Orb", (120, 60, 200)), 0.8, "turbo_serpent"),
    "Electric Grid":  (["rain"], "speed_storm", ("Spark", (255, 240, 100)), 0.92, "thunder_run"),
    "Dream World":    (["sprinkles", "stardust"], "fruit_frenzy", ("Nightmare", (140, 80, 200)), 1.0, "cloud_garden"),
}
for _w in WORLDS:
    _x = _WX[_w["name"]]
    _w.update(id=slug(_w["name"]), weather=_x[0], event=_x[1], obst=_x[2], bright=_x[3], music=_x[4],
              fog=mix(_w["sky"][1], (0, 0, 0), 0.15))
WORLD_IDX = {w["id"]: i for i, w in enumerate(WORLDS)}
# (price, requirement) for each world; the original 10 are free from the start
_WORLD_UNLOCK = {10: (0, ("level", 10)), 11: (0, ("level", 12)), 12: (2500, ("level", 8)), 13: (0, ("level", 16)),
                 14: (3000, ("level", 10)), 15: (0, ("level", 18)), 16: (3500, ("level", 14)),
                 17: (0, ("ach", "boss_slayer")), 18: (4000, ("level", 20)), 19: (0, ("level", 30))}

SCEN_COUNT = 30
_SCEN_CACHE = {}


def get_scenery(widx):
    key = (widx, SCEN_COUNT)
    if key in _SCEN_CACHE:
        return _SCEN_CACHE[key]
    wd = WORLDS[widx]
    rng = random.Random(1000 + widx)
    pool = wd["scen"]
    objs, tries = [], 0
    while len(objs) < SCEN_COUNT and tries < 600:
        tries += 1
        x, z = rng.uniform(-14.8, 14.8), rng.uniform(-14.8, 14.8)
        if abs(x) < N / 2 + 1.8 and abs(z) < N / 2 + 1.8:
            continue
        if any((x - o[0]) ** 2 + (z - o[1]) ** 2 < 4 for o in objs):
            continue
        kind, _, cols = rng.choices(pool, weights=[p[1] for p in pool])[0]
        boxes, fl = SCEN[kind](rng, cols)
        objs.append((x, z, boxes, fl, rng.random() * 6.28))
    _SCEN_CACHE[key] = objs
    return objs


# --------------------------------------------------------------------------- #
#  Maps
# --------------------------------------------------------------------------- #
def _border():
    return {(x, y) for x in range(N) for y in range(N) if x in (0, N - 1) or y in (0, N - 1)}


def _seg(w, a, b):
    for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1):
        for y in range(min(a[1], b[1]), max(a[1], b[1]) + 1):
            w.add((x, y))


def map_classic():
    return set()


def map_arena():
    return _border()


def map_pillars():
    w = _border()
    for a in (3, 7, 12, 16):
        for b in (3, 7, 12, 16):
            for dx in (0, 1):
                for dy in (0, 1):
                    w.add((a + dx, b + dy))
    return w


def map_cross():
    w = _border()
    for i in range(5, 16):
        if abs(i - 10) >= 2:
            w.add((i, 10))
            w.add((10, i))
    return w


def map_corridors():
    w = _border()
    for x in range(1, 17):
        w.add((x, 4))
        w.add((x, 12))
    for x in range(4, 20):
        w.add((x, 8))
        w.add((x, 16))
    return w


def map_fortress():
    w = _border()
    for i in range(3, 18):
        for (x, y) in ((i, 3), (i, 17), (3, i), (17, i)):
            along = x if y in (3, 17) else y
            if abs(along - 10) >= 2:
                w.add((x, y))
    for i in range(7, 14):
        w.add((i, 7))
        w.add((i, 13))
        if i != 10:
            w.add((7, i))
            w.add((13, i))
    return w


def map_diamond():
    w = _border()
    for x in range(N):
        for y in range(N):
            dx, dy = x - 10, y - 10
            if abs(dx) + abs(dy) == 8 and dx != 0 and dy != 0:
                w.add((x, y))
    w.update({(8, 8), (12, 8), (8, 12), (12, 12)})
    return w


def map_spiral():
    w = _border()
    for a, b in (((3, 3), (17, 3)), ((17, 3), (17, 17)), ((17, 17), (3, 17)), ((3, 17), (3, 7)),
                 ((3, 7), (13, 7)), ((13, 7), (13, 13)), ((13, 13), (7, 13)), ((7, 13), (7, 10))):
        _seg(w, a, b)
    return w


def map_maze(seed=11, rooms=0):
    rng = random.Random(seed)
    w = {(x, y) for x in range(N) for y in range(N)}
    cells = [(x, y) for x in range(1, N, 2) for y in range(1, N, 2)]
    seen, stack = {(1, 1)}, [(1, 1)]
    w.discard((1, 1))
    while stack:
        x, y = stack[-1]
        opts = [(x + dx, y + dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2))
                if 1 <= x + dx <= N - 2 and 1 <= y + dy <= N - 2 and (x + dx, y + dy) not in seen]
        if not opts:
            stack.pop()
            continue
        nx, ny = rng.choice(opts)
        w.discard(((x + nx) // 2, (y + ny) // 2))
        w.discard((nx, ny))
        seen.add((nx, ny))
        stack.append((nx, ny))
    for (x, y) in cells:                                       # braid: remove dead ends
        if sum(1 for dx, dy in DIRS if (x + dx, y + dy) not in w) == 1:
            cand = [(x + dx, y + dy) for dx, dy in DIRS if (x + dx, y + dy) in w
                    and 1 <= x + 2 * dx <= N - 2 and 1 <= y + 2 * dy <= N - 2]
            if cand:
                w.discard(rng.choice(cand))
    for _ in range(rooms):
        cx, cy = rng.randrange(3, 18, 2), rng.randrange(3, 18, 2)
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                w.discard((cx + a, cy + b))
    return w


def map_islands():
    w = set()
    for ox in (3, 15):
        for oy in (3, 15):
            for dx in range(3):
                for dy in range(3):
                    w.add((ox + dx, oy + dy))
    w.update({(10, 5), (10, 15), (16, 10)})
    return w


def map_orchard():
    return {(x, y) for x in range(2, 19, 4) for y in range(2, 19, 4)}


def map_xmarks():
    w = _border()
    for i in range(3, 9):
        w.update({(i, i), (N - 1 - i, N - 1 - i), (N - 1 - i, i), (i, N - 1 - i)})
    return w


# name, description, wraps?, builder, spawn (x, y, direction)
MAPS = [
    ("Classic",    "Open field - the edges wrap around.",            True,  map_classic,   (4, 10, RIGHT)),
    ("Arena",      "A walled arena. Simple and honest.",             False, map_arena,     (4, 10, RIGHT)),
    ("Pillars",    "Sixteen stone blocks to weave through.",         False, map_pillars,   (4, 10, RIGHT)),
    ("Crossroads", "A giant plus-shaped wall in the middle.",        False, map_cross,     (4, 4, RIGHT)),
    ("Corridors",  "Long zig-zag lanes. Mind the turns!",            False, map_corridors, (4, 10, RIGHT)),
    ("Fortress",   "Concentric rings with narrow gates.",            False, map_fortress,  (4, 10, RIGHT)),
    ("Diamond",    "A diamond ring with four tiny gates.",           False, map_diamond,   (4, 10, RIGHT)),
    ("Spiral",     "Follow the spiral to the centre room.",          False, map_spiral,    (1, 5, DOWN)),
    ("Maze",       "A winding maze with no dead ends.",              False, map_maze,      (5, 1, RIGHT)),
    ("Islands",    "Wrap-around sea with four rocky islands.",       True,  map_islands,   (4, 10, RIGHT)),
    ("Orchard",    "Wrap-around grove of lonely pillars.",           True,  map_orchard,   (4, 4, RIGHT)),
    ("X Marks",    "Diagonal barriers form a big X.",                False, map_xmarks,    (4, 10, RIGHT)),
]


def neighbors(c, blocked, wrap):
    x, y = c
    for dx, dy in DIRS:
        nx, ny = x + dx, y + dy
        if wrap:
            nx %= N
            ny %= N
        elif not (0 <= nx < N and 0 <= ny < N):
            continue
        if (nx, ny) not in blocked:
            yield (nx, ny)


def reachable(start, blocked, wrap):
    seen = {start}
    dq = deque([start])
    while dq:
        c = dq.popleft()
        for n in neighbors(c, blocked, wrap):
            if n not in seen:
                seen.add(n)
                dq.append(n)
    return seen


def flood_count(start, blocked, wrap, limit):
    seen = {start}
    dq = deque([start])
    while dq and len(seen) < limit:
        c = dq.popleft()
        for n in neighbors(c, blocked, wrap):
            if n not in seen:
                seen.add(n)
                dq.append(n)
    return len(seen)


def build_walls(map_idx, level, rng):
    """Base layout + level obstacles. Keeps every free cell connected and the spawn lane clear."""
    _, _, wrap, builder, (sx, sy, sd) = MAPS[map_idx]
    walls = builder()
    for k in range(-3, 9):
        walls.discard(((sx + sd[0] * k) % N, (sy + sd[1] * k) % N))
    region = reachable((sx, sy), walls, wrap)
    for x in range(N):
        for y in range(N):
            if (x, y) not in region:
                walls.add((x, y))
    total = len(region)
    protected = {c for c in region if max(abs(c[0] - sx), abs(c[1] - sy)) <= 5}
    cells = [c for c in region if c not in protected]
    want, placed, tries = min(level - 1, 9) * 2, 0, 0
    while placed < want and tries < 500 and cells:
        tries += 1
        c = rng.choice(cells)
        if c in walls:
            continue
        walls.add(c)
        ok = len(reachable((sx, sy), walls, wrap)) == total - placed - 1
        if ok:
            ok = all(sum(1 for _ in neighbors(n, walls, wrap)) >= 2 for n in neighbors(c, walls, wrap))
        if ok:
            placed += 1
        else:
            walls.discard(c)
    return walls





# ---- 14 additional maps
def map_twin():
    w = _border()
    for a in (3, 13):
        for dx in range(5):
            for dy in range(5):
                w.add((a + dx, a + dy))
    return w


def map_ring():
    w = _border()
    for x in range(N):
        for y in range(N):
            if 6.0 <= math.hypot(x - 10, y - 10) <= 7.3 and abs(x - 10) > 1:
                w.add((x, y))
    return w


def map_tunnel():
    w = _border()
    for x in range(2, 19):
        w.add((x, 8))
        w.add((x, 12))
    return w


def map_checker():
    return {(x, y) for x in range(2, 19, 2) for y in range(2, 19, 2) if ((x + y) // 2) % 2 == 0}


def map_grid():
    w = _border()
    for i in range(1, 20):
        for line in (7, 13):
            if i not in (4, 10, 16):
                w.add((line, i))
                w.add((i, line))
    return w


def map_tower():
    w = _border()
    for x in range(8, 13):
        for y in range(8, 13):
            w.add((x, y))
    w.update({(5, 5), (15, 5), (5, 15), (15, 15)})
    return w


def map_corners():
    w = _border()
    for i in range(6):
        for (cx, cy, sx, sy) in ((2, 2, 1, 1), (18, 2, -1, 1), (2, 18, 1, -1), (18, 18, -1, -1)):
            w.add((cx + sx * i, cy))
            w.add((cx, cy + sy * i))
    return w


def map_pit():
    w = _border()
    for i in range(6, 15):
        w.add((i, 6))
        w.add((i, 14))
        if i != 10:
            w.add((6, i))
            w.add((14, i))
    w.update({(9, 9), (11, 9), (9, 11), (11, 11)})
    return w


def map_infinity():
    w = _border()
    for cx in (6, 14):
        for x in range(N):
            for y in range(N):
                if 3.0 <= math.hypot(x - cx, y - 10) <= 4.3 and x != cx:
                    w.add((x, y))
    return w


def map_reactor():
    w = _border()
    for x in range(9, 12):
        for y in range(9, 12):
            w.add((x, y))
    for i in range(5, 8):
        w.update({(10, i), (10, 20 - i), (i, 10), (20 - i, 10)})
    w.update({(6, 6), (14, 6), (6, 14), (14, 14)})
    return w


def map_floating():
    r = random.Random(5)
    w = set()
    for _ in range(7):
        cx, cy, rad = r.randrange(3, 18), r.randrange(3, 18), r.uniform(1.2, 2.2)
        for x in range(N):
            for y in range(N):
                if math.hypot(x - cx, y - cy) <= rad:
                    w.add((x, y))
    return w


def map_boss():
    w = _border()
    for (a, b) in ((5, 5), (15, 5), (5, 15), (15, 15)):
        w.update({(a, b), (a + 1, b), (a, b + 1), (a + 1, b + 1)})
    return w


def map_zigzag():
    w = _border()
    for x, (y0, y1) in ((5, (1, 14)), (9, (6, 19)), (13, (1, 14)), (17, (6, 19))):
        for y in range(y0, y1 + 1):
            w.add((x, y))
    return w


MAPS += [
    ("Twin Islands",     "Two heavy islands in a walled sea.",            False, map_twin,     (4, 10, RIGHT)),
    ("Ring",             "A round ring with north & south gates.",        False, map_ring,     (4, 10, RIGHT)),
    ("Labyrinth",        "A big maze with open chambers.",                False, lambda: map_maze(23, 3), (5, 1, RIGHT)),
    ("Tunnel",           "A long tunnel with open ends.",                 False, map_tunnel,   (4, 10, RIGHT)),
    ("Checker",          "Pillars laid out like a checkerboard.",         False, map_checker,  (4, 10, RIGHT)),
    ("Grid",             "Nine rooms linked by small gates.",             False, map_grid,     (4, 10, RIGHT)),
    ("Central Tower",    "A tower in the middle, guarded by pillars.",    False, map_tower,    (4, 4, RIGHT)),
    ("Four Corners",     "L-shaped walls guard each corner.",             False, map_corners,  (4, 10, RIGHT)),
    ("Snake Pit",        "A walled pit with four posts inside.",          False, map_pit,      (4, 10, RIGHT)),
    ("Infinity",         "Two linked loops shaped like an infinity sign.", False, map_infinity, (4, 10, RIGHT)),
    ("Reactor",          "A glowing core with cooling rods.",             False, map_reactor,  (4, 4, RIGHT)),
    ("Floating Islands", "Wrap-around sky with drifting rocks.",          True,  map_floating, (4, 10, RIGHT)),
    ("Boss Arena",       "Open arena built for boss fights.",             False, map_boss,     (4, 10, RIGHT)),
    ("Zigzag",           "Long serpentine lanes - take your time.",       False, map_zigzag,   (2, 5, DOWN)),
]
assert len(MAPS) == 26
BOSS_MAP = 24
_MAP_UNLOCK_LEVEL = {12: 2, 13: 3, 14: 6, 15: 4, 16: 5, 17: 7, 18: 9, 19: 11, 20: 13, 21: 15, 22: 17, 23: 19, 24: 0, 25: 22}



# --------------------------------------------------------------------------- #
#  Gameplay content: fruits, power-ups, events, objectives, bosses, challenges
# --------------------------------------------------------------------------- #
# id: (name, colour, score x, coins, xp)
FRUITS = {
    "apple":      ("Apple", (235, 60, 60), 1.0, 5, 3),
    "orange":     ("Orange", (255, 150, 40), 1.0, 5, 3),
    "banana":     ("Banana", (250, 220, 70), 1.0, 5, 3),
    "strawberry": ("Strawberry", (240, 50, 90), 1.1, 6, 3),
    "grape":      ("Grape", (150, 70, 200), 1.1, 6, 3),
    "watermelon": ("Watermelon", (60, 170, 80), 1.2, 6, 4),
    "pineapple":  ("Pineapple", (240, 200, 60), 1.2, 7, 4),
    "cherry":     ("Cherry", (200, 20, 50), 1.3, 7, 4),
    "blueberry":  ("Blueberry", (70, 90, 220), 1.3, 7, 4),
    "golden":     ("Golden Fruit", GOLD_COL, 5.0, 25, 15),
    "crystal":    ("Crystal Fruit", (140, 240, 255), 10.0, 50, 30),
    "plasma":     ("Plasma Fruit", (255, 70, 230), 15.0, 75, 45),
}
NORMAL_FRUITS = ["apple", "orange", "banana", "strawberry", "grape", "watermelon", "pineapple", "cherry", "blueberry"]
SPECIAL_FRUITS = ["golden", "crystal", "plasma"]

# id: (name, colour, base duration seconds, short description)
POWERUPS = {
    "speed":  ("Speed Boost", (255, 150, 40), 6.0, "Move 30% faster"),
    "slow":   ("Slow Motion", SLOW_COL, 6.0, "Slows the whole game"),
    "magnet": ("Magnet", (220, 80, 220), 8.0, "Pulls nearby pickups in"),
    "shield": ("Shield", (80, 230, 255), 20.0, "Absorbs one collision"),
    "dxp":    ("Double XP", (120, 255, 120), 15.0, "x2 XP"),
    "coinb":  ("Coin Boost", (255, 215, 60), 15.0, "x2 coins"),
    "mult":   ("Score x2", (255, 100, 100), 10.0, "x2 score"),
    "ghost":  ("Ghost Mode", (200, 200, 255), 6.0, "Pass through walls"),
    "freeze": ("Freeze", (160, 220, 255), 6.0, "Freezes hazards"),
    "time":   ("Time Bonus", (255, 255, 255), 0.0, "+10 seconds"),
}
EVENTS = {   # id: (banner, colour, duration)
    "golden_rush": ("GOLDEN RUSH!", GOLD_COL, 20.0),
    "coin_rain":   ("COIN RAIN!", COIN_COL, 8.0),
    "speed_storm": ("SPEED STORM!", (255, 120, 60), 15.0),
    "fruit_frenzy": ("FRUIT FRENZY!", (255, 110, 170), 1.0),
    "dark_mode":   ("DARK MODE!", (150, 150, 200), 15.0),
}
OBJ_TEXT = {
    "fruits":  "Collect {n} fruits",
    "score":   "Earn {n} points",
    "survive": "Survive {n} seconds",
    "combo":   "Reach a x{n} combo chain",
    "golden":  "Collect {n} special fruits",
    "coins":   "Collect {n} coins",
    "flawless": "Collect {n} fruits without crashing",
    "boss":    "Defeat the boss",
    "time":    "Score as much as you can",
}
OBJ_CYCLE = ["fruits", "score", "fruits", "combo", "survive", "golden", "flawless", "coins", "fruits", "score"]


def obj_target(kind, lvl):
    return {"fruits": 5 + lvl, "score": 100 + 45 * lvl, "survive": 20 + 3 * lvl, "combo": 3 + lvl // 2,
            "golden": 2 + lvl // 4, "coins": 4 + lvl // 2, "flawless": 5 + lvl, "boss": 1, "time": 0}[kind]


# id, name, kind, world, hp, body colour, accent, music, coins, xp, description
BOSSES = [
    dict(id="giant_cobra", name="GIANT COBRA", kind="cobra", world=1, hp=6, col=(90, 170, 60), acc=(255, 220, 80),
         music="boss_giant_cobra", coins=600, xp=600, desc="It hunts you across the dunes. Eat glowing fruit to wound it."),
    dict(id="cyber_worm", name="CYBER WORM", kind="worm", world=10, hp=7, col=(0, 255, 220), acc=(255, 0, 180),
         music="boss_cyber_worm", coins=800, xp=800, desc="Leaves glitch walls behind. Don't get boxed in."),
    dict(id="lava_dragon", name="LAVA DRAGON", kind="dragon", world=3, hp=8, col=(255, 90, 30), acc=(255, 220, 80),
         music="boss_lava_dragon", coins=1000, xp=1000, desc="Watch for warning lines - then run!"),
    dict(id="void_serpent", name="VOID SERPENT", kind="void", world=17, hp=9, col=(150, 80, 255), acc=(230, 160, 255),
         music="boss_void_serpent", coins=1300, xp=1300, desc="Opens voids beneath you. Keep moving."),
    dict(id="space_leviathan", name="SPACE LEVIATHAN", kind="leviathan", world=16, hp=10, col=(130, 150, 190),
         acc=(120, 220, 255), music="boss_space_leviathan", coins=1800, xp=1800,
         desc="A huge ship plus incoming meteors."),
]

# fixed challenge levels: id, name, desc, map, world, objective, lives, speed x, roamers, dark, coins, xp
CHALLENGES = [
    dict(id="speed_demon", name="Speed Demon", desc="Everything is 35% faster. Only 2 lives.", map=1, world=3,
         obj=("fruits", 12), lives=2, speed=1.35, roamers=0, dark=False, coins=400, xp=500),
    dict(id="blackout", name="Blackout Tunnel", desc="The lights are off. Feel your way through.", map=15, world=5,
         obj=("fruits", 10), lives=3, speed=1.0, roamers=0, dark=True, coins=400, xp=500),
    dict(id="minefield", name="Minefield", desc="Four roaming hazards. No crashing allowed.", map=16, world=15,
         obj=("flawless", 10), lives=3, speed=1.0, roamers=4, dark=False, coins=450, xp=550),
    dict(id="gold_rush", name="Gold Rush", desc="Hunt down special fruits.", map=0, world=1,
         obj=("golden", 6), lives=3, speed=1.0, roamers=0, dark=False, coins=400, xp=500),
    dict(id="combo_king", name="Combo King", desc="Chain 12 fruits in a row.", map=17, world=4,
         obj=("combo", 12), lives=3, speed=1.1, roamers=0, dark=False, coins=500, xp=600),
    dict(id="coin_chaser", name="Coin Chaser", desc="Grab 15 coins floating around the sky.", map=23, world=14,
         obj=("coins", 15), lives=3, speed=1.0, roamers=1, dark=False, coins=400, xp=500),
    dict(id="maze_runner", name="Maze Runner", desc="Survive 60 seconds in the maze.", map=8, world=11,
         obj=("survive", 60), lives=3, speed=1.0, roamers=3, dark=False, coins=450, xp=550),
    dict(id="iron_snake", name="Iron Snake", desc="Score 1200 with a single life.", map=7, world=2,
         obj=("score", 1200), lives=1, speed=1.1, roamers=0, dark=False, coins=600, xp=700),
]
ADV_STAGES = 25


def adventure_stage(i):
    """Definition of adventure stage i (1..25)."""
    playable = [k for k in range(len(MAPS)) if k != BOSS_MAP]
    level = 1 + (i - 1) * 9 // (ADV_STAGES - 1)
    boss = BOSSES[i // 5 - 1] if i % 5 == 0 else None
    if boss:
        return dict(stage=i, level=level, map=BOSS_MAP, world=boss["world"], obj=("boss", 1), boss=boss)
    widx = (i - 1) % 20 if i <= 20 else (i - 21) * 4 + 1
    kind = OBJ_CYCLE[(i - 1) % len(OBJ_CYCLE)]
    return dict(stage=i, level=level, map=playable[((i - 1) * 3) % len(playable)], world=widx,
                obj=(kind, obj_target(kind, level)), boss=None)


# --------------------------------------------------------------------------- #
#  Cosmetics + shop catalog
# --------------------------------------------------------------------------- #
RARITY_PRICE = {"common": 500, "rare": 1500, "epic": 3500, "legendary": 7500}
RARITY_COL = {"common": (190, 200, 215), "rare": (90, 160, 255), "epic": (190, 110, 255), "legendary": (255, 190, 60)}

SKIN_DEFS = {   # id: (name, rarity, req, b0, b1, acc, pattern, head colour)
    "neon":    ("Neon", "common", None, (0, 230, 255), (255, 0, 200), (255, 255, 120), "glow", (120, 255, 255)),
    "fire":    ("Fire", "rare", None, (255, 200, 40), (200, 30, 10), (255, 255, 160), "flame", (255, 230, 120)),
    "ice":     ("Ice", "common", None, (170, 230, 255), (80, 140, 230), (255, 255, 255), "gradient", (225, 245, 255)),
    "toxic":   ("Toxic", "rare", None, (150, 255, 40), (40, 120, 20), (230, 255, 80), "spots", (200, 255, 90)),
    "galaxy":  ("Galaxy", "epic", ("ach", "world_explorer"), (50, 30, 130), (10, 5, 50), (255, 255, 255), "galaxy", (140, 110, 255)),
    "gold":    ("Gold", "epic", None, (255, 220, 90), (190, 130, 20), (255, 255, 230), "stripes", (255, 240, 150)),
    "cyber":   ("Cyber", "rare", None, (30, 60, 90), (10, 20, 40), (0, 255, 200), "checker", (120, 255, 255)),
    "shadow":  ("Shadow", "common", None, (60, 60, 80), (15, 15, 25), (120, 60, 200), "gradient", (90, 90, 115)),
    "crystal": ("Crystal", "epic", None, (150, 240, 255), (90, 150, 240), (255, 255, 255), "checker", (210, 250, 255)),
    "rainbow": ("Rainbow", "legendary", None, (255, 255, 255), (255, 255, 255), (255, 255, 255), "rainbow", (255, 140, 200)),
}
HEAD_DEFS = {"block": ("Classic Block", "common", 0), "viper": ("Viper", "common", 1), "bulldog": ("Bulldog", "common", 1),
             "robot": ("Robot", "rare", 1), "dragon": ("Dragon", "epic", 1)}
HAT_DEFS = {   # id: (name, rarity, req)
    "crest": ("Crest", "common", None), "horns": ("Horns", "common", None), "party": ("Party Hat", "common", None),
    "headband": ("Headband", "common", None), "pumpkin": ("Pumpkin Stem", "common", None), "cap": ("Ball Cap", "common", None),
    "shades": ("Cool Shades", "common", None), "flower": ("Flower", "common", None),
    "crown": ("Crown", "rare", None), "wizard": ("Wizard Hat", "rare", None), "antenna": ("Antenna", "rare", None),
    "tophat": ("Top Hat", "rare", None), "cowboy": ("Cowboy Hat", "rare", None),
    "halo": ("Halo", "epic", None), "viking": ("Viking Helmet", "epic", ("level", 12)),
}
TRAIL_DEFS = {"spark": ("Spark Trail", "common", None), "smoke": ("Smoke Trail", "common", None),
              "fire": ("Fire Trail", "rare", None), "neon": ("Neon Trail", "rare", None),
              "galaxy": ("Galaxy Trail", "epic", None), "lightning": ("Lightning Trail", "epic", ("ach", "combo_master"))}
EFFECT_DEFS = {"confetti": ("Confetti Pop", "common"), "sparkle": ("Sparkle Burst", "common"), "pixel": ("Pixel Pop", "common"),
               "stars": ("Star Shower", "rare"), "fire": ("Flame Burst", "rare")}
THEME_DEFS = {   # id: (name, rarity, accent, panel, text-dim)
    "classic":  ("Classic Green", "common", (130, 255, 160), (8, 12, 28)),
    "midnight": ("Midnight Blue", "common", (120, 170, 255), (6, 8, 34)),
    "sunset":   ("Sunset", "common", (255, 170, 90), (34, 12, 14)),
    "forest":   ("Deep Forest", "rare", (140, 230, 120), (8, 28, 16)),
    "neon":     ("Neon Night", "rare", (255, 80, 220), (16, 6, 28)),
    "royal":    ("Royal Gold", "epic", (255, 215, 90), (24, 10, 38)),
}
BG_DEFS = {   # id: (name, rarity, world id or None for auto-rotate)
    "auto":    ("Auto Rotate", "common", None), "meadow": ("Meadow", "common", "meadow"),
    "cosmos":  ("Cosmos", "common", "cosmos"), "sunset": ("Autumn Sunset", "common", "autumn_hills"),
    "neon":    ("Neon City", "rare", "neon_city"), "ocean": ("Deep Ocean", "rare", "deep_ocean"),
    "dream":   ("Dream World", "epic", "dream_world"), "hole": ("Black Hole", "epic", "black_hole"),
}
BOOSTER_DEFS = {   # id: (name, desc, price)
    "b_shield": ("Head-Start Shield", "Begin your next run with a 6 second shield.", 200),
    "b_magnet": ("Magnet Start", "Begin your next run with a 10 second magnet.", 200),
    "b_xp":     ("XP Charm", "+50% XP for your next run.", 250),
    "b_coin":   ("Coin Charm", "+50% coins for your next run.", 250),
    "b_life":   ("Extra Heart", "+1 life for your next run.", 400),
    "b_time":   ("Extra Time", "+15 seconds in timed modes.", 250),
}
ITEMS = {}


def add_item(cat, iid, name, desc, price=0, req=None, rarity="common", **kw):
    ITEMS[(cat, iid)] = dict(cat=cat, id=iid, name=name, desc=desc, price=price, req=req, rarity=rarity, **kw)


def _register_items():
    for c in CHARACTERS:
        r = "legendary" if c["price"] >= 7500 else "epic" if c["price"] >= 4000 else "rare" if c["price"] >= 1500 else "common"
        add_item("characters", c["id"], c["name"], c["perk"], c["price"], c["req"], r)
    add_item("skins", "default", "Character Default", "Use the character's own colours.")
    for k, (n, r, req, *_) in SKIN_DEFS.items():
        add_item("skins", k, n + " Skin", "A " + r + " body skin.", 0 if req else RARITY_PRICE[r], req, r)
    for k, (n, r, p) in HEAD_DEFS.items():
        add_item("heads", k, n + " Head", "A head style.", 0 if p == 0 else RARITY_PRICE[r], None, r)
    add_item("hats", "default", "Character Hat", "Use the character's own hat.")
    add_item("hats", "none", "No Hat", "Go bare-headed.")
    for k, (n, r, req) in HAT_DEFS.items():
        add_item("hats", k, n, "A hat for your snake.", RARITY_PRICE[r], req, r)
    add_item("trails", "none", "No Trail", "No trail behind the snake.")
    for k, (n, r, req) in TRAIL_DEFS.items():
        add_item("trails", k, n, "A visual trail behind the tail.", 0 if req else RARITY_PRICE[r], req, r)
    add_item("effects", "default", "Classic Burst", "The standard pickup burst.")
    for k, (n, r) in EFFECT_DEFS.items():
        add_item("effects", k, n, "Particle effect for pickups.", RARITY_PRICE[r], None, r)
    for k, (n, r, acc, pan) in THEME_DEFS.items():
        add_item("themes", k, n, "A colour theme for menus.", 0 if k == "classic" else RARITY_PRICE[r], None, r)
    for k, (n, r, w) in BG_DEFS.items():
        add_item("backgrounds", k, n, "Animated menu background.", 0 if k in ("auto", "meadow") else RARITY_PRICE[r], None, r)
    for k, (n, d, p) in BOOSTER_DEFS.items():
        add_item("boosters", k, n, d, p)
    for i, w in enumerate(WORLDS):
        p, req = _WORLD_UNLOCK.get(i, (0, None))
        r = "legendary" if p >= 4000 else "epic" if p >= 3000 else "rare" if p else "common"
        add_item("worlds", w["id"], w["name"], "World " + str(i + 1), p, req, r)
    for i, m in enumerate(MAPS):
        lv = _MAP_UNLOCK_LEVEL.get(i)
        add_item("maps", slug(m[0]), m[0], m[1], 0, ("level", lv) if lv else None)


_register_items()
SHOP_TABS = ["characters", "skins", "heads", "hats", "trails", "effects", "themes", "backgrounds", "music", "boosters"]
TAB_NAMES = {"characters": "Characters", "skins": "Skins", "heads": "Heads", "hats": "Hats", "trails": "Trails",
             "effects": "Effects", "themes": "UI Themes", "backgrounds": "Backgrounds", "music": "Music",
             "boosters": "Boosters"}
EQUIP_SLOT = {"characters": "character", "skins": "skin", "heads": "head", "hats": "hat", "trails": "trail",
              "effects": "effect", "themes": "theme", "backgrounds": "background"}
EQUIP_DEFAULT = {"character": "emerald_viper", "skin": "default", "head": "block", "hat": "default", "trail": "none",
                 "effect": "default", "theme": "classic", "background": "auto"}


def req_text(req):
    if not req:
        return ""
    if req[0] == "level":
        return "Reach player level %d" % req[1]
    a = next((x for x in ACHIEVEMENTS if x["id"] == req[1]), None)
    return "Achievement: " + (a["name"] if a else req[1])


# --------------------------------------------------------------------------- #
#  Missions (52) and achievements (40)
# --------------------------------------------------------------------------- #
def _m(cat, mid, name, stat, target, xp, coins, mode="sum", **kw):
    d = dict(id=mid, cat=cat, name=name, stat=stat, target=target, xp=xp, coins=coins, mode=mode)
    d.update(kw)
    return d


DAILY_POOL = [
    _m("daily", "d_fruit50", "Collect 50 fruits", "fruits", 50, 500, 250),
    _m("daily", "d_fruit30", "Collect 30 fruits", "fruits", 30, 300, 150),
    _m("daily", "d_fruit100", "Collect 100 fruits", "fruits", 100, 800, 400),
    _m("daily", "d_games3", "Play 3 games", "games", 3, 300, 150),
    _m("daily", "d_games5", "Play 5 games", "games", 5, 450, 220),
    _m("daily", "d_clear3", "Clear 3 levels", "levels_cleared", 3, 400, 200),
    _m("daily", "d_combo10", "Reach a x10 combo", "best_combo", 10, 450, 250, "max"),
    _m("daily", "d_power5", "Collect 5 power-ups", "powerups", 5, 300, 150),
    _m("daily", "d_golden3", "Collect 3 special fruits", "golden", 3, 350, 200),
    _m("daily", "d_coins100", "Collect 100 coins", "coins_collected", 100, 300, 200),
    _m("daily", "d_score1500", "Score 1500 in one run", "best_score", 1500, 400, 250, "max"),
    _m("daily", "d_time5", "Play for 5 minutes", "play_time", 300, 300, 150),
]
WEEKLY_POOL = [
    _m("weekly", "w_fruit300", "Collect 300 fruits", "fruits", 300, 1500, 900),
    _m("weekly", "w_combo20", "Reach a x20 combo", "best_combo", 20, 1500, 1000, "max"),
    _m("weekly", "w_score8000", "Earn 8000 total score", "total_score", 8000, 1400, 900),
    _m("weekly", "w_clear15", "Clear 15 levels", "levels_cleared", 15, 1400, 800),
    _m("weekly", "w_boss1", "Defeat a boss", "boss_wins", 1, 1800, 1200),
    _m("weekly", "w_power25", "Collect 25 power-ups", "powerups", 25, 1200, 700),
    _m("weekly", "w_games15", "Play 15 games", "games", 15, 1200, 700),
    _m("weekly", "w_coins1500", "Collect 1500 coins", "coins_collected", 1500, 1300, 800),
]
PERM_MISSIONS = []
for _i in range(12):
    PERM_MISSIONS.append(_m("world", "wm_%d" % _i, "Clear 3 levels in %s" % WORLDS[_i]["name"], "world_levels_%d" % _i,
                            3, 200 + 20 * _i, 120 + 15 * _i))
for _c in CHARACTERS[:10]:
    PERM_MISSIONS.append(_m("character", "cm_" + _c["id"], "Play 5 games as %s" % _c["name"], "char_games_" + _c["id"],
                            5, 250, 200))
PERM_MISSIONS += [
    _m("challenge", "c_flawless", "Clear a level without losing a life", "flawless_levels", 1, 400, 250),
    _m("challenge", "c_flawless5", "Clear 5 levels flawlessly", "flawless_levels", 5, 900, 600),
    _m("challenge", "c_combo15", "Reach a x15 combo in one run", "best_combo", 15, 700, 450, "max"),
    _m("challenge", "c_score3000", "Score 3000 in a single run", "best_score", 3000, 800, 500, "max"),
    _m("challenge", "c_survive120", "Survive 2 minutes in Survival", "survive_best", 120, 800, 500, "max"),
    _m("challenge", "c_ta1000", "Score 1000 in Time Attack", "ta_best", 1000, 700, 450, "max"),
    _m("challenge", "c_stars3", "Earn 3 stars on a level", "three_stars", 1, 500, 300),
    _m("challenge", "c_golden10", "Collect 10 special fruits", "golden", 10, 600, 400),
    _m("challenge", "c_boss", "Defeat the Giant Cobra", "boss_win_giant_cobra", 1, 900, 700),
    _m("challenge", "c_adv5", "Clear 5 Adventure stages", "adv_stage", 5, 700, 500, "max"),
]
ALL_MISSIONS = {m["id"]: m for m in DAILY_POOL + WEEKLY_POOL + PERM_MISSIONS}
assert len(ALL_MISSIONS) >= 50


def _a(aid, name, desc, stat, target, xp, coins):
    return dict(id=aid, name=name, desc=desc, stat=stat, target=target, xp=xp, coins=coins)


ACHIEVEMENTS = [
    _a("first_bite", "FIRST BITE", "Collect your first fruit.", "fruits", 1, 20, 50),
    _a("fruit_fan", "FRUIT FAN", "Collect 100 fruits.", "fruits", 100, 100, 100),
    _a("fruit_fanatic", "FRUIT FANATIC", "Collect 1,000 fruits.", "fruits", 1000, 300, 300),
    _a("fruit_titan", "FRUIT TITAN", "Collect 5,000 fruits.", "fruits", 5000, 1000, 1000),
    _a("combo_5", "COMBO STARTER", "Reach a x5 combo.", "best_combo", 5, 30, 50),
    _a("combo_10", "COMBO ADEPT", "Reach a x10 combo.", "best_combo", 10, 80, 100),
    _a("combo_master", "COMBO MASTER", "Reach a x20 combo.", "best_combo", 20, 200, 250),
    _a("combo_legend", "COMBO LEGEND", "Reach a x50 combo.", "best_combo", 50, 800, 800),
    _a("survivor", "SURVIVOR", "Complete a level without losing a life.", "flawless_levels", 1, 60, 100),
    _a("untouchable", "UNTOUCHABLE", "Complete 10 levels flawlessly.", "flawless_levels", 10, 300, 400),
    _a("pocket_change", "POCKET CHANGE", "Collect 500 coins.", "coins_collected", 500, 50, 50),
    _a("rich_snake", "RICH SNAKE", "Collect 10,000 coins.", "coins_collected", 10000, 400, 500),
    _a("shopper", "FIRST PURCHASE", "Buy something in the shop.", "purchases", 1, 30, 50),
    _a("collector", "COLLECTOR", "Buy 15 items.", "purchases", 15, 300, 300),
    _a("big_spender", "BIG SPENDER", "Spend 5,000 coins.", "coins_spent", 5000, 150, 100),
    _a("world_explorer", "WORLD EXPLORER", "Unlock 15 worlds.", "worlds_unlocked", 15, 250, 300),
    _a("world_master", "WORLD MASTER", "Unlock all 20 worlds.", "worlds_unlocked", 20, 800, 1000),
    _a("map_runner", "MAP RUNNER", "Unlock 20 maps.", "maps_unlocked", 20, 300, 300),
    _a("char_collector", "CHARACTER COLLECTOR", "Own 10 characters.", "characters_owned", 10, 300, 400),
    _a("squad_goals", "SQUAD GOALS", "Own all 20 characters.", "characters_owned", 20, 1000, 1500),
    _a("rookie", "ROOKIE", "Reach player level 5.", "level", 5, 40, 100),
    _a("veteran", "VETERAN", "Reach player level 25.", "level", 25, 400, 600),
    _a("legend", "LEGEND", "Reach player level 50.", "level", 50, 1000, 2000),
    _a("level_crusher", "LEVEL CRUSHER", "Clear 25 levels.", "levels_cleared", 25, 100, 150),
    _a("level_lord", "LEVEL LORD", "Clear 100 levels.", "levels_cleared", 100, 400, 500),
    _a("boss_slayer", "BOSS SLAYER", "Defeat your first boss.", "boss_wins", 1, 300, 400),
    _a("boss_hunter", "BOSS HUNTER", "Defeat 5 bosses.", "boss_wins", 5, 800, 1000),
    _a("gold_digger", "GOLD DIGGER", "Collect 25 special fruits.", "golden", 25, 150, 200),
    _a("power_user", "POWER USER", "Collect 50 power-ups.", "powerups", 50, 100, 150),
    _a("mission_man", "MISSION MAN", "Complete 10 missions.", "missions_done", 10, 150, 200),
    _a("mission_boss", "MISSION BOSS", "Complete 50 missions.", "missions_done", 50, 600, 800),
    _a("star_collector", "STAR COLLECTOR", "Earn 30 stars.", "stars_total", 30, 200, 250),
    _a("perfectionist", "PERFECTIONIST", "Earn 3 stars on 10 levels.", "three_stars", 10, 300, 300),
    _a("adventurer", "ADVENTURER", "Clear 10 Adventure stages.", "adv_stage", 10, 300, 400),
    _a("adventure_hero", "ADVENTURE HERO", "Clear all 25 Adventure stages.", "adv_stage", 25, 1000, 1500),
    _a("high_scorer", "HIGH SCORER", "Score 5,000 in a single run.", "best_score", 5000, 200, 250),
    _a("score_hero", "SCORE HERO", "Score 25,000 in a single run.", "best_score", 25000, 600, 800),
    _a("marathon", "MARATHON", "Play for one hour in total.", "play_time", 3600, 200, 250),
    _a("daily_hero", "DAILY HERO", "Complete 7 daily challenges.", "daily_done", 7, 300, 400),
    _a("streaker", "STREAKER", "Reach a 7 day login streak.", "streak_best", 7, 300, 500),
    _a("time_ace", "TIME ACE", "Score 1,500 in Time Attack.", "ta_best", 1500, 250, 300),
    _a("survival_pro", "SURVIVAL PRO", "Survive 3 minutes in Survival.", "survive_best", 180, 250, 300),
]
ACH_IDX = {a["id"]: a for a in ACHIEVEMENTS}
STREAK_REWARDS = [100, 150, 200, 250, 300, 400, 1000]      # coins for day 1..7 (day 7 also gives XP)



# --------------------------------------------------------------------------- #
#  Save system
# --------------------------------------------------------------------------- #
DEFAULT_SETTINGS = dict(quality=2, particles=True, shadows=True, shake=True, effects=True, weather=True,
                        music_vol=0.6, sfx_vol=0.8, mute=False, difficulty=1, camera=0, screen_fx=True,
                        ui_scale=1.0, reduce_motion=False, show_controls=True, music_mode="auto",
                        music_track="dawn_drift", sel_map="classic", sel_world="auto")


def default_save():
    return dict(version=VERSION, name="Player", xp=0, level=1, coins=500, stats={},
                owned={k: [] for k in ("characters", "skins", "heads", "hats", "trails", "effects", "themes",
                                       "backgrounds", "music", "worlds", "maps")},
                equipped=dict(EQUIP_DEFAULT), boosters={}, armed=[], achievements={},
                missions=dict(daily_key="", weekly_key="", daily=[], weekly=[], progress={}, claimed=[]),
                daily=dict(date="", char="", target=0, map=0, world=0, done=False, claimed=False),
                streak=dict(last="", count=0, best=0), settings=dict(DEFAULT_SETTINGS), scores=[],
                adventure=dict(stage=1, stars={}), seen_intro=False)


def _merge(default, loaded):
    """Overlay `loaded` on `default`, keeping only values of the right type (robust to bad/old saves)."""
    out = copy.deepcopy(default)
    if not isinstance(loaded, dict):
        return out
    for k, v in loaded.items():
        if k not in default:
            continue
        dv = default[k]
        if isinstance(dv, dict):
            if isinstance(v, dict):
                out[k] = _merge(dv, v) if dv else v
        elif isinstance(dv, bool):
            if isinstance(v, bool):
                out[k] = v
        elif isinstance(dv, (int, float)):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = v
        elif isinstance(v, type(dv)):
            out[k] = v
    return out


class SaveSystem:
    def __init__(self, path=SAVE_FILE):
        self.path = path
        self.status = ""
        self.last_save = 0.0
        self.dirty = False
        self.data = self.load()

    def load(self):
        data, bad = None, False
        for p in (self.path, self.path + ".bak"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if not isinstance(raw, dict):
                    raise ValueError("bad save")
                data = _merge(default_save(), raw)
                if p != self.path:
                    self.status = "Recovered from backup"
                break
            except FileNotFoundError:
                continue
            except Exception:
                bad = True
                continue
        if data is None:
            data = default_save()
            if bad:
                self.status = "Save was corrupted - started a new one"
                try:
                    os.replace(self.path, self.path + ".corrupt")
                except Exception:
                    pass
            if not data["scores"]:                        # import v1 high scores once
                try:
                    with open(OLD_SCORE_FILE, "r", encoding="utf-8") as f:
                        old = json.load(f)
                    data["scores"] = [d for d in old if isinstance(d, dict) and isinstance(d.get("score"), int)][:10]
                except Exception:
                    pass
        data["settings"] = _merge(DEFAULT_SETTINGS, data.get("settings", {}))
        return data

    def save(self):
        self.dirty = False
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f)
            if os.path.exists(self.path):
                try:
                    os.replace(self.path, self.path + ".bak")
                except Exception:
                    pass
            os.replace(tmp, self.path)
            self.last_save = time.time()
            return True
        except Exception:
            return False


# --------------------------------------------------------------------------- #
#  Player / progression / inventory / missions / achievements / shop
# --------------------------------------------------------------------------- #
def xp_for_level(level):
    return int(80 + 22 * level + 0.8 * level * level)


MAX_PLAYER_LEVEL = 100


class Player:
    def __init__(self, prog):
        self.p = prog

    @property
    def d(self):
        return self.p.d

    level = property(lambda s: s.d["level"])
    xp = property(lambda s: s.d["xp"])
    coins = property(lambda s: s.d["coins"])
    stats = property(lambda s: s.d["stats"])

    def xp_needed(self):
        return xp_for_level(self.level)

    def add_xp(self, n):
        n = int(n)
        if n <= 0 or self.level >= MAX_PLAYER_LEVEL:
            return 0
        self.d["xp"] += n
        gained = 0
        while self.d["level"] < MAX_PLAYER_LEVEL and self.d["xp"] >= xp_for_level(self.d["level"]):
            self.d["xp"] -= xp_for_level(self.d["level"])
            self.d["level"] += 1
            gained += 1
            bonus = 100 + 10 * self.d["level"]
            self.d["coins"] += bonus
            self.p.notify("LEVEL UP!  Level %d  (+%d coins)" % (self.d["level"], bonus), (255, 230, 90), "level")
            self.p.event("level", self.d["level"], "max")
        if self.d["level"] >= MAX_PLAYER_LEVEL:
            self.d["xp"] = 0
        if gained:
            self.p.refresh_unlocks()
        return gained

    def add_coins(self, n, earned=True):
        n = int(n)
        if n <= 0:
            return
        self.d["coins"] += n
        if earned:
            self.p.event("coins_collected", n)

    def spend(self, n):
        if self.d["coins"] < n:
            return False
        self.d["coins"] -= n
        self.p.event("coins_spent", n)
        return True


class Inventory:
    def __init__(self, prog):
        self.p = prog

    def owned(self, cat):
        return self.p.d["owned"].setdefault(cat, [])

    def owns(self, cat, iid):
        return iid in self.owned(cat)

    def grant(self, cat, iid, notify=True):
        if self.owns(cat, iid):
            return False
        self.owned(cat).append(iid)
        if notify and (cat, iid) in ITEMS:
            msg = {"characters": "NEW CHARACTER UNLOCKED!", "worlds": "WORLD UNLOCKED!", "maps": "NEW MAP UNLOCKED!",
                   "music": "NEW TRACK UNLOCKED!"}.get(cat, "NEW ITEM UNLOCKED!")
            self.p.notify("%s  %s" % (msg, ITEMS[(cat, iid)]["name"]), (140, 255, 170), "unlock")
        return True

    def req_met(self, req):
        if not req:
            return True
        if req[0] == "level":
            return self.p.d["level"] >= req[1]
        return req[1] in self.p.d["achievements"]

    def state(self, item):
        if self.owns(item["cat"], item["id"]):
            return "owned"
        return "buyable" if self.req_met(item["req"]) else "locked"

    def equipped(self, slot):
        return self.p.d["equipped"].get(slot, EQUIP_DEFAULT.get(slot))

    def equip(self, cat, iid):
        slot = EQUIP_SLOT.get(cat)
        if slot and self.owns(cat, iid):
            self.p.d["equipped"][slot] = iid
            return True
        return False

    def is_equipped(self, cat, iid):
        slot = EQUIP_SLOT.get(cat)
        return bool(slot) and self.equipped(slot) == iid

    def booster_count(self, bid):
        return self.p.d["boosters"].get(bid, 0)

    def toggle_armed(self, bid):
        a = self.p.d["armed"]
        if bid in a:
            a.remove(bid)
        elif self.booster_count(bid) > 0:
            a.append(bid)

    def consume_armed(self):
        used = []
        for bid in list(self.p.d["armed"]):
            if self.booster_count(bid) > 0:
                self.p.d["boosters"][bid] -= 1
                used.append(bid)
            if self.booster_count(bid) <= 0 and bid in self.p.d["armed"]:
                self.p.d["armed"].remove(bid)
        return used

    def count_owned(self, cat):
        return len(self.owned(cat))


class Shop:
    def __init__(self, prog):
        self.p = prog

    def items(self, cat):
        return [it for (c, _), it in ITEMS.items() if c == cat]

    def act(self, item):
        """Buy / equip / arm. Returns a status message."""
        p, inv = self.p, self.p.inv
        cat, iid = item["cat"], item["id"]
        if cat == "boosters":
            return self.buy_booster(item)
        st = inv.state(item)
        if st == "locked":
            return "Locked: " + req_text(item["req"])
        if st == "buyable":
            if item["price"] <= 0:
                inv.grant(cat, iid)
                p.commit()
                return "Unlocked!"
            if p.d["coins"] < item["price"]:
                p.sfx("deny")
                return "Not enough coins"
            p.player.spend(item["price"])
            inv.grant(cat, iid, notify=False)
            p.event("purchases", 1)
            p.refresh_unlocks()
            p.notify("PURCHASED  " + item["name"], (255, 230, 120), "buy")
            p.sfx("buy")
            if EQUIP_SLOT.get(cat):
                inv.equip(cat, iid)
            p.commit()
            return "Purchased!"
        if EQUIP_SLOT.get(cat):
            inv.equip(cat, iid)
            p.sfx("click")
            p.commit()
            return "Equipped"
        return ""

    def buy_booster(self, item):
        p = self.p
        if p.d["coins"] < item["price"]:
            p.sfx("deny")
            return "Not enough coins"
        p.player.spend(item["price"])
        p.d["boosters"][item["id"]] = p.d["boosters"].get(item["id"], 0) + 1
        if item["id"] not in p.d["armed"]:
            p.d["armed"].append(item["id"])
        p.event("purchases", 1)
        p.notify("PURCHASED  " + item["name"], (255, 230, 120), "buy")
        p.sfx("buy")
        p.commit()
        return "Bought - armed for your next run"


class MissionSystem:
    def __init__(self, prog):
        self.p = prog
        self.rollover()

    @property
    def st(self):
        return self.p.d["missions"]

    def rollover(self):
        today = datetime.date.today()
        dk = today.isoformat()
        wk = "%d-W%02d" % today.isocalendar()[:2]
        st = self.st
        if st["daily_key"] != dk:
            for mid in st["daily"]:
                st["progress"].pop(mid, None)
                if mid in st["claimed"]:
                    st["claimed"].remove(mid)
            st["daily"] = [m["id"] for m in random.Random("d" + dk).sample(DAILY_POOL, 3)]
            st["daily_key"] = dk
        if st["weekly_key"] != wk:
            for mid in st["weekly"]:
                st["progress"].pop(mid, None)
                if mid in st["claimed"]:
                    st["claimed"].remove(mid)
            st["weekly"] = [m["id"] for m in random.Random("w" + wk).sample(WEEKLY_POOL, 2)]
            st["weekly_key"] = wk
        st["claimed"] = [m for m in st["claimed"] if m in ALL_MISSIONS]

    def active_ids(self):
        return list(self.st["daily"]) + list(self.st["weekly"]) + [m["id"] for m in PERM_MISSIONS]

    def progress(self, mid):
        return min(ALL_MISSIONS[mid]["target"], self.st["progress"].get(mid, 0))

    def claimed(self, mid):
        return mid in self.st["claimed"]

    def done(self, mid):
        return self.progress(mid) >= ALL_MISSIONS[mid]["target"]

    def on_event(self, stat, value, mode):
        for mid in self.active_ids():
            m = ALL_MISSIONS.get(mid)
            if not m or m["stat"] != stat or mid in self.st["claimed"]:
                continue
            old = self.st["progress"].get(mid, 0)
            if old >= m["target"]:
                continue
            new = old + value if m["mode"] == "sum" else max(old, value)
            self.st["progress"][mid] = min(new, m["target"])
            if new >= m["target"]:
                self.p.notify("MISSION COMPLETE!  " + m["name"], (120, 220, 255), "mission")

    def claim(self, mid):
        m = ALL_MISSIONS[mid]
        if not self.done(mid) or self.claimed(mid):
            return False
        self.st["claimed"].append(mid)
        self.p.player.add_coins(m["coins"], earned=False)
        self.p.player.add_xp(m["xp"])
        self.p.event("missions_done", 1)
        self.p.notify("+%d COINS  +%d XP" % (m["coins"], m["xp"]), COIN_COL, "coin")
        self.p.commit()
        return True

    def claimable(self):
        return sum(1 for mid in self.active_ids() if self.done(mid) and not self.claimed(mid))

    def listing(self):
        """Missions in display order: claimable first, then in progress, then claimed."""
        ids = self.active_ids()

        def key(mid):
            return (2 if self.claimed(mid) else 0 if self.done(mid) else 1,
                    {"daily": 0, "weekly": 1, "challenge": 2, "world": 3, "character": 4}[ALL_MISSIONS[mid]["cat"]])
        return sorted(ids, key=key)


class AchievementSystem:
    def __init__(self, prog):
        self.p = prog

    def unlocked(self, aid):
        return aid in self.p.d["achievements"]

    def check(self, stat=None):
        for a in ACHIEVEMENTS:
            if a["id"] in self.p.d["achievements"] or (stat and a["stat"] != stat):
                continue
            if self.p.stat(a["stat"]) >= a["target"]:
                self.unlock(a)

    def unlock(self, a):
        self.p.d["achievements"][a["id"]] = int(time.time())
        self.p.notify("ACHIEVEMENT UNLOCKED!  " + a["name"], (255, 210, 90), "ach")
        self.p.recent.append(a["name"])
        self.p.player.add_coins(a["coins"], earned=False)
        self.p.player.add_xp(a["xp"])
        self.p.refresh_unlocks()

    def progress(self, a):
        return min(a["target"], self.p.stat(a["stat"]))


class ProgressionSystem:
    """Hub that ties the player, inventory, missions, achievements and shop together."""

    def __init__(self, save, notify=None, sfx=None):
        self.save = save
        self.d = save.data
        self.notify = notify or (lambda *a, **k: None)
        self.sfx = sfx or (lambda *a, **k: None)
        self.recent = []                      # achievement names unlocked recently (for result screens)
        self.player = Player(self)
        self.inv = Inventory(self)
        self.missions = MissionSystem(self)
        self.ach = AchievementSystem(self)
        self.shop = Shop(self)
        self.refresh_unlocks(silent=True)

    # -- stats / events ----------------------------------------------------- #
    def stat(self, name):
        return self.d["stats"].get(name, 0)

    def event(self, stat, value=1, mode="sum"):
        st = self.d["stats"]
        st[stat] = st.get(stat, 0) + value if mode == "sum" else max(st.get(stat, 0), value)
        self.missions.on_event(stat, value, mode)
        self.ach.check(stat)

    def commit(self):
        return self.save.save()

    # -- unlocks ------------------------------------------------------------ #
    def refresh_unlocks(self, silent=False):
        for (cat, iid), it in ITEMS.items():
            if it["price"] == 0 and self.inv.req_met(it["req"]) and not self.inv.owns(cat, iid):
                self.inv.grant(cat, iid, notify=not silent)
        for stat, cat in (("worlds_unlocked", "worlds"), ("maps_unlocked", "maps"), ("characters_owned", "characters")):
            n = self.inv.count_owned(cat)
            if n > self.stat(stat):
                self.d["stats"][stat] = n
                self.ach.check(stat)
        eq = self.d["equipped"]
        for slot, default in EQUIP_DEFAULT.items():
            cat = {v: k for k, v in EQUIP_SLOT.items()}[slot]
            if not self.inv.owns(cat, eq.get(slot)):
                eq[slot] = default
                self.inv.grant(cat, default, notify=False)

    def unlock_world(self, widx):
        if self.inv.grant("worlds", WORLDS[widx]["id"]):
            self.refresh_unlocks()

    def unlock_map(self, midx):
        if self.inv.grant("maps", slug(MAPS[midx][0])):
            self.refresh_unlocks()

    def owned_worlds(self):
        return [i for i, w in enumerate(WORLDS) if self.inv.owns("worlds", w["id"])]

    def owned_maps(self):
        return [i for i, m in enumerate(MAPS) if self.inv.owns("maps", slug(m[0]))]

    # -- daily challenge + streak -------------------------------------------- #
    def daily_challenge(self):
        dk = datetime.date.today().isoformat()
        dd = self.d["daily"]
        if dd["date"] != dk:
            rng = random.Random("daily" + dk)
            chars = [c["id"] for c in CHARACTERS if self.inv.owns("characters", c["id"])]
            maps = [m for m in self.owned_maps() if m != BOSS_MAP]
            worlds = self.owned_worlds()
            self.d["daily"] = dd = dict(date=dk, char=rng.choice(chars), target=rng.choice((600, 800, 1000, 1200, 1500)),
                                        map=rng.choice(maps), world=rng.choice(worlds), done=False, claimed=False)
        return dd

    def check_streak(self):
        today = datetime.date.today()
        st = self.d["streak"]
        if st["last"] == today.isoformat():
            return None
        count = 1
        if st["last"]:
            try:
                gap = (today - datetime.date.fromisoformat(st["last"])).days
            except ValueError:
                gap = 99
            if gap < 0:
                return None                                  # clock went backwards: no reward
            count = st["count"] + 1 if gap == 1 else 1
        st.update(last=today.isoformat(), count=count, best=max(st["best"], count))
        day = (count - 1) % 7
        coins, xp = STREAK_REWARDS[day], (500 if day == 6 else 50)
        self.player.add_coins(coins, earned=False)
        self.player.add_xp(xp)
        self.event("streak_best", count, "max")
        self.commit()
        return dict(day=day + 1, count=count, coins=coins, xp=xp)




# --------------------------------------------------------------------------- #
#  Sound effects (procedural) + music track list
# --------------------------------------------------------------------------- #
def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


CHORDS = {"maj": (0, 4, 7), "min": (0, 3, 7)}


class Sfx:
    def __init__(self, settings=None):
        self.s = settings if settings is not None else DEFAULT_SETTINGS
        self.ok = False
        self.sounds = {}
        self.rate, self.ch = 22050, 1
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.rate, _, self.ch = pygame.mixer.get_init()
            pygame.mixer.set_reserved(1)                      # channel 0 is for music
            T = self.tone
            m = mtof
            snd = {
                "eat":   T([(660, .05), (880, .08)]),
                "coin":  T([(1318, .04), (1760, .09)], 0.2),
                "gold":  T([(660, .06), (880, .06), (1100, .06), (1320, .12)]),
                "slow":  T([(900, .08), (600, .08), (400, .14)]),
                "die":   T([(400, .08), (330, .08), (260, .10), (180, .10), (110, .25)], 0.35),
                "clear": T([(523, .1), (659, .1), (784, .1), (1047, .25)]),
                "life":  T([(784, .08), (988, .08), (1175, .16)]),
                "level": T([(523, .09), (659, .09), (784, .09), (1047, .09), (1319, .28)]),
                "mission": T([(659, .08), (880, .08), (1319, .18)]),
                "ach":   T([(784, .07), (988, .07), (1175, .07), (1568, .24)]),
                "buy":   T([(880, .05), (1175, .05), (1760, .12)], 0.25),
                "unlock": T([(523, .06), (784, .06), (1047, .15)]),
                "hover": T([(520, .025)], 0.12),
                "click": T([(520, .04), (780, .06)], 0.22),
                "deny":  T([(220, .12), (180, .16)], 0.25),
                "boss_warn": T([(147, .18), (110, .18), (147, .18), (110, .3)], 0.4),
                "boss_defeat": T([(392, .1), (494, .1), (587, .1), (784, .12), (988, .12), (1175, .32)]),
                "gameover": T([(392, .15), (330, .15), (262, .15), (196, .42)], 0.3),
                "world": T([(392, .08), (523, .08), (659, .08), (784, .08), (1047, .26)]),
                "event": T([(300, .1), (450, .1), (600, .1), (900, .22)], 0.3),
                "shield_break": T([(900, .05), (400, .1), (200, .16)], 0.3),
                "boss_hit": T([(200, .06), (320, .08), (160, .12)], 0.3),
                "warn": T([(800, .05), (800, .05)], 0.18),
            }
            for i in range(6):                                  # combo ladder
                b0 = 72 + 2 * i
                snd["combo%d" % i] = T([(m(b0), .04), (m(b0 + 7), .07)], 0.2)
            for i, k in enumerate(POWERUPS):                    # one jingle per power-up
                b0 = 60 + 3 * i
                snd["pw_" + k] = T([(m(b0), .05), (m(b0 + 4), .05), (m(b0 + 12), .1)], 0.25)
            self.sounds = snd
            self.ok = True
        except Exception:
            self.ok = False

    def tone(self, notes, vol=0.28):
        data = array.array("h")
        for f, d in notes:
            n = int(self.rate * d)
            for i in range(n):
                t = i / self.rate
                env = (1 - i / n) ** 1.3
                sn = math.sin(2 * math.pi * f * t)
                s = int(32767 * vol * env * (0.7 * sn + 0.3 * math.copysign(1, sn)))
                for _ in range(self.ch):
                    data.append(s)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def play(self, name, vol=1.0):
        if self.ok and not self.s.get("mute") and name in self.sounds:
            snd = self.sounds[name]
            snd.set_volume(max(0.0, min(1.0, self.s.get("sfx_vol", 0.8) * vol)))
            snd.play()


def _trk(name, style, bpm, root, scale, prog, layers, seed, echo=0, price=0, req=None):
    return dict(id=slug(name), name=name, style=style, bpm=bpm, root=root, scale=scale, prog=prog, layers=layers,
                seed=seed, echo=echo, price=price, req=req)


_PA = ((0, "min"), (8, "maj"), (3, "maj"), (10, "maj")) * 2
_PB = ((0, "maj"), (7, "maj"), (9, "min"), (5, "maj")) * 2
_PC = ((0, "min"), (5, "min"), (8, "maj"), (7, "maj")) * 2
_PD = ((0, "min"), (10, "maj"), (8, "maj"), (10, "maj")) * 2
_PE = ((0, "maj"), (5, "maj"), (9, "min"), (7, "maj"), (0, "maj"), (5, "maj"), (7, "maj"), (0, "maj"))
_PF = ((0, "min"), (3, "maj"), (5, "min"), (7, "maj")) * 2
_PENT, _MINP, _MAJ, _NMIN, _HMIN = (0, 2, 4, 7, 9), (0, 3, 5, 7, 10), (0, 2, 4, 5, 7, 9, 11), (0, 2, 3, 5, 7, 8, 10), (0, 2, 3, 5, 7, 8, 11)
TRACKS = [
    # --- Calm
    _trk("Dawn Drift", "Calm", 66, 48, _PENT, ((0, "maj"), (9, "min"), (5, "maj"), (7, "maj")) * 2, ("pad", "bass", "bell"), 1, 0.75),
    _trk("Moonlit Pond", "Calm", 72, 45, _MINP, _PA, ("pad", "bass", "harp", "bell"), 2, 0.75),
    _trk("Cloud Garden", "Calm", 80, 53, _PENT, _PB, ("pad", "bass", "box"), 3, 0.75),
    _trk("Still Waters", "Calm", 60, 46, _PENT, _PE, ("pad", "sub", "flute"), 11, 0.75, 800),
    _trk("Lantern Glow", "Calm", 74, 50, _MINP, _PF, ("pad", "bass", "box", "harp"), 12, 0.75, 1500),
    # --- Energetic
    _trk("Turbo Serpent", "Energetic", 140, 40, _MINP, ((0, "min"), (8, "maj"), (10, "maj"), (7, "maj")) * 2,
         ("drums", "bass8", "lead16"), 4),
    _trk("Neon Chase", "Energetic", 128, 45, _MINP, _PA, ("drums4", "bassoff", "saw8", "pad"), 5),
    _trk("Dragon Rush", "Energetic", 150, 50, _NMIN, ((0, "min"), (8, "maj"), (10, "maj"), (7, "maj")) * 2,
         ("drums", "bass8", "lead8", "arp"), 6),
    _trk("Pulse Runner", "Energetic", 134, 43, _MINP, _PC, ("drums4", "bassoff", "arp16", "offbeat"), 13, 0, 1200),
    _trk("Thunder Run", "Energetic", 156, 38, _NMIN, _PD, ("drums", "bass8", "lead16", "march"), 14, 0, 2000),
    # --- Adventure
    _trk("Wanderers Road", "Adventure", 100, 52, _MAJ, _PB, ("strings", "bass", "flute", "tom"), 21),
    _trk("Ancient Trails", "Adventure", 92, 47, _NMIN, _PC, ("strings", "bass", "flute", "tom"), 22, 0, 1000),
    _trk("Skybound", "Adventure", 110, 55, _PENT, _PB, ("pad", "bass", "arp16", "flute"), 23, 0, 1200),
    _trk("Deep Expedition", "Adventure", 84, 41, _NMIN, _PA, ("strings", "sub", "bell", "tom"), 24, 0.75, 1500),
    _trk("Starfarer", "Adventure", 96, 45, _PENT, _PD, ("pad", "sub", "arp16", "brass"), 25, 0.5, 1800),
    # --- Boss
    _trk("Boss Giant Cobra", "Boss", 138, 38, _HMIN, ((0, "min"), (8, "maj"), (7, "maj"), (0, "min")) * 2,
         ("drums", "sub", "brass", "lead8"), 31, 0, 2500),
    _trk("Boss Cyber Worm", "Boss", 150, 40, _MINP, _PA, ("drums4", "bass8", "saw8", "march"), 32, 0, 2500),
    _trk("Boss Lava Dragon", "Boss", 144, 37, _NMIN, _PD, ("drums", "sub", "epic", "lead16"), 33, 0, 2500),
    _trk("Boss Void Serpent", "Boss", 126, 36, (0, 1, 4, 5, 7, 8, 10), _PF, ("tom", "sub", "strings", "flute"), 34, 0.75, 2500),
    _trk("Boss Space Leviathan", "Boss", 160, 33, _HMIN, _PC, ("drums", "bass8", "epic", "arp16"), 35, 0, 2500),
    # --- Menu
    _trk("Main Theme", "Menu", 90, 48, _PENT, _PB, ("pad", "bass", "bell", "flute"), 41),
    _trk("Quiet Hub", "Menu", 70, 45, _MINP, _PF, ("strings", "sub", "bell"), 42, 0.75),
]
TRACK_IDX = {t["id"]: i for i, t in enumerate(TRACKS)}
TRACK_STYLES = ["Calm", "Energetic", "Adventure", "Boss", "Menu"]
for _t in TRACKS:      # register every track as a shop / unlock item
    add_item("music", _t["id"], _t["name"], "%s track - %d BPM" % (_t["style"], _t["bpm"]), _t["price"], _t["req"],
             "rare" if _t["price"] >= 1500 else "common")



def synth(inst, f, dur, sr, rnd):
    n = max(16, int(dur * sr))
    out = [0.0] * n
    exp, sin = math.exp, math.sin
    if inst == "kick":
        ph = 0.0
        for i in range(n):
            t = i / sr
            ph += 2 * math.pi * (45 + 110 * exp(-t * 28)) / sr
            out[i] = sin(ph) * exp(-t * 12)
    elif inst == "snare":
        for i in range(n):
            t = i / sr
            out[i] = (rnd.uniform(-1, 1) * 0.8 + sin(2 * math.pi * 190 * t) * 0.5) * exp(-t * 22)
    elif inst == "tom":
        ph = 0.0
        base = f if f else 110.0
        for i in range(n):
            t = i / sr
            ph += 2 * math.pi * (base * (0.6 + 0.4 * exp(-t * 14))) / sr
            out[i] = sin(ph) * exp(-t * 9)
    elif inst == "hat":
        last = 0.0
        for i in range(n):
            x = rnd.uniform(-1, 1)
            out[i] = (x - last) * exp(-i / sr * 70) * 0.7
            last = x
    else:
        k = 2 * math.pi * f / sr
        a, r = min(0.8, dur * 0.35), min(1.2, dur * 0.45)
        for i in range(n):
            t = i / sr
            p = k * i
            if inst == "pad":
                v = min(1.0, t / a, (dur - t) / r) * (0.5 * sin(p) + 0.3 * sin(p * 1.004) + 0.15 * sin(p * 2))
            elif inst == "bell":
                v = exp(-t * 2.6) * min(1.0, t * 150) * (0.6 * sin(p) + 0.25 * sin(p * 2.4) + 0.12 * sin(p * 3.9))
            elif inst == "pluck":
                v = exp(-t * 5) * min(1.0, t * 300) * (0.7 * sin(p) + 0.3 * sin(2 * p) + 0.15 * sin(3 * p))
            elif inst == "bass":
                v = min(1.0, t * 100) * exp(-t * 1.6) * (0.8 * sin(p) + 0.3 * sin(2 * p))
            elif inst == "bass2":
                v = min(1.0, t * 200) * exp(-t * 7) * 0.6 * (sin(p) + 0.5 * sin(2 * p) + 0.33 * sin(3 * p) + 0.25 * sin(4 * p))
            elif inst == "lead":
                v = min(1.0, t * 200) * exp(-t * 4) * (sin(p) + 0.33 * sin(3 * p) + 0.2 * sin(5 * p))
            elif inst == "flute":
                v = min(1.0, t * 20, (dur - t) * 8) * (sin(p + 0.15 * sin(t * 30)) * 0.7 + 0.2 * sin(2 * p) + 0.05 * sin(3 * p))
            elif inst == "brass":
                v = min(1.0, t * 12, (dur - t) * 10) * 0.6 * sum(sin(h * p) / h for h in range(1, 5))
            elif inst == "sub":
                v = min(1.0, t * 80) * exp(-t * 2.5) * sin(p)
            else:  # saw
                v = min(1.0, t * 200) * exp(-t * 3) * 0.7 * sum(sin(h * p) / h for h in range(1, 6))
            out[i] = v
    m = min(n, int(sr * 0.008))
    for j in range(m):
        out[n - 1 - j] *= j / m
    return out


def _add(buf, o, w, v):
    L = len(buf)
    if o + len(w) <= L:
        for i, x in enumerate(w, o):
            buf[i] += x * v
    else:
        for i, x in enumerate(w, o):
            buf[i % L] += x * v


def render_track(spec, sr, channels):
    """Compose and render a seamless loop. Returns raw 16-bit PCM bytes."""
    rng, rnd = random.Random(spec["seed"]), random.Random(spec["seed"] + 99)
    beat = 60.0 / spec["bpm"]
    bar = beat * 4
    prog, root, scale = spec["prog"], spec["root"], spec["scale"]
    L = int(round(bar * len(prog) * sr))
    buf = [0.0] * L
    cache = {}

    def put(inst, m, start, dur, vol):
        key = (inst, m, round(dur, 3))
        w = cache.get(key)
        if w is None:
            w = cache[key] = synth(inst, mtof(m) if m is not None else 0.0, dur, sr, rnd)
        _add(buf, int(start * sr), w, vol)

    pitches = [root + 24 + 12 * o + s for o in (0, 1) for s in scale]
    cur = len(pitches) // 2

    def walk():
        nonlocal cur
        cur = max(0, min(len(pitches) - 1, cur + rng.choice((-2, -1, -1, 0, 1, 1, 2))))
        return pitches[cur]

    for b, (off, q) in enumerate(prog):
        t0 = b * bar
        cr = root + off
        tones = [cr + i for i in CHORDS[q]]
        for lay in spec["layers"]:
            if lay == "pad":
                for tn in tones:
                    put("pad", tn + 12, t0, bar * 1.08, 0.10)
            elif lay == "bass":
                put("bass", cr, t0, beat * 2.1, 0.26)
                put("bass", cr + 7, t0 + 2 * beat, beat * 2.0, 0.2)
            elif lay == "harp":
                for k in range(8):
                    put("pluck", tones[(0, 1, 2, 1, 0, 1, 2, 1)[k]] + 24, t0 + k * beat / 2, beat * 1.6, 0.07)
            elif lay == "bell":
                for st, ln in rng.choice((
                        ((0, 2), (2, 2)), ((0, 1), (1, 1), (2, 2)), ((0, 2), (2, 1), (3, 1)),
                        ((0, 1.5), (1.5, .5), (2, 2)))):
                    if rng.random() < 0.85:
                        put("bell", walk(), t0 + st * beat, ln * beat * 1.8, 0.11)
            elif lay == "box":
                for k in range(8):
                    if rng.random() < 0.75:
                        put("pluck", walk() + 12, t0 + k * beat / 2, beat * 1.2, 0.07)
            elif lay == "bass8":
                for k, o in enumerate((0, 0, 12, 0, 0, 12, 7, 0)):
                    put("bass2", cr + o, t0 + k * beat / 2, beat * 0.45, 0.30)
            elif lay == "bassoff":
                for k in range(4):
                    put("bass2", cr, t0 + k * beat + beat / 2, beat * 0.4, 0.32)
            elif lay in ("drums", "drums4"):
                kicks = (0, 1, 2, 3) if lay == "drums4" else (0, 2, 2.5)
                for kb in kicks:
                    put("kick", None, t0 + kb * beat, 0.25, 0.55)
                for sb in (1, 3):
                    put("snare", None, t0 + sb * beat, 0.2, 0.28)
                for k in range(8):
                    put("hat", None, t0 + k * beat / 2, 0.06, 0.13 if k % 2 else 0.08)
            elif lay == "lead16":
                for k in range(16):
                    put("lead", tones[(0, 1, 2, 1)[k % 4]] + 24, t0 + k * beat / 4, beat * 0.22, 0.075)
            elif lay == "lead8":
                for k in range(8):
                    if rng.random() < 0.85:
                        put("lead", walk() + 12, t0 + k * beat / 2, beat * 0.45, 0.08)
            elif lay == "saw8":
                for k in range(8):
                    put("saw", tones[k % 3] + 12, t0 + k * beat / 2, beat * 0.4, 0.07)
            elif lay == "flute":
                for st, ln in rng.choice((((0, 3), (3, 1)), ((0, 1.5), (1.5, 1.5), (3, 1)), ((0, 2), (2, 2)))):
                    if rng.random() < 0.9:
                        put("flute", walk() + 12, t0 + st * beat, ln * beat * 0.95, 0.12)
            elif lay == "brass":
                put("brass", tones[0] + 12, t0, beat * 1.9, 0.1)
                put("brass", tones[2] + 12, t0 + 2 * beat, beat * 1.9, 0.1)
            elif lay == "sub":
                put("sub", cr if cr - 12 < 24 else cr - 12, t0, bar * 0.98, 0.3)
            elif lay == "tom":
                for sb, nt in ((0, 0), (1.5, 7), (2.5, 3), (3.5, 0)):
                    put("tom", cr + nt, t0 + sb * beat, 0.3, 0.45)
            elif lay == "march":
                for k in range(8):
                    put("snare", None, t0 + k * beat / 2, 0.12, 0.14 if k % 2 else 0.1)
                for kb in (0, 2):
                    put("kick", None, t0 + kb * beat, 0.25, 0.5)
            elif lay == "arp16":
                for k in range(16):
                    put("pluck", tones[(0, 1, 2, 1)[k % 4]] + 24 + (12 if k % 8 >= 4 else 0), t0 + k * beat / 4, beat * 0.6, 0.06)
            elif lay == "epic":
                for tn in tones:
                    put("brass", tn + 12, t0, beat * 3.5, 0.07)
                for kb in (0, 2.5):
                    put("kick", None, t0 + kb * beat, 0.25, 0.5)
            elif lay == "strings":
                for tn in tones:
                    put("pad", tn + 24, t0, bar * 1.08, 0.06)
            elif lay == "offbeat":
                for k in range(4):
                    for tn in tones:
                        put("saw", tn + 12, t0 + k * beat + beat / 2, beat * 0.3, 0.04)
            elif lay == "arp":
                for k in range(8):
                    put("pluck", tones[(0, 2, 1, 2)[k % 4]] + 12, t0 + k * beat / 2, beat * 0.9, 0.07)
    if spec.get("echo"):
        d = int(spec["echo"] * beat * sr)
        for i in range(d, L):
            buf[i] += 0.28 * buf[i - d]
    pk = max(1e-9, max(abs(x) for x in buf))
    sc = 0.82 * 32767 / pk
    mono = array.array("h", (int(x * sc) for x in buf))
    if channels > 1:
        out = array.array("h", [0]) * (L * channels)
        for c in range(channels):
            out[c::channels] = mono
        return out.tobytes()
    return mono.tobytes()


class Music:
    """Composes tracks on a background thread, then loops them on a reserved channel."""

    def __init__(self, sfx):
        self.sfx = sfx
        self.sounds, self.done, self.busy = {}, {}, set()
        self.want = self.playing = None
        self.lock = threading.Lock()
        self.chan = None
        self.last_vol = None
        if sfx.ok:
            try:
                self.chan = pygame.mixer.Channel(0)
            except Exception:
                self.chan = None

    @property
    def ok(self):
        return self.chan is not None

    def composing(self):
        return self.want is not None and self.want in self.busy

    def set_track(self, tid):
        self.want = tid
        if not self.ok:
            return
        if tid is None:
            self.chan.fadeout(400)
            self.playing = None
        elif tid in self.sounds:
            self._start(tid)
        elif tid not in self.busy:
            self.busy.add(tid)
            threading.Thread(target=self._work, args=(tid,), daemon=True).start()

    def _work(self, tid):
        try:
            data = render_track(TRACKS[tid], self.sfx.rate, self.sfx.ch)
        except Exception:
            data = None
        with self.lock:
            self.done[tid] = data

    def poll(self):
        if not self.ok:
            return
        with self.lock:
            items = list(self.done.items())
            self.done.clear()
        for tid, data in items:
            self.busy.discard(tid)
            if data:
                try:
                    self.sounds[tid] = pygame.mixer.Sound(buffer=data)
                except Exception:
                    pass
        if self.want is not None and self.want in self.sounds and self.playing != self.want:
            self._start(self.want)

    def _start(self, tid):
        if self.playing == tid:
            return
        self.playing = tid
        self.chan.play(self.sounds[tid], loops=-1, fade_ms=800)
        self.last_vol = None

    def volume(self, v):
        if self.ok and v != self.last_vol:
            self.last_vol = v
            self.chan.set_volume(v)





class AudioManager:
    """Sound effects + context-aware music (menu / world / boss / selected / shuffle)."""

    def __init__(self, settings):
        self.s = settings
        self.sfx = Sfx(settings)
        self.music = Music(self.sfx)
        self.prog = None
        self.context, self.world, self.boss = "menu", 0, None
        self.shuf, self.shuf_t = None, 0.0

    ok = property(lambda s: s.music.ok)

    def play(self, name, vol=1.0):
        self.sfx.play(name, vol)

    def owned_tracks(self):
        if not self.prog:
            return list(range(len(TRACKS)))
        return [i for i, t in enumerate(TRACKS) if self.prog.inv.owns("music", t["id"])]

    def desired(self):
        s = self.s
        if self.boss:
            return TRACK_IDX.get(self.boss)
        mode = s["music_mode"]
        if mode == "off":
            return None
        owned = self.owned_tracks() or [0]
        if mode == "track":
            idx = TRACK_IDX.get(s["music_track"], 0)
            return idx if idx in owned else owned[0]
        if mode == "shuffle":
            if self.shuf not in owned:
                self.shuf = random.choice(owned)
            return self.shuf
        if self.context == "menu":
            return TRACK_IDX["main_theme"]
        idx = TRACK_IDX.get(WORLDS[self.world]["music"], 0)
        return idx if idx in owned else TRACK_IDX["dawn_drift"]

    def set_context(self, context, world=0, boss=None):
        self.context, self.world, self.boss = context, world, boss
        self.refresh()

    def refresh(self):
        self.music.set_track(self.desired())

    def step_track(self, d=1):
        owned = self.owned_tracks() or [0]
        cur = self.music.want if self.music.want in owned else owned[0]
        nxt = owned[(owned.index(cur) + d) % len(owned)]
        self.s["music_mode"], self.s["music_track"] = "track", TRACKS[nxt]["id"]
        self.refresh()
        return TRACKS[nxt]["name"]

    def current_name(self):
        w = self.music.want
        return TRACKS[w]["name"] if w is not None else "Off"

    def update(self, dt, paused=False):
        self.music.poll()
        if self.s["music_mode"] == "shuffle" and not self.boss:
            self.shuf_t += dt
            if self.shuf_t > 70:
                self.shuf_t, self.shuf = 0.0, random.choice(self.owned_tracks() or [0])
                self.refresh()
        vol = 0.0 if self.s.get("mute") else self.s.get("music_vol", 0.6) * 0.9 * (0.4 if paused else 1.0)
        self.music.volume(vol)

# --------------------------------------------------------------------------- #
#  Tiny software 3D engine
# --------------------------------------------------------------------------- #
class Camera:
    def __init__(self):
        self.yaw = 0.0
        self.pitch = math.radians(52)
        self.dist = 32.0
        self.target = [0.0, 0.0, 0.0]
        self.W = self.H = 1
        self.f = 900.0
        self.cx = self.cy = 0.0

    def setup(self, W, H, shake=(0.0, 0.0, 0.0)):
        self.W, self.H = W, H
        self.f = H * 1.25
        self.cx, self.cy = W / 2, H / 2 + 24
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        tx, ty, tz = (self.target[i] + shake[i] for i in range(3))
        self.px = tx + self.dist * cp * math.sin(self.yaw)
        self.py = ty + self.dist * sp
        self.pz = tz + self.dist * cp * math.cos(self.yaw)
        fx, fy, fz = tx - self.px, ty - self.py, tz - self.pz
        fl = math.sqrt(fx * fx + fy * fy + fz * fz)
        fx, fy, fz = fx / fl, fy / fl, fz / fl
        rl = math.hypot(fx, fz)
        rx, rz = -fz / rl, fx / rl
        self.fx, self.fy, self.fz = fx, fy, fz
        self.rx, self.rz = rx, rz
        self.ux, self.uy, self.uz = -rz * fy, rz * fx - rx * fz, rx * fy
        self.pos = (self.px, self.py, self.pz)

    def to_cam(self, x, y, z):
        dx, dy, dz = x - self.px, y - self.py, z - self.pz
        return (dx * self.rx + dz * self.rz,
                dx * self.ux + dy * self.uy + dz * self.uz,
                dx * self.fx + dy * self.fy + dz * self.fz)


CORNERS = [(sx, sy, sz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
FACES = (   # local normal, corner indices (the bottom face is never visible)
    (0, 1, 0, (2, 6, 7, 3)),
    (1, 0, 0, (4, 5, 7, 6)),
    (-1, 0, 0, (0, 1, 3, 2)),
    (0, 0, 1, (1, 5, 7, 3)),
    (0, 0, -1, (0, 4, 6, 2)),
)
NEAR = 0.4


def clip_near(pts, near=NEAR):
    out = []
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        ain, bin_ = a[2] >= near, b[2] >= near
        if ain:
            out.append(a)
        if ain != bin_:
            t = (near - a[2]) / (b[2] - a[2])
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, near))
    return out


class Renderer:
    """Collects boxes, depth-sorts them (painter's algorithm) and draws them."""

    def __init__(self):
        self.cam = self.surf = None
        self.floor = (N, (50, 50, 50), (40, 40, 40), set())
        self.ground = None
        self.bright, self.fog, self.glow_on = 1.0, None, True
        self.reset()

    def reset(self):
        self.queue, self.pre_g, self.pre0, self.pre1 = [], [], [], []
        self.glows = []

    def begin(self, surf, cam):
        self.surf, self.cam = surf, cam
        self.reset()

    def set_floor(self, n, a, b, skip=()):
        self.floor = (n, a, b, skip)

    def set_ground(self, half, y, c1, c2):
        self.ground = (half, y, c1, c2)

    def box(self, cx, cy, cz, hx, hy, hz, color, rot=0.0, layer=0, edge=False, bias=0.0, skip=()):
        px, py, pz = self.cam.pos
        d2 = (px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2 - bias
        item = (d2, cx, cy, cz, hx, hy, hz, color, rot, edge, skip)
        lst = self.pre_g if layer <= -2 else self.pre0 if layer < 0 else self.pre1 if layer > 0 else self.queue
        lst.append(item)

    def glow(self, x, y, z, r, color):
        if len(self.glows) < 40:
            self.glows.append((x, y, z, r, color))

    def _glows(self):
        cam = self.cam
        for (x, y, z, r, col) in self.glows:
            X, Y, Z = cam.to_cam(x, y, z)
            if Z < 1.0:
                continue
            rad = int(r / Z * cam.f)
            if rad < 4 or rad > 260:
                continue
            sx, sy = cam.cx + X / Z * cam.f, cam.cy - Y / Z * cam.f
            if sx < -rad or sx > cam.W + rad or sy < -rad or sy > cam.H + rad:
                continue
            s = glow_surface(col, rad // 6 * 6 + 6)
            self.surf.blit(s, (int(sx) - s.get_width() // 2, int(sy) - s.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)

    def culled(self, x, y, z, r):
        cam = self.cam
        X, Y, Z = cam.to_cam(x, y, z)
        if Z < -r:
            return True
        if Z <= 0.5:
            return False
        sx, sy, m = cam.cx + X / Z * cam.f, cam.cy - Y / Z * cam.f, r / Z * cam.f
        return sx + m < 0 or sx - m > cam.W or sy + m < 0 or sy - m > cam.H

    def _poly(self, pts, color, edge=None):
        cam = self.cam
        if min(p[2] for p in pts) < NEAR:
            pts = clip_near(pts)
            if len(pts) < 3:
                return
        f, cx, cy = cam.f, cam.cx, cam.cy
        sc = [(cx + x / z * f, cy - y / z * f) for x, y, z in pts]
        xs, ys = [p[0] for p in sc], [p[1] for p in sc]
        if max(xs) < 0 or min(xs) > cam.W or max(ys) < 0 or min(ys) > cam.H:
            return
        pygame.draw.polygon(self.surf, color, sc)
        if edge:
            pygame.draw.polygon(self.surf, edge, sc, 1)

    def _box(self, it):
        d2, cx, cy, cz, hx, hy, hz, col, rot, edge, skip = it
        cam = self.cam
        ff = 0.0
        if self.fog and d2 > 0:
            ff = max(0.0, min(self.fog[2], (math.sqrt(d2) - self.fog[1]) * self.fog[3]))
        px, py, pz = cam.pos
        c, s = math.cos(rot), math.sin(rot)
        dxc, dyc, dzc = px - cx, py - cy, pz - cz
        faces = []
        for fi, (nx, ny, nz, idx) in enumerate(FACES):
            if fi in skip:
                continue
            wnx, wnz = nx * c - nz * s, nx * s + nz * c
            half = hx if nx else (hy if ny else hz)
            if wnx * dxc + ny * dyc + wnz * dzc > half:
                faces.append((idx, (AMB + DIF * max(0.0, wnx * LX + ny * LY + wnz * LZ)) * self.bright))
        if not faces:
            return
        cs = []
        for sx, sy, sz in CORNERS:
            lx, lz = sx * hx, sz * hz
            cs.append(cam.to_cam(cx + lx * c - lz * s, cy + sy * hy, cz + lx * s + lz * c))
        for idx, k in faces:
            fc = shade(col, k)
            if ff:
                fc = mix(fc, self.fog[0], ff)
            self._poly([cs[i] for i in idx], fc, shade(fc, 0.72) if edge else None)

    def _ground(self):
        if not self.ground:
            return
        G, y, c1, c2 = self.ground
        cam = self.cam
        self._poly([cam.to_cam(-G, y, -G), cam.to_cam(G, y, -G), cam.to_cam(G, y, G), cam.to_cam(-G, y, G)], c1)
        step = 4
        for i in range(-G // step, G // step):
            for j in range(-G // step, G // step):
                if (i + j) % 2:
                    x0, z0, x1, z1 = i * step, j * step, (i + 1) * step, (j + 1) * step
                    self._poly([cam.to_cam(x0, y, z0), cam.to_cam(x1, y, z0), cam.to_cam(x1, y, z1),
                                cam.to_cam(x0, y, z1)], c2, c2)

    def _floor(self):
        n, ca, cb, skip = self.floor
        cam, half = self.cam, n / 2
        V = [[cam.to_cam(i - half, 0.0, j - half) for i in range(n + 1)] for j in range(n + 1)]
        self._poly((V[0][0], V[0][n], V[n][n], V[n][0]), ca)
        for j in range(n):
            for i in range(n):
                if (i + j) % 2 and (i, j) not in skip:
                    self._poly((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]), cb, cb)

    def flush(self):
        for it in self.pre_g:
            self._box(it)
        self._ground()
        for it in self.pre0:
            self._box(it)
        self._floor()
        for it in self.pre1:
            self._box(it)
        self.queue.sort(key=lambda it: -it[0])
        for it in self.queue:
            self._box(it)
        if self.glow_on:
            self._glows()
        self.reset()





# --------------------------------------------------------------------------- #
#  Particles, snake body, bosses
# --------------------------------------------------------------------------- #
class ParticleSystem:
    def __init__(self):
        self.p = []
        self.enabled = True
        self.density = 1.0

    def add(self, x, y, z, vx, vy, vz, life, color, size, grav=-14.0, glow=False):
        if self.enabled and len(self.p) < 600:
            self.p.append([x, y, z, vx, vy, vz, life, life, color, size, grav, glow])

    def burst(self, x, y, z, color, n=14, power=4.0, kind="default"):
        n = max(1, int(n * self.density))
        for i in range(n):
            a = random.uniform(0, 6.283)
            s = random.uniform(0.3, 1.0) * power
            col, size, grav, up, life, glow = color, random.uniform(0.06, 0.14), -14.0, random.uniform(2, 6), random.uniform(0.6, 1.1), False
            if kind == "confetti":
                col = colorsys.hsv_to_rgb(random.random(), 0.8, 1.0)
                col = (int(col[0] * 255), int(col[1] * 255), int(col[2] * 255))
            elif kind == "sparkle":
                col, size, grav, glow = random.choice((WHITE, (255, 240, 160), color)), 0.06, -4.0, True
            elif kind == "pixel":
                size, grav = 0.16, -10.0
            elif kind == "stars":
                col, size, grav, up, glow = random.choice(((255, 235, 120), (255, 255, 200), color)), 0.1, -6.0, random.uniform(3, 7), True
            elif kind == "fire":
                col, grav, up = random.choice(((255, 160, 40), (255, 90, 30), (255, 220, 90))), 3.0, random.uniform(1, 3)
            self.add(x, 0.5 if y is None else y, z, math.cos(a) * s, up, math.sin(a) * s, life, col, size, grav, glow)

    def update(self, dt):
        for p in self.p:
            p[6] -= dt
            p[3] *= (1 - 0.8 * dt)
            p[5] *= (1 - 0.8 * dt)
            p[4] += p[10] * dt
            p[0] += p[3] * dt
            p[1] += p[4] * dt
            p[2] += p[5] * dt
            if p[1] < 0.06 and p[10] < 0:
                p[1], p[4] = 0.06, -p[4] * 0.4
        self.p = [p for p in self.p if p[6] > 0]

    def render(self, R, glow_budget=10):
        for p in self.p:
            k = p[6] / p[7]
            s = p[9] * (0.4 + 0.6 * k)
            R.box(p[0], p[1], p[2], s, s, s, p[8], rot=p[6] * 6)
            if p[11] and glow_budget > 0:
                R.glow(p[0], p[1], p[2], 0.5 * k, p[8])
                glow_budget -= 1


class Snake:
    """Grid snake. `body[0]` is the head; `prev` holds last step's cells for smooth interpolation."""

    def __init__(self, cells, d):
        self.body = list(cells)
        self.prev = list(cells)
        self.dir = d
        self.dirq = []
        self.grow = 0
        self.alpha = 1.0
        self.visible = True
        self.age = 0.0             # spawn animation clock
        self.wobble = 0.0          # head turn animation

    head = property(lambda s: s.body[0])

    def turn(self, d):
        last = self.dirq[-1] if self.dirq else self.dir
        if d == last or d == opp(last) or len(self.dirq) >= 3:
            return
        self.dirq.append(d)

    def pop_dir(self):
        if self.dirq:
            d = self.dirq.pop(0)
            if d != opp(self.dir):
                if d != self.dir:
                    self.wobble = 0.35 if (d[0] * self.dir[1] - d[1] * self.dir[0]) > 0 else -0.35
                self.dir = d

    def advance(self, new):
        old = list(self.body)
        self.body.insert(0, new)
        if self.grow > 0:
            self.grow -= 1
        else:
            self.body.pop()
        self.prev = [old[i] if i < len(old) else self.body[i] for i in range(len(self.body))]

    def pos(self, i):
        cx, cy = self.body[i]
        px, py = self.prev[i] if i < len(self.prev) else (cx, cy)
        if abs(cx - px) + abs(cy - py) > 1.5:
            return (cx, cy)
        a = self.alpha
        return (px + (cx - px) * a, py + (cy - py) * a)

    def reset(self, cells, d):
        self.__init__(cells, d)


class BossSystem:
    """Five boss behaviours sharing one hazard model: deadly cells, warnings, hit points."""

    def __init__(self, game, d):
        self.g, self.d, self.kind = game, d, d["kind"]
        self.max = self.hp = d["hp"]
        self.t = self.acc = self.flash = 0.0
        self.defeated = False
        self.body, self.dir = [], (1, 0)
        self.warn, self.fire, self.temp, self.meteors = {}, {}, {}, []
        self.timer = 2.5
        self.ship, self.ship_dir = [15.0, 10.0], (-1, 0)
        if self.kind in ("cobra", "worm"):
            head = game.far_cell(9)
            self.body = [head]
            for _ in range(8 if self.kind == "cobra" else 5):
                self.body.append(head)
            self.dir = random.choice(DIRS)

    def dmg(self):
        return self.max - self.hp

    def hit(self):
        self.hp -= 1
        self.flash = 0.6
        if self.hp <= 0:
            self.defeated = True
            self.warn.clear()
            self.fire.clear()
            self.temp.clear()
            self.meteors.clear()
            self.body = []

    # -- helpers ------------------------------------------------------------- #
    def _free(self, c):
        return 0 <= c[0] < N and 0 <= c[1] < N and c not in self.g.walls

    def _move_body(self, chase):
        head = self.body[0]
        target = self.g.snake.head
        opts = []
        for d in DIRS:
            if d == opp(self.dir) and len(self.body) > 1:
                continue
            c = (head[0] + d[0], head[1] + d[1])
            if self.g.wrap:
                c = (c[0] % N, c[1] % N)
            if not self._free(c):
                continue
            if chase:
                sc = abs(c[0] - target[0]) + abs(c[1] - target[1]) + random.random() * 2.5
            else:
                sc = random.random() + (0 if d == self.dir else 0.35)
            opts.append((sc, d, c))
        if not opts:
            self.dir = opp(self.dir)
            return
        _, d, c = min(opts)
        if not chase and any(o[1] == self.dir for o in opts) and random.random() > 0.12:
            _, d, c = next(o for o in opts if o[1] == self.dir)
        if self.kind == "worm" and len(self.body) > 1 and random.random() < 0.34:
            tail = self.body[-1]
            if abs(tail[0] - target[0]) + abs(tail[1] - target[1]) > 3:
                self.temp[tail] = 6.0
        self.body.insert(0, c)
        self.body.pop()
        self.dir = d

    def _line(self, horizontal, idx, warn_t=1.1, dur=0.7):
        for k in range(N):
            c = (k, idx) if horizontal else (idx, k)
            if c not in self.g.walls:
                self.warn[c] = [warn_t, dur]

    # -- update -------------------------------------------------------------- #
    def update(self, dt):
        if self.defeated:
            return
        g = self.g
        f = 0.4 if g.pw.get("freeze", 0) > 0 else 1.0
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        for c in list(self.warn):
            w = self.warn[c]
            w[0] -= dt
            if w[0] <= 0:
                del self.warn[c]
                if w[1] > 0:
                    self.fire[c] = w[1]
        for dct in (self.fire, self.temp):
            for c in list(dct):
                dct[c] -= dt
                if dct[c] <= 0:
                    del dct[c]
        head = g.snake.head
        k = self.kind
        if k in ("cobra", "worm"):
            iv = max(0.12, (0.30 if k == "cobra" else 0.20) - 0.02 * self.dmg()) / f
            self.acc += dt
            while self.acc >= iv:
                self.acc -= iv
                self._move_body(k == "cobra")
        elif k == "dragon":
            self.timer -= dt * f
            if self.timer <= 0:
                self.timer = max(1.3, 3.0 - 0.18 * self.dmg())
                if random.random() < 0.5:
                    self._line(True, head[1])
                else:
                    self._line(False, head[0])
                if random.random() < 0.4 + 0.05 * self.dmg():
                    self._line(random.random() < 0.5, random.randrange(1, N - 1))
        elif k == "void":
            self.timer -= dt * f
            if self.timer <= 0:
                self.timer = max(0.7, 1.6 - 0.09 * self.dmg())
                for _ in range(3 + self.dmg() // 3):
                    c = (head[0] + random.randint(-6, 6), head[1] + random.randint(-6, 6))
                    if self._free(c) and abs(c[0] - head[0]) + abs(c[1] - head[1]) > 1 and c != g.food:
                        self.warn[c] = [1.0, 2.5]
        elif k == "leviathan":
            self.acc += dt
            iv = max(0.18, 0.34 - 0.015 * self.dmg()) / f
            while self.acc >= iv:
                self.acc -= iv
                nx, ny = self.ship[0] + self.ship_dir[0], self.ship[1] + self.ship_dir[1]
                if not (2 <= nx <= N - 3) or not (2 <= ny <= N - 3):
                    self.ship_dir = random.choice([d for d in DIRS if d != self.ship_dir])
                    nx, ny = self.ship[0], self.ship[1]
                self.ship = [nx, ny]
            self.timer -= dt * f
            if self.timer <= 0:
                self.timer = max(0.9, 2.0 - 0.1 * self.dmg())
                horiz = random.random() < 0.5
                idx = random.randrange(1, N - 1)
                dr = random.choice((1, -1))
                for q in range(N):
                    c = (q, idx) if horiz else (idx, q)
                    self.warn[c] = [0.9, 0]
                self.meteors.append(dict(x=-1.0 if (horiz and dr > 0) else N * 1.0 if horiz else float(idx),
                                         y=float(idx) if horiz else (-1.0 if dr > 0 else N * 1.0),
                                         dx=dr if horiz else 0, dy=0 if horiz else dr, delay=0.9))
        for m in self.meteors:
            if m["delay"] > 0:
                m["delay"] -= dt
            else:
                m["x"] += m["dx"] * 9 * dt * f
                m["y"] += m["dy"] * 9 * dt * f
        self.meteors = [m for m in self.meteors if -2 < m["x"] < N + 2 and -2 < m["y"] < N + 2]

    def deadly(self):
        s = set(self.body) | set(self.fire) | set(self.temp)
        for m in self.meteors:
            if m["delay"] <= 0:
                s.add((int(round(m["x"])), int(round(m["y"]))))
        if self.kind == "leviathan" and not self.defeated:
            cx, cy = int(self.ship[0]), int(self.ship[1])
            s.update((cx + a, cy + b) for a in (-1, 0, 1) for b in (-1, 0, 1))
        return s

    # -- render -------------------------------------------------------------- #
    def render(self, R, t):
        if self.defeated:
            return
        col = WHITE if self.flash > 0 and int(t * 20) % 2 else self.d["col"]
        acc = self.d["acc"]
        for i, c in enumerate(self.body):
            x, z = wx(c[0]), wx(c[1])
            if i == 0:
                R.box(x, 0.6, z, 0.5, 0.5, 0.5, col, edge=True)
                R.box(x + self.dir[0] * 0.3 - self.dir[1] * 0.22, 0.85, z + self.dir[1] * 0.3 + self.dir[0] * 0.22,
                      0.09, 0.09, 0.09, acc, bias=2)
                R.box(x + self.dir[0] * 0.3 + self.dir[1] * 0.22, 0.85, z + self.dir[1] * 0.3 - self.dir[0] * 0.22,
                      0.09, 0.09, 0.09, acc, bias=2)
                R.glow(x, 0.8, z, 1.2, acc)
            else:
                s = 0.46 - 0.2 * i / max(1, len(self.body))
                R.box(x, 0.45, z, s, 0.42, s, col if i % 3 else shade(col, 0.8), edge=True)
        for c, tl in self.temp.items():
            R.box(wx(c[0]), 0.4, wx(c[1]), 0.42, 0.4, 0.42, self.d["acc"] if tl > 1.2 or int(t * 8) % 2 else (60, 20, 60), edge=True)
        for c in self.fire:
            h = 0.45 + 0.15 * math.sin(t * 14 + c[0])
            R.box(wx(c[0]), h, wx(c[1]), 0.42, h, 0.42, (255, 130 + int(80 * math.sin(t * 10 + c[1])), 30), rot=t * 3)
            R.glow(wx(c[0]), 0.6, wx(c[1]), 1.0, (255, 120, 40))
        for c, w in self.warn.items():
            pulse = 0.5 + 0.5 * math.sin(t * 16)
            R.box(wx(c[0]), 0.03, wx(c[1]), 0.46, 0.03, 0.46, (255, int(60 + 120 * pulse), 40), layer=1)
        for m in self.meteors:
            if m["delay"] <= 0:
                R.box(wx(m["x"]), 0.5, wx(m["y"]), 0.38, 0.38, 0.38, (150, 110, 90), rot=t * 5, edge=True)
                R.glow(wx(m["x"]), 0.5, wx(m["y"]), 1.2, (255, 150, 60))
        if self.kind == "leviathan":
            x, z = wx(self.ship[0]), wx(self.ship[1])
            R.box(x, 0.9, z, 1.5, 0.8, 1.5, col, edge=True)
            R.box(x, 1.75, z, 0.9, 0.12, 0.9, acc, rot=t)
            R.glow(x, 1.7, z, 2.0, acc)
        elif self.kind == "dragon":
            R.box(0, 2.2, -(N / 2 + 2.2), 2.4, 1.2, 1.4, col, edge=True)
            R.box(-0.9, 3.4, -(N / 2 + 2.2), 0.3, 0.6, 0.3, (240, 230, 200))
            R.box(0.9, 3.4, -(N / 2 + 2.2), 0.3, 0.6, 0.3, (240, 230, 200))
            R.glow(0, 2.4, -(N / 2 + 1.2), 3.0, (255, 120, 40))
        elif self.kind == "void":
            R.box(0, 3.0 + 0.3 * math.sin(t * 2), 0, 0.9, 0.9, 0.9, shade(col, 0.6), rot=t, edge=True)
            R.box(0, 3.0 + 0.3 * math.sin(t * 2), 0, 0.9, 0.9, 0.9, col, rot=t + 0.785, edge=True)
            R.glow(0, 3.0, 0, 3.5, col)



# --------------------------------------------------------------------------- #
#  Game logic
# --------------------------------------------------------------------------- #
COMBO_TIERS = (2, 3, 4, 5, 10, 20, 50)


def combo_mult(c):
    if c < 2:
        return 1
    if c <= 5:
        return c
    return 5 if c < 10 else 10 if c < 20 else 20 if c < 50 else 50


def combo_tier(c):
    return sum(1 for t in COMBO_TIERS if c >= t)


def make_look(ch, skin_id="default"):
    look = dict(head=ch["head"], b0=ch["b0"], b1=ch["b1"], acc=ch["acc"], pat=ch["pat"])
    s = SKIN_DEFS.get(skin_id)
    if s:
        look.update(b0=s[3], b1=s[4], acc=s[5], pat=s[6], head=s[7])
    return look


def draw_fruit(R, ft, x, z, t, y0=0.0, sc=1.0):
    col = FRUITS[ft][1]
    cy = 0.42 + y0 + 0.1 * math.sin(t * 4 + x)
    r = t * 1.5
    if ft == "apple":
        R.box(x, cy, z, .3 * sc, .3 * sc, .3 * sc, col, rot=r, edge=True)
        R.box(x, cy + .36 * sc, z, .04, .08, .04, (90, 60, 30))
    elif ft == "orange":
        R.box(x, cy, z, .3 * sc, .3 * sc, .3 * sc, col, rot=r, edge=True)
        R.box(x + .06, cy + .33 * sc, z, .1, .02, .06, (70, 160, 60), rot=r)
    elif ft == "banana":
        R.box(x, cy - .05, z, .42 * sc, .09, .14 * sc, col, rot=r, edge=True)
        R.box(x, cy + .03, z, .12, .09, .12, shade(col, .9), rot=r + .5)
    elif ft == "strawberry":
        R.box(x, cy, z, .24 * sc, .28 * sc, .24 * sc, col, rot=r, edge=True)
        R.box(x, cy + .3 * sc, z, .2, .04, .2, (60, 170, 70), rot=r)
    elif ft == "grape":
        for ox, oz, oy in ((0, 0, .1), (.15, .1, -.05), (-.15, .08, -.05), (0, -.14, -.05)):
            R.box(x + ox, cy + oy, z + oz, .12, .12, .12, col, rot=r)
        R.box(x, cy + .28, z, .03, .06, .03, (80, 130, 50))
    elif ft == "watermelon":
        R.box(x, cy, z, .36 * sc, .26 * sc, .3 * sc, col, rot=r, edge=True)
        R.box(x, cy + .27 * sc, z, .3, .03, .24, (240, 70, 90), rot=r)
    elif ft == "pineapple":
        R.box(x, cy, z, .22 * sc, .3 * sc, .22 * sc, col, rot=r, edge=True)
        R.box(x, cy + .38 * sc, z, .14, .12, .14, (60, 170, 70), rot=r)
    elif ft == "cherry":
        for sg in (-1, 1):
            R.box(x + .14 * sg, cy - .05, z, .13, .13, .13, col, rot=r)
            R.box(x + .07 * sg, cy + .22, z, .02, .16, .02, (80, 130, 50))
    elif ft == "blueberry":
        for ox, oz in ((0, 0), (.15, .1), (-.14, .1)):
            R.box(x + ox, cy - .05, z + oz, .12, .12, .12, col, rot=r)
    elif ft == "golden":
        R.box(x, cy + .1, z, .32, .32, .32, col, rot=t * 2.2, edge=True)
        R.box(x, cy + .1, z, .32, .32, .32, col, rot=t * 2.2 + .785, edge=True)
    elif ft == "crystal":
        R.box(x, cy + .15, z, .2, .38, .2, col, rot=t * 1.8, edge=True)
        R.box(x, cy + .15, z, .2, .38, .2, shade(col, .85), rot=t * 1.8 + .785)
    else:
        p = 0.3 + 0.05 * math.sin(t * 8)
        R.box(x, cy + .1, z, p, p, p, col, rot=t * 3, edge=True)
        R.box(x, cy + .1, z, .42, .42, .42, shade(col, .6), rot=-t * 2)
    if ft in SPECIAL_FRUITS:
        R.glow(x, cy + .1, z, 1.1, col)


class Game:
    def __init__(self, cfg, audio=None, prog=None, demo=False):
        self.cfg, self.demo = cfg, demo
        self.audio = None if demo else audio
        self.prog = None if demo else prog
        self.mode = cfg.get("mode", "classic")
        self.rng = random.Random()
        self.diff = cfg.get("diff", 1)
        self.char_idx = cfg.get("char", 0)
        self.ch = CHARACTERS[self.char_idx]
        self.look = cfg.get("look") or make_look(self.ch)
        self.hat = cfg.get("hat", "default")
        self.head_style = cfg.get("head", "block")
        self.trail = cfg.get("trail", "none")
        self.effect = cfg.get("effect", "default")
        self.settings = cfg.get("settings", DEFAULT_SETTINGS)
        self.worlds = cfg.get("worlds") or list(range(10))
        self.world_fixed = cfg.get("world")
        self.map_idx = cfg.get("map", 0)
        self.stage = cfg.get("stage", 1)
        self.boost = set(cfg.get("boosters", []))
        self.xpmul = 1.5 if "b_xp" in self.boost else 1.0
        self.coinmul = 1.5 if "b_coin" in self.boost else 1.0
        self.speed_mult = cfg.get("speed", 1.0)
        self.dark_base = 0.7 if cfg.get("dark") else 0.0
        self.particles = ParticleSystem()
        q = self.settings.get("quality", 2)
        self.particles.enabled = bool(self.settings.get("particles", True))
        self.particles.density = (0.5, 0.8, 1.0)[q]
        self.score = 0
        self.lives = cfg.get("lives", self.ch.get("lives", 3)) + (1 if "b_life" in self.boost else 0)
        self.time, self.shake, self.dark = 0.0, 0.0, self.dark_base
        self.toasts, self.banner_ = [], None
        self.run = dict(coins=0, xp=0, fruits=0, best_combo=0, golden=0, powerups=0, levels=0, time=0.0, stars=0)
        self.committed = self.reported = False
        self.new_best = False
        self.result = {}
        self.outcome = {}
        self.time_left = (90.0 + (15 if "b_time" in self.boost else 0)) if self.mode == "timeattack" else 0.0
        self.timeup = False
        self.level = 1
        self.invuln = 0.0
        self.snake = Snake([(4, 10)], RIGHT)
        self.boss = None
        self.start_level(1, first=True)

    # -- setup --------------------------------------------------------------- #
    def make_plan(self, level):
        m, cfg = self.mode, self.cfg
        if m == "adventure":
            a = adventure_stage(self.stage)
            return dict(map=a["map"], world=a["world"], obj=a["obj"], boss=a["boss"], level=a["level"], force_world=True)
        if m == "challenge":
            c = cfg["challenge"]
            return dict(map=c["map"], world=c["world"], obj=c["obj"], boss=None, level=3, force_world=True)
        if m == "daily":
            d = cfg["daily"]
            return dict(map=d["map"], world=d["world"], obj=("score", d["target"]), boss=None, level=3, force_world=True)
        if m == "timeattack":
            return dict(map=self.map_idx, world=None, obj=("time", 0), boss=None, level=level)
        if m == "survival":
            return dict(map=self.map_idx, world=None, obj=("endless", 0), boss=None, level=level)
        return dict(map=self.map_idx, world=None, obj=("fruits", obj_target("fruits", level)), boss=None, level=level)

    def pick_world(self, plan, level):
        if plan.get("force_world") and plan["world"] is not None:
            return plan["world"]
        if self.world_fixed is not None:
            return self.world_fixed
        return self.worlds[(level - 1) % len(self.worlds)]

    def start_level(self, level, first=False):
        plan = self.make_plan(level)
        self.level = plan["level"] if self.mode == "adventure" else level
        self.map_idx = plan["map"]
        self.wrap = MAPS[self.map_idx][2]
        self.widx = self.pick_world(plan, level)
        self.obj = plan["obj"]
        self.walls = build_walls(self.map_idx, 1 if plan["boss"] else self.level, self.rng)
        self.rebuild_wall_draw()
        self.lv = dict(fruits=0, score0=self.score, time=0.0, combo=0, golden=0, coins=0, flaw=0, lost=0,
                       coins0=self.run["coins"], xp0=self.run["xp"])
        self.items, self.roamers, self.pw = [], [], {}
        self.food, self.ftype = None, "apple"
        self.combo, self.combo_t = 0, 0.0
        self.event, self.ev_timer = None, self.rng.uniform(28, 50)
        self.spawn_t, self.coin_t, self.gold_t = self.rng.uniform(3, 6), 0.0, 0.0
        self.survive_tick = 0.0
        self.respawn()
        if first:
            if "b_shield" in self.boost:
                self.pw["shield"] = 6.0
            if "b_magnet" in self.boost:
                self.pw["magnet"] = 10.0
        if self.ch.get("startshield"):
            self.pw["shield"] = max(self.pw.get("shield", 0), self.ch["startshield"])
        self.boss = BossSystem(self, plan["boss"]) if plan["boss"] else None
        nr = self.cfg.get("roamers") if self.mode == "challenge" else (0 if plan["boss"] or self.mode == "survival"
                                                                      else min(4, (self.level + 1) // 3))
        self.spawn_roamers(nr or 0)
        self.food = self.spawn_fruit()
        self.state = "play" if self.demo else "ready"
        self.state_t = 3.0 if plan["boss"] else 2.6
        if self.audio:
            self.audio.set_context("game", self.widx, plan["boss"]["music"] if plan["boss"] else None)
            if plan["boss"]:
                self.audio.play("boss_warn")

    def advance(self):
        self.start_level(self.level + 1)

    def rebuild_wall_draw(self):
        self.wall_draw = []
        for (x, y) in self.walls:
            sk = frozenset(i for i, (dx, dy) in ((1, (1, 0)), (2, (-1, 0)), (3, (0, 1)), (4, (0, -1)))
                           if (x + dx, y + dy) in self.walls)
            self.wall_draw.append((x, y, sk))

    def respawn(self):
        sx, sy, sd = MAPS[self.map_idx][4]
        self.snake.reset([((sx - sd[0] * i) % N, (sy - sd[1] * i) % N) for i in range(3)], sd)
        self.acc = 0.0
        if self.food in self.snake.body:
            self.food = self.spawn_fruit()
        self.items = [it for it in self.items if it["pos"] not in self.snake.body]

    # -- cells --------------------------------------------------------------- #
    def occupied(self):
        occ = set(self.snake.body) | self.walls
        if self.food:
            occ.add(self.food)
        occ.update(it["pos"] for it in self.items)
        occ.update(r["pos"] for r in self.roamers)
        if self.boss:
            occ |= self.boss.deadly() | set(self.boss.warn)
        return occ

    def free_cell(self, mind=0):
        occ = self.occupied()
        head = self.snake.head
        cells = [(x, y) for x in range(N) for y in range(N) if (x, y) not in occ
                 and abs(x - head[0]) + abs(y - head[1]) >= mind]
        self.rng.shuffle(cells)
        for c in cells[:80]:
            if sum(1 for _ in neighbors(c, self.walls, self.wrap)) >= 2:
                return c
        return cells[0] if cells else None

    def far_cell(self, mind):
        return self.free_cell(mind) or (10, 10)

    # -- helpers ------------------------------------------------------------- #
    def speed(self):
        s = min(20.0, BASE_SPEED[self.diff] + (self.level - 1) * 0.9) * self.ch.get("speed", 1.0) * self.speed_mult
        if self.pw.get("speed", 0) > 0:
            s *= 1.3
        if self.pw.get("slow", 0) > 0:
            s *= 0.62
        if self.event and self.event["kind"] == "speed_storm":
            s *= 1.25
        return s

    def base_points(self):
        return 10 + 2 * (self.level - 1)

    def play(self, name, vol=1.0):
        if self.audio:
            self.audio.play(name, vol)

    def toast(self, text, color=WHITE):
        if not self.demo:
            self.toasts.append([text, color, 1.8])

    def banner(self, text, color, dur=2.2):
        if not self.demo:
            self.banner_ = [text, color, dur, dur]

    def kick(self, amt):
        if self.settings.get("shake", True):
            self.shake = max(self.shake, amt * (0.3 if self.settings.get("reduce_motion") else 1.0))

    def pxz(self, cell):
        return wx(cell[0]), wx(cell[1])

    def burst(self, cell, color, n=14, power=4.0, y=0.5, kind=None):
        x, z = self.pxz(cell)
        self.particles.burst(x, y, z, color, n, power, kind or self.effect)

    def add_score(self, pts):
        self.score += pts

    def turn(self, d):
        self.snake.turn(d)

    # -- objective ----------------------------------------------------------- #
    def obj_text(self):
        k, n = self.obj
        if k == "endless":
            return "Survive as long as you can"
        if k == "boss":
            return "Defeat the " + self.boss.d["name"].title() if self.boss else OBJ_TEXT["boss"].format(n=n)
        return OBJ_TEXT[k].format(n=n)

    def obj_target_n(self):
        return self.boss.max if self.obj[0] == "boss" and self.boss else self.obj[1]

    def obj_progress(self):
        k, lv = self.obj[0], self.lv
        return {"fruits": lv["fruits"], "score": self.score - lv["score0"], "survive": int(lv["time"]),
                "combo": lv["combo"], "golden": lv["golden"], "coins": lv["coins"], "flawless": lv["flaw"],
                "boss": (self.boss.max - self.boss.hp) if self.boss else 0, "time": 0, "endless": 0}[k]

    def check_objective(self):
        k, n = self.obj
        if k in ("time", "endless") or self.state != "play":
            return
        if k == "boss":
            if self.boss and self.boss.defeated:
                self.level_clear()
        elif self.obj_progress() >= n:
            self.level_clear()

    # -- collisions ---------------------------------------------------------- #
    def deadly_cells(self):
        s = {r["pos"] for r in self.roamers}
        if self.boss:
            s |= self.boss.deadly()
        return s

    def is_border(self, c):
        return not self.wrap and (c[0] in (0, N - 1) or c[1] in (0, N - 1))

    def protect(self):
        if self.invuln > 0:
            return True
        if self.pw.get("shield", 0) > 0:
            del self.pw["shield"]
            self.invuln = 1.3
            self.play("shield_break")
            self.burst(self.snake.head, (80, 230, 255), 20, 5, kind="sparkle")
            self.toast("SHIELD BROKEN", (80, 230, 255))
            self.kick(0.3)
            return True
        return False

    def hazard_hit(self):
        if not self.protect():
            self.crash()

    def step(self):
        if self.demo:
            self.ai()
        else:
            self.snake.pop_dir()
        sn = self.snake
        hx, hy = sn.head
        nx, ny = hx + sn.dir[0], hy + sn.dir[1]
        if self.wrap:
            nx %= N
            ny %= N
        new = (nx, ny)
        ghost = self.pw.get("ghost", 0) > 0 or (sn.head in self.walls and not self.is_border(sn.head))
        body = sn.body if sn.grow > 0 else sn.body[:-1]
        oob = not (0 <= nx < N and 0 <= ny < N)
        wall_block = new in self.walls and not (ghost and not self.is_border(new))
        body_block = new in body and not ghost
        if oob or wall_block or body_block:
            if self.protect():
                return
            self.crash()
            return
        old_tail = sn.body[-1]
        sn.advance(new)
        self.emit_trail(old_tail)
        if self.pw.get("magnet", 0) > 0 or self.ch.get("magnet"):
            self.magnet_pull()
        if new == self.food:
            self.eat_fruit(new, self.ftype, True)
        else:
            for it in list(self.items):
                if it["pos"] == new:
                    self.eat_item(it)
        if self.state == "play" and (new in self.deadly_cells()):
            self.hazard_hit()

    def magnet_pull(self):
        r = 5 if self.pw.get("magnet", 0) > 0 else self.ch.get("magnet", 0)
        hx, hy = self.snake.head
        occ = self.occupied()
        targets = [it for it in self.items] + ([{"pos": self.food, "main": True}] if self.food and not self.boss else [])
        for it in targets:
            px, py = it["pos"]
            dist = abs(px - hx) + abs(py - hy)
            if 1 < dist <= r:
                dx = (hx > px) - (hx < px)
                dy = (hy > py) - (hy < py)
                for c in (((px + dx, py) if abs(hx - px) >= abs(hy - py) else (px, py + dy)), (px + dx, py), (px, py + dy)):
                    if c not in occ and 0 <= c[0] < N and 0 <= c[1] < N and c != (px, py):
                        if it.get("main"):
                            self.food = c
                        else:
                            it["pos"] = c
                        occ.add(c)
                        break

    def emit_trail(self, cell):
        t = self.trail
        if t == "none" or not self.particles.enabled:
            return
        x, z = self.pxz(cell)
        P = self.particles
        r = random.uniform
        if t == "fire":
            P.add(x, 0.3, z, r(-.3, .3), r(1, 2.2), r(-.3, .3), 0.55, random.choice(((255, 160, 40), (255, 90, 30))), .13, 3.0, True)
        elif t == "neon":
            P.add(x, 0.15, z, 0, 0, 0, 0.8, random.choice(((0, 255, 230), (255, 60, 220))), .16, 0, True)
        elif t == "spark":
            for _ in range(2):
                P.add(x, 0.3, z, r(-2, 2), r(1, 3), r(-2, 2), 0.35, (255, 240, 120), .06, -9)
        elif t == "smoke":
            P.add(x, 0.3, z, r(-.2, .2), r(.6, 1.2), r(-.2, .2), 1.0, (130, 130, 140), .17, .5)
        elif t == "galaxy":
            P.add(x + r(-.3, .3), 0.3, z + r(-.3, .3), 0, r(.2, .8), 0, 0.9, random.choice(((150, 110, 255), (255, 255, 255), (90, 150, 255))), .07, 0, True)
        elif t == "lightning":
            for _ in range(2):
                P.add(x + r(-.4, .4), r(.1, .6), z + r(-.4, .4), 0, 0, 0, 0.18, (190, 220, 255), .05, 0, True)

    # -- pickups ------------------------------------------------------------- #
    def spawn_fruit(self):
        c = self.free_cell(2)
        self.ftype = self.rng.choice(NORMAL_FRUITS)
        return c

    def spawn_item(self, kind=None, sub=None, life=None):
        if len(self.items) >= 5:
            return
        c = self.free_cell(2)
        if not c:
            return
        ch, ev = self.ch, self.event["kind"] if self.event else ""
        if kind is None:
            ok = self.obj[0]
            bonus = ch.get("bonus", 1.0)
            w_sp = 22 * bonus * (2.5 if ok == "golden" or ev == "golden_rush" else 1.0)
            w_co = 24 * (3.0 if ok == "coins" else 1.0)
            kind = self.rng.choices(("fruit", "coin", "power"), weights=(w_sp, w_co, 42))[0]
        if kind == "fruit" and not sub:
            sub = self.rng.choices(SPECIAL_FRUITS, weights=(70, 25, 5))[0]
        elif kind == "power" and not sub:
            pool = [p for p in POWERUPS if not (p == "time" and self.mode not in ("timeattack",) and self.rng.random() < .5)]
            sub = self.rng.choice(pool)
        life = life or (10.0 if kind == "fruit" else 12.0) * ch.get("blife", 1.0)
        self.items.append(dict(pos=c, kind=kind, sub=sub, t=life, t0=life))

    def spawn_roamers(self, n):
        for _ in range(n):
            c = self.free_cell(7)
            if c:
                self.roamers.append(dict(pos=c, dir=self.rng.choice(DIRS), kind=WORLDS[self.widx]["obst"]))
        self.roam_acc = 0.0

    def roamer_step(self):
        for r in self.roamers:
            opts = []
            for d in DIRS:
                c = (r["pos"][0] + d[0], r["pos"][1] + d[1])
                if self.wrap:
                    c = (c[0] % N, c[1] % N)
                if 0 <= c[0] < N and 0 <= c[1] < N and c not in self.walls:
                    opts.append((d, c))
            if not opts:
                continue
            keep = next((o for o in opts if o[0] == r["dir"]), None)
            d, c = keep if keep and self.rng.random() > 0.2 else self.rng.choice(opts)
            r["dir"], r["pos"] = d, c

    def eat_fruit(self, pos, ft, main):
        name, col, smult, coins, xp = FRUITS[ft]
        ch = self.ch
        self.combo = self.combo + 1 if self.combo_t > 0 else 1
        self.combo_t = ch.get("combo", 4.0)
        prev_tier = combo_tier(self.combo - 1)
        mult = combo_mult(self.combo)
        tier = combo_tier(self.combo)
        pts = self.base_points() * smult * mult * DMULT[self.diff] * ch.get("score", 1.0)
        if self.pw.get("mult", 0) > 0:
            pts *= 2
        pts = int(pts)
        cg = int((coins + mult // 5) * ch.get("coinx", 1.0) * (2 if self.pw.get("coinb", 0) > 0 else 1) * self.coinmul)
        xg = int(xp * (1 + min(mult, 20) * 0.05) * ch.get("xpx", 1.0) * (2 if self.pw.get("dxp", 0) > 0 else 1) * self.xpmul)
        self.add_score(pts)
        self.run["coins"] += cg
        self.run["xp"] += xg
        self.run["fruits"] += 1
        self.run["best_combo"] = max(self.run["best_combo"], self.combo)
        self.lv["fruits"] += 1
        self.lv["flaw"] += 1
        self.lv["combo"] = max(self.lv["combo"], self.combo)
        self.snake.grow += {"golden": 2, "crystal": 2, "plasma": 3}.get(ft, 1)
        special = ft in SPECIAL_FRUITS
        if special:
            self.lv["golden"] += 1
            self.run["golden"] += 1
        if self.prog:
            P = self.prog
            P.event("fruits", 1)
            P.event("best_combo", self.combo, "max")
            if special:
                P.event("golden", 1)
            P.player.add_coins(cg)
            P.player.add_xp(xg)
        self.burst(pos, col, 14 + 4 * tier, 4.0 + 0.4 * tier)
        if tier > prev_tier:
            self.play("combo%d" % min(5, tier - 1))
            if tier >= 5:
                self.kick(0.25)
                self.banner("COMBO x%d!" % mult, (255, 170, 60), 1.0)
        else:
            self.play("gold" if special else "eat")
        self.toast("+%d" % pts + ("   COMBO x%d" % mult if mult > 1 else ""), (255, 235, 150) if not special else col)
        if self.mode == "timeattack":
            self.time_left += 2.0
        if main:
            if self.boss:
                self.boss.hit()
                self.play("boss_hit")
                self.kick(0.4)
                self.burst(pos, self.boss.d["col"], 20, 5, kind="stars")
                if self.boss.defeated:
                    self.boss_defeated()
                    return
            self.food = self.spawn_fruit()
        else:
            self.items = [i for i in self.items if i["pos"] != pos]
        if self.mode == "timeattack":
            self.level = 1 + self.run["fruits"] // 8
        self.check_objective()

    def eat_item(self, it):
        self.items = [i for i in self.items if i is not it]
        if it["kind"] == "fruit":
            self.eat_fruit(it["pos"], it["sub"], False)
        elif it["kind"] == "coin":
            cg = int(10 * self.ch.get("coinx", 1.0) * (2 if self.pw.get("coinb", 0) > 0 else 1) * self.coinmul)
            self.run["coins"] += cg
            self.lv["coins"] += 1
            if self.prog:
                self.prog.player.add_coins(cg)
            self.burst(it["pos"], COIN_COL, 8, 3, kind="sparkle")
            self.play("coin")
            self.toast("+%d COINS" % cg, COIN_COL)
            self.check_objective()
        else:
            self.activate_power(it["sub"], it["pos"])

    def activate_power(self, k, pos=None):
        name, col, dur = POWERUPS[k][:3]
        ch = self.ch
        if k == "time":
            if self.mode == "timeattack":
                self.time_left += 10
            else:
                self.run["coins"] += 25
                if self.prog:
                    self.prog.player.add_coins(25)
        else:
            dur *= ch.get("pw", 1.0)
            if k == "slow":
                dur = ch.get("slow", 6.0) * ch.get("pw", 1.0)
            elif k == "ghost":
                dur *= ch.get("gdur", 1.0)
            self.pw[k] = dur
        self.run["powerups"] += 1
        if self.prog:
            self.prog.event("powerups", 1)
        self.burst(pos or self.snake.head, col, 22, 4.5, kind="sparkle")
        self.play("pw_" + k)
        self.toast(name.upper(), col)

    # -- events -------------------------------------------------------------- #
    def start_event(self, kind=None):
        if not kind:
            fav = WORLDS[self.widx]["event"]
            kind = fav if self.rng.random() < 0.35 else self.rng.choice(list(EVENTS))
        name, col, dur = EVENTS[kind]
        self.event = dict(kind=kind, t=dur)
        self.banner(name, col, 2.4)
        self.play("event")
        if kind == "fruit_frenzy":
            for _ in range(8):
                self.spawn_item("fruit", self.rng.choice(NORMAL_FRUITS), 14.0)
        if kind == "dark_mode":
            self.dark_base_ev = True

    def crash(self):
        if self.demo:
            self.respawn()
            return
        n = len(self.snake.body)
        for i, c in enumerate(self.snake.body):
            self.burst(c, self.look["head"] if i == 0 else seg_color(self.look, i, n, self.time), 4, 3.5, 0.4, "default")
        self.play("die")
        self.kick(1.0)
        self.lives -= 1
        self.lv["lost"] += 1
        self.lv["flaw"] = 0
        self.combo, self.combo_t = 0, 0.0
        self.snake.visible = False
        self.state, self.state_t = "dying", 1.5

    # -- finishing ----------------------------------------------------------- #
    def level_clear(self, boss=False):
        if self.demo:
            self.lv["fruits"] = 0
            return
        lv = self.lv
        flawless = lv["lost"] == 0
        stars = 1 + (1 if lv["lost"] <= (0 if flawless else 1) and lv["lost"] == 0 else 0) + (1 if flawless and lv["combo"] >= 5 else 0)
        mult = self.ch.get("clear", 1.0)
        bonus = int((100 * self.level + 50 * self.lives) * mult)
        coins = int((20 * self.level + 10 * stars + (50 if flawless else 0)) * mult * self.coinmul)
        xp = int((40 + 10 * self.level + (100 if flawless else 0)) * self.ch.get("xpx", 1.0) * self.xpmul)
        extra = ""
        if self.mode == "challenge":
            c = self.cfg["challenge"]
            coins, xp, extra = coins + c["coins"], xp + c["xp"], c["name"]
        if self.mode == "daily":
            coins, xp = coins + 500, xp + 1000
        if boss and self.boss:
            coins, xp = coins + self.boss.d["coins"], xp + self.boss.d["xp"]
        self.add_score(bonus)
        self.run["coins"] += coins
        self.run["xp"] += xp
        self.run["levels"] += 1
        self.run["stars"] += stars
        if self.prog:
            P = self.prog
            P.player.add_coins(coins)
            P.player.add_xp(xp)
            P.event("levels_cleared", 1)
            P.event("highest_level", self.level, "max")
            P.event("world_levels_%d" % self.widx, 1)
            if flawless:
                P.event("flawless_levels", 1)
            P.event("stars_total", stars)
            if stars == 3:
                P.event("three_stars", 1)
            if boss and self.boss:
                P.event("boss_wins", 1)
                P.event("boss_win_" + self.boss.d["id"], 1)
        final = (self.mode == "classic" and self.level >= MAX_LEVEL) or self.mode in ("daily", "challenge") or \
                (self.mode == "adventure" and self.stage >= ADV_STAGES)
        self.result = dict(score=self.score, coins=coins, xp=xp, bonus=bonus, stars=stars, combo=lv["combo"],
                           flawless=flawless, extra=extra, fruits=lv["fruits"])
        self.outcome = dict(cleared=True, stage=self.stage, boss=bool(boss), mode=self.mode, final=final)
        self.state = "win" if final else "clear"
        self.state_t = 4.0
        self.play("boss_defeat" if boss else "clear")
        self.kick(0.5)
        for _ in range(8):
            self.burst((self.rng.randrange(N), self.rng.randrange(N)), self.rng.choice([GOLD_COL, FOOD_COL, SLOW_COL, (120, 255, 150)]),
                       10, 5, 1.0, "confetti")
        self.commit_run()

    def boss_defeated(self):
        for c in list(self.boss.warn) + list(self.boss.fire):
            pass
        self.level_clear(boss=True)

    def commit_run(self):
        if self.committed or self.demo or not self.prog:
            return
        self.committed = True
        P = self.prog
        P.event("games", 1)
        P.event("char_games_" + self.ch["id"], 1)
        P.event("total_score", self.score)
        P.event("best_score", self.score, "max")
        P.event("play_time", int(self.run["time"]))
        P.event("highest_level", self.level, "max")
        if self.mode == "survival":
            P.event("survive_best", int(self.run["time"]), "max")
        if self.mode == "timeattack":
            P.event("ta_best", self.score, "max")
        P.commit()

    # -- update -------------------------------------------------------------- #
    def update(self, dt):
        self.time += dt
        self.shake = max(0.0, self.shake - dt * 2.2)
        self.particles.update(dt)
        sn = self.snake
        sn.age += dt
        sn.wobble *= max(0.0, 1 - dt * 9)
        self.invuln = max(0.0, self.invuln - dt)
        for t in self.toasts:
            t[2] -= dt
        self.toasts = [t for t in self.toasts if t[2] > 0]
        if self.banner_:
            self.banner_[2] -= dt
            if self.banner_[2] <= 0:
                self.banner_ = None
        target = 0.7 if (self.event and self.event["kind"] == "dark_mode") else self.dark_base
        self.dark += (target - self.dark) * min(1.0, dt * 3)
        st = self.state
        if st == "ready":
            self.state_t -= dt
            if self.state_t <= 0:
                self.state = "play"
        elif st == "play":
            self.play_update(dt)
        elif st == "dying":
            self.state_t -= dt
            if self.state_t <= 0:
                if self.lives <= 0 or self.mode == "survival":
                    self.state = "over"
                    self.play("gameover")
                    self.outcome = dict(cleared=False, mode=self.mode, stage=self.stage, final=True)
                    self.commit_run()
                else:
                    self.respawn()
                    self.invuln = 2.0
                    self.state, self.state_t = "ready", 1.4
        elif st in ("clear", "win"):
            self.state_t -= dt

    def play_update(self, dt):
        lv = self.lv
        self.run["time"] += dt
        lv["time"] += dt
        if self.combo_t > 0:
            self.combo_t -= dt
            if self.combo_t <= 0:
                self.combo = 0
        for k in list(self.pw):
            self.pw[k] -= dt
            if self.pw[k] <= 0:
                del self.pw[k]
        for it in self.items:
            it["t"] -= dt
        self.items = [i for i in self.items if i["t"] > 0]
        # random pickups
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self.spawn_t = self.rng.uniform(3, 5) if self.obj[0] in ("golden", "coins") else self.rng.uniform(5, 9)
            if not self.boss or self.rng.random() < 0.5:
                self.spawn_item()
        # world events
        if self.event:
            self.event["t"] -= dt
            k = self.event["kind"]
            if k == "coin_rain":
                self.coin_t -= dt
                if self.coin_t <= 0:
                    self.coin_t = 0.45
                    self.spawn_item("coin", None, 9.0)
            elif k == "golden_rush":
                self.gold_t -= dt
                if self.gold_t <= 0:
                    self.gold_t = 1.6
                    self.spawn_item("fruit", "golden", 8.0)
            if self.event["t"] <= 0:
                self.event = None
        elif not self.boss and not self.demo and self.mode != "daily":
            self.ev_timer -= dt
            if self.ev_timer <= 0:
                self.ev_timer = self.rng.uniform(40, 75)
                self.start_event()
        # modes
        if self.mode == "timeattack":
            self.time_left -= dt
            if self.time_left <= 0:
                self.timeup = True
                self.state = "over"
                self.outcome = dict(cleared=False, mode=self.mode, stage=self.stage, final=True, timeup=True)
                self.play("gameover")
                self.commit_run()
                return
        elif self.mode == "survival":
            self.level = 1 + int(lv["time"] // 25)
            self.survive_tick += dt
            if self.survive_tick >= 5.0:
                self.survive_tick = 0
                self.add_score(5 * self.level)
            if int(lv["time"]) % 12 == 11 and not getattr(self, "_obst_done", False):
                self._obst_done = True
                self.add_obstacle()
            elif int(lv["time"]) % 12 != 11:
                self._obst_done = False
        if self.boss:
            self.boss.update(dt)
            if self.state == "play" and self.snake.head in self.boss.deadly():
                self.hazard_hit()
        if self.roamers and self.state == "play":
            if self.pw.get("freeze", 0) <= 0:
                self.roam_acc += dt
                while self.roam_acc >= 0.5:
                    self.roam_acc -= 0.5
                    self.roamer_step()
            if any(r["pos"] == self.snake.head for r in self.roamers):
                self.hazard_hit()
        if self.state != "play":
            return
        if self.obj[0] == "survive":
            self.check_objective()
        self.acc += dt
        iv = 1.0 / self.speed()
        n = 0
        while self.acc >= iv and self.state == "play" and n < 4:
            self.acc -= iv
            self.step()
            n += 1
        self.snake.alpha = min(1.0, self.acc / iv)

    def add_obstacle(self):
        c = self.free_cell(6)
        if not c:
            return
        sx, sy, _ = MAPS[self.map_idx][4]
        self.walls.add(c)
        total = N * N - len(self.walls)
        if len(reachable(self.snake.head, self.walls, self.wrap)) != total or \
                any(sum(1 for _ in neighbors(n, self.walls, self.wrap)) < 2 for n in neighbors(c, self.walls, self.wrap)):
            self.walls.discard(c)
            return
        self.rebuild_wall_draw()
        self.toast("NEW OBSTACLE", (255, 150, 120))

    def ai(self):
        sn = self.snake
        head = sn.head
        blocked = set(sn.body[:-1]) | self.walls
        fx, fy = self.food
        best = None
        for d in DIRS:
            if d == opp(sn.dir):
                continue
            nx, ny = head[0] + d[0], head[1] + d[1]
            if self.wrap:
                nx %= N
                ny %= N
            if not (0 <= nx < N and 0 <= ny < N) or (nx, ny) in blocked:
                continue
            dx, dy = abs(nx - fx), abs(ny - fy)
            if self.wrap:
                dx, dy = min(dx, N - dx), min(dy, N - dy)
            room = flood_count((nx, ny), blocked | {head}, self.wrap, len(sn.body) + 4)
            key = (room < min(len(sn.body) + 2, 30), dx + dy, random.random())
            if best is None or key < best[0]:
                best = (key, d)
        if best:
            sn.dir = best[1]

    # -- rendering ----------------------------------------------------------- #
    def render(self, R, wd, widx):
        t, h = self.time, N / 2
        S = self.settings
        q = S.get("quality", 2)
        dim = 1.0 - 0.5 * self.dark
        R.bright = wd.get("bright", 1.0) * (1.0 - 0.45 * self.dark)
        R.fog = (wd["fog"], 22.0, 0.65, 1 / 30.0) if q >= 1 else None
        R.set_floor(N, shade(wd["fa"], dim), shade(wd["fb"], dim), self.walls)
        R.set_ground(GROUND_HALF, GY, shade(wd["ground"], dim), shade(wd["ground"], 0.93 * dim))
        dirt = wd["dirt"]
        R.box(0, -4.6, 0, 4.5, 0.35, 4.5, shade(dirt, 0.65), layer=-2)
        R.box(0, -3.7, 0, 9.5, 0.6, 9.5, shade(dirt, 0.8), layer=-2)
        R.box(0, -2.0, 0, GROUND_HALF, 1.1, GROUND_HALF, dirt, layer=-2)
        R.box(0, -0.45, 0, h + 0.4, 0.45, h + 0.4, TEAL if self.wrap else wd["slab"], layer=-1)
        lc = wd["lamp"]
        for sx in (-1, 1):
            for sz in (-1, 1):
                px, pz = sx * (h + 0.9), sz * (h + 0.9)
                R.box(px, -0.1, pz, 0.1, 0.8, 0.1, (70, 70, 80))
                R.box(px, 0.85 + 0.03 * math.sin(t * 3 + sx), pz, 0.2, 0.16, 0.2, lc, rot=t, edge=True)
                R.glow(px, 0.9, pz, 1.4, lc)
        for (x, z, boxes, fl, ph) in get_scenery(widx):
            if R.culled(x, 0.5, z, 2.5):
                continue
            for (ox, oy, oz, hx, hy, hz, col, rot) in boxes:
                if fl:
                    R.box(x + ox, GY + oy + 0.3 * math.sin(t * 0.9 + ph), z + oz, hx, hy, hz, col, rot + t * 0.15)
                else:
                    R.box(x + ox, GY + oy, z + oz, hx, hy, hz, col, rot)
        w0, w1 = shade(wd["wall"], 1.0), shade(wd["wall"], 1.07)
        for (x, y, sk) in self.wall_draw:
            R.box(wx(x), 0.5, wx(y), 0.5, 0.5, 0.5, w1 if (x + y) % 2 else w0, edge=True, skip=sk)
        shadows = S.get("shadows", True)
        sh = shade(wd["fa"], 0.55 * dim)

        def shadow(x, z, r):
            if shadows:
                R.box(x, 0.012, z, r, 0.005, r, sh, layer=1)

        if self.food:
            x, z = self.pxz(self.food)
            R.box(x, 0.02, z, 0.46, 0.02, 0.46, shade(FRUITS[self.ftype][1], 0.6), layer=1)
            shadow(x, z, 0.3)
            draw_fruit(R, self.ftype, x, z, t)
            if self.boss:
                R.glow(x, 0.6, z, 1.5, self.boss.d["acc"])
        for it in self.items:
            if it["t"] < 2 and int(it["t"] * 6) % 2:
                continue
            x, z = self.pxz(it["pos"])
            shadow(x, z, 0.28)
            if it["kind"] == "fruit":
                R.box(x, 0.02, z, 0.5, 0.02, 0.5, shade(FRUITS[it["sub"]][1], 0.6), layer=1)
                draw_fruit(R, it["sub"], x, z, t, 0.05)
            elif it["kind"] == "coin":
                b = 0.1 * math.sin(t * 4 + x)
                R.box(x, 0.5 + b, z, 0.26, 0.26, 0.04, COIN_COL, rot=t * 3, edge=True)
                R.glow(x, 0.5 + b, z, 0.8, COIN_COL)
            else:
                col = POWERUPS[it["sub"]][1]
                b = 0.14 * math.sin(t * 5 + z)
                R.box(x, 0.02, z, 0.5, 0.02, 0.5, shade(col, 0.6), layer=1)
                R.box(x, 0.55 + b, z, 0.3, 0.3, 0.3, col, rot=t * 2.2, edge=True)
                R.box(x, 0.55 + b, z, 0.14, 0.4, 0.14, WHITE, rot=-t * 2.2)
                R.glow(x, 0.55 + b, z, 1.2, col)
        for r in self.roamers:
            x, z = self.pxz(r["pos"])
            col = r["kind"][1]
            frozen = self.pw.get("freeze", 0) > 0
            shadow(x, z, 0.34)
            R.box(x, 0.4, z, 0.36, 0.36, 0.36, mix(col, (200, 235, 255), 0.6) if frozen else col, rot=0 if frozen else t * 2, edge=True)
            R.box(x, 0.4, z, 0.2, 0.5, 0.2, shade(col, 1.2), rot=t * 2 + 0.5)
            R.glow(x, 0.5, z, 1.0, col)
        if self.boss:
            self.boss.render(R, t)
        if self.snake.visible:
            self.render_snake(R, t, shadow)
        if q >= 1:
            self.particles.render(R, 10 if q == 2 else 4)
        else:
            self.particles.render(R, 0)

    def render_snake(self, R, t, shadow):
        sn, look = self.snake, self.look
        n = len(sn.body)
        if self.invuln > 0 and int(t * 14) % 2:
            return
        ghost = self.pw.get("ghost", 0) > 0
        for i in range(n - 1, -1, -1):
            gx, gy = sn.pos(i)
            a = min(1.0, max(0.0, (sn.age - i * 0.05) / 0.4)) if sn.age < 1.2 + n * 0.05 else 1.0
            dy = (1 - a) * 2.5 - (0.12 if ghost else 0)
            x, z = wx(gx), wx(gy)
            if i > 0:
                px, py = sn.pos(i - 1)
                vx, vz = px - gx, py - gy
                if abs(vx) + abs(vz) < 1.6:
                    ln = math.hypot(vx, vz) or 1.0
                    wob = 0.05 * math.sin(t * 7 - i * 0.9) * min(1.0, i / 3)
                    if i >= n - 2:
                        wob += 0.07 * math.sin(t * 9)
                    x += -vz / ln * wob
                    z += vx / ln * wob
            shadow(x, z, 0.38)
            if i == 0:
                hc = look["head"]
                if ghost:
                    hc = mix(hc, WHITE, 0.5)
                R.box(x, 0.40 + dy + 0.02 * math.sin(t * 6), z, 0.47, 0.40, 0.47, hc, rot=sn.wobble, edge=True)
                d = sn.dir
                p = (-d[1], d[0])
                for sg in (-1, 1):
                    ex = x + d[0] * 0.25 + p[0] * 0.21 * sg
                    ez = z + d[1] * 0.25 + p[1] * 0.21 * sg
                    R.box(ex, 0.84 + dy, ez, 0.11, 0.05, 0.11, (245, 245, 245), bias=2.0)
                    R.box(ex + d[0] * 0.06, 0.90 + dy, ez + d[1] * 0.06, 0.06, 0.04, 0.06, (15, 15, 25), bias=3.0)
                if (t * 1.3) % 1 < 0.22:
                    R.box(x + d[0] * 0.62, 0.3 + dy, z + d[1] * 0.62, 0.04 + 0.16 * abs(d[0]), 0.02,
                          0.04 + 0.16 * abs(d[1]), (230, 40, 70), bias=1.0)
                draw_head_style(R, look, self.head_style, x, z, d)
                draw_hat(R, look, self.ch["hat"] if self.hat == "default" else self.hat, x, z, d, t)
                self.render_aura(R, x, z, t)
            else:
                s = 0.43 - 0.08 * i / max(1, n - 1)
                if i == n - 1 and n > 3:
                    s *= 0.8
                col = seg_color(look, i, n, t)
                if ghost:
                    col = mix(col, WHITE, 0.5)
                R.box(x, 0.34 + dy, z, s, 0.34, s, col, edge=True)

    def render_aura(self, R, x, z, t):
        pw = self.pw
        glow = None
        if pw.get("shield", 0) > 0:
            for k in range(4):
                a = t * 3 + k * 1.571
                R.box(x + 0.75 * math.cos(a), 0.5, z + 0.75 * math.sin(a), 0.08, 0.08, 0.08, (90, 235, 255), rot=a, bias=1)
            glow = (80, 230, 255)
        if pw.get("magnet", 0) > 0:
            for k in range(3):
                a = -t * 4 + k * 2.09
                R.box(x + 0.95 * math.cos(a), 0.3, z + 0.95 * math.sin(a), 0.07, 0.07, 0.07, (230, 90, 230), bias=1)
            glow = glow or (220, 80, 220)
        if pw.get("speed", 0) > 0:
            glow = glow or (255, 150, 40)
        elif pw.get("freeze", 0) > 0:
            glow = glow or (160, 220, 255)
        elif pw.get("mult", 0) > 0 or pw.get("dxp", 0) > 0 or pw.get("coinb", 0) > 0:
            glow = glow or (255, 230, 120)
        if glow:
            R.glow(x, 0.5, z, 1.6, glow)

# --------------------------------------------------------------------------- #
#  Sky backdrop + weather
# --------------------------------------------------------------------------- #
class Backdrop:
    def __init__(self):
        self.grad, self.glow, self.stars, self.clouds = {}, {}, {}, {}

    def draw(self, surf, wd, widx, yaw, t):
        W, H = surf.get_size()
        key = (W, H, widx)
        bg = self.grad.get(key)
        if bg is None:
            if len(self.grad) > 12:
                self.grad.clear()
            bg = pygame.Surface((W, H))
            top, bot = wd["sky"]
            for y in range(H):
                pygame.draw.line(bg, mix(top, bot, (y / H) ** 0.9), (0, y), (W, y))
            self.grad[key] = bg
        surf.blit(bg, (0, 0))
        off = yaw * W * 0.1

        if wd["stars"]:
            st = self.stars.get(widx)
            if st is None:
                r = random.Random(widx * 13 + 5)
                st = self.stars[widx] = [(r.random(), r.random() * 0.8, r.choice((1, 1, 2, 2, 3)), r.random() * 6.28)
                                         for _ in range(wd["stars"])]
            for u, v, s, ph in st:
                c = int(110 + 145 * (0.55 + 0.45 * math.sin(t * 1.6 + ph)))
                surf.fill((c, c, min(255, c + 25)), (int((u * W - off) % W), int(v * H), s, s))

        kind, col, (u, v) = wd["body"]
        bx, by = (u * W - off * 1.3) % (W + 260) - 130, v * H
        r = int(H * (0.095 if kind == "sun" else 0.07 if kind == "moon" else 0.085))
        g = self.glow.get((kind, col, r))
        if g is None:
            big = int(r * 3.2)
            g = pygame.Surface((big * 2, big * 2), pygame.SRCALPHA)
            for i in range(14, 0, -1):
                pygame.draw.circle(g, (*col, int(8 + (15 - i) * 3.5)), (big, big), int(r * (1 + i * 0.16)))
            self.glow[(kind, col, r)] = g
        surf.blit(g, (int(bx) - g.get_width() // 2, int(by) - g.get_height() // 2))
        pygame.draw.circle(surf, col, (int(bx), int(by)), r)
        if kind == "moon":
            for dx, dy, rr in ((-.3, -.2, .22), (.25, .15, .17), (-.05, .35, .12)):
                pygame.draw.circle(surf, shade(col, 0.86), (int(bx + dx * r), int(by + dy * r)), max(2, int(rr * r)))
        elif kind == "planet":
            for dy in (-.35, .1, .45):
                pygame.draw.circle(surf, shade(col, 0.85), (int(bx), int(by + dy * r)), int(r * .5), 3)
            pygame.draw.ellipse(surf, (225, 205, 255), (int(bx - 1.9 * r), int(by - .45 * r), int(3.8 * r), int(.9 * r)), 5)

        mount = wd["mount"]
        if mount:
            self._mountain(surf, mount[0], H * 0.50, 62, yaw * W * 0.30, 0.004, W, H, wd["skyline"])
        if wd["clouds"]:
            cl = self.clouds.get(widx)
            if cl is None:
                r2 = random.Random(widx * 7 + 3)
                cl = self.clouds[widx] = [(r2.random(), r2.uniform(0.1, 0.38), r2.uniform(0.7, 1.5), r2.uniform(4, 12))
                                          for _ in range(8)]
            for u2, v2, s, sp in cl:
                x = (u2 * (W + 500) + t * sp - off * 1.6) % (W + 500) - 250
                y = v2 * H
                for dx, dy, w, hh in ((0, 0, 150, 40), (-45, 8, 110, 32), (50, 10, 120, 34), (10, -14, 90, 34)):
                    pygame.draw.ellipse(surf, wd["clouds"], (int(x + dx * s), int(y + dy * s), int(w * s), int(hh * s)))
        if mount:
            self._mountain(surf, mount[1], H * 0.57, 46, yaw * W * 0.55, 0.007, W, H, wd["skyline"])

    @staticmethod
    def _mountain(surf, col, base, amp, off, k, W, H, skyline):
        if skyline:
            for x in range(0, W + 40, 40):
                idx = int((x + off) // 40)
                hgt = 20 + ((idx * 7919) % 101) * 0.9 * (amp / 50.0)
                pygame.draw.rect(surf, col, (x, int(base - hgt), 40, int(H - base + hgt)))
            return
        pts = [(0, H)]
        for x in range(0, W + 30, 30):
            X = x + off
            pts.append((x, base - amp * (abs(math.sin(X * k)) * 0.7 + 0.3 * abs(math.sin(X * k * 2.7 + 1)))))
        pts.append((W, H))
        pygame.draw.polygon(surf, col, pts)


AMBIENT = {   # count, vx, vy, size, colours, style
    "snow":      (70, (-.01, .01), (.04, .09), (1.5, 3.2), [(255, 255, 255)], "circle"),
    "petals":    (45, (-.02, .01), (.03, .06), (2, 3.5), [(255, 190, 210), (255, 230, 240), (255, 255, 255)], "rect"),
    "dust":      (40, (.03, .07), (-.005, .005), (1, 2), [(230, 200, 150)], "circle"),
    "embers":    (55, (-.01, .01), (-.10, -.04), (1.5, 3), [(255, 160, 60), (255, 100, 30), (255, 210, 90)], "glow"),
    "sparks":    (50, (-.005, .005), (-.12, -.05), (1, 2.4), [(0, 255, 230), (255, 60, 200), (120, 160, 255)], "glow"),
    "fireflies": (35, (-.02, .02), (-.02, .02), (2, 3.5), [(220, 255, 120)], "glow"),
    "leaves":    (40, (-.03, .0), (.04, .08), (3, 5), [(220, 90, 40), (240, 160, 50), (180, 60, 40)], "rect"),
    "bubbles":   (35, (-.01, .01), (-.07, -.03), (2, 5), [(200, 240, 255)], "ring"),
    "sprinkles": (50, (-.01, .01), (.04, .09), (2, 3.5), [(255, 90, 120), (90, 200, 255), (255, 230, 90), (150, 255, 150)], "rect"),
    "stardust":  (60, (.005, .02), (-.01, .01), (1, 2.2), [(200, 210, 255), (255, 240, 200)], "glow"),
}


class Ambient:
    def __init__(self, kind, seed=1, scale=1.0):
        rng = random.Random(seed)
        n, vxr, vyr, sr, cols, self.style = AMBIENT[kind]
        self.items = [[rng.random(), rng.random(), rng.uniform(*vxr), rng.uniform(*vyr), rng.uniform(*sr),
                       rng.choice(cols), rng.random() * 6.28] for _ in range(max(4, int(n * scale)))]
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        for p in self.items:
            p[0] = (p[0] + (p[2] + 0.012 * math.sin(self.t * 1.3 + p[6])) * dt) % 1.0
            p[1] = (p[1] + p[3] * dt) % 1.0

    def draw(self, surf):
        W, H = surf.get_size()
        for x, y, _, _, s, col, ph in self.items:
            px, py = int(x * W), int(y * H)
            if self.style == "circle":
                pygame.draw.circle(surf, col, (px, py), max(1, int(s)))
            elif self.style == "rect":
                pygame.draw.rect(surf, col, (px, py, int(s * 1.7), max(2, int(s))))
            elif self.style == "line":
                pygame.draw.line(surf, col, (px, py), (px - 3, py + int(s * 6)), 1)
            elif self.style == "ring":
                pygame.draw.circle(surf, col, (px, py), max(2, int(s)), 1)
            else:
                b = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(self.t * 3 + ph))
                pygame.draw.circle(surf, shade(col, b), (px, py), max(1, int(s)))





# --------------------------------------------------------------------------- #
#  Weather (screen-space particles per world) + glow sprites
# --------------------------------------------------------------------------- #
AMBIENT["rain"] = (90, (-.03, -.015), (.55, .8), (1, 1.8), [(150, 185, 235), (120, 150, 205)], "line")
AMBIENT["ash"] = (70, (-.01, .02), (.02, .05), (1.5, 3), [(110, 100, 100), (160, 150, 140), (80, 75, 75)], "circle")
_GLOW_CACHE = {}


def glow_surface(col, rad):
    key = (col, rad)
    s = _GLOW_CACHE.get(key)
    if s is None:
        if len(_GLOW_CACHE) > 120:
            _GLOW_CACHE.clear()
        s = pygame.Surface((rad * 2, rad * 2))
        step = max(1, rad // 10)
        for i in range(rad, 0, -step):
            k = 0.5 * (1 - i / rad) ** 1.6
            pygame.draw.circle(s, (int(col[0] * k), int(col[1] * k), int(col[2] * k)), (rad, rad), i)
        _GLOW_CACHE[key] = s
    return s


class WeatherSystem:
    def __init__(self):
        self.layers, self.key = [], None

    def set_world(self, widx, S):
        key = (widx, S.get("weather", True), S.get("quality", 2))
        if key == self.key:
            return
        self.key, self.layers = key, []
        if S.get("weather", True):
            for i, kind in enumerate(WORLDS[widx]["weather"]):
                self.layers.append(Ambient(kind, widx * 7 + i + 1, (0.4, 0.7, 1.0)[S.get("quality", 2)]))

    def update(self, dt, reduce=False):
        for l in self.layers:
            l.update(dt * (0.35 if reduce else 1.0))

    def draw(self, surf):
        for l in self.layers:
            l.draw(surf)


# --------------------------------------------------------------------------- #
#  UI toolkit
# --------------------------------------------------------------------------- #
class UI:
    def __init__(self, settings):
        self.S = settings
        self._fonts, self._titles, self._vign = {}, {}, {}
        self.notes = []
        self.snd = None
        self.set_theme("classic")

    def set_theme(self, tid):
        t = THEME_DEFS.get(tid, THEME_DEFS["classic"])
        self.acc, self.pc = t[2], t[3]
        self._titles.clear()

    def clear_fonts(self):
        self._fonts.clear()
        self._titles.clear()

    def font(self, size):
        size = max(10, int(size * self.S.get("ui_scale", 1.0)))
        f = self._fonts.get(size)
        if f is None:
            f = self._fonts[size] = pygame.font.Font(None, size)
        return f

    def text(self, surf, s, size, color, pos, anchor="center", shadow=True):
        f = self.font(size)
        img = f.render(s, True, color)
        r = img.get_rect()
        setattr(r, anchor, pos)
        if shadow:
            sh = f.render(s, True, (0, 0, 0))
            sh.set_alpha(140)
            surf.blit(sh, r.move(2, 2))
        surf.blit(img, r)
        return r

    def wrap(self, s, size, width):
        f, lines, cur = self.font(size), [], ""
        for w in s.split():
            test = (cur + " " + w).strip()
            if f.size(test)[0] > width and cur:
                lines.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            lines.append(cur)
        return lines

    def panel(self, surf, rect, alpha=185, border=None):
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*self.pc, alpha), s.get_rect(), border_radius=16)
        pygame.draw.rect(s, (*(border or self.acc), 200), s.get_rect(), 2, border_radius=16)
        surf.blit(s, rect.topleft)

    def bar(self, surf, rect, frac, color, bg=(30, 40, 60), border=True):
        pygame.draw.rect(surf, bg, rect, border_radius=rect.height // 2)
        if frac > 0:
            r = pygame.Rect(rect.x, rect.y, max(rect.height, int(rect.width * min(1.0, frac))), rect.height)
            pygame.draw.rect(surf, color, r, border_radius=rect.height // 2)
        if border:
            pygame.draw.rect(surf, (200, 225, 215), rect, 1, border_radius=rect.height // 2)

    def title3d(self, s, size, front, back):
        key = (s, size, front)
        if key not in self._titles:
            f = self.font(size)
            w, h = f.size(s)
            surf = pygame.Surface((w + 30, h + 30), pygame.SRCALPHA)
            for i in range(12, 0, -1):
                surf.blit(f.render(s, True, mix(back, (0, 0, 0), i / 16)), (4 + i * 0.9, 4 + i * 1.1))
            surf.blit(f.render(s, True, front), (4, 4))
            self._titles[key] = surf
        return self._titles[key]

    # -- notifications -------------------------------------------------------- #
    def notify(self, text, color=WHITE, kind=""):
        self.notes.append(dict(text=text, color=color, age=0.0))
        if len(self.notes) > 6:
            self.notes.pop(0)
        if self.snd:
            snd = {"level": "level", "unlock": "unlock", "mission": "mission", "ach": "ach", "coin": "coin"}.get(kind)
            if snd:
                self.snd(snd)

    def update_notes(self, dt):
        for n in self.notes:
            n["age"] += dt
        self.notes = [n for n in self.notes if n["age"] < 3.6]

    def draw_notes(self, surf, y0=80):
        W = surf.get_width()
        for i, n in enumerate(self.notes[-5:]):
            a = n["age"]
            ease = min(1.0, a / 0.25)
            ease = 1 - (1 - ease) ** 3
            fade = min(1.0, (3.6 - a) / 0.4)
            f = self.font(26)
            w = f.size(n["text"])[0] + 56
            rect = pygame.Rect(0, 0, w, 40)
            rect.topright = (W - 14 + int((1 - ease) * (w + 20)), y0 + i * 46)
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (*self.pc, 225), s.get_rect(), border_radius=12)
            pygame.draw.rect(s, (*n["color"], 255), s.get_rect(), 2, border_radius=12)
            pygame.draw.circle(s, n["color"], (22, 20), 7)
            s.blit(f.render(n["text"], True, (240, 245, 250)), (40, 11))
            s.set_alpha(int(255 * max(0.0, fade)))
            surf.blit(s, rect.topleft)

    def vignette(self, W, H):
        key = (W, H)
        v = self._vign.get(key)
        if v is None:
            if len(self._vign) > 3:
                self._vign.clear()
            v = pygame.Surface((W, H), pygame.SRCALPHA)
            for i in range(0, 200, 8):
                a = int(230 * (1 - i / 200) ** 1.6)
                pygame.draw.rect(v, (0, 0, 0, a), (i, i, W - 2 * i, H - 2 * i), 10)
            self._vign[key] = v
        return v

    # -- icons ---------------------------------------------------------------- #
    def star(self, surf, cx, cy, r, filled=True):
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = r if k % 2 == 0 else r * 0.45
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        pygame.draw.polygon(surf, (255, 205, 50) if filled else (60, 66, 84), pts)
        pygame.draw.polygon(surf, (255, 235, 140) if filled else (100, 108, 130), pts, 2)

    def stars(self, surf, cx, cy, n, r=11, total=3):
        for i in range(total):
            self.star(surf, cx + (i - (total - 1) / 2) * r * 2.3, cy, r, i < n)

    def icon(self, surf, kind, cx, cy, r, col=WHITE):
        D = pygame.draw
        cx, cy, r = int(cx), int(cy), int(r)
        if kind == "coin":
            D.circle(surf, COIN_COL, (cx, cy), r)
            D.circle(surf, (190, 140, 20), (cx, cy), r, 2)
            D.circle(surf, (230, 170, 30), (cx, cy), max(2, r // 2), 2)
        elif kind == "xp":
            D.polygon(surf, XP_COL, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])
            D.polygon(surf, WHITE, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], 2)
        elif kind == "heart":
            D.circle(surf, (255, 90, 110), (cx - r // 2, cy - r // 4), r // 2 + 1)
            D.circle(surf, (255, 90, 110), (cx + r // 2, cy - r // 4), r // 2 + 1)
            D.polygon(surf, (255, 90, 110), [(cx - r, cy), (cx + r, cy), (cx, cy + r)])
        elif kind == "star":
            self.star(surf, cx, cy, r)
        elif kind == "lock":
            D.rect(surf, (150, 160, 180), (cx - r * 0.7, cy - r * 0.1, r * 1.4, r * 1.0), border_radius=3)
            D.circle(surf, (150, 160, 180), (cx, cy - r * 0.15), int(r * 0.5), 3)
        elif kind == "check":
            D.lines(surf, (120, 255, 160), False, [(cx - r * .7, cy), (cx - r * .15, cy + r * .6), (cx + r * .8, cy - r * .6)], 4) if hasattr(D, "lines") else None
        elif kind == "note":
            D.circle(surf, col, (cx - r // 3, cy + r // 2), r // 2)
            D.line(surf, col, (cx + r // 6, cy + r // 2), (cx + r // 6, cy - r), 3)
            D.line(surf, col, (cx + r // 6, cy - r), (cx + r, cy - r // 2), 3)
        elif kind in POWERUPS:
            c = POWERUPS[kind][1]
            D.circle(surf, (20, 26, 44), (cx, cy), r)
            D.circle(surf, c, (cx, cy), r, 2)
            if kind == "speed":
                for o in (-r // 3, r // 4):
                    D.polygon(surf, c, [(cx + o - r // 4, cy - r // 2), (cx + o + r // 4, cy), (cx + o - r // 4, cy + r // 2)])
            elif kind in ("slow", "time"):
                D.line(surf, c, (cx, cy), (cx, cy - r // 2), 2)
                D.line(surf, c, (cx, cy), (cx + r // 3, cy + r // 5), 2)
            elif kind == "magnet":
                D.circle(surf, c, (cx, cy + r // 8), r // 2, 4)
                D.rect(surf, (20, 26, 44), (cx - r // 2, cy + r // 8, r, r // 2))
            elif kind == "shield":
                D.polygon(surf, c, [(cx - r // 2, cy - r // 2), (cx + r // 2, cy - r // 2), (cx + r // 2, cy), (cx, cy + r // 1.6), (cx - r // 2, cy)])
            elif kind == "ghost":
                D.circle(surf, c, (cx, cy - r // 6), r // 2)
                D.rect(surf, c, (cx - r // 2, cy - r // 6, r, r // 2))
            elif kind == "freeze":
                for a in (0, 1.047, 2.094):
                    D.line(surf, c, (cx + math.cos(a) * r * .6, cy + math.sin(a) * r * .6), (cx - math.cos(a) * r * .6, cy - math.sin(a) * r * .6), 2)
            else:
                self.text(surf, {"dxp": "XP", "coinb": "$", "mult": "x2"}.get(kind, "?"), r + 4, c, (cx, cy), shadow=False)
        else:
            D.circle(surf, col, (cx, cy), r)

    def snake_icon(self, surf, look, hat, rect, t=0.0, n=7):
        """2D preview of a snake (used by the character / shop screens)."""
        w, h = rect.width, rect.height
        r = min(h * 0.22, w / (n * 2.3))
        pts = []
        for i in range(n):
            x = rect.x + w * 0.12 + i * (w * 0.76 / (n - 1))
            y = rect.centery + math.sin(t * 2.2 + i * 0.8) * h * 0.1
            pts.append((x, y))
        for i in range(n - 1):                                    # tail first, head last
            rr = r * (0.6 + 0.4 * i / n)
            pygame.draw.circle(surf, seg_color(look, n - 1 - i, n, t), (int(pts[i][0]), int(pts[i][1])), int(rr))
        hx, hy = pts[-1]
        pygame.draw.circle(surf, look["head"], (int(hx), int(hy)), int(r * 1.25))
        pygame.draw.circle(surf, (250, 250, 250), (int(hx + r * .45), int(hy - r * .35)), max(2, int(r * .32)))
        pygame.draw.circle(surf, (15, 15, 25), (int(hx + r * .55), int(hy - r * .35)), max(1, int(r * .16)))
        top = hy - r * 1.25
        acc = look["acc"]
        if hat in ("crown", "halo"):
            pygame.draw.polygon(surf, (255, 215, 70), [(hx - r, top), (hx - r * .7, top - r * .7), (hx - r * .3, top - r * .2), (hx, top - r * .8),
                                                         (hx + r * .3, top - r * .2), (hx + r * .7, top - r * .7), (hx + r, top)]) if hat == "crown" else \
                pygame.draw.ellipse(surf, (255, 230, 120), (hx - r, top - r * .5, r * 2, r * .5), 3)
        elif hat in ("wizard", "party"):
            pygame.draw.polygon(surf, look["b1"] if hat == "wizard" else acc, [(hx - r, top), (hx + r, top), (hx, top - r * 2)])
        elif hat in ("horns", "viking"):
            for sg in (-1, 1):
                pygame.draw.polygon(surf, (245, 240, 220), [(hx + sg * r * .5, top), (hx + sg * r * 1.0, top - r * 1.0), (hx + sg * r * 1.1, top + r * .1)])
        elif hat in ("tophat", "cowboy", "cap"):
            pygame.draw.rect(surf, (35, 35, 48) if hat == "tophat" else (150, 100, 60), (hx - r * .7, top - r * 1.1, r * 1.4, r * 1.1))
            pygame.draw.rect(surf, (35, 35, 48) if hat == "tophat" else (150, 100, 60), (hx - r * 1.1, top - r * .15, r * 2.2, r * .25))
        elif hat in ("crest", "antenna", "flower", "pumpkin", "headband", "shades"):
            pygame.draw.circle(surf, acc, (int(hx), int(top - r * .2)), max(3, int(r * .35)))

    def draw_ovl_buttons(self, surf, labels, sel, cy, hits):
        W = surf.get_width()
        bw, gap = 190, 18
        total = len(labels) * bw + (len(labels) - 1) * gap
        x0 = W // 2 - total // 2
        for i, lab in enumerate(labels):
            r = pygame.Rect(x0 + i * (bw + gap), cy, bw, 46)
            on = i == sel
            s = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (*(self.acc if on else (50, 60, 84)), 235 if on else 200), s.get_rect(), border_radius=12)
            pygame.draw.rect(s, (255, 255, 255, 230 if on else 90), s.get_rect(), 2, border_radius=12)
            surf.blit(s, r.topleft)
            self.text(surf, lab, 30, (10, 16, 28) if on else (225, 232, 245), r.center, shadow=False)
            hits.append((r, i))




# --------------------------------------------------------------------------- #
#  Application: menus, screens, HUD, input, camera
# --------------------------------------------------------------------------- #
MAP_IDX = {slug(m[0]): i for i, m in enumerate(MAPS)}
MENU_ITEMS = ("PLAY", "ADVENTURE", "CLASSIC", "WORLDS", "MAPS", "CHARACTERS", "SHOP", "MISSIONS", "ACHIEVEMENTS",
              "MUSIC", "SETTINGS", "HIGH SCORES", "PROFILE", "QUIT")
SCREEN_OF = {"PLAY": "play", "ADVENTURE": "adventure", "WORLDS": "worlds", "MAPS": "maps", "CHARACTERS": "characters",
             "SHOP": "shop", "MISSIONS": "missions", "ACHIEVEMENTS": "achievements", "MUSIC": "music",
             "SETTINGS": "settings", "HIGH SCORES": "scores", "PROFILE": "profile"}
SCREEN_TITLES = {"play": "PLAY", "adventure": "ADVENTURE", "challenge": "CHALLENGES", "worlds": "WORLDS", "maps": "MAPS",
                 "characters": "CHARACTERS", "shop": "SHOP", "missions": "MISSIONS", "achievements": "ACHIEVEMENTS",
                 "music": "MUSIC", "settings": "SETTINGS", "scores": "HIGH SCORES", "profile": "PROFILE"}
SET_ROWS = [
    ("hdr", "GRAPHICS"), ("quality", "Quality", ["Low", "Medium", "High"]), ("particles", "Particles", "bool"),
    ("shadows", "Shadows", "bool"), ("shake", "Screen Shake", "bool"), ("effects", "Glow & Effects", "bool"),
    ("weather", "Weather", "bool"),
    ("hdr", "AUDIO"), ("music_vol", "Music Volume", "vol"), ("sfx_vol", "SFX Volume", "vol"), ("mute", "Mute All", "bool"),
    ("hdr", "GAMEPLAY"), ("difficulty", "Difficulty", DIFFS), ("camera", "Camera Mode", ["Overview", "Chase", "Top-down"]),
    ("screen_fx", "Screen Effects", "bool"),
    ("hdr", "ACCESSIBILITY"), ("ui_scale", "UI Scale", "scale"), ("reduce_motion", "Reduce Motion", "bool"),
    ("hdr", "CONTROLS"), ("show_controls", "Show Controls Hint", "bool"), ("help", "Keyboard Controls", "info"),
]
KEY_HELP = ["Arrows / WASD  -  steer the snake", "Q / E  -  rotate the camera", "Mouse drag  -  orbit / tilt", "Mouse wheel  -  zoom",
            "V  -  switch camera mode", "P / Esc  -  pause / back", "N / B  -  next / previous music track", "M  -  mute all",
            "F11  -  fullscreen", "Menus: arrows + Enter, or use the mouse"]
MODE_INFO = {
    "adventure": "25 hand-built stages across 20 worlds. Every stage has its own objective and a boss waits at stages 5, 10, 15, 20 and 25.",
    "classic": "The original: 10 levels on your selected map and world. Collect fruit, dodge obstacles, keep your lives.",
    "timeattack": "90 seconds on the clock. Every fruit adds time. Score as much as you can.",
    "survival": "One life. The arena fills with obstacles and the speed keeps climbing. How long can you last?",
    "challenge": "Eight hand-made challenges with special rules and big rewards.",
    "daily": "A new challenge every day with a fixed snake. Big coin and XP reward - once per day.",
}


def _row(label, sub="", right="", rc=WHITE, **kw):
    d = dict(label=label, sub=sub, right=right, rc=rc)
    d.update(kw)
    return d


class MenuFX:
    def __init__(self):
        r = random.Random(7)
        self.items = [(r.random(), r.random(), r.choice(list(FRUITS)), r.uniform(0.5, 1.4), r.uniform(0, 6.28)) for _ in range(14)]

    def draw(self, surf, t):
        W, H = surf.get_size()
        for u, v, ft, sc, ph in self.items:
            x = (u * (W + 200) + t * 14 * sc) % (W + 200) - 100
            y = v * H + math.sin(t * 0.8 + ph) * 18
            r = int(10 * sc + 4)
            col = FRUITS[ft][1]
            pygame.draw.circle(surf, shade(col, 0.5), (int(x), int(y)), r)
            pygame.draw.circle(surf, shade(col, 0.85), (int(x - r * .25), int(y - r * .25)), max(2, r // 2))


def _inside(r, pos):
    return r.x <= pos[0] < r.x + r.width and r.y <= pos[1] < r.y + r.height


class App:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("SNAKE 3D")
        pygame.display.set_mode((1100, 720), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.save = SaveSystem()
        self.S = self.save.data["settings"]
        self.audio = AudioManager(self.S)
        self.ui = UI(self.S)
        self.ui.snd = self.audio.play
        self.prog = ProgressionSystem(self.save, notify=self.ui.notify, sfx=self.audio.play)
        self.audio.prog = self.prog
        self.apply_settings()
        self.cam, self.R, self.sky = Camera(), Renderer(), Backdrop()
        self.weather, self.fx = WeatherSystem(), MenuFX()
        self.mode = "intro" if not self.prog.d["seen_intro"] else "menu"
        self.intro_t, self.menu_t, self.menu_yaw = 0.0, 0.0, 0.0
        self.sel, self.psel, self.scr, self.back = 0, 0, None, "menu"
        self.lsel, self.shop_tab, self.hits = {}, 0, []
        self.game = self.demo = None
        self.menu_world = 0
        self.cam_mode, self.zoom = 0, 1.0
        self.user_yaw, self.user_pitch = 0.0, math.radians(52)
        self.dragging = False
        self.trans = None
        self.modal = None
        self.ovl_sel = 0
        self.last_start = ("classic", {})
        self.map_cache = {}
        self.autosave_t = 0.0
        self.rebuild_demo()
        self.audio.set_context("menu")
        streak = self.prog.check_streak()
        if streak:
            self.modal = ("DAILY REWARD", ["Day %d of your streak!" % streak["day"],
                                           "+%d coins" % streak["coins"], "+%d XP" % streak["xp"],
                                           "Come back tomorrow for more." if streak["day"] < 7 else "Week complete - big reward!"])
            self.audio.play("unlock")
        if self.save.status:
            self.ui.notify(self.save.status, (255, 180, 100))
        self.prog.commit()

    # -- settings / helpers ---------------------------------------------------- #
    def apply_settings(self):
        global SCEN_COUNT
        SCEN_COUNT = (12, 22, 30)[self.S["quality"]]
        self.ui.clear_fonts()
        self.ui.set_theme(self.prog.d["equipped"]["theme"])

    def eq(self, slot):
        return self.prog.d["equipped"][slot]

    def in_menu(self):
        return self.mode in ("menu", "screen", "intro")

    def rebuild_demo(self):
        cfg = self.make_cfg("classic")
        cfg["boosters"] = []
        self.demo = Game(cfg, demo=True)

    def selected_map(self):
        mid = self.S["sel_map"]
        i = MAP_IDX.get(mid, 0)
        return i if self.prog.inv.owns("maps", mid) else 0

    def selected_world(self):
        wid = self.S["sel_world"]
        if wid == "auto" or wid not in WORLD_IDX or not self.prog.inv.owns("worlds", wid):
            return None
        return WORLD_IDX[wid]

    def make_cfg(self, mode, **kw):
        eq = self.prog.d["equipped"]
        forced = kw.pop("char_id", None)
        char = CHAR_IDX.get(forced or eq["character"], 0)
        cfg = dict(mode=mode, map=self.selected_map(), world=self.selected_world(), worlds=self.prog.owned_worlds(),
                   diff=self.S["difficulty"], char=char, look=make_look(CHARACTERS[char], "default" if forced else eq["skin"]),
                   hat=eq["hat"], head=eq["head"], trail=eq["trail"], effect=eq["effect"], settings=self.S, boosters=[])
        cfg.update(kw)
        return cfg

    def map_walls(self, idx):
        if idx not in self.map_cache:
            self.map_cache[idx] = build_walls(idx, 1, random.Random(1))
        return self.map_cache[idx]

    # -- transitions / flow ---------------------------------------------------- #
    def go(self, fn):
        if self.trans:
            self.queued = fn
            return
        self.trans = dict(t=0.0, fn=fn, phase=0)

    def end_intro(self):
        self.prog.d["seen_intro"] = True
        self.prog.commit()
        self.go(lambda: setattr(self, "mode", "menu"))

    def open_screen(self, name, back="menu"):
        def f():
            self.scr, self.mode, self.back = name, "screen", back
            self.lsel.setdefault(name, 0)
            if name == "adventure":
                self.lsel[name] = min(ADV_STAGES, self.prog.d["adventure"]["stage"]) - 1
        self.go(f)

    def close_screen(self):
        def f():
            self.mode = "pause" if self.back == "pause" else "menu"
            if self.scr in ("characters", "shop"):
                self.rebuild_demo()
            if self.scr == "challenge":
                self.scr, self.mode = "play", "screen"
        self.go(f)

    def start_game(self, mode, **kw):
        self.go(lambda: self._start(mode, **kw))

    def _start(self, mode, **kw):
        cfg = self.make_cfg(mode, **kw)
        cfg["boosters"] = self.prog.inv.consume_armed()
        self.last_start = (mode, kw)
        self.game = Game(cfg, self.audio, self.prog)
        self.prog.recent.clear()
        self.mode, self.ovl_sel = "game", 0
        self.cam_mode, self.zoom = self.S["camera"], 1.0
        self.user_yaw, self.user_pitch = 0.0, math.radians(52)
        self.audio.play("click")
        self.prog.commit()

    def start_daily(self):
        dd = self.prog.daily_challenge()
        if dd["done"]:
            self.ui.notify("Daily challenge already completed today!", (255, 200, 100))
            self.audio.play("deny")
            return
        self.start_game("daily", daily=dd, char_id=dd["char"])

    def leave_game(self, then=None):
        g = self.game
        if g and not g.demo:
            if g.run["time"] > 3:
                g.commit_run()
            self.record_score(g)
        self.prog.commit()
        self.game = None
        self.audio.set_context("menu")
        self.rebuild_demo()

        def f():
            self.mode = "menu"
            if then:
                then()
        self.go(f)

    def record_score(self, g):
        if getattr(g, "saved", False) or g.mode not in ("classic", "timeattack", "survival") or g.score <= 0:
            return
        g.saved = True
        sc = self.prog.d["scores"]
        best = max([s.get("score", 0) for s in sc] or [0])
        g.new_best = g.score > best
        sc.append(dict(score=g.score, level=g.level, map=MAPS[g.map_idx][0], diff=DIFFS[g.diff], mode=g.mode,
                       date=time.strftime("%Y-%m-%d")))
        self.prog.d["scores"] = sorted(sc, key=lambda d: -d["score"])[:10]

    def on_game_end(self, g):
        g.reported = True
        self.ovl_sel = 0
        o, P = g.outcome, self.prog
        if o.get("cleared"):
            if g.mode == "adventure":
                adv = P.d["adventure"]
                key = str(g.stage)
                adv["stars"][key] = max(adv["stars"].get(key, 0), g.result["stars"])
                adv["stage"] = max(adv["stage"], min(ADV_STAGES, g.stage + 1))
                P.event("adv_stage", len(adv["stars"]), "max")
                a = adventure_stage(g.stage)
                P.unlock_world(a["world"])
                P.unlock_map(a["map"])
            elif g.mode == "daily":
                P.daily_challenge()["done"] = True
                P.event("daily_done", 1)
            elif g.mode == "challenge":
                P.event("challenge_done_" + g.cfg["challenge"]["id"], 1)
        if g.state == "win":
            P.event("games_won", 1)
        if g.state in ("over", "win"):
            self.record_score(g)
        P.commit()

    def ovl_labels(self, g):
        if g.state == "clear":
            return ["NEXT LEVEL", "REPLAY", "MAIN MENU"]
        return ["REPLAY" if g.state == "win" else "RETRY", "SHOP", "MAIN MENU"]

    def ovl_act(self, label):
        g = self.game
        if label == "NEXT LEVEL":
            if g.mode == "adventure":
                self.start_game("adventure", stage=g.stage + 1)
            else:
                g.reported = False
                self.prog.recent.clear()
                self.go(g.advance)
        elif label in ("RETRY", "REPLAY"):
            mode, kw = self.last_start
            self.leave_game_silent()
            self.start_game(mode, **kw)
        elif label == "SHOP":
            self.leave_game(lambda: self.open_screen("shop"))
        else:
            self.leave_game()

    def leave_game_silent(self):
        g = self.game
        if g and not g.demo:
            if g.run["time"] > 3:
                g.commit_run()
            self.record_score(g)
        self.prog.commit()

    # -- input -------------------------------------------------------------------- #
    def handle(self, e):
        K = pygame
        if e.type == K.QUIT:
            self.quit()
        if self.mode == "intro":
            if e.type in (K.KEYDOWN, K.MOUSEBUTTONDOWN):
                self.end_intro()
            return
        if self.trans:
            return
        if self.modal:
            if e.type in (K.KEYDOWN, K.MOUSEBUTTONDOWN):
                self.modal = None
                self.audio.play("click")
            return
        if e.type == K.MOUSEWHEEL:
            if self.mode == "screen":
                self.move_sel(-e.y * 2)
            elif self.mode == "game":
                self.zoom = max(0.55, min(1.6, self.zoom - e.y * 0.06))
        elif e.type == K.MOUSEMOTION:
            self.on_motion(e)
        elif e.type == K.MOUSEBUTTONDOWN and e.button == 1:
            self.on_click(e.pos)
        elif e.type == K.MOUSEBUTTONUP and e.button == 1:
            self.dragging = False
        elif e.type == K.KEYDOWN:
            self.on_key(e.key)

    def on_motion(self, e):
        if self.dragging and self.mode == "game":
            self.user_yaw -= e.rel[0] * 0.008
            self.user_pitch = max(0.3, min(1.5, self.user_pitch + e.rel[1] * 0.005))
            return
        for r, idx, tag in self.hits:
            if _inside(r, e.pos):
                if tag == "menu" and self.sel != idx:
                    self.sel = idx
                    self.audio.play("hover", 0.6)
                elif tag == "row" and self.lsel.get(self.scr) != idx:
                    rows = self.rows()
                    if 0 <= idx < len(rows) and not rows[idx].get("hdr"):
                        self.lsel[self.scr] = idx
                        self.audio.play("hover", 0.6)
                elif tag == "pause" and self.psel != idx:
                    self.psel = idx
                    self.audio.play("hover", 0.6)
                elif tag == "ovl" and self.ovl_sel != idx:
                    self.ovl_sel = idx
                    self.audio.play("hover", 0.6)
                return

    def on_click(self, pos):
        for r, idx, tag in self.hits:
            if not _inside(r, pos):
                continue
            if tag == "menu":
                self.sel = idx
                self.menu_activate(idx)
            elif tag == "row":
                rows = self.rows()
                if 0 <= idx < len(rows) and not rows[idx].get("hdr"):
                    self.lsel[self.scr] = idx
                    if rows[idx].get("adj") and hasattr(self, "adj_" + self.scr):
                        getattr(self, "adj_" + self.scr)(idx, rows, 1 if pos[0] > r.x + r.width // 2 else -1)
                    else:
                        self.screen_act()
            elif tag == "tab":
                self.adj_shop(0, [], idx)
            elif tag == "pause":
                self.psel = idx
                self.pause_act(idx)
            elif tag == "ovl":
                self.ovl_sel = idx
                self.ovl_act(self.ovl_labels(self.game)[idx])
            return
        if self.mode == "game" and self.game.state in ("ready", "play", "dying"):
            self.dragging = True

    def on_key(self, k):
        K = pygame
        if k == K.K_F11:
            pygame.display.toggle_fullscreen()
            return
        if k == K.K_m:
            self.S["mute"] = not self.S["mute"]
            self.ui.notify("MUTED" if self.S["mute"] else "SOUND ON", (200, 210, 230))
            return
        if k in (K.K_n, K.K_b) and self.mode != "intro":
            name = self.audio.step_track(1 if k == K.K_n else -1)
            self.ui.notify("Now playing: " + name, (170, 210, 255))
            return
        if self.mode == "menu":
            self.key_menu(k)
        elif self.mode == "screen":
            self.key_screen(k)
        elif self.mode == "pause":
            self.key_pause(k)
        elif self.mode == "game":
            self.key_game(k)

    def key_menu(self, k):
        K = pygame
        n = len(MENU_ITEMS)
        if k in (K.K_UP, K.K_w):
            self.sel = (self.sel - 1) % n
            self.audio.play("hover", 0.6)
        elif k in (K.K_DOWN, K.K_s):
            self.sel = (self.sel + 1) % n
            self.audio.play("hover", 0.6)
        elif k in (K.K_RETURN, K.K_SPACE, K.K_KP_ENTER):
            self.menu_activate(self.sel)

    def menu_activate(self, i):
        item = MENU_ITEMS[i]
        self.audio.play("click")
        if item == "QUIT":
            self.quit()
        elif item == "CLASSIC":
            self.start_game("classic")
        else:
            self.open_screen(SCREEN_OF[item])

    def step_sel(self, rows, sel, d):
        n = len(rows)
        if not n:
            return 0
        i = sel
        for _ in range(n):
            i = (i + d) % n if abs(d) == 1 else max(0, min(n - 1, i + d))
            if not rows[i].get("hdr"):
                return i
            if abs(d) != 1:
                d = 1 if d > 0 else -1
        return sel

    def move_sel(self, d):
        rows = self.rows()
        if rows:
            old = self.lsel.get(self.scr, 0)
            self.lsel[self.scr] = self.step_sel(rows, old, d)
            if self.lsel[self.scr] != old:
                self.audio.play("hover", 0.6)

    def key_screen(self, k):
        K = pygame
        if k in (K.K_ESCAPE, K.K_BACKSPACE):
            self.audio.play("click")
            self.close_screen()
        elif k in (K.K_UP, K.K_w):
            self.move_sel(-1)
        elif k in (K.K_DOWN, K.K_s):
            self.move_sel(1)
        elif k == K.K_PAGEUP:
            self.move_sel(-6)
        elif k == K.K_PAGEDOWN:
            self.move_sel(6)
        elif k in (K.K_LEFT, K.K_a, K.K_RIGHT, K.K_d):
            adj = getattr(self, "adj_" + self.scr, None)
            if adj:
                rows = self.rows()
                adj(self.lsel.get(self.scr, 0), rows, -1 if k in (K.K_LEFT, K.K_a) else 1)
        elif k == K.K_t and self.scr == "shop":
            self.toggle_booster()
        elif k in (K.K_RETURN, K.K_SPACE, K.K_KP_ENTER):
            self.screen_act()

    def screen_act(self):
        rows = self.rows()
        i = self.lsel.get(self.scr, 0)
        fn = getattr(self, "act_" + self.scr, None)
        if fn and 0 <= i < len(rows) and not rows[i].get("hdr"):
            fn(i, rows)

    def key_pause(self, k):
        K = pygame
        if k in (K.K_UP, K.K_w):
            self.psel = (self.psel - 1) % 4
            self.audio.play("hover", 0.6)
        elif k in (K.K_DOWN, K.K_s):
            self.psel = (self.psel + 1) % 4
            self.audio.play("hover", 0.6)
        elif k in (K.K_ESCAPE, K.K_p):
            self.mode = "game"
        elif k in (K.K_RETURN, K.K_SPACE, K.K_KP_ENTER):
            self.pause_act(self.psel)

    def pause_act(self, i):
        self.audio.play("click")
        if i == 0:
            self.mode = "game"
        elif i == 1:
            mode, kw = self.last_start
            self.leave_game_silent()
            self.start_game(mode, **kw)
        elif i == 2:
            self.open_screen("settings", "pause")
        else:
            self.leave_game()

    def key_game(self, k):
        K = pygame
        g = self.game
        if k == K.K_v:
            self.cam_mode = (self.cam_mode + 1) % 3
            g.toast(("OVERVIEW CAMERA", "CHASE CAMERA", "TOP-DOWN CAMERA")[self.cam_mode], (200, 230, 255))
            return
        if g.state in ("ready", "play", "dying") and k in (K.K_ESCAPE, K.K_p):
            self.mode, self.psel = "pause", 0
            return
        if g.state in ("ready", "play"):
            self.steer(k)
        elif g.state in ("clear", "win", "over"):
            labels = self.ovl_labels(g)
            if k in (K.K_LEFT, K.K_a, K.K_UP, K.K_w):
                self.ovl_sel = (self.ovl_sel - 1) % len(labels)
            elif k in (K.K_RIGHT, K.K_d, K.K_DOWN, K.K_s):
                self.ovl_sel = (self.ovl_sel + 1) % len(labels)
            elif k in (K.K_RETURN, K.K_SPACE, K.K_KP_ENTER):
                self.ovl_act(labels[self.ovl_sel])
            elif k == K.K_ESCAPE:
                self.leave_game()

    def steer(self, key):
        g = self.game
        K = pygame
        left, right = key in (K.K_LEFT, K.K_a), key in (K.K_RIGHT, K.K_d)
        up, down = key in (K.K_UP, K.K_w), key in (K.K_DOWN, K.K_s)
        if self.cam_mode == 1:
            cur = g.snake.dirq[-1] if g.snake.dirq else g.snake.dir
            if left:
                g.turn((cur[1], -cur[0]))
            elif right:
                g.turn((-cur[1], cur[0]))
            return
        fx, fz = -math.sin(self.cam.yaw), -math.cos(self.cam.yaw)
        f = ((1 if fx > 0 else -1), 0) if abs(fx) > abs(fz) else (0, (1 if fz > 0 else -1))
        r = (-f[1], f[0])
        if up:
            g.turn(f)
        elif down:
            g.turn(opp(f))
        elif right:
            g.turn(r)
        elif left:
            g.turn(opp(r))

    def quit(self):
        try:
            if self.game and not self.game.demo and self.game.run["time"] > 3:
                self.game.commit_run()
                self.record_score(self.game)
            self.prog.commit()
        finally:
            pygame.quit()
            sys.exit(0)


    # ====================================================================== #
    #  Screen rows / actions
    # ====================================================================== #
    def rows(self):
        fn = getattr(self, "rows_" + (self.scr or ""), None)
        return fn() if fn else []

    def state_text(self, item):
        inv = self.prog.inv
        st = inv.state(item)
        if st == "owned":
            return ("EQUIPPED", (130, 255, 160), st) if inv.is_equipped(item["cat"], item["id"]) else ("OWNED", (170, 200, 230), st)
        if st == "buyable":
            return (("%d c" % item["price"]), COIN_COL, st) if item["price"] > 0 else ("FREE", (130, 255, 160), st)
        return ("LOCKED", (150, 150, 165), st)

    def rows_play(self):
        adv = self.prog.d["adventure"]["stage"]
        dd = self.prog.daily_challenge()
        return [_row("Adventure", "Continue at stage %d of %d" % (adv, ADV_STAGES), icon="star"),
                _row("Classic", "10 levels - your selected map & world"),
                _row("Time Attack", "90 seconds - fruit adds time", icon="slow"),
                _row("Survival", "One life - rising chaos", icon="heart"),
                _row("Challenge", "Eight special challenges"),
                _row("Daily Challenge", "Reach %d score as %s" % (dd["target"], CHARACTERS[CHAR_IDX[dd["char"]]]["name"]),
                     "DONE" if dd["done"] else "+500c +1000xp", (130, 255, 160) if dd["done"] else COIN_COL, icon="coin")]

    def act_play(self, i, rows):
        self.audio.play("click")
        if i == 0:
            self.open_screen("adventure")
        elif i == 4:
            self.open_screen("challenge")
        elif i == 5:
            self.start_daily()
        else:
            self.start_game(("classic", "classic", "timeattack", "survival")[i])

    def rows_adventure(self):
        adv = self.prog.d["adventure"]
        out = []
        for i in range(1, ADV_STAGES + 1):
            a = adventure_stage(i)
            locked = i > adv["stage"]
            if a["boss"]:
                label, sub = "%d. BOSS - %s" % (i, a["boss"]["name"]), a["boss"]["desc"]
            else:
                label = "%d. %s" % (i, WORLDS[a["world"]]["name"])
                sub = "%s  -  %s" % (OBJ_TEXT[a["obj"][0]].format(n=a["obj"][1]), MAPS[a["map"]][0])
            out.append(_row(label, sub, state="locked" if locked else "", icon="lock" if locked else ("heart" if a["boss"] else None),
                            stars=None if locked else adv["stars"].get(str(i), 0), data=i))
        return out

    def act_adventure(self, i, rows):
        stage = rows[i]["data"]
        if stage > self.prog.d["adventure"]["stage"]:
            self.audio.play("deny")
            self.ui.notify("Clear stage %d first" % (stage - 1), (255, 180, 100))
            return
        self.start_game("adventure", stage=stage)

    def rows_challenge(self):
        return [_row(c["name"], c["desc"], "+%dc +%dxp" % (c["coins"], c["xp"]), COIN_COL,
                     icon="check" if self.prog.stat("challenge_done_" + c["id"]) else None, data=c) for c in CHALLENGES]

    def act_challenge(self, i, rows):
        c = rows[i]["data"]
        self.start_game("challenge", challenge=c, lives=c["lives"], speed=c["speed"], roamers=c["roamers"], dark=c["dark"])

    def rows_worlds(self):
        out = [_row("AUTO", "A new world every level", "SELECTED" if self.S["sel_world"] == "auto" else "", (130, 255, 160))]
        for w in WORLDS:
            it = ITEMS[("worlds", w["id"])]
            txt, col, st = self.state_text(it)
            if st == "owned" and self.S["sel_world"] == w["id"]:
                txt, col = "SELECTED", (130, 255, 160)
            elif st == "owned":
                txt = "OWNED"
            out.append(_row(w["name"], req_text(it["req"]) if st == "locked" else ", ".join(w["weather"]), txt, col, state=st,
                            icon="lock" if st == "locked" else None, data=it))
        return out

    def act_worlds(self, i, rows):
        if i == 0:
            self.S["sel_world"] = "auto"
            self.audio.play("click")
            return self.prog.commit()
        it = rows[i]["data"]
        st = self.prog.inv.state(it)
        if st == "buyable":
            msg = self.prog.shop.act(it)
            if msg == "Not enough coins":
                self.ui.notify(msg, (255, 120, 120))
                return
            st = "owned"
        if st == "owned":
            self.S["sel_world"] = it["id"]
            self.audio.play("click")
        else:
            self.audio.play("deny")
            self.ui.notify("Locked: " + req_text(it["req"]), (255, 180, 100))
        self.prog.commit()

    def rows_maps(self):
        out = []
        for i, m in enumerate(MAPS):
            it = ITEMS[("maps", slug(m[0]))]
            txt, col, st = self.state_text(it)
            if st == "owned":
                txt, col = ("SELECTED", (130, 255, 160)) if self.S["sel_map"] == it["id"] else ("OWNED", (170, 200, 230))
            out.append(_row(m[0], req_text(it["req"]) if st == "locked" else m[1], txt, col, state=st,
                            icon="lock" if st == "locked" else None, data=(i, it)))
        return out

    def act_maps(self, i, rows):
        idx, it = rows[i]["data"]
        st = self.prog.inv.state(it)
        if st == "owned":
            self.S["sel_map"] = it["id"]
            self.audio.play("click")
            self.rebuild_demo()
            self.prog.commit()
        else:
            self.audio.play("deny")
            self.ui.notify("Locked: " + req_text(it["req"]), (255, 180, 100))

    def rows_characters(self):
        out = []
        for c in CHARACTERS:
            it = ITEMS[("characters", c["id"])]
            txt, col, st = self.state_text(it)
            out.append(_row(c["name"], c["perk"] if st != "locked" else req_text(it["req"]), txt, col, state=st,
                            icon="lock" if st == "locked" else None, data=it))
        return out

    def act_characters(self, i, rows):
        self.shop_act(rows[i]["data"])

    def shop_act(self, it):
        if it["cat"] == "music":
            return self.music_pick(it)
        msg = self.prog.shop.act(it)
        if msg:
            self.ui.notify(msg, (255, 120, 120) if "enough" in msg or "Locked" in msg else (170, 255, 190))
        if it["cat"] == "themes":
            self.ui.set_theme(self.eq("theme"))
        if it["cat"] in EQUIP_SLOT:
            self.rebuild_demo()

    def rows_shop(self):
        tab = SHOP_TABS[self.shop_tab]
        out = []
        for it in self.prog.shop.items(tab):
            if tab == "boosters":
                n = self.prog.inv.booster_count(it["id"])
                armed = it["id"] in self.prog.d["armed"]
                out.append(_row(it["name"], it["desc"], ("x%d%s" % (n, " ARMED" if armed else "") if n else "%d c" % it["price"]),
                                (130, 255, 160) if armed else COIN_COL, data=it, icon="coin"))
                continue
            txt, col, st = self.state_text(it)
            out.append(_row(it["name"], req_text(it["req"]) if st == "locked" else it["desc"], txt, col, state=st,
                            icon="lock" if st == "locked" else ("note" if tab == "music" else None), data=it))
        return out

    def act_shop(self, i, rows):
        self.shop_act(rows[i]["data"])

    def adj_shop(self, i, rows, d):
        self.shop_tab = (self.shop_tab + d) % len(SHOP_TABS)
        self.lsel["shop"] = 0
        self.audio.play("hover")

    def toggle_booster(self):
        rows = self.rows()
        i = self.lsel.get("shop", 0)
        if SHOP_TABS[self.shop_tab] == "boosters" and 0 <= i < len(rows):
            self.prog.inv.toggle_armed(rows[i]["data"]["id"])
            self.audio.play("click")
            self.prog.commit()

    def rows_missions(self):
        M = self.prog.missions
        out = []
        for mid in M.listing():
            m = ALL_MISSIONS[mid]
            p, done, cl = M.progress(mid), M.done(mid), M.claimed(mid)
            right = "DONE" if cl else "CLAIM" if done else "%d / %d" % (p, m["target"])
            out.append(_row(m["name"], "%s  -  +%d XP  +%d coins" % (m["cat"].title(), m["xp"], m["coins"]), right,
                            (130, 255, 160) if (done or cl) else (210, 220, 235), bar=p / m["target"],
                            state="claim" if done and not cl else "done" if cl else "", data=mid))
        return out

    def act_missions(self, i, rows):
        if not self.prog.missions.claim(rows[i]["data"]):
            self.audio.play("deny")
        else:
            self.audio.play("coin")

    def rows_achievements(self):
        A = self.prog.ach
        order = sorted(ACHIEVEMENTS, key=lambda a: (not A.unlocked(a["id"]), ACHIEVEMENTS.index(a)))
        return [_row(a["name"], a["desc"], "UNLOCKED" if A.unlocked(a["id"]) else "%d / %d" % (A.progress(a), a["target"]),
                     (255, 210, 90) if A.unlocked(a["id"]) else (190, 200, 215), bar=A.progress(a) / a["target"],
                     icon="star" if A.unlocked(a["id"]) else "lock", data=a) for a in order]

    # -- music ---------------------------------------------------------------- #
    MODE_NAMES = {"auto": "Auto", "track": "Selected", "shuffle": "Shuffle", "off": "Off"}

    def rows_music(self):
        S = self.S
        out = [_row("Music Mode", "Auto follows the world, menu and boss fights", self.MODE_NAMES[S["music_mode"]], adj=True, data=("mode",)),
               _row("Music Volume", "", "%d%%" % int(S["music_vol"] * 100), adj=True, data=("mvol",)),
               _row("SFX Volume", "", "%d%%" % int(S["sfx_vol"] * 100), adj=True, data=("svol",)),
               _row("Mute All", "", "ON" if S["mute"] else "OFF", adj=True, data=("mute",))]
        playing = self.audio.music.want
        for style in TRACK_STYLES:
            out.append(_row(style.upper(), hdr=True))
            for i, t in enumerate(TRACKS):
                if t["style"] != style:
                    continue
                it = ITEMS[("music", t["id"])]
                txt, col, st = self.state_text(it)
                if st == "owned":
                    txt, col = ("PLAYING", (130, 255, 160)) if playing == i else ("OWNED", (170, 200, 230))
                out.append(_row(t["name"], "%d BPM" % t["bpm"] if st != "locked" else req_text(it["req"]), txt, col, state=st,
                                icon="note", data=("track", i, it)))
        return out

    def adj_music(self, i, rows, d):
        data = rows[i].get("data")
        S = self.S
        if not data:
            return
        if data[0] == "mode":
            modes = ["auto", "track", "shuffle", "off"]
            S["music_mode"] = modes[(modes.index(S["music_mode"]) + d) % 4]
            self.audio.refresh()
        elif data[0] in ("mvol", "svol"):
            k = "music_vol" if data[0] == "mvol" else "sfx_vol"
            S[k] = round(max(0.0, min(1.0, S[k] + 0.1 * d)), 1)
            self.audio.play("click")
        elif data[0] == "mute":
            S["mute"] = not S["mute"]
        else:
            return
        self.prog.commit()

    def act_music(self, i, rows):
        data = rows[i].get("data")
        if data and data[0] == "track":
            self.music_pick(data[2])
        else:
            self.adj_music(i, rows, 1)

    def music_pick(self, it):
        st = self.prog.inv.state(it)
        if st == "buyable":
            msg = self.prog.shop.act(it)
            if msg == "Not enough coins":
                self.ui.notify(msg, (255, 120, 120))
                return
            st = "owned"
        if st == "owned":
            self.S["music_mode"], self.S["music_track"] = "track", it["id"]
            self.audio.refresh()
            self.audio.play("click")
            self.prog.commit()
        else:
            self.audio.play("deny")
            self.ui.notify("Locked: " + req_text(it["req"]), (255, 180, 100))

    # -- settings ------------------------------------------------------------- #
    def rows_settings(self):
        out = []
        for spec in SET_ROWS:
            if spec[0] == "hdr":
                out.append(_row(spec[1], hdr=True))
                continue
            key, label, kind = spec
            if kind == "info":
                out.append(_row(label, "", "view", data=key))
                continue
            v = self.S[key]
            txt = ("ON" if v else "OFF") if kind == "bool" else "%d%%" % int(v * 100) if kind in ("vol", "scale") else kind[int(v)]
            out.append(_row(label, "", txt, adj=True, data=key))
        return out

    def adj_settings(self, i, rows, d):
        spec = SET_ROWS[i]
        if spec[0] == "hdr" or spec[2] == "info":
            return
        key, _, kind = spec
        S = self.S
        if kind == "bool":
            S[key] = not S[key]
        elif kind == "vol":
            S[key] = round(max(0.0, min(1.0, S[key] + 0.1 * d)), 1)
        elif kind == "scale":
            vals = [0.85, 1.0, 1.15, 1.3]
            cur = min(range(4), key=lambda k: abs(vals[k] - S[key]))
            S[key] = vals[(cur + d) % 4]
        else:
            S[key] = (int(S[key]) + d) % len(kind)
        self.audio.play("click")
        self.apply_settings()
        if key in ("particles", "quality") and self.game:
            self.game.particles.enabled = bool(S["particles"])
        self.prog.commit()

    def act_settings(self, i, rows):
        self.adj_settings(i, rows, 1)

    # ====================================================================== #
    #  Drawing helpers
    # ====================================================================== #
    def clip(self, s, size, width):
        f = self.ui.font(size)
        if f.size(s)[0] <= width:
            return s
        while len(s) > 3 and f.size(s + "...")[0] > width:
            s = s[:-1]
        return s + "..."

    def para(self, surf, text, size, color, x, y, w, gap=4):
        for ln in self.ui.wrap(text, size, w):
            self.ui.text(surf, ln, size, color, (x, y), "topleft", False)
            y += self.ui.font(size).size(ln)[1] + gap
        return y

    def draw_chips(self, surf):
        W = surf.get_width()
        P, ui = self.prog, self.ui
        ui.icon(surf, "coin", W - 30, 34, 13)
        ui.text(surf, "{:,}".format(P.player.coins), 34, COIN_COL, (W - 52, 34), "midright")
        r = pygame.Rect(W - 250, 62, 214, 10)
        ui.bar(surf, r, P.player.xp / max(1, P.player.xp_needed()), XP_COL, border=False)
        ui.text(surf, "LV %d" % P.player.level, 22, WHITE, (W - 262, 67), "midright")

    def draw_rows(self, surf, rect, rows, sel, rowh=52):
        ui = self.ui
        n = len(rows)
        vis = max(1, rect.height // rowh)
        sc = self.lscroll.get(self.scr, 0) if hasattr(self, "lscroll") else 0
        sc = max(0, min(sc, max(0, n - vis)))
        if sel < sc:
            sc = sel
        elif sel >= sc + vis:
            sc = sel - vis + 1
        if not hasattr(self, "lscroll"):
            self.lscroll = {}
        self.lscroll[self.scr] = sc
        t = time.time()
        for k in range(vis):
            i = sc + k
            if i >= n:
                break
            r = rows[i]
            rr = pygame.Rect(rect.x, rect.y + k * rowh, rect.width - 14, rowh - 4)
            if r.get("hdr"):
                ui.text(surf, r["label"], 24, ui.acc, (rr.x + 10, rr.centery + 6), "midleft", False)
                continue
            on = i == sel
            if on:
                s = pygame.Surface(rr.size, pygame.SRCALPHA)
                a = 60 + int(20 * math.sin(t * 6))
                pygame.draw.rect(s, (*ui.acc, a), s.get_rect(), border_radius=10)
                pygame.draw.rect(s, (*ui.acc, 230), s.get_rect(), 2, border_radius=10)
                surf.blit(s, rr.topleft)
            x = rr.x + 14
            if r.get("icon"):
                ui.icon(surf, r["icon"], rr.x + 28, rr.centery, 14, ui.acc)
                x = rr.x + 54
            locked = r.get("state") == "locked"
            ui.text(surf, self.clip(r["label"], 30, rr.width * 0.5), 30, (140, 145, 160) if locked else WHITE,
                    (x, rr.y + (14 if r.get("sub") else rr.height // 2)), "midleft")
            if r.get("sub"):
                ui.text(surf, self.clip(r["sub"], 21, rr.width - (x - rr.x) - 150), 21, (165, 178, 198), (x, rr.y + 36), "midleft", False)
            if r.get("stars") is not None:
                ui.stars(surf, rr.right - 52, rr.centery, r["stars"], 10)
            elif r.get("right"):
                ui.text(surf, r["right"], 26, r.get("rc", WHITE), (rr.right - 12, rr.centery - (5 if r.get("bar") is not None else 0)), "midright")
            if r.get("bar") is not None:
                ui.bar(surf, pygame.Rect(rr.right - 160, rr.bottom - 14, 148, 7), r["bar"], (110, 235, 140), border=False)
            if r.get("adj") and on:
                ui.text(surf, "<", 30, ui.acc, (rr.right - 190, rr.centery), "midright", False)
            self.hits.append((rr, i, "row"))
        if n > vis:
            h = rect.height
            bh = max(24, int(h * vis / n))
            by = rect.y + int((h - bh) * sc / max(1, n - vis))
            pygame.draw.rect(surf, (*ui.acc,), (rect.right - 8, by, 5, bh), border_radius=3)

    def draw_screen(self, surf):
        W, H = surf.get_size()
        ui, scr = self.ui, self.scr
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 110))
        surf.blit(dim, (0, 0))
        ui.text(surf, SCREEN_TITLES[scr], 54, ui.acc, (36, 28), "topleft")
        self.draw_chips(surf)
        if scr == "scores":
            return self.draw_scores(surf)
        if scr == "profile":
            return self.draw_profile(surf)
        rows = self.rows()
        sel = max(0, min(self.lsel.get(scr, 0), len(rows) - 1))
        if rows and rows[sel].get("hdr"):
            sel = self.step_sel(rows, sel, 1)
        self.lsel[scr] = sel
        left = pygame.Rect(30, 100, int(W * 0.47), H - 156)
        right = pygame.Rect(left.right + 14, 100, W - left.right - 44, left.height)
        ui.panel(surf, left)
        ui.panel(surf, right)
        top = left.y + 8
        if scr == "shop":
            r = pygame.Rect(left.x + 8, top, left.width - 16, 38)
            ui.text(surf, "<   %s   >" % TAB_NAMES[SHOP_TABS[self.shop_tab]], 32, ui.acc, r.center)
            self.hits.append((pygame.Rect(r.x, r.y, r.width // 2, r.height), -1, "tab"))
            self.hits.append((pygame.Rect(r.x + r.width // 2, r.y, r.width // 2, r.height), 1, "tab"))
            top += 42
        self.draw_rows(surf, pygame.Rect(left.x + 8, top, left.width - 16, left.bottom - top - 8), rows, sel)
        det = getattr(self, "det_" + scr, None)
        if det and rows:
            det(surf, right, rows, sel)
        hint = "Up/Down select   Enter confirm   Esc back"
        if scr in ("shop",):
            hint = "Left/Right category   Enter buy / equip   T arm booster   Esc back"
        elif scr in ("settings", "music"):
            hint = "Up/Down select   Left/Right change   Enter select   N/B tracks   Esc back"
        ui.text(surf, hint, 20, (200, 215, 230), (W // 2, H - 14), "midbottom")

    # -- detail panels ------------------------------------------------------- #
    def det_head(self, surf, rect, title, sub=None):
        self.ui.text(surf, title, 40, WHITE, (rect.x + 20, rect.y + 20), "topleft")
        y = rect.y + 62
        if sub:
            self.ui.text(surf, sub, 24, self.ui.acc, (rect.x + 20, y), "topleft", False)
            y += 30
        return y

    def det_play(self, surf, rect, rows, sel):
        key = ("adventure", "classic", "timeattack", "survival", "challenge", "daily")[sel]
        y = self.det_head(surf, rect, rows[sel]["label"].upper())
        self.para(surf, MODE_INFO[key], 26, (215, 225, 240), rect.x + 20, y + 10, rect.width - 40)
        if key == "daily":
            dd = self.prog.daily_challenge()
            self.para(surf, "Today: reach %d points as %s on %s (%s)." % (dd["target"], CHARACTERS[CHAR_IDX[dd["char"]]]["name"],
                                                                         MAPS[dd["map"]][0], WORLDS[dd["world"]]["name"]),
                      24, COIN_COL, rect.x + 20, y + 130, rect.width - 40)

    def det_adventure(self, surf, rect, rows, sel):
        a = adventure_stage(rows[sel]["data"])
        y = self.det_head(surf, rect, "STAGE %d" % a["stage"], WORLDS[a["world"]]["name"] + "  -  " + MAPS[a["map"]][0])
        txt = a["boss"]["desc"] if a["boss"] else OBJ_TEXT[a["obj"][0]].format(n=a["obj"][1])
        y = self.para(surf, ("BOSS: " + a["boss"]["name"] + ".  ") + txt if a["boss"] else "Objective: " + txt, 26, (215, 225, 240), rect.x + 20, y + 10, rect.width - 40)
        self.para(surf, "Clearing this stage unlocks its world and map for every mode.", 22, (170, 185, 205), rect.x + 20, y + 14, rect.width - 40)

    def det_challenge(self, surf, rect, rows, sel):
        c = rows[sel]["data"]
        y = self.det_head(surf, rect, c["name"].upper(), "%s - %s" % (MAPS[c["map"]][0], WORLDS[c["world"]]["name"]))
        y = self.para(surf, c["desc"], 26, (215, 225, 240), rect.x + 20, y + 10, rect.width - 40)
        self.para(surf, "Objective: " + OBJ_TEXT[c["obj"][0]].format(n=c["obj"][1]) + "   Lives: %d" % c["lives"], 24, (190, 205, 225), rect.x + 20, y + 10, rect.width - 40)

    def det_worlds(self, surf, rect, rows, sel):
        ui = self.ui
        if sel == 0:
            y = self.det_head(surf, rect, "AUTO WORLD")
            self.para(surf, "Each level uses the next world you own. Pick a world to stay in it.", 26, (215, 225, 240), rect.x + 20, y + 10, rect.width - 40)
            return
        w = WORLDS[sel - 1]
        sw = pygame.Rect(rect.x + 20, rect.y + 20, rect.width - 40, 120)
        top, bot = w["sky"]
        for yy in range(0, sw.height, 4):
            pygame.draw.rect(surf, mix(top, bot, yy / sw.height), (sw.x, sw.y + yy, sw.width, 4))
        pygame.draw.circle(surf, w["body"][1], (sw.x + int(sw.width * w["body"][2][0]), sw.y + 34), 18)
        pygame.draw.rect(surf, w["ground"], (sw.x, sw.y + 86, sw.width, 34))
        pygame.draw.rect(surf, w["fa"], (sw.x + sw.width // 2 - 40, sw.y + 78, 80, 16))
        for k in range(4):
            pygame.draw.rect(surf, w["wall"], (sw.x + 30 + k * 40, sw.y + 70, 20, 22))
        ui.text(surf, w["name"].upper(), 40, WHITE, (rect.x + 20, sw.bottom + 14), "topleft")
        it = ITEMS[("worlds", w["id"])]
        y = sw.bottom + 58
        for ln in ("Weather: " + ", ".join(w["weather"]), "Obstacle: " + w["obst"][0], "Event: " + EVENTS[w["event"]][0].title().replace("!", ""),
                   "Music: " + TRACKS[TRACK_IDX[w["music"]]]["name"]):
            ui.text(surf, ln, 24, (205, 218, 235), (rect.x + 20, y), "topleft", False)
            y += 28
        st = self.prog.inv.state(it)
        msg = "Owned - Enter to select" if st == "owned" else ("Enter to buy for %d coins" % it["price"] if st == "buyable" and it["price"] else "Locked: " + req_text(it["req"]))
        ui.text(surf, msg, 24, COIN_COL if st == "buyable" else (200, 205, 220), (rect.x + 20, y + 10), "topleft", False)

    def det_maps(self, surf, rect, rows, sel):
        idx, it = rows[sel]["data"]
        ui = self.ui
        cell = 10
        gx, gy = rect.x + 20, rect.y + 20
        walls = self.map_walls(idx)
        pygame.draw.rect(surf, (20, 28, 44), (gx - 4, gy - 4, N * cell + 8, N * cell + 8), border_radius=6)
        for x in range(N):
            for y in range(N):
                c = (150, 160, 190) if (x, y) in walls else (46, 70, 70) if (x + y) % 2 else (40, 62, 62)
                pygame.draw.rect(surf, c, (gx + x * cell, gy + y * cell, cell - 1, cell - 1))
        sx, sy, _ = MAPS[idx][4]
        pygame.draw.rect(surf, (120, 255, 160), (gx + sx * cell, gy + sy * cell, cell - 1, cell - 1))
        x2 = gx + N * cell + 24
        ui.text(surf, MAPS[idx][0].upper(), 36, WHITE, (x2, gy), "topleft")
        y = self.para(surf, MAPS[idx][1], 24, (210, 222, 238), x2, gy + 40, rect.right - x2 - 16)
        ui.text(surf, "Edges wrap around" if MAPS[idx][2] else "Walled edges", 22, (170, 200, 230), (x2, y + 6), "topleft", False)
        st = self.prog.inv.state(it)
        if st == "locked":
            ui.text(surf, "Locked: " + req_text(it["req"]), 22, (255, 180, 100), (x2, y + 34), "topleft", False)
        ui.text(surf, "Green = spawn point", 20, (140, 255, 170), (gx, gy + N * cell + 14), "topleft", False)

    def det_characters(self, surf, rect, rows, sel):
        c, ui = CHARACTERS[sel], self.ui
        it = rows[sel]["data"]
        look = make_look(c)
        ui.snake_icon(surf, look, c["hat"], pygame.Rect(rect.x + 10, rect.y + 20, rect.width - 20, 150), time.time())
        ui.text(surf, c["name"].upper(), 40, WHITE, (rect.x + 20, rect.y + 186), "topleft")
        y = self.para(surf, "Ability: " + c["perk"], 26, (215, 225, 240), rect.x + 20, rect.y + 232, rect.width - 40)
        txt, col, st = self.state_text(it)
        if st == "locked":
            ui.text(surf, "Locked: " + req_text(it["req"]), 24, (255, 180, 100), (rect.x + 20, y + 10), "topleft", False)
        elif st == "buyable":
            ui.text(surf, "Price: %d coins   (Enter to buy)" % it["price"], 24, COIN_COL, (rect.x + 20, y + 10), "topleft", False)
        else:
            ui.text(surf, "Enter to equip" if txt != "EQUIPPED" else "Currently equipped", 24, (130, 255, 160), (rect.x + 20, y + 10), "topleft", False)

    def shop_preview(self, surf, rect, it):
        ui, cat = self.ui, it["cat"]
        eqc = CHARACTERS[CHAR_IDX.get(self.eq("character"), 0)]
        t = time.time()
        if cat == "characters":
            c = CHARACTERS[CHAR_IDX[it["id"]]]
            ui.snake_icon(surf, make_look(c), c["hat"], rect, t)
        elif cat == "skins":
            ui.snake_icon(surf, make_look(eqc, it["id"]), eqc["hat"], rect, t)
        elif cat == "heads":
            ui.snake_icon(surf, make_look(eqc, self.eq("skin")), "none", rect, t)
        elif cat == "hats":
            hat = eqc["hat"] if it["id"] == "default" else it["id"]
            ui.snake_icon(surf, make_look(eqc, self.eq("skin")), hat, rect, t)
        elif cat in ("trails", "effects"):
            col = {"fire": (255, 140, 40), "neon": (0, 255, 230), "spark": (255, 240, 120), "smoke": (150, 150, 160), "galaxy": (150, 110, 255),
                   "lightning": (190, 220, 255), "confetti": (255, 120, 200), "sparkle": (255, 245, 180), "pixel": (120, 220, 255),
                   "stars": (255, 235, 120)}.get(it["id"], (200, 210, 225))
            for k in range(14):
                a = t * 2 + k * 0.9
                pygame.draw.circle(surf, shade(col, 0.6 + 0.4 * math.sin(a)), (int(rect.centerx - 80 + k * 12), int(rect.centery + math.sin(a) * 26)), 6)
        elif cat == "themes":
            d = THEME_DEFS[it["id"]]
            pygame.draw.rect(surf, d[3], rect, border_radius=12)
            pygame.draw.rect(surf, d[2], rect, 3, border_radius=12)
            ui.text(surf, "ABC", 48, d[2], rect.center)
        elif cat == "backgrounds":
            wid = BG_DEFS[it["id"]][2]
            sky = WORLDS[WORLD_IDX[wid]]["sky"] if wid else ((40, 60, 120), (160, 210, 230))
            for yy in range(0, rect.height, 4):
                pygame.draw.rect(surf, mix(sky[0], sky[1], yy / rect.height), (rect.x, rect.y + yy, rect.width, 4))
        elif cat == "music":
            ui.icon(surf, "note", rect.centerx, rect.centery, 34, ui.acc)
        else:
            ui.icon(surf, "coin", rect.centerx, rect.centery, 34)

    def det_shop(self, surf, rect, rows, sel):
        it, ui = rows[sel]["data"], self.ui
        self.shop_preview(surf, pygame.Rect(rect.x + 20, rect.y + 20, rect.width - 40, 140), it)
        ui.text(surf, it["name"].upper(), 36, WHITE, (rect.x + 20, rect.y + 176), "topleft")
        ui.text(surf, it["rarity"].upper(), 22, RARITY_COL[it["rarity"]], (rect.x + 20, rect.y + 214), "topleft", False)
        y = self.para(surf, it["desc"], 24, (210, 222, 238), rect.x + 20, rect.y + 244, rect.width - 40)
        if it["cat"] == "boosters":
            n = self.prog.inv.booster_count(it["id"])
            ui.text(surf, "Price: %d coins   Owned: %d" % (it["price"], n), 24, COIN_COL, (rect.x + 20, y + 10), "topleft", False)
            return
        txt, col, st = self.state_text(it)
        if st == "buyable" and it["price"]:
            ui.text(surf, "Price: %d coins   (Enter to buy)" % it["price"], 24, COIN_COL, (rect.x + 20, y + 10), "topleft", False)
            if self.prog.player.coins < it["price"]:
                ui.text(surf, "Not enough coins", 22, (255, 120, 120), (rect.x + 20, y + 40), "topleft", False)
        elif st == "locked":
            ui.text(surf, "Locked: " + req_text(it["req"]), 24, (255, 180, 100), (rect.x + 20, y + 10), "topleft", False)
        else:
            ui.text(surf, "Currently equipped" if txt == "EQUIPPED" else "Enter to equip", 24, (130, 255, 160), (rect.x + 20, y + 10), "topleft", False)

    def det_missions(self, surf, rect, rows, sel):
        mid = rows[sel]["data"]
        m, M, ui = ALL_MISSIONS[mid], self.prog.missions, self.ui
        y = self.det_head(surf, rect, m["cat"].upper() + " MISSION")
        y = self.para(surf, m["name"], 32, WHITE, rect.x + 20, y + 4, rect.width - 40)
        ui.bar(surf, pygame.Rect(rect.x + 20, y + 14, rect.width - 40, 18), M.progress(mid) / m["target"], (110, 235, 140))
        ui.text(surf, "%d / %d" % (M.progress(mid), m["target"]), 24, WHITE, (rect.x + 20, y + 44), "topleft", False)
        ui.text(surf, "Reward: +%d XP   +%d coins" % (m["xp"], m["coins"]), 26, COIN_COL, (rect.x + 20, y + 80), "topleft", False)
        msg = "Claimed" if M.claimed(mid) else "Press Enter to CLAIM" if M.done(mid) else "Keep playing!"
        ui.text(surf, msg, 24, (130, 255, 160) if M.done(mid) else (190, 200, 215), (rect.x + 20, y + 116), "topleft", False)
        ui.text(surf, "Daily missions refresh every day, weekly every Monday.", 20, (150, 165, 185), (rect.x + 20, rect.bottom - 32), "topleft", False)

    def det_achievements(self, surf, rect, rows, sel):
        a, A, ui = rows[sel]["data"], self.prog.ach, self.ui
        y = self.det_head(surf, rect, a["name"])
        y = self.para(surf, a["desc"], 26, (215, 225, 240), rect.x + 20, y + 6, rect.width - 40)
        ui.bar(surf, pygame.Rect(rect.x + 20, y + 14, rect.width - 40, 18), A.progress(a) / a["target"], (255, 210, 90))
        ui.text(surf, "%d / %d" % (A.progress(a), a["target"]), 24, WHITE, (rect.x + 20, y + 44), "topleft", False)
        ui.text(surf, "Reward: +%d XP   +%d coins" % (a["xp"], a["coins"]), 26, COIN_COL, (rect.x + 20, y + 80), "topleft", False)
        ui.text(surf, "%d / %d unlocked" % (len(self.prog.d["achievements"]), len(ACHIEVEMENTS)), 24, ui.acc, (rect.x + 20, y + 120), "topleft", False)

    def det_music(self, surf, rect, rows, sel):
        ui = self.ui
        y = self.det_head(surf, rect, "NOW PLAYING")
        ui.icon(surf, "note", rect.x + 44, y + 38, 24, ui.acc)
        ui.text(surf, self.audio.current_name(), 36, WHITE, (rect.x + 84, y + 36), "midleft")
        owned = len(self.audio.owned_tracks())
        ui.text(surf, "%d of %d tracks unlocked" % (owned, len(TRACKS)), 24, (190, 205, 225), (rect.x + 20, y + 84), "topleft", False)
        if self.audio.music.composing():
            ui.text(surf, "Composing track...", 22, (255, 220, 120), (rect.x + 20, y + 114), "topleft", False)
        d = rows[sel].get("data")
        if d and d[0] == "track":
            t = TRACKS[d[1]]
            ui.text(surf, "%s  -  %d BPM" % (t["style"], t["bpm"]), 24, (205, 218, 235), (rect.x + 20, y + 150), "topleft", False)
        self.para(surf, "N / B skip tracks anywhere in the game. Unlock more in the shop or by playing.", 22, (160, 175, 195), rect.x + 20, rect.bottom - 80, rect.width - 40)

    def det_settings(self, surf, rect, rows, sel):
        y = self.det_head(surf, rect, "SETTINGS")
        if SET_ROWS[sel][0] == "help":
            for ln in KEY_HELP:
                self.ui.text(surf, ln, 23, (215, 225, 240), (rect.x + 20, y + 8), "topleft", False)
                y += 30
        else:
            self.para(surf, "Left / Right (or click the left / right half of a row) changes a value. Everything is saved automatically.", 24, (205, 218, 235), rect.x + 20, y + 8, rect.width - 40)

    def draw_scores(self, surf):
        W, H = surf.get_size()
        ui = self.ui
        rect = pygame.Rect(0, 0, 800, 540)
        rect.center = (W // 2, H // 2 + 20)
        ui.panel(surf, rect, 215)
        sc = self.prog.d["scores"]
        if not sc:
            ui.text(surf, "No scores yet - go set one!", 32, (220, 230, 240), rect.center)
        for i, s in enumerate(sc):
            y = rect.y + 40 + i * 46
            col = (255, 225, 120) if i == 0 else (225, 235, 245)
            ui.text(surf, "%2d." % (i + 1), 30, col, (rect.x + 30, y), "midleft", False)
            ui.text(surf, "{:,}".format(s["score"]), 32, col, (rect.x + 110, y), "midleft", False)
            ui.text(surf, "%s  Lv %d" % (s.get("mode", "classic").title(), s.get("level", 1)), 24, col, (rect.x + 300, y), "midleft", False)
            ui.text(surf, "%s / %s" % (s.get("map", ""), s.get("diff", "")), 24, col, (rect.x + 500, y), "midleft", False)
            ui.text(surf, s.get("date", ""), 22, (170, 190, 210), (rect.right - 24, y), "midright", False)
        ui.text(surf, "Esc - back", 22, (200, 215, 230), (W // 2, H - 14), "midbottom")

    def draw_profile(self, surf):
        W, H = surf.get_size()
        ui, P = self.ui, self.prog
        rect = pygame.Rect(30, 100, W - 60, H - 156)
        ui.panel(surf, rect, 215)
        ui.text(surf, "LEVEL %d" % P.player.level, 64, WHITE, (rect.x + 30, rect.y + 20), "topleft")
        br = pygame.Rect(rect.x + 30, rect.y + 90, 340, 20)
        ui.bar(surf, br, P.player.xp / max(1, P.player.xp_needed()), XP_COL)
        ui.text(surf, "XP %s / %s" % ("{:,}".format(P.player.xp), "{:,}".format(P.player.xp_needed())), 26, XP_COL, (br.x, br.bottom + 8), "topleft", False)
        ui.icon(surf, "coin", rect.x + 44, rect.y + 156, 16)
        ui.text(surf, "COINS  {:,}".format(P.player.coins), 30, COIN_COL, (rect.x + 70, rect.y + 156), "midleft")
        st = P.d["stats"]
        secs = int(st.get("play_time", 0))
        inv = P.inv
        stats = [("Total Score", "{:,}".format(st.get("total_score", 0))), ("Games Played", st.get("games", 0)),
                 ("Games Won", st.get("games_won", 0)), ("Fruits Collected", "{:,}".format(st.get("fruits", 0))),
                 ("Best Combo", "x%d" % st.get("best_combo", 0)), ("Highest Level", st.get("highest_level", 0)),
                 ("Total Play Time", "%dh %02dm" % (secs // 3600, secs % 3600 // 60)),
                 ("Unlocked Worlds", "%d / %d" % (inv.count_owned("worlds"), len(WORLDS))),
                 ("Unlocked Characters", "%d / %d" % (inv.count_owned("characters"), len(CHARACTERS))),
                 ("Unlocked Skins", "%d / %d" % (inv.count_owned("skins"), len(SKIN_DEFS) + 1)),
                 ("Achievements", "%d / %d" % (len(P.d["achievements"]), len(ACHIEVEMENTS))),
                 ("Missions Done", st.get("missions_done", 0))]
        x0, y0 = rect.x + 30, rect.y + 214
        for i, (k, v) in enumerate(stats):
            col, row = i % 2, i // 2
            x, y = x0 + col * 330, y0 + row * 40
            ui.text(surf, k, 24, (170, 185, 205), (x, y), "midleft", False)
            ui.text(surf, str(v), 28, WHITE, (x + 320, y), "midright", False)
        rx = rect.x + 720
        eq = P.d["equipped"]
        c = CHARACTERS[CHAR_IDX.get(eq["character"], 0)]
        ui.snake_icon(surf, make_look(c, eq["skin"]), c["hat"] if eq["hat"] == "default" else eq["hat"],
                      pygame.Rect(rx - 20, rect.y + 16, rect.right - rx - 10, 130), time.time())
        ui.text(surf, "EQUIPPED", 26, ui.acc, (rx, rect.y + 160), "topleft")
        names = [("Character", ITEMS[("characters", eq["character"])]["name"]), ("Skin", ITEMS[("skins", eq["skin"])]["name"]),
                 ("Head", ITEMS[("heads", eq["head"])]["name"]), ("Hat", ITEMS[("hats", eq["hat"])]["name"]),
                 ("Trail", ITEMS[("trails", eq["trail"])]["name"]), ("Effect", ITEMS[("effects", eq["effect"])]["name"]),
                 ("UI Theme", ITEMS[("themes", eq["theme"])]["name"]), ("Background", ITEMS[("backgrounds", eq["background"])]["name"])]
        for i, (k, v) in enumerate(names):
            ui.text(surf, k, 22, (170, 185, 205), (rx, rect.y + 198 + i * 30), "topleft", False)
            ui.text(surf, self.clip(v, 22, 190), 22, WHITE, (rect.right - 24, rect.y + 198 + i * 30), "topright", False)
        ui.text(surf, "Esc - back", 22, (200, 215, 230), (W // 2, H - 14), "midbottom")


    # ====================================================================== #
    #  Menu / HUD / overlays
    # ====================================================================== #
    def top_mission(self):
        M = self.prog.missions
        best, bf = None, -1.0
        for mid in M.active_ids():
            if M.claimed(mid) or M.done(mid):
                continue
            m = ALL_MISSIONS[mid]
            f = M.progress(mid) / m["target"]
            if f > bf:
                best, bf = mid, f
        return best

    def mission_lines(self, n=2):
        M = self.prog.missions
        out = []
        for mid in M.listing():
            if M.claimed(mid):
                continue
            m = ALL_MISSIONS[mid]
            if M.done(mid):
                out.append(("%s - CLAIM in Missions!" % m["name"], (130, 255, 160)))
            elif M.progress(mid) > 0:
                out.append(("%s  %d/%d" % (m["name"], M.progress(mid), m["target"]), (200, 215, 235)))
            if len(out) >= n:
                break
        return out

    def draw_intro(self, surf):
        W, H = surf.get_size()
        ui, t = self.ui, self.intro_t
        surf.fill((6, 10, 20))
        self.fx.draw(surf, t * 3)
        title = ui.title3d("SNAKE 3D", 150, ui.acc, shade(ui.acc, 0.45))
        title.set_alpha(int(255 * min(1.0, t / 0.8)))
        surf.blit(title, title.get_rect(center=(W // 2, H // 2 - 30)))
        if t > 1.4:
            a = min(1.0, (t - 1.4) / 0.8)
            ui.text(surf, "Collect. Survive. Evolve.", 40, shade((235, 245, 255), a), (W // 2, H // 2 + 70))
        ui.text(surf, "press any key", 20, (130, 145, 165), (W // 2, H - 24))

    def draw_menu(self, surf):
        W, H = surf.get_size()
        ui, P = self.ui, self.prog
        t = time.time()
        self.fx.draw(surf, t)
        title = ui.title3d("SNAKE 3D", 112, ui.acc, shade(ui.acc, 0.45))
        title.set_alpha(255)
        surf.blit(title, (30, 14 + int(math.sin(t * 1.6) * 3)))
        ui.text(surf, "Collect. Survive. Evolve.", 26, (230, 240, 250), (48, 128), "topleft")
        y0, rh = 172, 35
        claim = P.missions.claimable()
        for i, item in enumerate(MENU_ITEMS):
            y = y0 + i * rh
            on = i == self.sel
            rr = pygame.Rect(36, y - 16, 330, rh - 3)
            if on:
                s = pygame.Surface(rr.size, pygame.SRCALPHA)
                pygame.draw.rect(s, (*ui.acc, 60 + int(18 * math.sin(t * 6))), s.get_rect(), border_radius=10)
                pygame.draw.rect(s, (*ui.acc, 230), s.get_rect(), 2, border_radius=10)
                surf.blit(s, rr.topleft)
            off = 14 + int(3 * math.sin(t * 5)) if on else 0
            ui.text(surf, item, 32 if on else 29, WHITE if on else (200, 212, 228), (60 + off, y), "midleft")
            if item == "MISSIONS" and claim:
                pygame.draw.circle(surf, (255, 90, 90), (rr.right - 22, y), 11)
                ui.text(surf, str(claim), 20, WHITE, (rr.right - 22, y), shadow=False)
            self.hits.append((rr, i, "menu"))
        cx = W - 390
        r = pygame.Rect(cx, 24, 360, 150)
        ui.panel(surf, r)
        ui.text(surf, "LEVEL %d" % P.player.level, 46, WHITE, (cx + 20, 38), "topleft")
        ui.bar(surf, pygame.Rect(cx + 20, 94, 320, 16), P.player.xp / max(1, P.player.xp_needed()), XP_COL)
        ui.text(surf, "XP %s / %s" % ("{:,}".format(P.player.xp), "{:,}".format(P.player.xp_needed())), 22, XP_COL, (cx + 20, 116), "topleft", False)
        ui.icon(surf, "coin", cx + 32, 150, 13)
        ui.text(surf, "{:,}".format(P.player.coins), 32, COIN_COL, (cx + 54, 150), "midleft")
        dd = P.daily_challenge()
        r2 = pygame.Rect(cx, 190, 360, 112)
        ui.panel(surf, r2)
        ui.text(surf, "DAILY CHALLENGE", 24, ui.acc, (cx + 20, 204), "topleft", False)
        self.para(surf, "Reach %d score as %s" % (dd["target"], CHARACTERS[CHAR_IDX[dd["char"]]]["name"]), 22, (215, 225, 240), cx + 20, 232, 320)
        ui.text(surf, "COMPLETED" if dd["done"] else "+500 coins  +1000 XP", 22, (130, 255, 160) if dd["done"] else COIN_COL, (cx + 20, 280), "topleft", False)
        st = P.d["streak"]
        r3 = pygame.Rect(cx, 316, 360, 78)
        ui.panel(surf, r3)
        ui.text(surf, "LOGIN STREAK", 24, ui.acc, (cx + 20, 330), "topleft", False)
        ui.text(surf, "Day %d    Best %d" % (st["count"], st["best"]), 28, WHITE, (cx + 20, 358), "topleft", False)
        if H >= 600:
            r4 = pygame.Rect(cx, 410, 360, 118)
            ui.panel(surf, r4)
            eq = P.d["equipped"]
            ui.text(surf, "Snake:  " + ITEMS[("characters", eq["character"])]["name"], 22, (215, 225, 240), (cx + 20, 424), "topleft", False)
            ui.text(surf, "Map:  " + MAPS[self.selected_map()][0], 22, (215, 225, 240), (cx + 20, 452), "topleft", False)
            sw = self.selected_world()
            ui.text(surf, "World:  " + (WORLDS[sw]["name"] if sw is not None else "Auto"), 22, (215, 225, 240), (cx + 20, 480), "topleft", False)
            if P.d["armed"]:
                ui.text(surf, "Boosters armed: %d" % len(P.d["armed"]), 20, (130, 255, 160), (cx + 20, 506), "topleft", False)
        ui.text(surf, "Up/Down select   Enter confirm   M mute   N/B music   F11 fullscreen", 20, (200, 215, 230), (W // 2, H - 12), "midbottom")

    def draw_hud(self, surf, g):
        W, H = surf.get_size()
        ui, P, S = self.ui, self.prog, self.S
        bar = pygame.Surface((W, 70), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 120))
        surf.blit(bar, (0, 0))
        ui.text(surf, "SCORE", 20, (170, 200, 220), (20, 6), "topleft")
        ui.text(surf, "{:,}".format(g.score), 42, WHITE, (20, 22), "topleft")
        best = max([s["score"] for s in P.d["scores"]] + [g.score])
        ui.text(surf, "BEST %s" % "{:,}".format(best), 20, (255, 225, 120), (20 + 6 + ui.font(42).size("{:,}".format(g.score))[0] + 12, 40), "topleft", False)
        y = 80
        if g.combo >= 2:
            mult = combo_mult(g.combo)
            tier = combo_tier(g.combo)
            col = [(255, 235, 150), (255, 210, 110), (255, 180, 80), (255, 140, 60), (255, 100, 60), (255, 70, 120), (255, 60, 220), (200, 90, 255)][min(7, tier)]
            ui.text(surf, "COMBO x%d" % mult, 30 + min(14, tier * 2), col, (20, y), "topleft")
            ui.bar(surf, pygame.Rect(20, y + 32 + min(14, tier * 2), 180, 7), g.combo_t / g.ch.get("combo", 4.0), col, border=False)
            ui.text(surf, "chain %d" % g.combo, 18, (200, 210, 225), (210, y + 8), "topleft", False)
            y += 56
        for k, tl in g.pw.items():
            name, col, dur = POWERUPS[k][:3]
            ui.icon(surf, k, 34, y + 14, 15)
            ui.text(surf, name, 20, WHITE, (58, y + 6), "topleft", False)
            ui.bar(surf, pygame.Rect(58, y + 24, 120, 6), min(1.0, tl / max(1.0, dur)), col, border=False)
            y += 36
        # centre: mode / objective
        k, n = g.obj
        lab = {"adventure": "STAGE %d" % g.stage, "classic": "LEVEL %d / %d" % (g.level, MAX_LEVEL), "timeattack": "TIME ATTACK",
               "survival": "SURVIVAL", "challenge": "CHALLENGE", "daily": "DAILY CHALLENGE"}[g.mode]
        ui.text(surf, "%s   -   %s  /  %s" % (lab, WORLDS[g.widx]["name"], MAPS[g.map_idx][0]), 20, (190, 205, 225), (W // 2, 4), "midtop", False)
        if g.mode == "timeattack":
            tl = max(0, int(g.time_left))
            ui.text(surf, "%d:%02d" % (tl // 60, tl % 60), 44, (255, 120, 120) if tl < 10 else (255, 235, 150), (W // 2, 24), "midtop")
        elif g.mode == "survival" or k == "endless":
            s = int(g.lv["time"])
            ui.text(surf, "SURVIVED %d:%02d" % (s // 60, s % 60), 34, (255, 235, 150), (W // 2, 26), "midtop")
        else:
            ui.text(surf, g.obj_text(), 26, (255, 235, 150), (W // 2, 24), "midtop")
            tgt = g.obj_target_n()
            ui.bar(surf, pygame.Rect(W // 2 - 150, 50, 300, 14), min(1.0, g.obj_progress() / max(1, tgt)), (110, 235, 140))
            ui.text(surf, "%d / %d" % (g.obj_progress(), tgt), 16, (15, 25, 35), (W // 2, 57), shadow=False)
        if g.boss and not g.boss.defeated:
            ui.text(surf, g.boss.d["name"], 26, g.boss.d["acc"], (W // 2, 80), "midtop")
            ui.bar(surf, pygame.Rect(W // 2 - 200, 106, 400, 16), g.boss.hp / g.boss.max, (230, 60, 70))
        # right: coins, level, lives
        ui.icon(surf, "coin", W - 30, 20, 12)
        ui.text(surf, "{:,}".format(P.player.coins), 30, COIN_COL, (W - 50, 20), "midright")
        ui.bar(surf, pygame.Rect(W - 230, 40, 190, 8), P.player.xp / max(1, P.player.xp_needed()), XP_COL, border=False)
        ui.text(surf, "LV %d" % P.player.level, 20, WHITE, (W - 240, 44), "midright", False)
        for i in range(max(0, g.lives)):
            ui.icon(surf, "heart", W - 30 - i * 26, 60, 9)
        # bottom: mission + music + controls
        mid = self.top_mission()
        if mid:
            m = ALL_MISSIONS[mid]
            ui.text(surf, "MISSION  %s   %d/%d" % (m["name"], P.missions.progress(mid), m["target"]), 20, (200, 215, 235), (14, H - 34), "bottomleft", False)
        if S["show_controls"]:
            ui.text(surf, "WASD/Arrows steer   Q/E rotate   V camera   P pause   N next track   M mute", 18, (190, 205, 225), (W // 2, H - 10), "midbottom", False)
        ui.text(surf, "Music: " + self.audio.current_name(), 18, (170, 190, 215), (W - 14, H - 10), "bottomright", False)
        if g.banner_:
            txt, col, ttl, mx = g.banner_
            a = min(1.0, ttl / 0.5, (mx - ttl) / 0.15 + 0.2)
            ui.text(surf, txt, 72 if mx < 1.5 else 64, shade(col, max(0.2, a)), (W // 2, int(H * 0.2)))
        for i, (s, col, ttl) in enumerate(g.toasts[-3:]):
            ui.text(surf, s, 34, col, (W // 2, int(H * 0.30) + i * 34 - int((1.8 - ttl) * 6)))
        if g.dark > 0.05:
            v = ui.vignette(W, H)
            v.set_alpha(int(255 * min(1.0, g.dark / 0.7)))
            surf.blit(v, (0, 0))

    def draw_state_overlay(self, surf, g, wd):
        W, H = surf.get_size()
        ui = self.ui
        if g.state == "ready":
            go = g.state_t < 0.6
            lab = {"adventure": "STAGE %d" % g.stage, "classic": "LEVEL %d" % g.level}.get(g.mode, g.mode.upper().replace("TIMEATTACK", "TIME ATTACK"))
            ui.text(surf, "GO!" if go else lab, 100, (255, 240, 130), (W // 2, int(H * 0.26)))
            if not go:
                if g.boss:
                    ui.text(surf, "BOSS: " + g.boss.d["name"], 46, (255, 90, 90), (W // 2, int(H * 0.26) + 66))
                ui.text(surf, "OBJECTIVE: " + g.obj_text(), 32, WHITE, (W // 2, int(H * 0.26) + 112))
                ui.text(surf, "%s  -  %s" % (wd["name"], MAPS[g.map_idx][0]), 26, (215, 225, 240), (W // 2, int(H * 0.26) + 150))
        elif g.state == "dying":
            a = pygame.Surface((W, H), pygame.SRCALPHA)
            a.fill((255, 0, 0, int(70 * g.state_t / 1.5) if self.S["screen_fx"] else 0))
            surf.blit(a, (0, 0))
        elif g.state in ("clear", "win", "over"):
            self.draw_end_panel(surf, g)

    def draw_end_panel(self, surf, g):
        W, H = surf.get_size()
        ui, P = self.ui, self.prog
        res = g.result
        lines, extra = [], []
        if g.state == "over":
            title, col = ("TIME UP!", (255, 200, 90)) if g.timeup else ("GAME OVER", (255, 110, 110))
            best = max([s["score"] for s in P.d["scores"]] + [g.score])
            lines = [("FINAL SCORE", "{:,}".format(g.score), WHITE), ("BEST SCORE", "{:,}".format(best), (255, 225, 120)),
                     ("COINS EARNED", "+%d" % g.run["coins"], COIN_COL), ("XP EARNED", "+%d" % g.run["xp"], XP_COL),
                     ("FRUITS", str(g.run["fruits"]), WHITE), ("BEST COMBO", "x%d" % g.run["best_combo"], (255, 170, 60))]
            if g.new_best:
                extra.append(("NEW HIGH SCORE!", (255, 225, 90)))
        else:
            if g.state == "win":
                title = {"classic": "YOU WIN!", "adventure": "ADVENTURE COMPLETE!", "daily": "DAILY CHALLENGE COMPLETE!",
                         "challenge": "CHALLENGE COMPLETE!"}.get(g.mode, "YOU WIN!")
            else:
                title = "BOSS DEFEATED!" if g.outcome.get("boss") else "LEVEL COMPLETE!"
            col = (130, 255, 160)
            lines = [("SCORE", "{:,}".format(g.score), WHITE), ("COINS", "+%d" % res.get("coins", 0), COIN_COL),
                     ("XP", "+%d" % res.get("xp", 0), XP_COL), ("BEST COMBO", "x%d" % res.get("combo", 0), (255, 170, 60))]
            if res.get("flawless"):
                extra.append(("PERFECT RUN!  Bonus coins & XP", (255, 225, 90)))
        for text, c in self.mission_lines(2):
            extra.append(("Mission: " + text, c))
        for name in P.recent[-3:]:
            extra.append(("ACHIEVEMENT UNLOCKED: " + name, (255, 210, 90)))
        stars_h = 54 if g.state != "over" else 0
        h = 70 + stars_h + len(lines) * 36 + len(extra) * 28 + 110
        rect = pygame.Rect(0, 0, 680, h)
        rect.center = (W // 2, H // 2)
        ui.panel(surf, rect, 225)
        ui.text(surf, title, 62, col, (W // 2, rect.y + 44))
        y = rect.y + 86
        if g.state != "over":
            ui.stars(surf, W // 2, y + 18, res.get("stars", 1), 22)
            y += stars_h
        for k, v, c in lines:
            ui.text(surf, k, 28, (185, 198, 218), (rect.x + 120, y + 14), "midleft", False)
            ui.text(surf, v, 32, c, (rect.right - 120, y + 14), "midright", False)
            y += 36
        y += 4
        for t, c in extra:
            ui.text(surf, t, 22, c, (W // 2, y + 10), shadow=False)
            y += 28
        tmp = []
        ui.draw_ovl_buttons(surf, self.ovl_labels(g), self.ovl_sel, rect.bottom - 70, tmp)
        self.hits += [(r, i, "ovl") for r, i in tmp]

    def draw_pause(self, surf):
        W, H = surf.get_size()
        ui = self.ui
        a = pygame.Surface((W, H), pygame.SRCALPHA)
        a.fill((0, 0, 0, 130))
        surf.blit(a, (0, 0))
        rect = pygame.Rect(0, 0, 440, 360)
        rect.center = (W // 2, H // 2)
        ui.panel(surf, rect, 230)
        ui.text(surf, "PAUSED", 64, (255, 240, 130), (W // 2, rect.y + 52))
        for i, lab in enumerate(("RESUME", "RESTART", "SETTINGS", "QUIT TO MENU")):
            rr = pygame.Rect(rect.x + 40, rect.y + 100 + i * 58, rect.width - 80, 48)
            on = i == self.psel
            s = pygame.Surface(rr.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (*(ui.acc if on else (50, 60, 84)), 230 if on else 190), s.get_rect(), border_radius=12)
            surf.blit(s, rr.topleft)
            ui.text(surf, lab, 32, (10, 16, 28) if on else (225, 232, 245), rr.center, shadow=False)
            self.hits.append((rr, i, "pause"))

    def draw_modal(self, surf):
        W, H = surf.get_size()
        ui = self.ui
        title, lines = self.modal
        a = pygame.Surface((W, H), pygame.SRCALPHA)
        a.fill((0, 0, 0, 150))
        surf.blit(a, (0, 0))
        rect = pygame.Rect(0, 0, 520, 120 + 40 * len(lines))
        rect.center = (W // 2, H // 2)
        ui.panel(surf, rect, 235)
        ui.text(surf, title, 52, ui.acc, (W // 2, rect.y + 50))
        for i, ln in enumerate(lines):
            ui.text(surf, ln, 32 if i else 28, COIN_COL if "coins" in ln else XP_COL if "XP" in ln else WHITE, (W // 2, rect.y + 104 + i * 40))
        ui.text(surf, "Press any key", 20, (170, 185, 205), (W // 2, rect.bottom - 18))

    # ====================================================================== #
    #  Camera / update / draw / loop
    # ====================================================================== #
    def update_camera(self, dt):
        cam, rate = self.cam, 5.0
        if self.mode in ("game", "pause") and self.game:
            g = self.game
            if self.cam_mode == 1:
                d = g.snake.dir
                gy, gp, gd = math.atan2(-d[0], -d[1]), math.radians(32), 10.5 * self.zoom
                x, z = g.snake.pos(0)
                gt = (wx(x), 0.3, wx(z))
                rate = 4.0
            elif self.cam_mode == 2:
                gy, gp, gd, gt = self.user_yaw, math.radians(86), 36.0 * self.zoom, (0.0, 0.0, 0.0)
            else:
                gy, gp, gd, gt = self.user_yaw, self.user_pitch, 32.0 * self.zoom, (0.0, 0.0, 0.0)
        else:
            gy, gp, gd, gt = self.menu_yaw, 0.82, 34.0, (0.0, 0.0, 0.0)
        k = 1 - math.exp(-dt * rate)
        cam.yaw += ((gy - cam.yaw + math.pi) % (2 * math.pi) - math.pi) * k
        cam.pitch += (gp - cam.pitch) * k
        cam.dist += (gd - cam.dist) * k
        for i in range(3):
            cam.target[i] += (gt[i] - cam.target[i]) * k

    def world_idx(self):
        if self.mode in ("game", "pause") and self.game:
            return self.game.widx
        return self.menu_world

    def update(self, dt):
        S = self.S
        self.audio.update(dt, self.mode == "pause")
        self.ui.update_notes(dt)
        self.autosave_t += dt
        if self.autosave_t > 25:
            self.autosave_t = 0
            self.prog.commit()
        if self.trans:
            tr = self.trans
            tr["t"] += dt / 0.16
            if tr["t"] >= 1:
                if tr["phase"] == 0:
                    tr["fn"]()
                    tr["phase"], tr["t"] = 1, 0.0
                else:
                    self.trans = None
                    q, self.queued = self.queued, None
                    if q:
                        self.go(q)
        m = self.mode
        if m == "intro":
            self.intro_t += dt
            if self.intro_t > 4.0 and not self.trans:
                self.end_intro()
        elif m in ("menu", "screen"):
            self.menu_t += dt
            self.menu_yaw += dt * 0.2
            self.demo.update(dt)
            bg = BG_DEFS[self.eq("background")][2]
            if bg:
                self.menu_world = WORLD_IDX[bg]
            else:
                owned = self.prog.owned_worlds() or [0]
                self.menu_world = owned[int(self.menu_t / 25) % len(owned)]
        elif m == "game":
            g = self.game
            keys = pygame.key.get_pressed()
            if keys[pygame.K_q]:
                self.user_yaw -= 1.8 * dt
            if keys[pygame.K_e]:
                self.user_yaw += 1.8 * dt
            g.update(dt)
            if g.state in ("clear", "win", "over") and not g.reported:
                self.on_game_end(g)
        self.update_camera(dt)
        widx = self.world_idx()
        self.weather.set_world(widx, S)
        self.weather.update(dt, S["reduce_motion"])

    queued = None

    def draw(self):
        surf = pygame.display.get_surface()
        W, H = surf.get_size()
        self.hits = []
        if self.mode == "intro":
            self.draw_intro(surf)
            self.draw_trans(surf)
            return
        in_g = self.mode in ("game", "pause") and self.game
        g = self.game if in_g else self.demo
        widx = self.world_idx()
        wd = WORLDS[widx]
        S = self.S
        self.sky.draw(surf, wd, widx, self.cam.yaw, time.time())
        sh = g.shake * 0.45
        shake = (random.uniform(-sh, sh), random.uniform(-sh, sh) * 0.5, random.uniform(-sh, sh)) if sh else (0, 0, 0)
        self.cam.setup(W, H, shake)
        self.R.begin(surf, self.cam)
        self.R.glow_on = bool(S["effects"]) and S["quality"] >= 1
        g.render(self.R, wd, widx)
        self.R.flush()
        self.weather.draw(surf)
        if self.mode == "menu":
            self.draw_menu(surf)
        elif self.mode == "screen":
            self.draw_screen(surf)
        else:
            self.draw_hud(surf, g)
            self.draw_state_overlay(surf, g, wd)
            if self.mode == "pause":
                self.draw_pause(surf)
        if self.modal:
            self.draw_modal(surf)
        self.ui.draw_notes(surf)
        if S["mute"]:
            self.ui.text(surf, "MUTED", 20, (255, 150, 150), (W - 14, 100), "topright", False)
        self.draw_trans(surf)

    def draw_trans(self, surf):
        if not self.trans:
            return
        tr = self.trans
        a = tr["t"] if tr["phase"] == 0 else 1 - tr["t"]
        if a > 0:
            W, H = surf.get_size()
            s = pygame.Surface((W, H))
            s.set_alpha(int(255 * min(1.0, a)))
            surf.blit(s, (0, 0))

    def run(self):
        while True:
            dt = min(0.05, self.clock.tick(60) / 1000.0)
            for e in pygame.event.get():
                self.handle(e)
            self.update(dt)
            self.draw()
            pygame.display.flip()


def main():
    App().run()


if __name__ == "__main__":
    main()