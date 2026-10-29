#!/usr/bin/env python3
"""Render scenario sheets straight to print-ready PDF (US Letter, landscape). Seed in, page out.

    python3 scen/render_pdf.py 0105-a6a3-a450-7                       # -> sheets/0105-a6a3-a450-7.pdf
    python3 scen/render_pdf.py CODE1 CODE2 CODE3 -o campaign.pdf      # one multi-page PDF
    python3 scen/render_pdf.py CODE --cap 20                          # danger-track length override
    python3 scen/render_pdf.py CODE --dmg-add 1 --hp-scale 1.1   # difficulty kit (see steps.py)

Everything printed comes from the generator: map, enemies, keywords, boss, danger track, objectives, pools, shop.
Layout is in the design's pixels (1056 x 816 px = 11 x 8.5 in at 96 px/in) and converted to PDF points (x 0.75).
Fonts (Bungee, Barlow Condensed; SIL Open Font License) are embedded from ../fonts.
"""
import os, sys, re, argparse, copy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import osw_paths  # noqa: F401
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter, landscape

PX = 0.75                          # 1 design px = 0.75 pt
PW, PH = 1056, 816                 # page in design px
INK, INK2, MUTED, LINE = "#15142B", "#2E2D45", "#6F6E86", "#D6D5E0"
RED, GOLD_T, GOLD_B, VIO, VIO_B, TEAL = "#B91C1C", "#A16207", "#FEF3C7", "#6D28D9", "#F5F3FF", "#0F766E"
CS = 34                            # map cell (9 mm)

