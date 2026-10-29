"""Plays generated scenarios end to end: exploration on the scenario sheet + combat on the Warrior's attack grid.

Assumptions not fixed by the spec (flagged in the analysis):
- Warrior map stats STR +2, DEX 0, INT -1, WIS 0; a map stat roll succeeds on d6 + stat >= 4. WIS adjustments unused.
- Quest/escort rewards: 2 / 4 / 6 money for 1-5 / 6-10 / 11+ cells of travel; villager escort pays 3.
- Minor sheet effects (effect tiles, pocket upgrades, rumors, blessings, spare runners, map scraps, Cutpurse theft)
  are ignored; Weapon +1 = +1 damage per attack, Armor +1 = +1 guard per round.
"""
import random, copy, sys
from collections import deque, Counter
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__))); import osw_paths
import engine2
from engine2 import E, I, fight, draw_offers
from classcfg import CLASS_KNOBS
from statcfg import STATKNOBS
from generate import generate, quad, nbrs
import pools as PL

P0 = copy.deepcopy(engine2.P)
WEAK = {"3·11": "w311", "4·10": "w410", "5·9": "w59"}
TW = {"Iron Wall": "ironwall", "Shieldwall": "shieldwall", "Thick Hide": "thickhide", "Trapper": "traps", "Jinx": "jinx",
      "Plate": "plate", "Gatehouse": "gate678", "Daze": "daze", "Pin": "pin"}
PR = {"Doom": "doom", "Fortify": "fortify", "Regenerate": "regen", "Frenzy": "frenzy", "Haste": "haste", "Berserk": "berserk"}
OP = {"Exposed": "exposed", "Cracked Shell": "cracked"}
CLASS_STATS = {  # map stats as printed on the hero sheets
    "Warrior":   dict(STR=2, DEX=0,  INT=-1, WIS=0),
    "Knight":    dict(STR=2, DEX=-1, INT=0,  WIS=1),
    "Barbarian": dict(STR=2, DEX=1,  INT=-1, WIS=0),
    "Paladin":   dict(STR=2, DEX=-1, INT=0,  WIS=2),
    "Cavalier":  dict(STR=2, DEX=1,  INT=0,  WIS=0),
    "Berserker": dict(STR=2, DEX=2,  INT=-1, WIS=0),
    "Beastkin":  dict(STR=1, DEX=2,  INT=-1, WIS=1),
}
STATS = dict(CLASS_STATS["Warrior"])

def mk_enemy(e, boss=False):
    its = []
    for a in e["attacks"]:
        tag = a[2] if len(a) > 2 else ""
        its.append(I(a[0], a[1], {"p": "poison", "d": "daze", "g": "pin"}.get(tag), 0.5 if tag == "x" else 0.0))
    import re as _re
    kw = {(_re.match(r"^(.*?)(?: [0-9A-I,()]+)*$", k).group(1)) for k in e.get("keywords", [])}   # "Thick Hide A,I" -> "Thick Hide"
    if "Sunder" in kw:
        for it in its: it["pierce"] = 0.5
    if "Venom" in kw:
        for it in its: it["onhit"] = "poison"
    prof = "thickhide" if "Bulk" in kw else ("plate" if "Plate" in kw else None)
    mode = "traps" if "Trapper" in kw else ("daze" if "Daze" in kw else None)
    en = E(e["name"], e["hp"], its, weak=WEAK[e["weak"][0]], mode=mode, profile=prof, cover="Bodyguard" in kw, boss=boss)
    # keyword-engine view of the same enemy (used when P['KW'] is on)
    full = e.get("keywords", [])
    base = lambda k: _re.match(r"^(.*?)(?: [0-9A-I,()]+)*$", k).group(1)
    en.kwb = [k for k in full if base(k) in ("Daze", "Pin", "Trapper", "Lock", "Grapple", "Taunt")]
    en.kwt = [k for k in full if base(k) in ("Bulk", "Fractured", "Plate", "Exposed")]
    en.kwp = {base(k): k for k in full if base(k) in ("Frenzy", "Fortify", "Regen", "Haste", "Berserk")}
    en.thief = next((int(k.split()[1]) for k in full if k.startswith("Thief") and len(k.split()) > 1), 0)
    return en

