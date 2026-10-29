#!/usr/bin/env python3
"""Generate a seeded hero and print the hero sheet (US Letter, landscape): one sheet for the hero's whole career.

    python3 scen/render_hero.py 0102-1a2b-3c4d-0        # -> sheets/hero-<code>.pdf

The layout matches the canvas design (the "Hero Sheets" artifact) measurement for measurement. The code's band sets the
starting level (low 1, mid 3, high 5); the seed decides the path taken at levels 3 and 5 and the effects dealt per rarity.
"""
import os, sys, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import osw_paths  # noqa: F401
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.colors import HexColor
from render_pdf import Page, tw, wrap_rich, _fonts, PX
from generate import Rng

CLASSES = {
    "Warrior":   dict(desc="A decent fighter with a balance between defense and attack.", stats=(2, 0, -1, 0)),
    "Knight":    dict(desc="An armored soldier who wins by outlasting.", stats=(2, -1, 0, 1)),
    "Barbarian": dict(desc="A wild fighter whose fury grows with every misstep.", stats=(2, 1, -1, 0)),
    "Paladin":   dict(desc="A holy knight whose defense becomes power.", stats=(2, -1, 0, 2)),
    "Cavalier":  dict(desc="A mounted knight who strikes in charges.", stats=(2, 1, 0, 0)),
    "Berserker": dict(desc="Most dangerous when nearly beaten.", stats=(2, 2, -1, 0)),
    "Beastkin":  dict(desc="Hunts weak points with a beast at its side.", stats=(1, 2, -1, 1)),
}
PATHS = {"Knight": ("Paladin", "Cavalier"), "Barbarian": ("Berserker", "Beastkin")}
# Warrior abilities; the level tag shows when each one starts
ABILITIES = [("HEAVY BLOWS", None, "Columns A and I deal 3 per square."),
             ("SHIELD", None, "+1 guard every round."),
             ("RIPOSTE", None, "After the enemy turn, 1 damage per 4 leftover guard, up to 2."),
             ("HEAVY BLOWS II", 2, "From row 6 up, every damage column deals +1 per square (notched squares)."),
             ("RESERVE RUNNER", 4, "Once per fight, when a roll would bust: add a 4th runner, use the dice again.")]
# path abilities: (level, name, rule); the second entry is the rank-up
PATH_ABIL = {
    "Knight":    [(3, "Hold the Line", "After the enemy turn: Riposte, or carry half your leftover guard into next round."),
                  (4, "", "Carry all of it.")],
    "Barbarian": [(3, "Rage", "Each fumble fills a Rage box. Spend all 3 to re-roll a bust or fumble."),
                  (4, "Fury", "At full Rage, a fumble's counter can hit the enemy instead (Rage empties).")],
    "Paladin":   [(5, "Oath", "Leftover guard: 1 damage or 1 healing per 3, up to 5."),
                  (6, "Radiant Aura", "Immune to Daze, Pin, Venom. Oath does both, 1 per 4, up to 4 each.")],
    "Cavalier":  [(5, "Charge", "First attack, every 3rd, and after a kill: an extra lance runner starts on row 3; enemies skip that round."),
                  (6, "Trample", "Overkill hits another enemy. Lance squares +1.")],
    "Berserker": [(5, "Bloodlust", "At 18 HP or less, a matching pair (like 3+3) moves 2."),
                  (6, "Unstoppable", "First fumble each fight: take the counter, move 1 wild, keep rolling.")],
    "Beastkin":  [(5, "Claws", "Weak points are 1 row lower. A weak-point hit: 4 free steps, ×3 that column."),
                  (6, "Pack", "On 1-1 or 6-6 your beast climbs 1, below the danger line. Its squares deal double.")],
}
EFFECTS = {   # wording from the player rules, shortened for the sheet
    "C": [("Extra Attack", "(once) +1 damage."),
          ("Brace", "(once) +3 guard this round if any enemy's next attack is heavy."),
          ("Mark", "(once) +1 damage on your next attack.")],
    "U": [("Poison I", "(once) Your target takes 1 damage per round for 2 rounds."),
          ("Ranged", "(once) 2 damage to any enemy, ignoring Bodyguard (1 if it's the only enemy)."),
          ("Pickpocket", "(once) Gain gold equal to your top column, and +1 damage."),
          ("Cleave", "(once) Another enemy takes a third of your top column, rounded down."),
          ("Leech", "(once per fight) Heal a fifth of your top column, rounded down."),
          ("Disarm", "For its next 2 turns, your target's heavy attacks become its first listed attack.")],
    "R": [("Poison II", "Your target takes 2 damage per round for 4 rounds."),
          ("Sleep", "Your target skips its next attack; the one after is halved."),
          ("Weaken", "Your target's attacks deal 3 less for the rest of the fight."),
          ("Momentum", "Your next attack deals a third of your top column extra, rounded up.")],
    "L": [("Critical Hit", "Your top column counts five times."),
          ("Chain", "Another enemy takes twice your top column."),
          ("Execute", "Defeat an enemy at half its HP or less, or at 8 or less; otherwise 15 damage."),
          ("Encore", "Take another full attack now; if this one fumbled, ignore the fumble.")],
    "M": [("Meteor", "Every enemy takes your top column ×4."),
          ("Time Stop", "When your attack ends, roll d6 more times (no fumbles); enemies skip a round."),
          ("Overdrive", "Every filled square deals +2 this attack."),
          ("Phoenix", "Once per scenario, at 0 HP return at 10 HP instead."),
          ("Godslayer", "Defeat a minion or miniboss outright; a boss takes 25."),
          ("Echo", "This attack happens again next turn, with your next attack.")],
}
RARITY_ORDER = "CURLM"
BADGE = {"C": ("#CCFBF1", "#0F766E"), "U": ("#EDE9FE", "#6D28D9"), "R": ("#FCE7F3", "#BE185D"), "L": ("#FEF3C7", "#A16207"), "M": ("#15142B", "#FCD34D")}

