import json, re, sys, collections, numpy as np
rows = json.load(open(sys.argv[1])); W = [r for r in rows if r["win"]]
print(f"win {len(W)/len(rows):.0%} | level-up among wins {np.mean([r['level_up'] for r in W]):.0%}")
st = collections.defaultdict(list)
for r in W:
    for t, ok in r["objectives"]: st[re.sub(r"\d+", "N", t)].append(ok)
for k, v in sorted(st.items(), key=lambda kv: -np.mean(kv[1])): print(f"  {k:46s} offered {len(v):4d}  done {np.mean(v):4.0%}")
d = [r["danger_at_boss"] / r["cap"] for r in W if r.get("danger_at_boss") is not None]
print(f"danger at boss / track length among wins: median {np.median(d):.2f}")