RULES = dict(level=None, path=None, strategy="Tactical", offers=None, chests=True, npcs=True, shop=True, quests=True, chest_hp=15, avoid_d2="lowhp", quads="objective", ready_hp=(30, 22), kw=True, any_double=False, nothing_max=5, cap=None, shop_danger=0, smart=True, wis=3, boss_hp=None, start_money=6)   # 1-1/6-6 fuse, V4b otherwise

BRANCH = {"Knight": "Knight", "Barbarian": "Barbarian", "Paladin": "Knight", "Cavalier": "Knight", "Berserker": "Barbarian", "Beastkin": "Barbarian"}
FINALS = ("Paladin", "Cavalier", "Berserker", "Beastkin")

def hero_config(level, path=None):
    """A leveled Warrior: grid height, Heavy Blows II, danger line and path abilities for this level."""
    branch = BRANCH.get(path); final = path if path in FINALS else None
    lv = dict(H=9 if level < 3 else (11 if level < 5 else 13), hb2=level >= 2, fat=5 if level >= 6 else 4, wsteps=2, wcolm=2, abil=[])
    if level >= 3: lv["abil"].append("hold" if branch == "Knight" else "rage")
    if level >= 4: lv["abil"] += ["reserve", "hold2" if branch == "Knight" else "fury"]   # Fury: unleash full Rage on a fumble
    if level >= 5:
        lv["abil"].append({"Paladin": "oath", "Cavalier": "charge", "Berserker": "bloodlust", "Beastkin": "claws"}[final])
        if final == "Beastkin": lv.update(wsteps=3, wcolm=3)
    if level >= 6: lv["abil"].append({"Paladin": "aura", "Cavalier": "trample", "Berserker": "unstoppable", "Beastkin": "pack"}[final])
    cls = final if level >= 5 else (branch if level >= 3 else "Warrior")
    return lv, cls

