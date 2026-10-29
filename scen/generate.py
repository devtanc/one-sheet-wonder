"""One Sheet Wonder scenario generator, engine version 01 (draft).

generate("0105-1a2b-3c4d-?") -> dict with everything the scenario sheet prints. Follows the pipeline order in
the Scenario Sheet Spec. DD = 01-09: band = (DD-1)//3 + 1 (Low/Mid/High), difficulty = Easy/Normal/Hard.
"""
import re, copy
import json, sys
from collections import deque
import pools as P

HEX = "0123456789abcdef"

def check_char(payload):
    digits = payload.replace("-", "").lower()
    total, factor = 0, 2
    for c in reversed(digits):
        a = factor * HEX.index(c); total += a // 16 + a % 16; factor = 3 - factor
    return HEX[(16 - total % 16) % 16]

def make_code(vv, dd, seed_hex):
    s = f"{vv:02d}{dd:02d}{seed_hex.lower()}"
    return f"{s[0:4]}-{s[4:8]}-{s[8:12]}-{check_char(s)}"

class Rng:
    """mulberry32: tiny, fast and identical in JavaScript."""
    def __init__(self, seed): self.a = seed & 0xFFFFFFFF
    def random(self):
        self.a = (self.a + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    def randint(self, lo, hi): return lo + int(self.random() * (hi - lo + 1))
    def choice(self, seq): return seq[int(self.random() * len(seq))]
    def shuffle(self, seq):
        seq = list(seq)
        for i in range(len(seq) - 1, 0, -1):
            j = int(self.random() * (i + 1)); seq[i], seq[j] = seq[j], seq[i]
        return seq
    def weighted(self, items, weights):
        tot = sum(weights); r = self.random() * tot
        for it, w in zip(items, weights):
            r -= w
            if r < 0: return it
        return items[-1]

QB = {1: (1, 6, 1, 6), 2: (7, 12, 1, 6), 3: (1, 6, 7, 12), 4: (7, 12, 7, 12)}
def quad(x, y): return 1 + (x > 6) + 2 * (y > 6)
CELLS = [(x, y) for y in range(1, 13) for x in range(1, 13)]
def nbrs(c):
    x, y = c
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if 1 <= x + dx <= 12 and 1 <= y + dy <= 12: yield (x + dx, y + dy)
def edge(a, b): return (a, b) if a < b else (b, a)

def generate(code):
    raw = code.replace("-", "").lower()
    assert len(raw) == 13 and check_char(raw[:12]) == raw[12], "bad check character"
    vv, dd, seed = int(raw[0:2]), int(raw[2:4]), int(raw[4:12], 16)
    band = (dd - 1) // 3 + 1; diff = ["Easy", "Normal", "Hard"][(dd - 1) % 3]
    D = P.DIFFICULTY[diff]; R = Rng(seed)

    # 2. quadrant danger
    total = R.randint(*D["danger_total"]); danger = {1: 0, 2: 0, 3: 0, 4: 0}
    for _ in range(total):
        q = R.choice([q for q in danger if danger[q] < 2]); danger[q] += 1

    # 3. blocks
    blocks = []; used = set()
    for q in (1, 2, 3, 4):
        r = R.random(); n = 0 if r < 0.375 else (1 if r < 0.75 else 2)
        x0, x1, y0, y1 = QB[q]
        for _ in range(n):
            size = 2 if R.random() < 0.75 else 3
            kind = "open" if R.random() < 0.6 else "closed"
            for _try in range(30):
                bx = R.randint(x0, x1 - size + 1); by = R.randint(y0, y1 - size + 1)
                cells = {(bx + i, by + j) for i in range(size) for j in range(size)}
                if not cells & used:
                    used |= cells; blocks.append(dict(q=q, x=bx, y=by, size=size, kind=kind, cells=cells)); break

    # 4. reachability: drop closed blocks (last first) until every passable cell connects
    def passable_set():
        closed = set().union(*[b["cells"] for b in blocks if b["kind"] == "closed"]) if blocks else set()
        return {c for c in CELLS if c not in closed}
    def connected(ps):
        start = next(iter(ps)); seen = {start}; dq = deque([start])
        while dq:
            c = dq.popleft()
            for n in nbrs(c):
                if n in ps and n not in seen: seen.add(n); dq.append(n)
        return len(seen) == len(ps)
    while not connected(passable_set()):
        idx = max(i for i, b in enumerate(blocks) if b["kind"] == "closed"); blocks.pop(idx)
    passable = passable_set()

    # 5. maze: rooms are single nodes; carve a spanning tree, then knock out loop walls
    node_of = {}
    for i, b in enumerate(blocks):
        if b["kind"] == "open":
            for c in b["cells"]: node_of[c] = ("room", i)
    for c in passable: node_of.setdefault(c, c)
    adj = {}
    for c in passable:
        for n in nbrs(c):
            if n in passable and node_of[c] != node_of[n]:
                adj.setdefault(node_of[c], {}).setdefault(node_of[n], []).append(edge(c, n))
    opened = set(); nodes = sorted(adj.keys(), key=str)
    start = R.choice(nodes); visited = {start}; stack = [start]
    while stack:
        cur = stack[-1]
        opts = sorted([n for n in adj[cur] if n not in visited], key=str)
        if not opts: stack.pop(); continue
        nxt = R.choice(opts); opened.add(R.choice(sorted(set(adj[cur][nxt])))); visited.add(nxt); stack.append(nxt)
    all_walls = sorted({e for a in adj for b in adj[a] for e in adj[a][b]})
    remaining = [e for e in all_walls if e not in opened]
    for e in R.shuffle(remaining)[: int(round(len(remaining) * D["loops"]))]: opened.add(e)
    walls = [e for e in all_walls if e not in opened]

    # 6. one start per quadrant (outside blocks)
    in_block = set().union(*[b["cells"] for b in blocks]) if blocks else set()
    starts = {}
    for q in (1, 2, 3, 4):
        cand = [c for c in CELLS if quad(*c) == q and c in passable and c not in in_block]
        starts[q] = R.choice(cand)

    # 7. shopkeeper, chests and NPCs, weighted by quadrant danger
    occupied = set(starts.values()); places = []
    def place(kind, weights):
        free = {q: [c for c in CELLS if quad(*c) == q and c in passable and c not in occupied] for q in (1, 2, 3, 4)}
        qs = [q for q in (1, 2, 3, 4) if free[q]]
        q = R.weighted(qs, [weights[danger[q]] for q in qs]); c = R.choice(free[q])
        occupied.add(c); places.append(dict(kind=kind, x=c[0], y=c[1]))
    place("shop", [1, 3, 3])
    n_chests = 1 if R.random() < 0.5 else 2
    for _ in range(n_chests): place("chest", [1, 2, 4])
    n_npcs = R.randint(1, 4)
    for _ in range(n_npcs): place("npc", [4, 3, 1])
    for i, p in enumerate([p for p in places if p["kind"] == "npc"]): p["n"] = i + 1
    for i, p in enumerate([p for p in places if p["kind"] == "chest"]): p["n"] = i + 1

    # 8. fuse and hard cap
    fuses = [f for f in P.FUSES if f[1] in D["fuses"]
             and not (f[0] == "Opened 2 chests" and n_chests < 2) and not (f[0] == "Talked to 2 NPCs" and n_npcs < 2)]
    fuse = R.choice(fuses)[0]; cap = D["cap"]

    # 9. enemy pool (Mid/Normal = listed numbers; other bands scale here once tuned)
    minions = R.shuffle(P.MINIONS)[:6]
    minis = sorted(R.shuffle(P.MINIBOSSES)[:3], key=lambda m: m["hp"])
    boss = dict(R.choice(P.BOSSES)); boss["hp"] = P.BOSS_HP; boss["reward"] = P.BOSS_REWARD
    # Henchmen come from their own stream off the same seed, so adding them reshuffles nothing else.
    RH = Rng(seed ^ 0x9E3779B9)
    n_min_h, n_mini_h, _w, h_hp = RH.weighted(P.BOSS_HENCHMEN, [h[2] for h in P.BOSS_HENCHMEN])
    boss["henchmen"] = dict(minions=n_min_h, minibosses=n_mini_h); boss["hp"] = h_hp
    wp = R.choice([("3·11", 6), ("4·10", 5), ("5·9", 6)]); boss["weak"] = wp
    def d20_rarity(table):
        r = R.randint(1, 20)
        for lim, rar in table:
            if r <= lim: return rar
    def pick(mods, table):
        rar = d20_rarity(table); names = sorted(k for k, v in mods.items() if v[0] == rar); return R.choice(names)
    TW = [(10, "C"), (16, "U"), (19, "R"), (20, "L")]; PR = [(11, "C"), (17, "U"), (20, "R")]
    def pressure_for(twist):
        while True:
            p = pick(P.PRESSURES, PR)
            if twist == "Pin": return None
            if twist in ("Jinx", "Plate") and p in ("Fortify", "Regenerate"): continue
            return p
    t2 = pick(P.TWISTS, TW); p2 = pressure_for(t2) if R.randint(1, 6) >= 4 else None
    if R.randint(1, 6) <= 4:
        o3 = "Exposed" if R.randint(1, 20) <= 18 else "Cracked Shell"; p3 = pick(P.PRESSURES, PR); t3 = None
    else:
        o3 = None; t3 = pick(P.TWISTS, TW); p3 = pressure_for(t3)
    def mod(name, table): return dict(name=name, text=table[name][1]) if name else None
    boss["phase2"] = [m for m in (mod(t2, P.TWISTS), mod(p2, P.PRESSURES)) if m]
    boss["phase3"] = [m for m in (mod(o3, P.OPENINGS), mod(t3, P.TWISTS), mod(p3, P.PRESSURES)) if m]
    # Small variation around the tuned numbers, from its own stream off the seed (nothing else reshuffles).
    J = P.JITTER; RJ = Rng(seed ^ 0x4A495454)
    def jit_hp(hp, f): return RJ.randint(max(1, int(round(hp * (1 - f)))), int(round(hp * (1 + f))))
    def jit_attacks(at):
        out = [tuple([max(1, a[0] + RJ.randint(-J["attack"], J["attack"])) if a[0] else 0] + list(a[1:])) for a in at]
        normals = [a[0] for a in out if not a[1] and a[0]]
        if normals:                                   # heavy attacks stay clearly heavier than normal ones
            out = [tuple([max(a[0], max(normals) + 2)] + list(a[1:])) if a[1] and a[0] else a for a in out]
        return out
    def jit_enemy(m):
        m = copy.deepcopy(m); m["hp"] = jit_hp(m["hp"], J["enemy_hp"]); m["attacks"] = jit_attacks(m["attacks"])
        m["reward"] = max(1, m["reward"] + RJ.randint(-J["reward"], J["reward"])); return m
    minions = [jit_enemy(m) for m in minions]
    minis = sorted((jit_enemy(m) for m in minis), key=lambda m: m["hp"])
    boss["hp"] = jit_hp(boss["hp"], J["boss_hp"]); boss["attacks"] = jit_attacks(boss["attacks"])
    boss["reward"] = max(1, boss["reward"] + RJ.randint(-J["boss_reward"], J["boss_reward"]))
    boss["thresholds"] = ((2 * boss["hp"]) // 3, boss["hp"] // 3)

    # 10. treasure pool, NPC pool, shop, trader
    def draw(pool, n):
        out, used_u = [], set()
        while len(out) < n:
            opts = [p for p in pool if not (p[2] and p[0] in used_u) and out.count(p[0]) < 2]
            e = R.weighted(opts, [p[1] for p in opts]); out.append(e[0])
            if e[2]: used_u.add(e[0])
        return out
    surprise = max(1, D["surprise"] + RJ.randint(-J["entry"], J["entry"]))
    def jit_text(t):                                  # "gain 4 gold", "take 4", "heal 5" -> +-1
        if "{s}" in t: return t
        return re.sub(r"\b(gain|take|heal) (\d+)", lambda m: f"{m.group(1)} {max(1, int(m.group(2)) + RJ.randint(-J['entry'], J['entry']))}", t)
    treasure = [jit_text(t).format(s=surprise) for t in draw(P.TREASURE, 6 + n_chests - 1)]
    npc_pool = [jit_text(t).format(s=surprise) for t in draw(P.NPCS, 6 + n_npcs - 1)]
    # Quest requests come from their own stream off the seed, so adding them reshuffles nothing else.
    quests = Rng(seed ^ 0x51ED270B).shuffle(P.QUESTS)
    npc_pool = [("Q|" + quests.pop(0)) if t == "Q|" else t for t in npc_pool]
    # Quest pay by distance: each scenario rolls its own table from its own stream (nothing else reshuffles).
    RQ = Rng(seed ^ 0x51554553); quest_pay, floor = [], 0
    for lim, lo, hi in P.QUEST_PAY_RANGE:
        gold = RQ.randint(max(lo, floor), max(hi, floor)); quest_pay.append((lim, gold)); floor = gold
    trap_dmg = max(1, P.TRAP_DAMAGE + RJ.randint(-J["entry"], J["entry"]))
    encounters = [(r, re.sub(r"take \d+", f"take {trap_dmg}", t) if t.startswith("Trap") else t) for r, t in P.ENCOUNTERS]
    price, floor = {}, 0
    for tier in sorted(P.PRICE):                      # each tier still costs more than the one below
        price[tier] = max(floor + 1, P.PRICE[tier] + RJ.randint(-J["price"], J["price"])); floor = price[tier]
    potion = [s for s in P.SHOP if s[0] == "Potion"][0]
    shop = [potion] + R.shuffle([s for s in P.SHOP if s[0] != "Potion"])[:5]
    shop = sorted(shop, key=lambda s: (s[1], s[0]))
    trader = sorted(R.shuffle([s for s in P.SHOP if s[0] not in P.PERMANENT])[:3], key=lambda s: (s[1], s[0]))

    # 11. expected run economy: movement rolls before the danger cap, and money earned along the way
    def roll_outcomes():
        """Yield (probability, money, danger_added) for one movement roll, averaged over the four quadrants."""
        avg_min = sum(m["reward"] for m in minions) / 6; avg_mini = sum(m["reward"] for m in minis) / 3
        for q in (1, 2, 3, 4):
            dq = danger[q]; step = 2 if dq == 2 else 1
            for a in range(1, 7):
                for b in range(1, 7):
                    p = 1 / 144
                    if a == b: yield p, avg_mini, step; continue
                    s = a + b + dq - (P.NOTHING_MAX - 4)
                    if a + b + dq <= P.NOTHING_MAX: yield p, 0, 0
                    elif s == 5: yield p, 0.5 * P.DIG_GOLD, step            # hidden treasure: about half succeed, ~2 money
                    elif s in (6, 9): yield p, 0, step             # trader, trap
                    elif s == 7: yield p, (2 * avg_min + 2 * 2 * avg_min + 2 * P.ESCORT_PAY) / 6, step   # villager
                    elif s == 8: yield p, avg_min, step
                    elif s == 10: yield p, 2 * avg_min, step
                    elif s in (11, 12): yield p, 3 * avg_min, step
                    else: yield p, avg_mini + avg_min, step
    outs = list(roll_outcomes())
    money_per_roll = sum(p * m for p, m, _ in outs); danger_per_roll = sum(p * d for p, _, d in outs)
    fixed_danger = n_chests + n_npcs + P.SHOP_DANGER         # opening chests, meeting NPCs, shop visit
    rolls_cap = max(1.0, (cap - fixed_danger) / danger_per_roll)   # if the run lasted until the track fills
    # Fuse-aware estimate: once the fuse is lit, each roll can bring the boss (1-1/6-6, or any double).
    import re as _re
    p_boss = (6 if P.ANY_DOUBLE_BOSS else 2) / 36 * P.FUSE_STEER   # steering: players nudge dice into 1-1/6-6 with WIS
    def dang(r): return danger_per_roll * r + fixed_danger * min(1.0, r / 6)   # interactions mostly happen early
    fm = _re.match(r"Danger (\d+)", fuse)
    if fm: t_fuse = next((r for r in range(0, 400) if dang(r) >= int(fm.group(1))), 400)
    else: t_fuse = {"Opened 2 chests": 5, "Talked to 2 NPCs": 4, "Bought anything from a shop": 3, "Visited all 4 quadrants": 7}.get(fuse, 5)
    r_cap = next((r for r in range(1, 400) if dang(r) >= cap), 400)
    surv, rolls_est = 1.0, 0.0
    for r in range(1, r_cap + 1):
        p_end = p_boss if r > t_fuse else 0.0
        rolls_est += surv * (1 - p_end); surv *= (1 - p_end)
    rolls_est = max(1.0, rolls_est)
    def money_in(text):
        m = [int(x) for x in __import__("re").findall(r"gain (\d+) gold", text)]
        return m[0] if m else 0
    money_est = (rolls_est * money_per_roll + n_chests * sum(money_in(t) for t in treasure) / len(treasure)
                 + n_npcs * sum(money_in(t) for t in npc_pool) / len(npc_pool) + boss["reward"])
    OF = P.OBJECTIVE_FIT
    money_goal = max(5, int(round(OF["gold"] * (money_est + P.START_MONEY))))

    # 12. objectives: feasible against this map, sized so each is met by about half of winning runs
    cells_est = max(10, int(round(OF["cells"] * (rolls_est + 2))))
    dmg_goal = max(10, int(round(OF["dmg_before_boss"] * rolls_est)))
    danger_goal = max(5, int(round(OF["danger_at_boss"] * cap)))
    restraint = [f"Take less than {dmg_goal} damage before the boss", f"Reach the boss at danger {danger_goal} or less"]
    n_min = max(2, int(round(OF["minions"] * rolls_est))); n_enc = max(3, int(round(OF["encounters"] * rolls_est)))
    npc_goal = 1 if n_npcs <= 1 else (2 if n_npcs <= 3 else 3)
    chest_goal = 2 if (n_chests >= 2 and rolls_est >= OF["long_chests"]) else 1
    pushers = [f"Open {chest_goal} chest{'s' if chest_goal > 1 else ''}",
               "Defeat 2 minibosses" if rolls_est >= OF["long_minis"] else "Defeat a miniboss",
               f"Complete {n_enc} encounters"] + ([f"Talk to {npc_goal} NPC{'s' if npc_goal > 1 else ''}"] if n_npcs else [])
    others = ["Visit all 4 quadrants", f"Buy {OF['buy']} items", f"Finish with {money_goal} or more gold", f"Defeat {n_min} minions",
              f"Travel {cells_est} cells"]
    objectives = [R.choice(restraint), R.choice(pushers)]
    rest = R.shuffle([o for o in pushers + others if o not in objectives])
    for o in rest:
        if len(objectives) == 5: break
        if o.startswith("Finish with") and any(x.startswith("Buy") for x in objectives): continue
        if o.startswith("Buy") and any(x.startswith("Finish with") for x in objectives): continue
        objectives.append(o)
    objectives = R.shuffle(objectives)

    return dict(code=code, version=vv, dd=dd, band=P.BANDS[band], difficulty=diff,
                danger=danger, blocks=[{k: v for k, v in b.items() if k != "cells"} for b in blocks],
                walls=walls, starts={q: list(c) for q, c in starts.items()}, places=places,
                fuse=fuse, cap=cap, minions=minions, minibosses=minis, boss=boss, treasure=treasure,
                npc_pool=npc_pool, quest_pay=quest_pay, shop=shop, trader=trader, objectives=objectives,
                encounters=encounters, trap_dmg=trap_dmg, price=price, money_est=round(money_est, 1), rolls_est=round(rolls_est, 1), rolls_cap=round(rolls_cap, 1), stranded=P.STRANDED,
                surprise=surprise, passable_count=len(passable))

if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else make_code(1, 5, "1a2b3c4d")
    print(json.dumps(generate(code), indent=1, default=list))
