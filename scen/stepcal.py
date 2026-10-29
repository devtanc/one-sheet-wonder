#!/usr/bin/env python3
"""Difficulty steps for each scenario and tier (all CPU cores).

1. Plan whole, visible steps from the scenario's rating (enemy damage +/-, starting potions), see steps.py.
2. Fine-tune enemy HP within x0.75-1.33 by simulation, then validate on fresh dice.

    python3 scen/stepcal.py                      # every scenario in stepplan.json
    python3 scen/stepcal.py --games 200 --valid 300
Results accumulate in scen/stepcal.json.
"""
import os, sys, json, math, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
from parallel import run_games
from steps import TARGET

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--games", type=int, default=200); ap.add_argument("--valid", type=int, default=300)
    o = ap.parse_args()
    P = json.load(open(os.path.join(HERE, "stepplan.json"))); OUT = os.path.join(HERE, "stepcal.json")
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for k, p in P.items():
        if k in res and "valid" in res[k]: continue
        c, t = k.split("|"); kit = dict(dmg_add=p["dmg_add"], potions=p["potions"])
        grid = [round(p["hp_scale"] * m, 3) for m in (0.75, 0.87, 1.0, 1.15, 1.33)]
        R = run_games([(c, 71000 + i, dict(kit, hp_scale=s)) for s in grid for i in range(o.games)])
        w = np.array([np.mean([r["win"] for r in R[j * o.games:(j + 1) * o.games]]) for j in range(len(grid))])
        x = np.log(grid); ok = (w > 0.03) & (w < 0.97)
        b, a = np.polyfit(x[ok], np.log(np.clip(w[ok], .02, .98) / (1 - np.clip(w[ok], .02, .98))), 1)
        pt = TARGET[t]; s = math.exp((math.log(pt / (1 - pt)) - a) / b); hp = round(min(max(s, 0.75), 1.33), 2)
        V = run_games([(c, 81000 + i, dict(kit, hp_scale=hp)) for i in range(o.valid)])
        wins = [r for r in V if r["win"]]
        res[k] = dict(grid={str(g): float(v) for g, v in zip(grid, w)}, hp_solved=s, hp=hp, clamped=not (0.75 <= s <= 1.33),
                      valid=dict(win=float(np.mean([r["win"] for r in V])), lvl=float(np.mean([r["level_up"] for r in wins])) if wins else 0.0,
                                 diex=float(np.mean([r["result"] == "died_explore" for r in V]))))
        json.dump(res, open(OUT, "w"))
        print(f"{k}: {p['dmg_add']:+d} damage, {p['potions']} potions, HP x{hp} -> {100*res[k]['valid']['win']:.0f}% (target {100*TARGET[t]:.0f}%)", flush=True)
