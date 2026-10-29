"""Keyword board resolver for the combat engine.

Board keywords (they change how the player's attack plays out) are merged into one spec:
    Daze                 two pairs also fumble past the danger line
    Pin                  -1 runner (each source of Pin removes one)
    Trapper X            X traps per attack
    Lock [cols]          those columns cannot have runners
    Grapple [cols]       wilds (2/12 pairs and surges) cannot move runners there; bare = every column
    Taunt                guard columns D-F deal 1 per square and give no guard
    Bulk X [cols]        those columns deal X less per square (min 0)
    Fractured X [cols]   those columns deal X more per square
    Plate [cols]         only those columns deal damage
    Exposed X            the weak point is X rows lower
A spec that equals a legacy mode reuses its d4/ data; any other spec is generated with cs5 on first use and cached.
"""
import os, re, json, subprocess, hashlib, tempfile
try: import fcntl            # macOS / Linux: lets parallel workers share on-demand data safely
except ImportError: fcntl = None
HERE = os.path.dirname(os.path.abspath(__file__))
D4 = os.path.join(HERE, "d4"); SPECS = os.path.join(D4, "kwspecs")

def simulator():
    """The attack simulator binary: $OSW_CS5, else the Rust build, else the C++ build (identical output)."""
    for p in (os.environ.get("OSW_CS5"), os.path.join(HERE, "cs5rs", "target", "release", "cs5"), os.path.join(HERE, "cs5")):
        if p and os.path.exists(p): return p
    raise FileNotFoundError("no simulator: run `cargo build --release` in cs5rs/ (or set OSW_CS5)")
COLS = "ABCDEFGHI"
BASE_DMG = (2, 1, 1, 0, 0, 0, 1, 1, 2)
WEAKARGS = {"w311": (0, 6), "w410": (1, 5), "w59": (2, 6)}

def parse(kw):
    """'Bulk 1 A,I' -> ('Bulk', 1, [0, 8]); 'Lock D,F' -> ('Lock', None, [3, 5]); 'Daze' -> ('Daze', None, [])."""
    toks = kw.split(); name = toks[0]; x = None; cols = []
    i = 1
    while i < len(toks) and not re.fullmatch(r"[0-9]+", toks[i]) and not re.fullmatch(r"[A-I](,[A-I])*", toks[i]):
        name += " " + toks[i]; i += 1
    for t in toks[i:]:
        if re.fullmatch(r"[0-9]+", t): x = int(t)
        elif re.fullmatch(r"[A-I](,[A-I])*", t): cols = [COLS.index(c) for c in t.split(",")]
    return name, x, cols

def spec_for(effects, runners=3, hero=None):
    s = dict(W=1, R=runners, FM=3, NH=0, LOCK=0, GRAP=0, DMG=list(BASE_DMG), GUARD=4, EXPO=0)
    bulk = [0] * 9; frac = [0] * 9; plate = None; taunt = False
    for kw in effects:
        name, x, cols = parse(kw)
        if name == "Daze": s["FM"] = 1
        elif name == "Pin": s["R"] = max(1, s["R"] - 1)
        elif name == "Trapper": s["NH"] = max(s["NH"], x or 2)
        elif name == "Lock": s["LOCK"] |= sum(1 << c for c in cols)
        elif name == "Grapple": s["GRAP"] |= (sum(1 << c for c in cols) if cols else 511)
        elif name == "Taunt": taunt = True
        elif name == "Bulk":
            for c in cols: bulk[c] += (x or 1)
        elif name == "Fractured":
            for c in cols: frac[c] += (x or 1)
        elif name == "Plate": plate = set(cols)
        elif name == "Exposed": s["EXPO"] = max(s["EXPO"], x or 2)
    d = list(BASE_DMG)
    if taunt:
        for c in (3, 4, 5): d[c] = 1
        s["GUARD"] = 0
    if plate is not None: d = [d[c] if c in plate else 0 for c in range(9)]
    s["DMG"] = [max(0, d[c] - bulk[c] + frac[c]) for c in range(9)]
    s["BULK"] = bulk
    if hero:                                          # a leveled hero: taller grid, printed layout, class mechanics
        opts = sorted(hero.get("opts", ()))
        if hero.get("hb2"):                           # Heavy Blows II: every column that deals damage, +1 from row 6
            opts.append("sqadd=" + ";".join(f"{c}:6:1" for c in range(9) if s["DMG"][c] > 0))
        s.update(HERO=1, SIM=_sim_stamp(), H=hero.get("H", 9), FAT=hero.get("fat", 4), WSTEPS=hero.get("wsteps", 2), WCOLM=hero.get("wcolm", 2),
                 RR=hero.get("rr", 0), OPTS=opts)
    return s

_STAMP = None
def _sim_stamp():
    """Fingerprint of the attack simulator's source: change the simulator, get fresh hero datasets (no stale reuse)."""
    global _STAMP
    if _STAMP is None:
        src = os.path.join(HERE, "cs5rs", "src", "main.rs")
        _STAMP = hashlib.sha1(open(src, "rb").read()).hexdigest()[:8] if os.path.exists(src) else "none"
    return _STAMP