def make_hero(code):
    raw = code.replace("-", "").lower(); dd = int(raw[2:4]); seed = int(raw[4:12], 16)
    band = (dd - 1) // 3; level = (1, 3, 5)[band]
    R = Rng(seed ^ 0x4845524F)                                   # the hero's own stream off the seed
    effects = {}
    for rar in "CULR":
        roll = R.randint(1, 6); n = 1 if roll == 1 else (3 if roll == 6 else 2)
        effects[rar] = R.shuffle(EFFECTS[rar])[:min(n, len(EFFECTS[rar]))]
    branch = R.choice(sorted(PATHS)) if level >= 3 else None
    final = R.choice(PATHS[branch]) if level >= 5 else None
    RM = Rng(seed ^ 0x4D595448)                                  # Mythic effects: their own stream (older draws unchanged)
    roll = RM.randint(1, 6); n = 1 if roll == 1 else (3 if roll == 6 else 2)
    effects["M"] = RM.shuffle(EFFECTS["M"])[:n]
    threes = [r for r in "CURLM" if len(effects[r]) == 3]                 # only one rarity may keep a third effect
    if len(threes) > 1:
        keep = Rng(seed ^ 0x54485245).choice(threes)                     # its own stream: other draws are unchanged
        for r in threes:
            if r != keep: effects[r] = effects[r][:2]
    cls = final or branch or "Warrior"
    return dict(code=code, level=level, branch=branch, final=final, cls=cls, effects=effects)

# =============================================================================================================
# Layout: a measurement-for-measurement copy of the canvas design ("Hero Sheets" artifact, Main.dc.html).
# Units are CSS px (1056 x 816 page = 11 x 8.5 in). Text sits where a browser puts it: CSS line boxes with each
# font's own metrics (Barlow Condensed: ascent 1.0 em, line 1.2 em; Bungee: ascent 1.02 em, line 1.32 em).

INK, INK2, MUTED, RED, GRAY, GRAY2 = "#15142B", "#2E2D45", "#6F6E86", "#B91C1C", "#EEEDF3", "#F5F4F8"
ASC = {"Bungee": 1.02, "Barlow": 1.00, "Barlow-SB": 1.00, "Barlow-B": 1.00}
CONT = {"Bungee": 1.32, "Barlow": 1.20, "Barlow-SB": 1.20, "Barlow-B": 1.20}
W = {500: "Barlow", 600: "Barlow-SB", 700: "Barlow-B"}
MARGIN = 5 * 96 / 25.4                                                     # 5 mm all round
LX, LW, RW = MARGIN, 528, 480
RX, TOP, BOTTOM = LX + LW + 10, MARGIN, 816 - MARGIN

def sgn(v): return f"+{v}" if v > 0 else ("\u2212" + str(-v) if v < 0 else "0")
def typo(s): return s.replace("'", "\u2019")
def lh_normal(font, size): return CONT[font] * size
def base(top, font, size, lh=None):
    L = lh_normal(font, size) if lh is None else lh
    return top + (L - CONT[font] * size) / 2 + ASC[font] * size
def T(pg, x, top, s, font, size, color=INK, lh=None, anchor="l", cs=0.0):
    """One line of text in a CSS line box starting at `top`; centred/right text allows for trailing letter-spacing."""
    if anchor == "c": x -= cs / 2
    elif anchor == "r": x -= cs
    return pg.text(x, base(top, font, size, lh), s, font, size, color, anchor=anchor, cs=cs)
def segs(t, w=500, c=INK, size=12): return [(typo(t), W[w], size, c)]
def lead(name, t, size, color=INK, ncolor=INK): return [(name + " ", "Barlow-B", size, ncolor)] + segs(t, 500, color, size)
def par(pg, sg, x, top, width, size, lhf, draw=True, align="l"):
    """Wrapped paragraph (Barlow) with line-height lhf x size; returns its height."""
    lines = wrap_rich(sg, width); L = lhf * size
    if draw:
        for i, ln in enumerate(lines):
            lw_ = sum(tw(p, f, sz) for p, f, sz, _ in ln)
            cx = x + ((width - lw_) / 2 if align == "c" else 0); b = base(top + i * L, "Barlow", size, L)
            for p, f, sz, col in ln: cx += pg.text(cx, b, p, f, sz, col)
    return len(lines) * L
