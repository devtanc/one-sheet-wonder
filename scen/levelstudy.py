#!/usr/bin/env python3
"""Power rating per hero level and path: the enemy-HP multiplier at which the hero wins 55% (the Normal target).

Each configuration plays the same maps at several enemy-HP multipliers; a logistic fit of win rate against
log(multiplier) gives the multiplier where it crosses 55%. Resumable: results accumulate in levelstudy.json.

    python3 scen/levelstudy.py [maps] [time budget seconds]
"""
import os, sys, json, math, time, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from parallel import run_games
from generate import make_code
CONFIGS = [(3, "Knight"), (3, "Barbarian"), (4, "Knight"), (4, "Barbarian"),
           (5, "Paladin"), (5, "Cavalier"), (5, "Berserker"), (5, "Beastkin"),
           (6, "Paladin"), (6, "Cavalier"), (6, "Berserker"), (6, "Beastkin")]
SCALES = (1.0, 1.4, 1.9, 2.6, 3.5, 4.8)
OUT = os.path.join(HERE, "levelstudy2.json")   # after Rage (cost 3/2) and Hold the Line (Riposte or carry)

def rating(points, target=0.55):
    xs = [math.log(s) for s, w in points]; ys = [math.log(min(max(w, .03), .97) / (1 - min(max(w, .03), .97))) for s, w in points]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys); sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx; a = my - b * mx
    return math.exp((math.log(target / (1 - target)) - a) / b) if b < 0 else float("inf")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60; budget = float(sys.argv[2]) if len(sys.argv) > 2 else 240
    rng = random.Random(777); maps = [make_code(1, 5, f"{rng.getrandbits(32):08x}") for _ in range(n)]
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    t0 = time.time()
    for lvl, path in CONFIGS:
        for s in SCALES:
            key = f"{lvl}|{path}|{s}|{n}"
            if key in res: continue
            if time.time() - t0 > budget: print("time budget reached; run again to continue", flush=True); sys.exit(0)
            R = run_games([(c, 40000 + i, dict(level=lvl, path=path, hp_scale=s)) for i, c in enumerate(maps)])
            res[key] = sum(r["win"] for r in R) / len(R); json.dump(res, open(OUT, "w"))
            print(f"level {lvl} {path or '':9s} enemy HP x{s}: win {res[key]:.0%}  ({time.time()-t0:.0f}s)", flush=True)
    print("\nPower rating: enemy-HP multiplier at which the hero wins 55%")
    for lvl, path in CONFIGS:
        pts = [(s, res[f"{lvl}|{path}|{s}|{n}"]) for s in SCALES]
        print(f"  level {lvl} {path or 'Warrior':9s}  x{rating(pts):.2f}   (" + "  ".join(f"x{s}:{w:.0%}" for s, w in pts) + ")")