def play(code, rng_seed, **rules):
    RL = dict(RULES); RL.update(rules)
    g = generate(code); R = random.Random(rng_seed); random.seed(rng_seed)
    if RL["cap"]: g["cap"] = RL["cap"]
    if RL.get("hp_scale", 1.0) != 1.0:   # difficulty dial: every enemy's HP x scale, whole numbers
        k = RL["hp_scale"]
        g["minions"] = [dict(m, hp=max(1, int(round(m["hp"] * k)))) for m in g["minions"]]
        g["minibosses"] = [dict(m, hp=max(1, int(round(m["hp"] * k)))) for m in g["minibosses"]]
        g["boss"] = dict(g["boss"], hp=max(1, int(round(g["boss"]["hp"] * k))))
    # --- difficulty levers (numbers only; the map and its content stay the same) ---
    def sc_hp(m, k): return dict(m, hp=max(1, int(round(m["hp"] * k))))
    def sc_atk(a, k): return [tuple([(max(1, int(round(x[0] * k))) if x[0] else 0)] + list(x[1:])) for x in a]
    if RL.get("boss_hp_scale", 1.0) != 1.0: g["boss"] = sc_hp(g["boss"], RL["boss_hp_scale"])
    if RL.get("mob_hp_scale", 1.0) != 1.0:
        g["minions"] = [sc_hp(m, RL["mob_hp_scale"]) for m in g["minions"]]; g["minibosses"] = [sc_hp(m, RL["mob_hp_scale"]) for m in g["minibosses"]]
    if RL.get("dmg_scale", 1.0) != 1.0:
        k = RL["dmg_scale"]
        g["minions"] = [dict(m, attacks=sc_atk(m["attacks"], k)) for m in g["minions"]]
        g["minibosses"] = [dict(m, attacks=sc_atk(m["attacks"], k)) for m in g["minibosses"]]
        g["boss"] = dict(g["boss"], attacks=sc_atk(g["boss"]["attacks"], k))
    if RL.get("dmg_add", 0):   # flat: every enemy attack +/- X (minimum 1; wind-ups stay 0)
        k = RL["dmg_add"]
        def ad(at): return [tuple([(max(1, x[0] + k) if x[0] else 0)] + list(x[1:])) for x in at]
        g["minions"] = [dict(m, attacks=ad(m["attacks"])) for m in g["minions"]]
        g["minibosses"] = [dict(m, attacks=ad(m["attacks"])) for m in g["minibosses"]]
        g["boss"] = dict(g["boss"], attacks=ad(g["boss"]["attacks"]))
    if RL.get("danger_add", 0):
        g["danger"] = {q: max(0, min(3, d + RL["danger_add"])) for q, d in g["danger"].items()}
    if RL.get("fuse_shift", 0):
        fm = __import__("re").match(r"Danger (\d+) or more", g["fuse"])
        if fm: g["fuse"] = f"Danger {max(1, int(fm.group(1)) + RL['fuse_shift'])} or more"
    if RL.get("boss_hp"): g["boss"]["hp"] = RL["boss_hp"]
    closed = set()
    for b in g["blocks"]:
        if b["kind"] == "closed":
            closed |= {(b["x"] + i, b["y"] + j) for i in range(b["size"]) for j in range(b["size"])}
    passable = {(x, y) for x in range(1, 13) for y in range(1, 13)} - closed
    walls = {tuple(map(tuple, w)) for w in g["walls"]}
    def moves(c):
        for n in nbrs(c):
            if n in passable and (min(c, n), max(c, n)) not in walls: yield n
    def bfs(src):
        dist = {src: 0}; prev = {}; dq = deque([src])
        while dq:
            c = dq.popleft()
            for n in moves(c):
                if n not in dist: dist[n] = dist[c] + 1; prev[n] = c; dq.append(n)
        return dist, prev
    def path_to(src, dst):
        dist, prev = bfs(src)
        if dst not in dist: return None
        p = [dst]
        while p[-1] != src: p.append(prev[p[-1]])
        return p[::-1][1:]
    def rolled_cell(frm):
        while True:
            c = (R.randint(1, 6) + (6 if R.randint(1, 6) % 2 == 0 else 0), R.randint(1, 6) + (6 if R.randint(1, 6) % 2 == 0 else 0))
            if c not in passable: c = min(passable, key=lambda p: (abs(p[0] - c[0]) + abs(p[1] - c[1]), p[0], p[1]))
            if c != frm: return c
    danger_q = g["danger"]
    # --- hero ---
    hero = dict(hp=50, max=50, cls="Warrior", potions=RL.get("potions", 3)); offers = draw_offers(fixed=RL["offers"])
    STATS = dict(CLASS_STATS["Warrior"])
    if RL.get("level"):                               # leveled hero (the level-1 reference uses the legacy path when level is None)
        hero["lv"], cls_ = hero_config(RL["level"], RL.get("path")); STATS = dict(CLASS_STATS.get(cls_, STATS))
        hero["lv"]["abil"] = [x for x in hero["lv"]["abil"] if x not in RL.get("drop", ())]      # ablation studies
        hero["lv"]["abil"] += [x for x in RL.get("add", ()) if x not in hero["lv"]["abil"]]
        if "claws" in RL.get("drop", ()): hero["lv"].update(wsteps=2, wcolm=2)
        if RL["level"] >= 3 and RL.get("mythic", True):   # Mythic effects (rows 10-13): drawn like the other rarities
            x = random.random(); k = 1 if x < 0.125 else (3 if x > 0.875 else 2)
            offers = dict(offers); offers["M"] = list(RL["mythic_pool"]) if RL.get("mythic_pool") else random.sample(engine2.MYTHIC, k)
    items = dict(weapon=0, armor=0); soldier = [0]
    S = Counter(); log = []
    money = [RL["start_money"]]; spent = [0]; earned = [0]
    def setP():
        engine2.P.clear(); engine2.P.update(copy.deepcopy(P0)); engine2.P.update(STATKNOBS); engine2.P.update(CLASS_KNOBS["Warrior"])
        engine2.P.update(dict(POT_THR=10, POT_HEAL=5, POT_MODE="low")); engine2.P["KW"] = 1 if RL["kw"] else 0
        engine2.P.update(RL.get("engine") or {})     # per-run engine settings (studies): survive the per-fight reset
        engine2.P["CL_FLAT"] = items["weapon"]; engine2.P["W_GUARD"] = CLASS_KNOBS["Warrior"].get("W_GUARD", 0) + items["armor"] + soldier[0]
    def do_fight(enemies, kind, phases=None):
        setP(); hp0 = hero["hp"]
        r = fight(enemies, RL["strategy"], offers, hero, phases=phases)
        soldier[0] = 0; hero["hp"] = max(0, r["hp"]); S["fights"] += 1; S[f"fights_{kind}"] += 1
        if kind == "boss": S["boss_rounds"] = r["rounds"]
        lost = min(money[0], r.get("gold_lost", 0)); money[0] -= lost; S["gold_stolen"] += lost
        S["dmg_taken"] += max(0, hp0 - hero["hp"]) + 0
        if r["win"]:
            for e in enemies:
                rew = e.reward
                money[0] += rew; earned[0] += rew
                if e.boss: S["boss_defeated"] += 1
                elif getattr(e, "mini", False): S["minibosses_defeated"] += 1
                else: S["minions_defeated"] += 1
        return r["win"]
    def minions(n, plus=0):
        out = []
        for _ in range(n):
            m = g["minions"][R.randint(1, 6) - 1]; e = mk_enemy(m); e.reward = m["reward"]
            if plus:
                for it in e.intents: it["d"] += plus
            out.append(e)
        return out
    def miniboss(idx=None):
        k = (R.randint(1, 6) - 1) // 2 if idx is None else idx
        m = g["minibosses"][k]; e = mk_enemy(m); e.reward = m["reward"]; e.mini = True
        out = [e]
        for k in m.get("keywords", []):
            r = __import__("re").match(r"Rally (\d+)(?:\((\d+)\))?$", k)
            if r:
                out += minions(int(r.group(1)))
                out += sum((miniboss() for _ in range(int(r.group(2) or 0))), [])
        return out
    wis = [RL["wis"] + STATS["WIS"] if RL["smart"] else 0]
    def stat_roll(stat):
        r = R.randint(1, 6) + STATS[stat]
        if r == PL.MAP_ROLL_TARGET - 1 and wis[0] > 0: wis[0] -= 1; S["wis_used"] += 1; r += 1
        return r >= PL.MAP_ROLL_TARGET
    def hurt(n):
        hero["hp"] -= n; S["dmg_taken"] += n
    # --- state ---
    pos = tuple(g["starts"][min(g["starts"], key=lambda q: danger_q[q])]); visited_q = {quad(*pos)}
    danger = [0]; cap = g["cap"]; boss_next = [False]; fuse_lit = [False]
    chests = {(p["x"], p["y"]) for p in g["places"] if p["kind"] == "chest"}
    npcs = {(p["x"], p["y"]) for p in g["places"] if p["kind"] == "npc"}
    shop_cell = [(p["x"], p["y"]) for p in g["places"] if p["kind"] == "shop"][0]
    shop_stock = [list(s) for s in g["shop"]]; trader_stock = [list(s) for s in g["trader"]]
    used_t, used_n = set(), set(); quest = [None]; shop_done = [False]
    moved = [0]; since_enc = [0]; best_quiet = [0]; rolls = [0]; encounters = [0]
    dmg_before_boss = [None]; danger_at_boss = [None]; arrival = [None]; bought = [0]
    def add_danger(n):
        danger[0] += n
        if danger[0] >= cap: boss_next[0] = True
        check_fuse()
    def check_fuse():
        f = g["fuse"]
        dm = __import__("re").match(r"Danger (\d+) or more", f)
        lit = ((dm is not None and danger[0] >= int(dm.group(1))) or ("chests" in f and S["chests"] >= 2)
               or ("quadrants" in f and len(visited_q) == 4) or ("NPCs" in f and S["npcs"] >= 2) or ("Bought" in f and bought[0] >= 1))
        if lit: fuse_lit[0] = True
    def buy(stock, at_shop):
        prices = g.get("price") or PL.PRICE
        want = []
        if hero["potions"] < 2: want.append("Potion")
        want += ["Weapon +1", "Armor +1", "Potion"]
        if RL["smart"]:
            import re as _re
            goal = next((int(_re.findall(r"\d+", o)[0]) for o in g["objectives"] if o.startswith("Finish")), None)
            need_buy = any(o.startswith("Buy") and bought[0] < int(_re.findall(r"\d+", o)[0]) for o in g["objectives"])
            if goal is not None and not need_buy:
                want = ["Potion"] if hero["potions"] == 0 else []
                for w in ("Weapon +1", "Armor +1"):
                    if money[0] - 6 >= goal: want.append(w)
        for w in want:
            for s in stock:
                if s[0] == w and len(s) == 3 and money[0] >= prices[s[1]]:
                    money[0] -= prices[s[1]]; spent[0] += prices[s[1]]; bought[0] += 1; s.append("sold")
                    if w == "Potion": hero["potions"] += 1
                    elif w == "Weapon +1": items["weapon"] += 1
                    else: items["armor"] += 1
        check_fuse()
    def draw_pool(pool, used):
        k = R.randint(1, 6) - 1
        if k in used:
            nxt = [i for i in range(6, len(pool)) if i not in used]
            if nxt: k = nxt[0]
        used.add(k); return pool[k]
    def num(t, word, default):                        # the number printed after "gain" / "take" / "heal" in an entry
        import re as _r; m_ = _r.search(word + r" (\d+)", t); return int(m_.group(1)) if m_ else default
    def quest_reward(d): return next(g_ for lim, g_ in (g.get("quest_pay") or PL.QUEST_PAY) if lim is None or d <= lim)
    def interact_chest():
        S["chests"] += 1; add_danger(1); t = draw_pool(g["treasure"], used_t)
        if t.startswith("Mimic"):
            if not stat_roll("INT"): hurt(g["surprise"])
            if hero["hp"] > 0 and not do_fight(miniboss(0), "miniboss"): return False
        elif t.startswith("Potion"): hero["potions"] += 1
        elif t.startswith("Purse") or t.startswith("Coins"): n_ = num(t, "gain", 0); money[0] += n_; earned[0] += n_
        elif t.startswith("Needle"):
            if not stat_roll("DEX"): hurt(num(t, "take", 4))
        elif t.startswith("Whetstone"): items["weapon"] += 1
        elif t.startswith("Buckler"): items["armor"] += 1
        return hero["hp"] > 0
    def interact_npc():
        S["npcs"] += 1; add_danger(1); t = draw_pool(g["npc_pool"], used_n)
        if t.startswith("Imposter"):
            if not stat_roll("INT"): hurt(g["surprise"])
            if hero["hp"] > 0 and not do_fight(minions(2), "minion"): return False
        elif t.startswith("Rumor"):
            quest[0] = (rolled_cell(pos), PL.DIG_GOLD if stat_roll("STR") else 0)   # dig at the rumored cell
        elif t.startswith("Q|") and not RL["quests"]: pass
        elif t.startswith("Q|"):
            tgt = rolled_cell(pos); d = len(path_to(pos, tgt) or []); quest[0] = (tgt, quest_reward(d))
        elif t.startswith("Lost child"):
            tgt = min((tuple(s) for s in g["starts"].values()), key=lambda s: len(path_to(pos, s) or [0] * 99) if s != pos else 99)
            quest[0] = (tgt, quest_reward(len(path_to(pos, tgt) or [])))
        elif t.startswith("Pilgrim"): n_ = num(t, "gain", 0); money[0] += n_; earned[0] += n_
        elif t.startswith("Herbalist"): hero["potions"] += 1
        elif t.startswith("Field medic"): hero["hp"] = min(hero["max"], hero["hp"] + num(t, "heal", 5))
        elif t.startswith("Old soldier"): soldier[0] = 1
        return hero["hp"] > 0
    def boss_fight(cause):
        arrival[0] = cause; dmg_before_boss[0] = S["dmg_taken"]; danger_at_boss[0] = danger[0]; S["hp_at_boss"] = hero["hp"]
        S["potions_at_boss"] = hero["potions"]
        b = g["boss"]; e = mk_enemy(dict(b, keywords=[], weak=b["weak"]), boss=True); e.reward = b["reward"]
        h = b.get("henchmen", {}); S["boss_henchmen"] = f'{h.get("minions", 0)}m{h.get("minibosses", 0)}b'
        team = [e] + sum((miniboss() for _ in range(h.get("minibosses", 0))), []) + minions(h.get("minions", 0))
        p2 = [m["name"] for m in b["phase2"]]; p3 = [m["name"] for m in b["phase3"]]
        def ph(names):
            mode = next((TW.get(n) or OP.get(n) for n in names if n in TW or n in OP), "normal")
            press = next((PR[n] for n in names if n in PR), "")
            return (mode, press)
        if RL["kw"]:   # boss phases as printed keywords, e.g. ["Bulk 1 A,I", "Frenzy H"]
            import pools as _PL
            lab = lambda names: [_PL.MODULE_LABEL.get(n, n) for n in names]
            return do_fight(team, "boss", phases=[[], lab(p2), lab(p3)])
        return do_fight(team, "boss", phases=[("normal", ""), ph(p2), ph(p3)])
    def outcome(a, b, dq):
        """Name the result of raw dice a, b in a quadrant with danger dq under the current rules."""
        if a == b:
            if fuse_lit[0] and (RL["any_double"] or a in (1, 6)): return "boss"
            return "miniboss"
        t = a + b + dq - (RL["nothing_max"] - 4)       # widening Nothing shifts the whole table up
        if a + b + dq <= RL["nothing_max"]: return "nothing"
        return {5: "dig", 6: "trader", 7: "villager", 8: "m1", 9: "trap", 10: "m2", 11: "m3", 12: "m3+"}.get(t, "mini+m1")
    def ready_for_boss(): return hero["hp"] >= RL["ready_hp"][0] or (hero["hp"] >= RL["ready_hp"][1] and hero["potions"] >= 2)
    def value(o):
        low = hero["hp"] < 22
        need_fights = any(o_.startswith(("Defeat", "Complete")) and not ok_now(o_) for o_ in g["objectives"])
        v = {"boss": 6 if ready_for_boss() else -12, "miniboss": -7 if low else -2, "mini+m1": -9 if low else -3,
             "m1": -1, "m2": -2.5, "m3": -4, "m3+": -5, "trap": -2, "nothing": 0.5, "dig": 1.5, "trader": 1 if money[0] >= 3 else 0,
             "villager": 0}[o]
        if low and o in ("m2", "m3", "m3+"): v -= 2
        if need_fights and o in ("m1", "m2", "miniboss"): v += 1.5
        return v
    def movement_roll():
        rolls[0] += 1
        if boss_next[0]: return ("boss", boss_fight("cap"))
        a, b = R.randint(1, 6), R.randint(1, 6); q = quad(*pos); dq = danger_q[q]; step = 2 if dq >= 2 else 1
        if RL["smart"] and wis[0] > 0:
            base = value(outcome(a, b, dq)); best = (base, a, b)
            for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                na, nb = a + da, b + db
                if 1 <= na <= 6 and 1 <= nb <= 6:
                    v = value(outcome(na, nb, dq))
                    if v > best[0]: best = (v, na, nb)
            if best[0] - base >= 3: a, b = best[1], best[2]; wis[0] -= 1; S["wis_used"] += 1
        o = outcome(a, b, dq)
        if o == "boss": return ("boss", boss_fight("fuse"))
        if o == "nothing": return ("nothing", True)
        encounters[0] += 1; since_enc[0] = 0; add_danger(step)
        if o == "miniboss": return ("fight", do_fight(miniboss(), "miniboss"))
        if o == "dig":
            if stat_roll("STR"): money[0] += PL.DIG_GOLD; earned[0] += PL.DIG_GOLD
            return ("dig", True)
        if o == "trader": buy(trader_stock, False); return ("trader", True)
        if o == "villager":
            r = R.randint(1, 6)
            if r <= 2: return ("fight", do_fight(minions(1), "minion"))
            if r <= 4: return ("fight", do_fight(minions(2), "minion"))
            if RL["quests"]: quest[0] = (rolled_cell(pos), PL.ESCORT_PAY)
            return ("escort", True)
        if o == "m1": return ("fight", do_fight(minions(1), "minion"))
        if o == "trap":
            if not stat_roll("DEX"): hurt(g.get("trap_dmg", 4))
            return ("trap", hero["hp"] > 0)
        if o == "m2": return ("fight", do_fight(minions(2), "minion"))
        if o == "m3": return ("fight", do_fight(minions(3), "minion"))
        if o == "m3+": return ("fight", do_fight(minions(3, plus=1), "minion"))
        return ("fight", do_fight(miniboss() + minions(1), "miniboss"))
    def ok_now(o):
        import re as _re
        n = [int(x) for x in _re.findall(r"\d+", o)]
        if o.startswith("Open"): return S["chests"] >= n[0]
        if o.startswith("Talk"): return S["npcs"] >= n[0]
        if o.startswith("Defeat") and "miniboss" in o: return S["minibosses_defeated"] >= (n[0] if n else 1)
        if o.startswith("Defeat"): return S["minions_defeated"] >= n[0]
        if o.startswith("Visit"): return len(visited_q) >= (n[0] if n else 4)
        if o.startswith("Buy"): return bought[0] >= n[0]
        if o.startswith("Complete"): return encounters[0] >= n[0]
        return True
    def next_target():
        if quest[0]: return quest[0][0]
        dist, _ = bfs(pos)
        def safe(c): return not (danger_q[quad(*c)] >= 2 and (RL["avoid_d2"] == "always" or (RL["avoid_d2"] == "lowhp" and RL["smart"] and hero["hp"] < 20)))
        chest_hp = RL["chest_hp"] if RL["smart"] else 18
        want_shop = (RL["shop"] and money[0] >= 3 and shop_stock and not shop_done[0])
        if RL["smart"]:
            goal = next((int(__import__("re").findall(r"\d+", o)[0]) for o in g["objectives"] if o.startswith("Finish")), None)
            if goal is not None and money[0] < goal + 3 and not any(o.startswith("Buy") and not ok_now(o) for o in g["objectives"]):
                want_shop = want_shop and hero["potions"] == 0
        cands = ([c for c in npcs] if RL["npcs"] else []) + ([c for c in chests] if RL["chests"] and hero["hp"] >= chest_hp else []) + ([shop_cell] if want_shop else [])
        cands = [c for c in cands if c != pos and c in dist and safe(c)]
        if cands: return min(cands, key=lambda c: dist[c])
        need_q = (not RL["smart"]) or RL["quads"] == "always" or (RL["quads"] == "objective" and any(o.startswith("Visit") and not ok_now(o) for o in g["objectives"]))
        unq = [c for c in dist if quad(*c) not in visited_q and safe(c)] if need_q else []
        if unq: return min(unq, key=lambda c: dist[c])
        pool = [c for c in dist if safe(c) and c != pos] or [c for c in dist if c != pos]
        far = sorted(pool, key=lambda c: -dist[c]); return far[R.randint(0, min(10, len(far) - 1))]
    result = None; target = None; route = []
    for _step in range(400):
        if quest[0] and pos == quest[0][0]:
            money[0] += quest[0][1]; earned[0] += quest[0][1]; S["quests"] += 1; add_danger(1); quest[0] = None
        if not route:
            target = next_target(); route = path_to(pos, target) or []
            if not route: continue
        pos = route.pop(0); moved[0] += 1; since_enc[0] += 1; best_quiet[0] = max(best_quiet[0], since_enc[0]); visited_q.add(quad(*pos)); check_fuse()
        alive = True
        if pos in npcs and RL["npcs"]: npcs.discard(pos); alive = interact_npc(); route = []
        elif pos in chests and RL["chests"] and hero["hp"] >= (RL["chest_hp"] if RL["smart"] else 18): chests.discard(pos); alive = interact_chest(); route = []
        elif pos == shop_cell and shop_stock and money[0] >= 3 and not shop_done[0]:
            shop_done[0] = True; S["shop_visits"] += 1; add_danger(RL["shop_danger"]); buy(shop_stock, True); route = []
        if quest[0] and pos == quest[0][0]:
            money[0] += quest[0][1]; earned[0] += quest[0][1]; S["quests"] += 1; add_danger(1); quest[0] = None; route = []
        if not alive or hero["hp"] <= 0: result = "died_explore"; break
        if moved[0] > 3 and (moved[0] - 3) % 3 == 0:
            kind, ok = movement_roll(); log.append(kind)
            if kind == "boss": result = "win" if ok else "died_boss"; break
            if not ok or hero["hp"] <= 0: result = "died_explore"; break
    if result is None: result = "timeout"
    # --- objectives ---
    import re
    done = []
    for o in g["objectives"]:
        n = [int(x) for x in re.findall(r"\d+", o)]; ok = False
        if o.startswith("Open"): ok = S["chests"] >= n[0]
        elif o.startswith("Talk"): ok = S["npcs"] >= n[0]
        elif o.startswith("Defeat") and "miniboss" in o: ok = S["minibosses_defeated"] >= (n[0] if n else 1)
        elif o.startswith("Defeat"): ok = S["minions_defeated"] >= n[0]
        elif o.startswith("Take less"): ok = dmg_before_boss[0] is not None and dmg_before_boss[0] < n[0]
        elif o.startswith("Reach the boss before"): ok = arrival[0] == "fuse"
        elif o.startswith("Reach the boss"): ok = danger_at_boss[0] is not None and danger_at_boss[0] <= n[0]
        elif o.startswith("Visit"): ok = len(visited_q) >= (n[0] if n and not o.startswith("Visit all") else 4)
        elif o.startswith("Buy"): ok = bought[0] >= n[0]
        elif o.startswith("Finish with"): ok = money[0] >= n[0]
        elif "without an encounter" in o: ok = best_quiet[0] >= n[0]
        elif o.startswith("Travel"): ok = moved[0] >= n[0]
        elif o.startswith("Complete"): ok = encounters[0] >= n[0]
        done.append((o, ok))
    win = result == "win"
    return dict(code=code, result=result, win=win, level_up=win and sum(ok for _, ok in done) >= 3, objectives=done,
                n_obj=sum(ok for _, ok in done), arrival=arrival[0], rolls=rolls[0], cells=moved[0], fights=S["fights"],
                fights_minion=S["fights_minion"], fights_miniboss=S["fights_miniboss"], hp_at_boss=S.get("hp_at_boss"),
                potions_at_boss=S.get("potions_at_boss"), danger_at_boss=danger_at_boss[0], money_final=money[0], earned=earned[0],
                spent=spent[0], bought=bought[0], chests=S["chests"], npcs=S["npcs"], shop=S["shop_visits"], quests=S["quests"],
                weapon=items["weapon"], armor=items["armor"], boss=g["boss"]["name"], boss_phases=[m["name"] for m in g["boss"]["phase2"] + g["boss"]["phase3"]],
                danger_total=sum(g["danger"].values()), log=log, n_chests=len([p for p in g["places"] if p["kind"] == "chest"]),
                n_npcs=len([p for p in g["places"] if p["kind"] == "npc"]), money_goal=next((int(re.findall(r"\d+", o)[0]) for o in g["objectives"] if o.startswith("Finish")), None),
                minions_defeated=S["minions_defeated"], wis_used=S["wis_used"], gold_stolen=S["gold_stolen"], boss_rounds=S.get("boss_rounds"), quadrants=len(visited_q), encounters=encounters[0], quiet_best=best_quiet[0], dmg_before_boss=dmg_before_boss[0], boss_henchmen=S.get("boss_henchmen"), minibosses_defeated=S["minibosses_defeated"], dmg_taken=S["dmg_taken"])
