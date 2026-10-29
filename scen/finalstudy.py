#!/usr/bin/env python3
"""Final power ratings for the Warrior line, levels 1-6, with every ability as designed (resumable)."""
import os, sys, json, time, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from parallel import run_games
from generate import make_code
from levelstudy import rating
OUT = os.path.join(HERE, "finalstudy.json"); N = 100
SC = {1: (0.7, 1.0, 1.4, 2.0), 2: (0.7, 1.0, 1.4, 2.0), 3: (1.2, 1.7, 2.4, 3.4), 4: (1.2, 1.7, 2.4, 3.4),
      5: (1.6, 2.4, 3.4, 4.8), 6: (2.4, 3.4, 4.8, 6.8)}
CONFIGS = [(1, None), (2, None), (3, "Knight"), (3, "Barbarian"), (4, "Knight"), (4, "Barbarian"),
           (5, "Paladin"), (5, "Cavalier"), (5, "Berserker"), (5, "Beastkin"), (6, "Paladin"), (6, "Cavalier"), (6, "Berserker"), (6, "Beastkin")]
if __name__ == "__main__":
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 270
    rng = random.Random(9753); maps = [make_code(1, 5, f"{rng.getrandbits(32):08x}") for _ in range(N)]
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}; t0 = time.time()
    for lvl, path in CONFIGS:
        for s in SC[lvl]:
            k = f"{lvl}|{path}|{s}"
            if k in res: continue
            if time.time() - t0 > budget: print(f"{len(res)} of {sum(len(SC[l]) for l, _ in CONFIGS)} points; run again", flush=True); sys.exit(0)
            R = run_games([(c, 80000 + i, dict(level=lvl, path=path, hp_scale=s)) for i, c in enumerate(maps)])
            res[k] = sum(r["win"] for r in R) / len(R); json.dump(res, open(OUT, "w"))
    print("Power rating (enemy-HP multiplier at which the hero wins 55%), 100 maps per point")
    for lvl, path in CONFIGS:
        pts = [(s, res[f"{lvl}|{path}|{s}"]) for s in SC[lvl]]
        print(f"  level {lvl} {path or 'Warrior':9s} x{rating(pts):.2f}   (" + "  ".join(f"x{s}:{w:.0%}" for s, w in pts) + ")")