# --------------------------------------------------------------------------------------------- fonts
def _fonts():
    d = None
    for cand in (os.path.join(osw_paths.ENGINE_DIR, "fonts"), os.path.join(HERE, "fonts"), os.path.join(os.path.dirname(HERE), "fonts")):
        if os.path.exists(os.path.join(cand, "Bungee-Regular.ttf")): d = cand; break
    if d is None: raise FileNotFoundError("fonts/ folder with Bungee and Barlow Condensed not found")
    for name, f in (("Bungee", "Bungee-Regular.ttf"), ("Barlow", "BarlowCondensed-Medium.ttf"),
                    ("Barlow-SB", "BarlowCondensed-SemiBold.ttf"), ("Barlow-B", "BarlowCondensed-Bold.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames(): pdfmetrics.registerFont(TTFont(name, os.path.join(d, f)))
FONT = {500: "Barlow", 600: "Barlow-SB", 700: "Barlow-B"}

def tw(s, font, size, cs=0.0): return pdfmetrics.stringWidth(s, font, size) + cs * max(0, len(s) - 1)

class Page:
    """Drawing in design px with a top-left origin."""
    def __init__(self, c): self.c = c
    def _x(self, x): return x * PX
    def _y(self, y): return (PH - y) * PX
    def col(self, h): return HexColor(h)
    def rect(self, x, y, w, h, fill=None, stroke=None, lw=1.0, r=0.0, dash=None):
        c = self.c; c.saveState()
        if fill: c.setFillColor(self.col(fill))
        if stroke: c.setStrokeColor(self.col(stroke)); c.setLineWidth(lw * PX)
        if dash: c.setDash([v * PX for v in dash])
        args = (self._x(x), self._y(y + h), w * PX, h * PX)
        if r > 0: c.roundRect(*args, r * PX, stroke=1 if stroke else 0, fill=1 if fill else 0)
        else: c.rect(*args, stroke=1 if stroke else 0, fill=1 if fill else 0)
        c.restoreState()
    def line(self, x1, y1, x2, y2, color=INK, lw=1.0, dash=None, cap=0):
        c = self.c; c.saveState(); c.setStrokeColor(self.col(color)); c.setLineWidth(lw * PX); c.setLineCap(cap)
        if dash: c.setDash([v * PX for v in dash])
        c.line(self._x(x1), self._y(y1), self._x(x2), self._y(y2)); c.restoreState()
    def circle(self, cx, cy, r, fill=None, stroke=None, lw=1.0):
        c = self.c; c.saveState()
        if fill: c.setFillColor(self.col(fill))
        if stroke: c.setStrokeColor(self.col(stroke)); c.setLineWidth(lw * PX)
        c.circle(self._x(cx), self._y(cy), r * PX, stroke=1 if stroke else 0, fill=1 if fill else 0); c.restoreState()
    def text(self, x, base, s, font="Barlow", size=12.5, color=INK, anchor="l", cs=0.0):
        """base = baseline y in px. anchor l/c/r. cs = letter spacing in px."""
        w = tw(s, font, size, cs)
        if anchor == "c": x -= w / 2
        elif anchor == "r": x -= w
        t = self.c.beginText(self._x(x), self._y(base)); t.setFont(font, size * PX); t.setFillColor(self.col(color))
        t.setCharSpace(cs * PX)          # always set: PDF letter spacing persists between text objects
        t.textOut(s); self.c.drawText(t); return w

def asc(size): return size * 0.78          # cap-height-ish offset from a box top to the baseline (Barlow / Bungee)

# --------------------------------------------------------------------------------------------- rich text
def wrap_rich(segs, width):
    """segs: [(text, font, size, color)] -> lines of segs, greedy word wrap."""
    words = []
    for text, font, size, color in segs:
        for i, part in enumerate(re.split(r"(\s+)", text)):
            if part: words.append((part, font, size, color))
    lines, cur, w = [], [], 0.0
    for part, font, size, color in words:
        pw = tw(part, font, size)
        if part.isspace():
            if cur: cur.append((part, font, size, color)); w += pw
            continue
        if cur and w + pw > width:
            while cur and cur[-1][0].isspace(): w -= tw(cur[-1][0], cur[-1][1], cur[-1][2]); cur.pop()
            lines.append(cur); cur, w = [], 0.0
        cur.append((part, font, size, color)); w += pw
    if cur: lines.append(cur)
    return lines or [[]]

def draw_rich(pg, segs, x, top, width, size=12.5, lead=1.2):
    lines = wrap_rich(segs, width); y = top
    for ln in lines:
        cx = x
        for part, font, sz, color in ln: cx += pg.text(cx, y + asc(sz), part, font, sz, color)
        y += size * lead
    return y - top

def rich_height(segs, width, size=12.5, lead=1.2): return len(wrap_rich(segs, width)) * size * lead

def plain(t, w=500, c=INK, size=12.5): return [(t, FONT[w], size, c)]

# --------------------------------------------------------------------------------------------- data
GLOSS_TAG = {"p": "Venom", "d": "Daze", "g": "Pin", "x": "Sunder"}
def typo(s): return s.replace("'", "\u2019")

def scenario(code, cap=None, hp_scale=1.0, dmg_add=0, potions=None, content=None):
    """content: the code whose map/enemies to draw (default: code). The printed seed is always `code`."""
    import pools
    from generate import generate
    if cap: pools.DIFFICULTY["Normal"]["cap"] = cap
    g = copy.deepcopy(generate(content or code)); g["code"] = code
    def scale_hp(m): return dict(m, hp=max(1, int(round(m["hp"] * hp_scale))))
    def add_dmg(at): return [tuple([(max(1, x[0] + dmg_add) if x[0] else 0)] + list(x[1:])) for x in at]
    if hp_scale != 1.0 or dmg_add:
        g["minions"] = [dict(scale_hp(m), attacks=add_dmg(m["attacks"])) for m in g["minions"]]
        g["minibosses"] = [dict(scale_hp(m), attacks=add_dmg(m["attacks"])) for m in g["minibosses"]]
        b = dict(scale_hp(g["boss"]), attacks=add_dmg(g["boss"]["attacks"])); b["thresholds"] = ((2 * b["hp"]) // 3, b["hp"] // 3); g["boss"] = b
    g["potions"] = potions
    return g

def weak(w):
    a, b = w[0].split("\u00b7"); L = lambda c: "ABCDEFGHI"[int(c) - 3]
    return f"{L(a)}{w[1]},{L(b)}{w[1]}"

def atk_parts(attacks):
    """[(prefix_text, chip_text_or_None)] e.g. Daze 4, 6, 10H -> [("", "Daze 4"), (", 6", None), (", 10H", None)]"""
    out = []
    for i, x in enumerate(attacks):
        d, h = x[0], x[1]; tag = x[2] if len(x) > 2 else ""
        val = "wind-up" if d == 0 else f"{d}{'H' if h else ''}"; sep = ", " if i else ""
        kw = GLOSS_TAG.get(tag)
        out.append((sep, f"{kw} {val}") if kw else (sep + val, None))
    return out

def module_label(name):
    import pools
    return pools.MODULE_LABEL.get(name, name)

# --------------------------------------------------------------------------------------------- components
def chip(pg, x, top, s, h=18, inline=False):
    """Violet keyword tag; returns width."""
    size = 12; w = tw(s, "Barlow-B", size, 0.3) + (8 if inline else 10)
    pg.rect(x, top, w, h, fill=VIO_B, stroke=VIO, lw=1.5, r=4)
    pg.text(x + w / 2, top + h / 2 + 4.2, s, "Barlow-B", size, VIO, anchor="c", cs=0.3)
    return w

def pill(pg, x, top, s, fill, color, h=18):
    w = tw(s, "Barlow-B", 12) + 12
    pg.rect(x, top, w, h, fill=fill, r=9); pg.text(x + w / 2, top + h / 2 + 4.2, s, "Barlow-B", 12, color, anchor="c")
    return w

def section_head(pg, x, top, w, title, note=None, lw=1.5):
    pg.text(x, top + 14, title, "Bungee", 14, INK)
    if note: pg.text(x + w, top + 14, note, "Barlow-SB", 12, INK2, anchor="r")
    pg.line(x, top + 20, x + w, top + 20, INK, lw)
    return 22

def checkbox(pg, x, top, s=13): pg.rect(x, top, s, s, stroke=INK, lw=1.5, r=3)

def chest_icon(pg, cx, cy, s=23):
    c = pg.c; k = s / 24.0; ox, oy = cx - s / 2, cy - s / 2
    P = lambda x, y: (pg._x(ox + x * k), pg._y(oy + y * k))
    c.saveState(); c.setFillColor(HexColor(GOLD_B)); c.setStrokeColor(HexColor(GOLD_T)); c.setLineWidth(1.9 * PX * k); c.setLineJoin(1); c.setLineCap(1)
    p = c.beginPath(); p.moveTo(*P(4, 10)); p.lineTo(*P(20, 10)); p.lineTo(*P(20, 19)); p.lineTo(*P(4, 19)); p.close()
    p.moveTo(*P(4, 10)); p.curveTo(*P(4, 6.5), *P(7, 5), *P(12, 5)); p.curveTo(*P(17, 5), *P(20, 6.5), *P(20, 10))
    c.drawPath(p, stroke=1, fill=1)
    c.line(*P(12, 12.5), *P(12, 15.5)); c.restoreState()

def person_icon(pg, cx, cy, s=15, color=TEAL):
    c = pg.c; k = s / 24.0; ox, oy = cx - s / 2, cy - s / 2
    P = lambda x, y: (pg._x(ox + x * k), pg._y(oy + y * k))
    c.saveState(); c.setStrokeColor(HexColor(color)); c.setLineWidth(2.4 * PX * k); c.setLineCap(1)
    hx, hy = P(12, 8); c.circle(hx, hy, 4 * k * PX, stroke=1, fill=0)
    p = c.beginPath(); p.moveTo(*P(4.5, 21)); p.curveTo(*P(4.5, 16), *P(8, 13.5), *P(12, 13.5)); p.curveTo(*P(16, 13.5), *P(19.5, 16), *P(19.5, 21))
    c.drawPath(p, stroke=1, fill=0); c.restoreState()

# --------------------------------------------------------------------------------------------- map
def draw_map(pg, g, x0, y0):
    mx, my = x0 + 20, y0 + 19            # grid origin (after left axis 20px and top axis 16px + 3px gap)
    for i in range(12):
        pg.text(mx + i * CS + CS / 2, y0 + 12.5, str(i + 1), "Barlow-B", 12, INK2, anchor="c")
        pg.text(mx - 6, my + i * CS + CS / 2 + 4.5, str(i + 1), "Barlow-B", 12, INK2, anchor="r")
    pg.rect(mx, my, 12 * CS, 12 * CS, fill="#FFFFFF")
    for i in range(12):                  # light 9 mm grid
        pg.line(mx + i * CS + 0.5, my, mx + i * CS + 0.5, my + 12 * CS, LINE, 1)
        pg.line(mx, my + i * CS + 0.5, mx + 12 * CS, my + i * CS + 0.5, LINE, 1)
    pg.line(mx + 6 * CS, my, mx + 6 * CS, my + 12 * CS, "#8E8DA3", 1.5, dash=[5, 3])
    pg.line(mx, my + 6 * CS, mx + 12 * CS, my + 6 * CS, "#8E8DA3", 1.5, dash=[5, 3])
    for q, (cx, cy) in {1: (3, 3), 2: (9, 3), 3: (3, 9), 4: (9, 9)}.items():   # quadrant labels + danger pips
        lx = mx + (cx - 1) * CS + CS; ty = my + (cy - 1) * CS + CS // 2 - 17
        pg.text(lx, ty + 15, f"Q{q}", "Bungee", 18, MUTED, anchor="c")
        n = g["danger"][q]
        if n == 0: pg.text(lx, ty + 33, "SAFE", "Barlow-B", 12, MUTED, anchor="c")
        else:
            w = n * 9 + (n - 1) * 3
            for k in range(n): pg.circle(lx - w / 2 + 4.5 + k * 12, ty + 25.5, 4.5, fill="#DC2626")
    for b in g["blocks"]:                # solid blocks: wall-filled
        if b["kind"] == "closed":
            pg.rect(mx + (b["x"] - 1) * CS - 1.5, my + (b["y"] - 1) * CS - 1.5, b["size"] * CS + 3, b["size"] * CS + 3, fill=INK)
    for (a, b) in g["walls"]:
        (x1, y1), (x2, y2) = a, b
        if y1 == y2: X = max(x1, x2) - 1; pg.rect(mx + X * CS - 1.5, my + (y1 - 1) * CS - 1.5, 3, CS + 3, fill=INK)
        else: Y = max(y1, y2) - 1; pg.rect(mx + (x1 - 1) * CS - 1.5, my + Y * CS - 1.5, CS + 3, 3, fill=INK)
    pg.rect(mx - 1.5, my - 1.5, 12 * CS + 3, 12 * CS + 3, stroke=INK, lw=3)   # outer wall
    def center(x, y): return mx + (x - 1) * CS + CS / 2, my + (y - 1) * CS + CS / 2
    for q, (x, y) in g["starts"].items():
        cx, cy = center(x, y); pg.circle(cx, cy, 11.5, fill=INK); pg.text(cx, cy + 4.3, f"S{q}", "Barlow-B", 12, "#FFFFFF", anchor="c")
    for p in g["places"]:
        cx, cy = center(p["x"], p["y"])
        if p["kind"] == "chest": chest_icon(pg, cx, cy)
        elif p["kind"] == "npc": pg.circle(cx, cy, 10.5, fill="#FFFFFF", stroke=TEAL, lw=2); person_icon(pg, cx, cy)
        elif p["kind"] == "shop":
            pg.rect(cx - 11.5, cy - 11.5, 23, 23, fill="#EDE9FE", stroke=VIO, lw=2, r=5); pg.text(cx, cy + 4.6, "$", "Bungee", 12, VIO, anchor="c")
    return my + 12 * CS + 1.5                                                 # bottom edge

def draw_legend(pg, x, top, w):
    items = [("start", "Start"), ("chest", "Chest"), ("npc", "NPC"), ("shop", "Shopkeeper"), ("pip", "+1 danger per pip")]
    widths = [(16 if k != "pip" else 9) + 4 + tw(t, "Barlow-SB", 12) for k, t in items]
    total = sum(widths) + 12 * (len(items) - 1); cx = x + (w - total) / 2; cy = top + 8
    for (k, t), iw in zip(items, widths):
        if k == "start": pg.circle(cx + 8, cy, 8, fill=INK); tx = cx + 20
        elif k == "chest": chest_icon(pg, cx + 8, cy, 16); tx = cx + 20
        elif k == "npc": pg.circle(cx + 8, cy, 7, stroke=TEAL, lw=2); tx = cx + 20
        elif k == "shop": pg.rect(cx, cy - 8, 16, 16, fill="#EDE9FE", stroke=VIO, lw=2, r=4); tx = cx + 20
        else: pg.circle(cx + 4.5, cy, 4.5, fill="#DC2626"); tx = cx + 13
        pg.text(tx, cy + 4.3, t, "Barlow-SB", 12, INK2); cx += iw + 12
    return 16

COORD = lambda s: (s, "Barlow-B", 12, INK)

# --------------------------------------------------------------------------------------------- left column
def left_blocks(g, W):
    """Each block: (height, draw(pg, x, top))."""
    blocks = []
    def map_block(pg, x, top): return draw_map(pg, g, x, top)
    blocks.append((19 + 12 * CS + 3, map_block))
    def legend(pg, x, top): draw_legend(pg, x + 20, top, W - 20)
    blocks.append((16, legend))
    rule = [("[_,_]", "Barlow-B", 12, INK), (" roll a cell: d6 per number, +6 if a second d6 shows 4-6. ", "Barlow", 12, INK2),
            ("Q3[_,_]", "Barlow-B", 12, INK), (" d6 per number, inside Q3.", "Barlow", 12, INK2)]
    rh = rich_height(rule, W - 20, 12)
    def rule_block(pg, x, top):
        lines = wrap_rich(rule, W - 20); y = top
        for ln in lines:
            lw = sum(tw(p, f, s) for p, f, s, c in ln); cx = x + 20 + (W - 20 - lw) / 2
            for p, f, s, c in ln: cx += pg.text(cx, y + asc(12), p, f, s, c)
            y += 14.4
    blocks.append((rh, rule_block))
    objs = [typo(o) for o in g["objectives"]]
    oh = 22 + 3 + sum(max(16, rich_height(plain(o), W - 20)) + 3 for o in objs)
    def objectives(pg, x, top):
        y = top + section_head(pg, x, top, W, "OBJECTIVES", "Win and complete 3: level up") + 3
        for o in objs:
            checkbox(pg, x, y + 1.5); h = draw_rich(pg, plain(o), x + 20, y, W - 20); y += max(16, h) + 3
    blocks.append((oh, objectives))
    import pools
    enc = [(r, typo(t)) for r, t in g.get("encounters", pools.ENCOUNTERS)]
    colw = (W - 14) / 2
    rows = [enc[i:i + 2] for i in range(0, len(enc), 2)]
    row_h = [max(rich_height(plain(t), colw - 30) for r, t in row) + 2 for row in rows]
    notes = [[("Doubles", "Barlow-B", 12.5, INK), (" (raw dice): a miniboss. 1-1 or 6-6 is the boss once the fuse is lit.", "Barlow", 12.5, INK)],
             [("Villager", "Barlow-B", 12.5, INK), (", d6: 1-2 fight 1 minion, 3-4 fight 2, 5-6 escort them to ", "Barlow", 12.5, INK), ("[_,_]", "Barlow-B", 12.5, INK), (".", "Barlow", 12.5, INK)]]
    eh = 22 + 3 + sum(row_h) + 3 + sum(rich_height(n, W) + 3 for n in notes)
    def encounters(pg, x, top):
        y = top + section_head(pg, x, top, W, "MOVEMENT ROLL", "Every 3rd cell (first 3 free): 2d6 + quadrant danger") + 3
        for row, h in zip(rows, row_h):
            for k, (r, t) in enumerate(row):
                cx = x + k * (colw + 14)
                pg.text(cx, y + asc(12.5), r, "Barlow-B", 12.5, INK); draw_rich(pg, plain(t), cx + 30, y, colw - 30)
            y += h
        y += 3
        for n in notes: y += draw_rich(pg, n, x, y, W) + 3
    blocks.append((eh, encounters))
    return blocks

# --------------------------------------------------------------------------------------------- enemy cards
def card(pg, m, x, top, w, h, badge, mini=False):
    pg.rect(x, top, w, h, fill="#F4F4F8" if mini else "#FFFFFF", stroke=INK, lw=2 if mini else 1.5, r=8)
    ix, iy, iw = x + 7, top + 2, w - 14
    if mini:
        bw = tw(badge, "Barlow-B", 12) + 10; pg.rect(ix, iy, bw, 18, fill=RED, r=9); pg.text(ix + bw / 2, iy + 13.2, badge, "Barlow-B", 12, "#FFFFFF", anchor="c")
    else:
        bw = 18; pg.circle(ix + 9, iy + 9, 9, fill=INK); pg.text(ix + 9, iy + 13.2, badge, "Barlow-B", 12, "#FFFFFF", anchor="c")
    name = m["name"].upper(); nx = ix + bw + 5
    while tw(name, "Bungee", 12) > iw - bw - 5 and len(name) > 3: name = name[:-2] + "\u2026"
    pg.text(nx, iy + 13.5, name, "Bungee", 12, INK)
    draw_stats(pg, m, ix, iy + 21, iw, 13)
    fy = top + h - 3 - 18                                                     # footer pinned to the bottom
    gw = pill(pg, x + w - 7 - (tw(f"{m['reward']} gold", "Barlow-B", 12) + 12), fy, f"{m['reward']} gold", GOLD_B, GOLD_T)
    cx = ix
    for k in m.get("keywords", []): cx += chip(pg, cx, fy, k) + 3

def stat_widths(m, vsize):
    hp, wk = str(m["hp"]), weak(m["weak"])
    return (max(tw("HP", "Barlow-SB", 12, 0.5), tw(hp, "Barlow-B", vsize)), max(tw("WEAK", "Barlow-SB", 12, 0.5), tw(wk, "Barlow-B", vsize)))

def draw_atk(pg, x, base, attacks, vsize):
    cx = x
    for txt, ch in atk_parts(attacks):
        if txt: cx += pg.text(cx, base, txt, "Barlow-B", vsize, INK)
        if ch: cx += chip(pg, cx, base - vsize * 0.95, ch, h=17, inline=True)
    return cx - x

def draw_stats(pg, m, x, top, w, vsize, gap=10):
    c1, c3 = stat_widths(m, vsize)
    xs = (x, x + c1 + gap, x + w - c3)
    for xx, lab in zip(xs, ("HP", "ATK", "WEAK")): pg.text(xx, top + 10, lab, "Barlow-SB", 12, MUTED, cs=0.5)
    vb = top + 13 + vsize * 0.95
    pg.text(xs[0], vb, str(m["hp"]), "Barlow-B", vsize, INK)
    draw_atk(pg, xs[1], vb, m["attacks"], vsize)
    pg.text(xs[2], vb, weak(m["weak"]), "Barlow-B", vsize, INK)

def banner(pg, x, top, h, text, fill):
    pg.rect(x, top, 18, h, fill=fill)
    c = pg.c; c.saveState(); c.translate(pg._x(x + 9 + 4.3), pg._y(top + h / 2)); c.rotate(90)
    t = c.beginText(-tw(text, "Barlow-B", 12, 1.5) * PX / 2, 0); t.setFont("Barlow-B", 12 * PX); t.setCharSpace(1.5 * PX); t.setFillColor(HexColor("#FFFFFF")); t.textOut(text); c.drawText(t); c.restoreState()

# --------------------------------------------------------------------------------------------- right column
def right_column(pg, g, X, TOP, W, BOTTOM):
    y = TOP
    y += section_head(pg, X, y, W, "ENEMIES", "Minions: d6 each \u00b7 H = heavy \u00b7 Weak = squares on your grid", lw=1.5) + 4
    gx, gw = X + 22, W - 22; cw = (gw - 8) / 3; ch = 70
    banner(pg, X, y, 2 * ch + 4, "MINIONS", INK)
    for i, m in enumerate(g["minions"]):
        r, k = divmod(i, 3); card(pg, m, gx + k * (cw + 4), y + r * (ch + 4), cw, ch, str(i + 1))
    y += 2 * ch + 4 + 4
    mh = 72
    banner(pg, X, y, mh, "MINIBOSSES", RED)
    for k, (m, rng) in enumerate(zip(g["minibosses"], ("1-2", "3-4", "5-6"))): card(pg, m, gx + k * (cw + 4), y, cw, mh, rng, mini=True)
    y += mh + 4
    # danger + fuse
    pg.text(X, y + 14, "DANGER", "Bungee", 14, INK)
    pg.text(X + tw("DANGER", "Bungee", 14) + 10, y + 13, "+1 per interaction, +2 in a 2-pip quadrant. Last box filled: the boss comes on the next roll.", "Barlow", 12.5, INK)
    ty = y + 21; m_f = re.match(r"Danger (\d+) or more", g["fuse"]); lit = int(m_f.group(1)) if m_f else None
    for i in range(1, g["cap"] + 1):
        bx = X + (i - 1) * 19; red = lit is not None and i >= lit
        pg.rect(bx, ty, 17, 20, fill=RED if red else None, stroke=RED if red else INK, lw=1.5, r=4)
        pg.text(bx + 8.5, ty + 14.5, str(i), "Barlow-B", 12, "#FFFFFF" if red else MUTED, anchor="c")
    note = ([("double 1 or 6 brings the boss when ", "Barlow", 12.5, INK), ("RED", "Barlow-B", 12.5, "#DC2626")] if lit is not None else
            [("Fuse: ", "Barlow-B", 12.5, RED), (typo(g["fuse"]) + ". Then double 1 or 6 brings the boss.", "Barlow", 12.5, INK)])
    nw = 120 if lit is not None else W - g["cap"] * 19 - 10
    lines = wrap_rich(note, nw); ly = ty + (20 - len(lines) * 15) / 2
    for ln in lines:
        lw_ = sum(tw(p, f, s) for p, f, s, c in ln); cx = X + W - lw_
        for p, f, s, c in ln: cx += pg.text(cx, ly + asc(12.5), p, f, s, c)
        ly += 15
    y = ty + max(20, len(lines) * 15) + 3; pg.line(X, y, X + W, y, INK, 1.5); y += 4
    # boss
    b = g["boss"]; bx, bw = X, W
    phase_rows = max(1, max(len(b["phase2"]), len(b["phase3"])))
    bh = 5 + 34 + 4 + 14 + 20 * 1 + 4 + 22 + 6
    pg.rect(bx, y, bw, bh, stroke=INK, lw=2.5, r=10)
    ix, iy, iw = bx + 10, y + 5, bw - 20
    pw = tw("BOSS", "Barlow-B", 12, 1) + 14; pg.rect(ix, iy + 7, pw, 20, fill=RED, r=10); pg.text(ix + pw / 2, iy + 21.3, "BOSS", "Barlow-B", 12, "#FFFFFF", anchor="c", cs=1)
    c1, c3 = stat_widths(b, 14); atkw = sum(tw(t, "Barlow-B", 14) + (tw(c, "Barlow-B", 12, 0.3) + 8 if c else 0) for t, c in atk_parts(b["attacks"]))
    sw = c1 + 14 + max(atkw, tw("ATK", "Barlow-SB", 12, 0.5)) + 14 + c3; sx = ix + iw - sw
    name = typo(b["name"]).upper(); avail = sx - (ix + pw + 8) - 8
    while tw(name, "Bungee", 18) > avail and len(name) > 3: name = name[:-2] + "\u2026"
    pg.text(ix + pw + 8, iy + 23, name, "Bungee", 18, RED)
    for xx, lab in zip((sx, sx + c1 + 14, sx + sw - c3), ("HP", "ATK", "WEAK")): pg.text(xx, iy + 11, lab, "Barlow-SB", 12, MUTED, cs=0.5)
    vb = iy + 29
    pg.text(sx, vb, str(b["hp"]), "Barlow-B", 14, INK); draw_atk(pg, sx + c1 + 14, vb, b["attacks"], 14); pg.text(sx + sw - c3, vb, weak(b["weak"]), "Barlow-B", 14, INK)
    py = iy + 38; pg.line(ix, py, ix + iw, py, LINE, 1); py += 3
    t2, t3 = b["thresholds"]; half = (iw - 14) / 2
    for k, (lab, mods) in enumerate(((f"PHASE 2 \u00b7 {t2} HP OR LESS", b["phase2"]), (f"PHASE 3 \u00b7 {t3} HP OR LESS", b["phase3"]))):
        px = ix + k * (half + 14); pg.text(px, py + 10, lab, "Barlow-SB", 12, MUTED, cs=0.5); cx = px
        for mod in mods: cx += chip(pg, cx, py + 14, module_label(mod["name"])) + 3
    fy = y + bh - 6 - 18
    h = b.get("henchmen", {}); n, mm = h.get("minions", 0), h.get("minibosses", 0)
    if n or mm: chip(pg, ix, fy, f"Rally {n}" + (f"({mm})" if mm else ""))
    gt = f"{b['reward']} gold"; pill(pg, ix + iw - (tw(gt, "Barlow-B", 12) + 12), fy, gt, GOLD_B, GOLD_T)
    y += bh + 4
    # shop (pinned to bottom)
    shop_h = 22 + 3 + 2 * 32 + 2 + 16
    sy = BOTTOM - shop_h
    # treasure + NPC lists fill the space between
    half = (W - 12) / 2
    tre = [plain(typo(t)) for t in g["treasure"]]
    def npc_segs(t):
        t = typo(t); q = t.startswith("Q|"); body = t[2:] if q else t
        m = re.search(r"(Q\d)?\[_,_\]", body); segs = [("Q ", "Barlow-B", 12.5, INK)] if q else []
        if m: segs += [(body[:m.start()], "Barlow", 12.5, INK), (m.group(0), "Barlow-B", 12.5, INK), (body[m.end():], "Barlow", 12.5, INK)]
        else: segs += [(body, "Barlow", 12.5, INK)]
        return [s for s in segs if s[0]]
    npcs = [npc_segs(t) for t in g["npc_pool"]]
    for k, (title, note, items) in enumerate((("TREASURE", "Chest: d6, then 7+ in order", tre), ("NPCS", "Meet: d6, then 7+ in order", npcs))):
        lx = X + k * (half + 12); ly = y + section_head(pg, lx, y, half, title, note) + 2
        for i, segs in enumerate(items):
            pg.text(lx, ly + asc(12.5), str(i + 1), "Barlow-B", 12.5, INK); ly += draw_rich(pg, segs, lx + 17, ly, half - 17) + 2
        if k == 1 and g.get("quest_pay") and any(t.startswith("Q|") for t in g["npc_pool"]):
            bands, lo = [], 1                                   # this scenario's quest pay table
            for lim, _ in g["quest_pay"]: bands.append(f"{lo}-{lim}" if lim else f"{lo}+"); lo = (lim or 0) + 1
            pays = " / ".join(str(x) for _, x in g["quest_pay"])
            draw_rich(pg, [("Q", "Barlow-B", 12.5, INK), (" quests pay ", "Barlow", 12.5, INK2), (pays + " gold", "Barlow-B", 12.5, INK),
                           (" for " + " / ".join(bands) + " cells away.", "Barlow", 12.5, INK2)], lx, ly + 4, half)
    sy2 = sy
    ny = sy2 + section_head(pg, X, sy2, W, "SHOPKEEPER", f"$ = {g['price'][1]}, $$ = {g['price'][2]}, $$$ = {g['price'][3]} gold \u00b7 free to visit") + 3
    third = (W - 20) / 3
    for i, (name, tier, text) in enumerate(g["shop"]):
        r, k = divmod(i, 3); sx2 = X + k * (third + 10); top = ny + r * 32
        checkbox(pg, sx2, top + 2); w1 = pg.text(sx2 + 19, top + asc(12.5), typo(name) + " ", "Barlow-B", 12.5, INK)
        pg.text(sx2 + 19 + w1, top + asc(12.5), "$" * tier, "Barlow-B", 12.5, VIO); pg.text(sx2 + 19, top + 15 + asc(12), typo(text), "Barlow", 12, INK2)
    trader = ", ".join(f"{typo(s[0])} {'$' * s[1]}" for s in g["trader"])
    draw_rich(pg, [("Wandering trader: ", "Barlow-B", 12.5, INK), (trader, "Barlow", 12.5, INK)], X, ny + 2 * 32 + 2, W)

# --------------------------------------------------------------------------------------------- page
def render_page(c, g):
    pg = Page(c); M, LW, GAP = 36, 432, 24
    blocks = left_blocks(g, LW)
    free = (PH - 2 * M) - sum(h for h, _ in blocks); gap = free / (len(blocks) - 1)
    y = M
    for h, draw in blocks: draw(pg, M, y); y += h + gap
    right_column(pg, g, M + LW + GAP, M, PW - 2 * M - LW - GAP, PH - M)
    pg.text(PW - 36, PH - 22, f"Seed: {g['code']}", "Barlow-SB", 12, INK2, anchor="r")
    c.showPage()

def render(codes, out, cap=None, hp_scale=1.0, dmg_add=0, potions=None, content=None):
    _fonts()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    c = rl_canvas.Canvas(out, pagesize=landscape(letter))
    c.setTitle("One Sheet Wonder scenarios: " + ", ".join(codes)); c.setAuthor("One Sheet Wonder generator")
    for code in codes: render_page(c, scenario(code, cap, hp_scale, dmg_add, potions, content if len(codes) == 1 else None))
    c.save(); return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("codes", nargs="+"); ap.add_argument("-o", "--out")
    ap.add_argument("--cap", type=int); ap.add_argument("--hp-scale", type=float, default=1.0)
    ap.add_argument("--dmg-add", type=int, default=0); ap.add_argument("--potions", type=int)
    a = ap.parse_args()
    out = a.out or os.path.join(os.getcwd(), "sheets", (a.codes[0] if len(a.codes) == 1 else f"{len(a.codes)}-scenarios") + ".pdf")
    print(render(a.codes, out, a.cap, a.hp_scale, a.dmg_add, a.potions))
