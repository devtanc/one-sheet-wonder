#!/usr/bin/env python3
"""Rate scenarios: win rate of the level-1 reference hero across an enemy-HP grid (all CPU cores).

    python3 scen/calibrate.py                         # the six calibration scenarios
    python3 scen/calibrate.py 0105-a6a3-a450-7 ...    # specific codes
Results accumulate in scen/calib.json (re-running skips finished cells).
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from parallel import run_games

CODES = ["0105-a6a3-a450-7", "0105-ffec-3fee-2", "0105-1d74-bd1c-9", "0105-536e-95df-7", "0105-d293-056a-f", "0105-d038-0cfb-4"]
GRID = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.15, 1.3, 1.5, 1.8]
GAMES = 300
OUT = os.path.join(HERE, "calib.json")

if __name__ == "__main__":
    codes = sys.argv[1:] or CODES
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for code in codes:
        todo = [s for s in GRID if f"{code}|{s}" not in res]
        jobs = [(code, 11000 + i, dict(hp_scale=s)) for s in todo for i in range(GAMES)]
        R = run_games(jobs)
        for k, s in enumerate(todo):
            part = R[k * GAMES:(k + 1) * GAMES]
            res[f"{code}|{s}"] = dict(win=sum(r["win"] for r in part) / GAMES, level=sum(r["level_up"] for r in part) / GAMES,
                                      died_explore=sum(r["result"] == "died_explore" for r in part) / GAMES)
        json.dump(res, open(OUT, "w"))
        print(code, " ".join(f"{s}:{100*res[f'{code}|{s}']['win']:.0f}%" for s in GRID), flush=True)