def bbox(pg, x, top, w, h, lw=1.5, r=3, fill=None, stroke=INK, dash=None):
    """CSS box-sizing: border-box rectangle (the border lies inside w x h)."""
    pg.rect(x + lw / 2, top + lw / 2, w - lw, h - lw, fill=fill, stroke=stroke, lw=lw, r=max(0, r - lw / 2), dash=dash)
def path_shape(pg, pts, fill=None, stroke=None, lw=1.0, close=True):
    c = pg.c; c.saveState()
    if fill: c.setFillColor(HexColor(fill))
    if stroke: c.setStrokeColor(HexColor(stroke)); c.setLineWidth(lw * PX); c.setLineJoin(1)
    p = c.beginPath(); p.moveTo(pg._x(pts[0][0]), pg._y(pts[0][1]))
    for a, b in pts[1:]: p.lineTo(pg._x(a), pg._y(b))
    if close: p.close()
    c.drawPath(p, stroke=1 if stroke else 0, fill=1 if fill else 0); c.restoreState()
def rrect(pg, x, top, w, h, fill, radii):
    """Filled rectangle with per-corner radii (tl, tr, br, bl)."""
    tl, tr, br, bl = radii; c = pg.c; k = 0.5523
    X = lambda v: pg._x(v); Y = lambda v: pg._y(v)
    c.saveState(); c.setFillColor(HexColor(fill)); p = c.beginPath()
    p.moveTo(X(x + tl), Y(top)); p.lineTo(X(x + w - tr), Y(top))
    if tr: p.curveTo(X(x + w - tr + tr * k), Y(top), X(x + w), Y(top + tr - tr * k), X(x + w), Y(top + tr))
    p.lineTo(X(x + w), Y(top + h - br))
    if br: p.curveTo(X(x + w), Y(top + h - br + br * k), X(x + w - br + br * k), Y(top + h), X(x + w - br), Y(top + h))
    p.lineTo(X(x + bl), Y(top + h))
    if bl: p.curveTo(X(x + bl - bl * k), Y(top + h), X(x), Y(top + h - bl + bl * k), X(x), Y(top + h - bl))
    p.lineTo(X(x), Y(top + tl))
    if tl: p.curveTo(X(x), Y(top + tl - tl * k), X(x + tl - tl * k), Y(top), X(x + tl), Y(top))
    p.close(); c.drawPath(p, stroke=0, fill=1); c.restoreState()
def vlabel(pg, cx, cy, text, size, color, ls):
    """Rotated (bottom-to-top) label centred on its capitals, as the canvas does it: rotate(-90deg) translate(ls/2, -0.05em)."""
    c = pg.c; w = tw(text, "Barlow-B", size, ls) + ls
    c.saveState(); c.translate(pg._x(cx), pg._y(cy)); c.rotate(90)
    t = c.beginText((-w / 2 + ls / 2) * PX, -0.35 * size * PX)
    t.setFont("Barlow-B", size * PX); t.setCharSpace(ls * PX); t.setFillColor(HexColor(color)); t.textOut(text); c.drawText(t); c.restoreState()
def check(pg, x, top, s=12):
    pg.line(x + s * 0.24, top + s * 0.52, x + s * 0.43, top + s * 0.72, "#FFFFFF", 1.8, cap=1)
    pg.line(x + s * 0.43, top + s * 0.72, x + s * 0.78, top + s * 0.28, "#FFFFFF", 1.8, cap=1)
def badge(pg, x, top, r, s=16, fs=9.5):
    tint, ink = BADGE[r]; pg.rect(x, top, s, s, fill=tint, r=4)
    T(pg, x + s / 2, top + (s - lh_normal("Bungee", fs)) / 2, r, "Bungee", fs, ink, anchor="c")
def lvtag(pg, x, top, n):
    """'LV n' tag: 11px bold, letter-spacing 0.4, padding 0 4px, 15px line box; returns its width."""
    w = tw(f"LV {n}", "Barlow-B", 11, 0.4) + 0.4 + 8
    pg.rect(x, top, w, 15, fill="#E9E8F0", r=3); T(pg, x + 4, top, f"LV {n}", "Barlow-B", 11, INK2, lh=15, cs=0.4)
    return w
def lvtag_w(n): return tw(f"LV {n}", "Barlow-B", 11, 0.4) + 0.4 + 8
H2ROW = lh_normal("Bungee", 14) + 3 + 1.5
def h2row(pg, X, top, Wd, title, note=None):
    """Section heading: Bungee 14 and an optional note on the same baseline, 3px padding, 1.5px rule."""
    b = base(top, "Bungee", 14); pg.text(X, b, title, "Bungee", 14, INK)
    if note: pg.text(X + Wd, b, note, "Barlow-SB", 11.5, INK2, anchor="r")
    pg.line(X, top + H2ROW - 0.75, X + Wd, top + H2ROW - 0.75, INK, 1.5)
    return H2ROW
def bottle(pg, x, top):
    pg.rect(x + 5.25, top + 2.25, 5.5, 3.5, fill=INK, r=0.6)
    path_shape(pg, [(x + 8, top + 4.2), (x + 14.6, top + 9.4), (x + 14.6, top + 20), (x + 1.4, top + 20), (x + 1.4, top + 9.4)], fill="#FFFFFF", stroke=INK, lw=1.6)