def hero_rarities(H):
    """Rarity of each bit of a hero attack's bonus mask: layout_hero.txt squares in (column, row) order up to row H."""
    R = {1: "C", 2: "U", 3: "R", 4: "L", 6: "M"}
    rows = [tuple(map(int, l.split())) for l in open(os.path.join(HERE, "layout_hero.txt")) if l.strip()]
    return [R[t] for c, r, t in sorted(rows) if t in R and r <= H]

def _legacy(s):
    core = {k: s[k] for k in ("W", "R", "FM", "NH", "LOCK", "GRAP", "GUARD", "EXPO")}; d = tuple(s["DMG"])
    plain = dict(W=1, R=3, FM=3, NH=0, LOCK=0, GRAP=0, GUARD=4, EXPO=0)
    def same(**kw): x = dict(plain); x.update(kw); return core == x
    if d == BASE_DMG:
        if same(): return "normal"
        if same(FM=1): return "daze"
        if same(NH=2): return "traps"
        if same(FM=1, NH=2): return "dazetraps"
        if same(R=2): return "pin"
        if same(EXPO=2): return "exposed2"
    if same():
        if d == (1, 1, 1, 0, 0, 0, 1, 1, 1): return "thickhide"
        if d == (2, 0, 0, 0, 0, 0, 0, 0, 2): return "plate"
        if d == (2, 1, 1, 1, 1, 1, 1, 1, 2): return "cracked"
    return None

def _atomic_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path)); os.write(fd, text.encode()); os.close(fd); os.replace(tmp, path)

class _Lock:
    """Exclusive per-file lock (no-op where fcntl is unavailable)."""
    def __init__(self, name): os.makedirs(os.path.join(D4, "locks"), exist_ok=True); self.p = os.path.join(D4, "locks", name + ".lock")
    def __enter__(self):
        self.f = open(self.p, "w")
        if fcntl: fcntl.flock(self.f, fcntl.LOCK_EX)
        return self
    def __exit__(self, *a):
        if fcntl: fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()

def _spec(name):
    p = os.path.join(SPECS, name + ".json")
    if os.path.exists(p): return json.load(open(p))
    old = os.path.join(D4, "kwspecs.json")          # registry format used before parallel support
    if os.path.exists(old): return json.load(open(old))[name]
    raise KeyError(name)

def mode_for(effects, runners=3, hero=None):
    """Return (mode name for engine keys, damage table, bulk-by-column) for a set of board keywords."""
    s = spec_for(effects, runners, hero)
    name = None if s.get("HERO") else _legacy(s)
    if name is None:
        name = "kw" + hashlib.sha1(json.dumps(s, sort_keys=True).encode()).hexdigest()[:10]
        p = os.path.join(SPECS, name + ".json")
        if not os.path.exists(p): _atomic_write(p, json.dumps(s, sort_keys=True))   # one file per spec: safe in parallel
    return name, s["DMG"], s["BULK"]

def generate(stem):
    """Generate d4/<stem>.npy for a kw mode: stem = kwXXXX_<weak>_a<0|1>_g<0|1|2>[_r1]."""
    import numpy as np
    m = re.fullmatch(r"(kw[0-9a-f]+)_(w311|w410|w59)_a([01])_g([012])(_r1)?", stem)
    if not m: raise FileNotFoundError(stem)
    s = _spec(m.group(1)); weak, aim, g, r1 = m.group(2), int(m.group(3)), int(m.group(4)), bool(m.group(5))
    final = os.path.join(D4, stem + ".npy")
    with _Lock(stem):                                  # one worker builds a file; the others wait, then reuse it
        if os.path.exists(final): return
        C, WR = WEAKARGS[weak]; WR -= s["EXPO"]
        n = 15000 if r1 else 25000; WV = 12 if aim else 0; WV2 = 24 if aim else 0
        hero = s.get("HERO"); n = 4000 if hero else n
        hm, ev = (2, 0.5) if s["NH"] else (1, 0)
        fd, out = tempfile.mkstemp(dir=D4, suffix=".txt"); os.close(fd)
        args = [simulator(), n, 0, 0, os.path.join(HERE, "layout_hero.txt" if hero else "layout_plus.txt"), 1, 1000, 0, 3, 1, 0, 6,
                s.get("H", 9), s["W"], s["R"], s.get("FAT", 4), s["FM"], 1, 0, 0,
                s["GUARD"], g, 3, C, WR, 2, WV, s["NH"], 8, out, hm, ev, 2, WV2, 1, s.get("WCOLM", 2), 0, s.get("WSTEPS", 2),
                s.get("RR", 1 if r1 else 0), s["LOCK"], s["GRAP"]] + s["DMG"]
        if hero: args += ["3,5,6,8,9,8,6,5,3"] + list(s.get("OPTS", []))
        subprocess.run([str(a) for a in args], check=True, stdout=subprocess.DEVNULL)
        fd, tmp = tempfile.mkstemp(dir=D4, suffix=".npy"); os.close(fd)
        np.save(tmp, np.loadtxt(out).astype(np.int64)); os.remove(out); os.replace(tmp, final)
