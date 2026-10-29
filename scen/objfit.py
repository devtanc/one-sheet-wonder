"""Play many Normal scenarios and record what each run achieved, to fit objective thresholds."""
import os, sys, json, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from parallel import run_games
from generate import make_code, generate
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 4242); codes = [make_code(1, 5, f"{rng.getrandbits(32):08x}") for _ in range(n)]
    R = run_games([(c, 20000 + i, {}) for i, c in enumerate(codes)])
    rows = []
    for c, r in zip(codes, R):
        g = generate(c)
        rows.append(dict(code=c, rolls_est=g["rolls_est"], money_est=g["money_est"], fuse=g["fuse"], n_npcs=sum(p["kind"] == "npc" for p in g["places"]),
                         n_chests=sum(p["kind"] == "chest" for p in g["places"]), win=r["win"], level_up=r["level_up"], objectives=r["objectives"],
                         quadrants=r["quadrants"], bought=r["bought"], spent=r["spent"], npcs=r["npcs"], chests=r["chests"], minis=r["minibosses_defeated"],
                         minions=r["minions_defeated"], encounters=r["encounters"], cells=r["cells"], gold=r["money_final"], arrival=r["arrival"],
                         dmg_before_boss=r.get("dmg_before_boss"), quiet=r["quiet_best"], danger_at_boss=r["danger_at_boss"], cap=g["cap"]))
    json.dump(rows, open(os.path.join(HERE, sys.argv[3] if len(sys.argv) > 3 else "objfit.json"), "w")); print("saved", len(rows))