def bolt(pg, cx, cy, s=22, sw=1.8):
    k = s / 24.0; ox, oy = cx - s / 2, cy - s / 2
    pts = [(13, 2), (4, 14), (11, 14), (10, 22), (20, 9), (13, 9)]
    path_shape(pg, [(ox + a * k, oy + b * k) for a, b in pts], fill=INK, stroke=INK, lw=sw * k)    # solid bolt

# --- left column -------------------------------------------------------------------------------------------
LEVEL_BOX = (7 + 3 * 43 + 2 * 6 + 7, 4 + 11 + 3 + 20 + 2 + 10.5 + 5)
def stat_cols(C):
    w = lambda lab, v: tw(lab + " ", "Barlow-SB", 12.5) + tw(sgn(v), "Barlow-B", 12.5)
    return max(w("STR", C[0]), w("INT", C[2])), max(w("DEX", C[1]), w("WIS", C[3]))

def header(pg, h, y, draw=True):
    cls = h["cls"]; C = CLASSES[cls]; bw, bh = LEVEL_BOX
    sub_w = LW - bw - 10; c1, c2 = stat_cols(C["stats"]); stats_w = c1 + 10 + c2
    fs = 30
    while tw(cls.upper(), "Bungee", fs) + 10 + stats_w > sub_w and fs > 20: fs -= 1   # long class names shrink to fit
    desc_h = par(pg, segs(C["desc"], 600, INK2, 12.5), 0, 0, sub_w, 12.5, 1.12, draw=False)
    sub_h = 31 + 3 + desc_h; row_h = max(sub_h, bh)
    if not draw: return row_h
    sy = y + (row_h - sub_h) / 2
    T(pg, LX, sy + (31 - fs) / 2, cls.upper(), "Bungee", fs, RED, lh=fs)
    sx = LX + tw(cls.upper(), "Bungee", fs) + 10
    for i, (lab, v) in enumerate(zip(("STR", "DEX", "INT", "WIS"), C["stats"])):
        cx = sx + (i % 2) * (c1 + 10); ty = sy + (i // 2) * 16
        w = T(pg, cx, ty, lab + " ", "Barlow-SB", 12.5, INK); T(pg, cx + w, ty, sgn(v), "Barlow-B", 12.5, INK)
    par(pg, segs(C["desc"], 600, INK2, 12.5), LX, sy + 34, sub_w, 12.5, 1.12)
    bx = LX + LW - bw; by = y + (row_h - bh) / 2
    pg.rect(bx, by, bw, bh, fill=GRAY, r=4)
    T(pg, bx + bw / 2, by + 4, "LEVEL", "Barlow-B", 11, INK2, lh=11, anchor="c", cs=1)
    for gi, name in enumerate(("LOW", "MID", "HIGH")):
        gx = bx + 7 + gi * (43 + 6); gy = by + 4 + 11 + 3
        for k in range(2):
            n = gi * 2 + k + 1; filled = n <= h["level"]
            bbox(pg, gx + k * 23, gy, 20, 20, 1.5, 5, fill=INK if filled else "#FFFFFF")
            T(pg, gx + k * 23 + 10, gy + 3.1, str(n), "Barlow-B", 11.5, "#FFFFFF" if filled else INK, anchor="c")
        T(pg, gx + 21.5, gy + 22, name, "Barlow-B", 10.5, INK2, lh=10.5, anchor="c", cs=0.6)
    return row_h

def stock(pg, y):
    """NAME / HP 50 | POTIONS + 8 bottles | GOLD box, then 50 HP circles (grid: 1fr auto 64px, gaps 12 / 5, align end)."""
    txt_w = max(tw("POTIONS", "Bungee", 14), tw("Drink: +5 HP", "Barlow-SB", 11.5))
    c2 = txt_w + 8 + 76; c3 = 64; c1 = LW - c2 - c3 - 24
    x1, x2, x3 = LX, LX + c1 + 12, LX + c1 + 12 + c2 + 12
    r1 = 45; total = r1 + 5 + 25
    t1 = y + r1 - 36.5                                                     # column 1: name row (17.5) + 5 + HP 50 (14), bottom-aligned
    nw = T(pg, x1, t1 + 17.5 - 14.4, "NAME", "Barlow-B", 12, INK2, cs=1) + 1
    pg.line(x1 + nw + 8, t1 + 16 + 0.75, x1 + c1, t1 + 16 + 0.75, INK, 1.5)
    T(pg, x1, t1 + 22.5, "HP 50", "Bungee", 14, INK, lh=14)
    T(pg, x2, y + r1 - 29.88, "POTIONS", "Bungee", 14, INK, lh=14)        # column 2: text bottom-aligned with the bottles
    par(pg, segs("Drink: +5 HP", 600, INK2, 11.5), x2, y + r1 - 12.88, txt_w + 1, 11.5, 1.12)
    for i in range(8): bottle(pg, x2 + txt_w + 8 + (i % 4) * 20, y + (i // 4) * 24)
    T(pg, x3, y, "GOLD", "Bungee", 14, INK, lh=14)                         # column 3: spans both rows
    bbox(pg, x3, y + 17, c3, total - 17, 1.5, 6)
    for i in range(50):
        pg.circle(x1 + (i % 25) * 14.6 + 5.5, y + r1 + 5 + (i // 25) * 14 + 5.5, 5.5 - 0.65, stroke=INK, lw=1.3)
    return total

def abilities(pg, y, draw=True):
    yy = y + 18.48 + 3 + 1.5 + 2
    for name, lv, text in ABILITIES:
        x = LX + (lvtag_w(lv) + 5 if lv else 0)
        ht = par(pg, lead(name, text, 12, INK, RED), x, yy, LX + LW - x, 12, 1.12, draw=False)
        if draw:
            if lv: lvtag(pg, LX, yy, lv)
            par(pg, lead(name, text, 12, INK, RED), x, yy, LX + LW - x, 12, 1.12)
        yy += max(ht, 15 if lv else 0) + 2
    if draw:
        b = base(y, "Bungee", 14); pg.text(LX, b, "WARRIOR ABILITIES", "Bungee", 14, INK)
        pg.line(LX, y + H2ROW - 0.75, LX + LW, y + H2ROW - 0.75, INK, 1.5)
        bx = LX + LW - (5 * 13 + 4 * 4); by = y + (18.48 - 13) / 2
        for k in range(5):
            bbox(pg, bx + k * 17, by, 13, 13)
            if k >= 3: T(pg, bx + k * 17 + 6.5, by + 1.5, "+", "Barlow-B", 10, MUTED, lh=10, anchor="c")
        T(pg, bx - 6, y + (18.48 - 11) / 2, "ADJUSTMENTS: 3 + WIS", "Barlow-B", 11, INK2, lh=11, anchor="r", cs=0.5)
    return yy - 2 - y

POCKET_W, POCKET_TEXT = 76, "Store triggered effects for later"
NOTE = "Top column = your highest-damage column this attack. Mythic tiles are on rows 10-13."
SQUEEZES = [(12, 4, False), (11.5, 4, False), (11, 4, False), (11, 3, False)]   # (text size, gap between rarities, note line: off, the rules sheet explains top column)

def effects(pg, h, y, mode, draw=True):
    fs, rgap, note = mode
    list_w = LW - POCKET_W - 10; text_w = list_w - 16 - 7
    yy = y + H2ROW + 4
    if draw: h2row(pg, LX, y, LW, "EFFECTS", "Reach a tile: use one effect of its rarity")
    ly = yy
    for i, rar in enumerate(RARITY_ORDER):
        if i: ly += rgap
        ty = ly
        for j, (name, text) in enumerate(h["effects"][rar]):
            if j: ty += 1
            ty += par(pg, lead(name, text, fs), LX + 23, ty, text_w, fs, 1.12, draw=draw)
        if draw: badge(pg, LX, ly, rar)
        ly = ly + max(16, ty - ly)
    guide = par(pg, segs(POCKET_TEXT, 600, INK2, 11), 0, 0, POCKET_W - 12, 11, 1.12, draw=False)
    ph = 6 + 13 + 5 + 56 + 5 + guide + 7
    if draw:
        px = LX + list_w + 10
        pg.rect(px, yy, POCKET_W, ph, fill=GRAY2, r=4)
        T(pg, px + POCKET_W / 2, yy + 6, "POCKETS", "Bungee", 13, INK, lh=13, anchor="c")
        sx = px + (POCKET_W - 56) / 2; sy = yy + 6 + 13 + 5
        for k in range(4):
            bx, by_ = sx + (k % 2) * 30, sy + (k // 2) * 30
            if k == 0: bbox(pg, bx, by_, 26, 26, 1.5, 4, fill="#FFFFFF")
            else: bbox(pg, bx, by_, 26, 26, 1.0, 4, fill="#FFFFFF", stroke="#A9A8BC", dash=[1, 1])
        par(pg, segs(POCKET_TEXT, 600, INK2, 11), px + 6, sy + 56 + 5, POCKET_W - 12, 11, 1.12, align="c")
    yy = yy + max(ly - yy, ph)
    if note:
        yy += 4
        yy += par(pg, segs(NOTE, 500, INK2, 11), LX, yy, LW, 11, 1.12, draw=draw, align="c")
    return yy - y

def pbox_h(name, w):
    inner = w - 3 - 14; h = 1.5 + 3 + 15.84
    for lv, an, text in PATH_ABIL[name]:
        hh = par(None, ([(an + " ", "Barlow-B", 11, RED)] if an else []) + segs(text, 500, INK, 11), 0, 0, inner - lvtag_w(lv) - 6, 11, 1.12, draw=False)
        h += 2 + max(15, hh)
    return h + 4 + 1.5

def pbox(pg, x, top, w, hgt, name, chosen):
    pg.rect(x + 0.75, top + 0.75, w - 1.5, hgt - 1.5, fill="#FFFFFF", stroke=INK, lw=1.5, r=6.25)
    ix = x + 1.5 + 7; iw = w - 3 - 14; y = top + 1.5 + 3
    bbox(pg, ix, y + (15.84 - 12) / 2, 12, 12, 1.5, 3, fill=INK if chosen else None)
    if chosen: check(pg, ix, y + (15.84 - 12) / 2)
    T(pg, ix + 18, y, name.upper(), "Bungee", 12, RED)
    T(pg, ix + iw, y + (15.84 - 13.2) / 2, "  ".join(sgn(v) for v in CLASSES[name]["stats"]), "Barlow-B", 11, INK2, anchor="r")
    y += 15.84
    for lv, an, text in PATH_ABIL[name]:
        y += 2; tg = lvtag(pg, ix, y, lv)
        hh = par(pg, ([(an + " ", "Barlow-B", 11, RED)] if an else []) + segs(text, 500, INK, 11), ix + tg + 6, y, iw - tg - 6, 11, 1.12)
        y += max(15, hh)

def orbadge(pg, cx, top):
    w = tw("OR", "Bungee", 9) + 8; pg.rect(cx - w / 2, top, w, 14, fill=INK, r=4)
    T(pg, cx, top + 1, "OR", "Bungee", 9, "#FFFFFF", lh=13, anchor="c")

def orline(pg, x, top, w):
    ow = tw("OR", "Bungee", 9) + 8; cy = top + 7
    pg.line(x + 6, cy, x + (w - ow) / 2 - 6, cy, "#8E8DA3", 1.3, dash=[3.9, 2.6])
    pg.line(x + (w + ow) / 2 + 6, cy, x + w - 6, cy, "#8E8DA3", 1.3, dash=[3.9, 2.6])
    orbadge(pg, x + w / 2, top)

def path_geometry():
    cw = LW - 16
    bw = (cw - 7 - 22) / 2; h1 = max(pbox_h("Knight", bw), pbox_h("Barbarian", bw))
    tile = (cw - 8) / 2; lw_, rw_ = tile - 7, tile - 10
    hl = pbox_h("Paladin", lw_) + 2 + 14 + 2 + pbox_h("Cavalier", lw_)
    hr = pbox_h("Berserker", rw_) + 2 + 14 + 2 + pbox_h("Beastkin", rw_)
    return dict(cw=cw, bw=bw, h1=h1, tile=tile, lw=lw_, rw=rw_, bh=max(hl, hr) + 10,
                height=H2ROW + 3 + (h1 + 10) + 8 + max(hl, hr) + 10)

def path(pg, h, y):
    G = path_geometry()
    yy = y + h2row(pg, LX, y, LW, "PATH", "Pick one at each step") + 3
    gx = LX + 16; th = G["h1"] + 10
    pg.rect(LX, yy, 16, th, fill=GRAY); rrect(pg, gx, yy, G["cw"], th, GRAY, (0, 8, 8, 0))
    vlabel(pg, LX + 8 + 1, yy + th / 2, "LEVEL 3-4", 11, INK2, 1)
    pbox(pg, gx + 2, yy + 5, G["bw"], G["h1"], "Knight", h["branch"] == "Knight")
    orbadge(pg, gx + 2 + G["bw"] + 11, yy + th / 2 - 7)
    pbox(pg, gx + 2 + G["bw"] + 22, yy + 5, G["bw"], G["h1"], "Barbarian", h["branch"] == "Barbarian")
    yy += th + 8; bh = G["bh"]
    pg.rect(LX, yy, 16, bh, fill=GRAY); vlabel(pg, LX + 8 + 1, yy + bh / 2, "LEVEL 5-6", 11, INK2, 1)
    rrect(pg, gx, yy, G["tile"], bh, GRAY, (0, 8, 8, 0)); rrect(pg, gx + G["tile"] + 8, yy, G["tile"], bh, GRAY, (8, 8, 8, 8))
    for k, (a, b) in enumerate((("Paladin", "Cavalier"), ("Berserker", "Beastkin"))):
        tx = gx + 2 if k == 0 else gx + G["tile"] + 8 + 5; iw = G["lw"] if k == 0 else G["rw"]; ty = yy + 5
        ha = pbox_h(a, iw); pbox(pg, tx, ty, iw, ha, a, h["final"] == a); ty += ha + 2
        orline(pg, tx, ty, iw); ty += 16
        pbox(pg, tx, ty, iw, pbox_h(b, iw), b, h["final"] == b)

def footer(pg, h):
    top = BOTTOM + 2.3 - 13.8; b = top + 11.5                              # baseline-aligned row; the baseline sits exactly on the 5 mm margin
    pg.text(LX, b, "Map rolls: d6 + stat, 4+ succeeds. An adjustment changes one die by 1.", "Barlow-SB", 11, INK2)
    pg.text(LX + LW, b, f"Seed: {h['code']}", "Barlow-SB", 11.5, INK2, anchor="r")
    return 13.8 - 2.3

# --- right column: attack grid -----------------------------------------------------------------------------
DMG = [3, 1, 1, 0, 0, 0, 1, 1, 3]
COLOR = ["#DC2626" if d == 3 else ("#D97706" if d == 1 else "#2563EB") for d in DMG]
SURGE = [3, 5, 6, 8, 9, 8, 6, 5, 3]
BONUS = {(0, 4): "R", (8, 4): "R", (0, 9): "L", (8, 9): "L", (1, 2): "U", (7, 2): "U", (1, 9): "L", (7, 9): "L", (2, 7): "R", (6, 7): "R",
         (3, 2): "C", (5, 2): "C", (3, 5): "U", (5, 5): "U", (4, 2): "C", (4, 5): "U", (4, 8): "R",
         (3, 13): "L", (4, 13): "M", (5, 13): "L", (2, 12): "L", (4, 12): "R", (6, 12): "L", (1, 11): "R", (3, 11): "M", (5, 11): "M",
         (7, 11): "R", (0, 10): "L", (2, 10): "R", (4, 10): "R", (6, 10): "R", (8, 10): "L"}
PLUS = {(4, 1), (3, 3), (5, 3), (4, 6), (3, 7), (5, 7)}
ROWS, PITCH, SQ, GX, HEAD = 13, 49, 46, 22, 28
GW = 9 * PITCH - (PITCH - SQ)
LINEGAP, EXTRA = (9, 4, 3), 2                                              # the gaps carrying a line are 5px, not 3
def gtop(r): return HEAD + (ROWS - r) * PITCH + EXTRA * sum(r <= b for b in LINEGAP)
def gmid(r): return gtop(r) - (PITCH - SQ + EXTRA) / 2
GRID_H = gtop(1) + PITCH + 18

def right(pg, h):
    X = RX; y = TOP
    pg.text(X + 22, y + 14.62, "ATTACK GRID", "Bungee", 17, INK)          # title row: baseline-aligned, 17px tall
    pg.text(X + GX + GW, y + 14.62, "4 dice \u00b7 2 pairs \u00b7 3 runners \u00b7 climb until you bust", "Barlow-SB", 12.5, INK2, anchor="r")
    oy = y + 17 + 6
    top = lambda r: oy + gtop(r); mid = lambda r: oy + gmid(r)
    for r_, shade, label in ((13, "#E6E4EE", "LEVEL 5"), (11, "#F1F0F6", "LEVEL 3")):
        rrect(pg, X, top(r_) - 2, GX + GW, 2 * PITCH, shade, (6, 0, 0, 6))
        pg.rect(X + GX + GW, top(r_) - 2, 20, 2 * PITCH, fill=shade)
        vlabel(pg, X + GX + GW + 10, top(r_) - 2 + PITCH, label, 11, INK2, 1)
    for c in range(9):
        x = X + GX + c * PITCH
        T(pg, x + SQ / 2, oy, str(c + 3), "Bungee", 16, INK, lh=16, anchor="c")
        T(pg, x + SQ / 2, oy + 17, "2 GRD" if DMG[c] == 0 else f"{DMG[c]} DMG", "Barlow-B", 11, COLOR[c], lh=11, anchor="c", cs=0.4)
        T(pg, x + SQ / 2, top(1) + PITCH - 1, "ABCDEFGHI"[c], "Bungee", 16, INK, lh=16, anchor="c")
    for r in range(ROWS, 0, -1):
        T(pg, X + GX - 5, top(r) + 15, str(r), "Barlow-B", 13, INK2, lh=13, anchor="r")
        for c in range(9):
            x = X + GX + c * PITCH; t = top(r); key = (c, r); b = BONUS.get(key); plus = key in PLUS; surge = not b and not plus and SURGE[c] == r
            bw = 2.5                                                       # Surge is marked by its bolt alone
            bbox(pg, x, t, SQ, SQ, bw, 7, fill=BADGE[b][0] if b else "#FFFFFF", stroke=COLOR[c])
            if b: T(pg, x + SQ / 2, t + (SQ - lh_normal("Bungee", 16)) / 2, b, "Bungee", 16, BADGE[b][1], anchor="c")
            elif plus: T(pg, x + SQ / 2, t + (SQ - lh_normal("Bungee", 15)) / 2, "+1", "Bungee", 15, "#DC2626", anchor="c")
            elif surge: bolt(pg, x + SQ / 2, t + SQ / 2, 22)
            if DMG[c] > 0 and r >= 6:                                      # Heavy Blows II notch: 10px corner triangle
                rx_, ty_ = x + SQ - bw - 2, t + bw + 2
                path_shape(pg, [(rx_ - 10, ty_), (rx_, ty_), (rx_, ty_ + 10)], fill="#D97706")
    gx0, gx1 = X + GX - 4, X + GX + GW + 4
    pg.line(gx0, mid(9), gx1, mid(9), INK, 2.2)
    pg.line(gx0, mid(3), gx1, mid(3), "#DC2626", 2.6, dash=[7.8, 5.2])
    pg.line(gx0, mid(4), gx1, mid(4), "#F87171", 1.6, dash=[4.8, 3.2])
    for cy, hh, bg, label in ((mid(3), 44, "#DC2626", "DANGER"), (mid(4), 28, "#F87171", "LV 6")):
        rrect(pg, X + GX + GW + 4, cy - hh / 2, 16, hh, bg, (0, 3, 3, 0))
        vlabel(pg, X + GX + GW + 4 + 8, cy, label, 9.5, "#FFFFFF", 0.8)
    # legend: a 2 x 3 grid spread across the grid's width (columns as wide as their widest item; space-between)
    ly = oy + GRID_H + 6; lx = X + 22; lwid = 438
    SB = lambda t: tw(t, "Barlow-SB", 11.5)
    def it_rar(x0, y0, hh):
        for k, r_ in enumerate(RARITY_ORDER): badge(pg, x0 + k * 19, y0 + (hh - 15) / 2, r_, 15, 9)
        T(pg, x0 + 5 * 19, y0 + (hh - 12.88) / 2, "Effect tiles", "Barlow-SB", 11.5, INK, lh=12.88)
    def it_plus(x0, y0, hh):
        w = T(pg, x0, y0 + (hh - 15.84) / 2, "+1", "Bungee", 12, "#DC2626")
        T(pg, x0 + w + 4, y0 + (hh - 12.88) / 2, "damage, no guard", "Barlow-SB", 11.5, INK, lh=12.88)
    def it_surge(x0, y0, hh): bolt(pg, x0 + 7.5, y0 + hh / 2, 15, 2); T(pg, x0 + 19, y0 + (hh - 12.88) / 2, "Surge: first time, +1 step", "Barlow-SB", 11.5, INK, lh=12.88)
    def it_dl(x0, y0, hh): pg.line(x0, y0 + hh / 2, x0 + 18, y0 + hh / 2, "#DC2626", 2.4, dash=[7.2, 4.8]); T(pg, x0 + 22, y0 + (hh - 12.88) / 2, "Past it, 3 of a kind fumbles (take 3)", "Barlow-SB", 11.5, INK, lh=12.88)
    def it_wild(x0, y0, hh): T(pg, x0, y0 + (hh - 12.88) / 2, "2 or 12: wild", "Barlow-SB", 11.5, INK, lh=12.88)
    def it_hb2(x0, y0, hh):
        t0 = y0 + (hh - 13) / 2; bbox(pg, x0, t0, 13, 13, 1.4, 2, stroke="#D97706")
        path_shape(pg, [(x0 + 13 - 1.4 - 7, t0 + 1.4), (x0 + 13 - 1.4, t0 + 1.4), (x0 + 13 - 1.4, t0 + 1.4 + 7)], fill="#D97706")
        T(pg, x0 + 17, y0 + (hh - 12.88) / 2, "+1 per notched square (LV 2)", "Barlow-SB", 11.5, INK, lh=12.88)
    items = [(5 * 19 + SB("Effect tiles"), 15, it_rar), (tw("+1", "Bungee", 12) + 4 + SB("damage, no guard"), 15.84, it_plus),
             (19 + SB("Surge: first time, +1 step"), 15, it_surge), (22 + SB("Past it, 3 of a kind fumbles (take 3)"), 12.88, it_dl),
             (SB("2 or 12: wild"), 12.88, it_wild), (17 + SB("+1 per notched square (LV 2)"), 13, it_hb2)]
    cols = [max(items[c][0], items[c + 3][0]) for c in range(3)]; free = (lwid - sum(cols)) / 2
    xs = [lx, lx + cols[0] + free, lx + cols[0] + cols[1] + 2 * free]
    for row in range(2):
        rh = max(items[row * 3 + c][1] for c in range(3))
        for c in range(3): items[row * 3 + c][2](xs[c], ly, rh)
        ly += rh + 2
    # tracker: a gray box across the same width, items spread evenly (space-between)
    ty = ly - 2 + 6; rrect(pg, lx, ty, lwid, 23, GRAY, (4, 4, 4, 4))
    TRK = [("Rage", 3), ("Reserve", 1), ("Carried", -1), ("Unstoppable", 1), ("Phoenix", 1)]
    widths = [tw("TRACKER", "Bungee", 11)] + [tw(n, "Barlow-B", 11.5) + 5 + (28 if k < 0 else k * 12 + (k - 1) * 3) for n, k in TRK]
    gap = (lwid - 16 - sum(widths)) / len(TRK); x = lx + 8; cy = ty + 11.5
    T(pg, x, cy - 5.5, "TRACKER", "Bungee", 11, INK, lh=11); x += widths[0] + gap
    for (n, k), w in zip(TRK, widths[1:]):
        nw = T(pg, x, cy - 5.75, n, "Barlow-B", 11.5, INK, lh=11.5) + 5
        if k < 0: bbox(pg, x + nw, cy - 7.5, 28, 15, 1.3, 3, fill="#FFFFFF")
        for j in range(max(0, k)): bbox(pg, x + nw + j * 15, cy - 6, 12, 12, 1.5, 3, fill="#FFFFFF")
        x += w + gap

def render(code, out):
    _fonts(); h = make_hero(code)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    c = rl_canvas.Canvas(out, pagesize=landscape(letter)); c.setTitle(f"One Sheet Wonder hero: {h['cls']} (level {h['level']}) {code}")
    pg = Page(c)
    y = TOP
    y += header(pg, h, y) + 3
    y += stock(pg, y) + 3
    y += abilities(pg, y) + 3
    fh = footer(pg, h); G = path_geometry()
    path_top = BOTTOM - fh - 2 - 3 - G["height"]
    mode = next((m for m in SQUEEZES if y + effects(None, h, y, m, draw=False) + 3 <= path_top), SQUEEZES[-1])
    effects(pg, h, y, mode)
    path(pg, h, path_top)
    right(pg, h)
    c.showPage(); c.save(); return out, h

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("code"); ap.add_argument("-o", "--out"); a = ap.parse_args()
    out, h = render(a.code, a.out or os.path.join(os.getcwd(), "sheets", f"hero-{a.code}.pdf"))
    print(out, "|", h["cls"], "level", h["level"], "|", {k: [n for n, _ in v] for k, v in h["effects"].items()})
