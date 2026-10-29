#!/usr/bin/env python3
"""Rebuild every attack-data file the engine reads (d4/*.npy), in parallel across all CPU cores.

Portable replacement for regen_all.sh (which needs bash 4; macOS ships bash 3.2). Builds the same 468 files:
13 board modes x 3 weak-point pairs x 2 aim settings x 3 stances, each with and without one re-roll (suffix _r1).
Uses the Rust simulator if built (cs5rs/target/release/cs5), else the C++ one; output is identical either way.

    python3 regen_all.py                 # all missing files, every core
    python3 regen_all.py --workers 4     # limit cores
    python3 regen_all.py --only normal_w410 --out /tmp/check   # a subset somewhere else (for testing)
"""
import os, sys, time, argparse, subprocess, tempfile, multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kwboard

#        mode:          W  R FM   L  PF NH HM  EV
MODES = {"normal":     (1, 3, 3,   0, 0, 0, 1, 0),   "daze":      (1, 3, 1, 0,   0, 0, 1, 0),
         "traps":      (1, 3, 3,   0, 0, 2, 2, 0.5), "dazetraps": (1, 3, 1, 0,   0, 2, 2, 0.5),
         "thickhide":  (1, 3, 3,   0, 1, 0, 1, 0),   "plate":     (1, 3, 3, 0,   2, 0, 1, 0),
         "jinx":       (0, 3, 3,   0, 0, 0, 1, 0),   "pin":       (1, 2, 3, 0,   0, 0, 1, 0),
         "shieldwall": (1, 3, 3, 311, 0, 0, 1, 0),   "ironwall":  (1, 3, 3, 68,  0, 0, 1, 0),
         "gate678":    (1, 3, 3, 678, 0, 0, 1, 0),   "cracked":   (1, 3, 3, 0,   3, 0, 1, 0)}
WEAK = {"w311": (0, 6), "w410": (1, 5), "w59": (2, 6)}

def jobs():
    out = []
    for suf, n, rr in (("", 25000, 0), ("_r1", 15000, 1)):
        for m, (W, R, FM, L, PF, NH, HM, EV) in MODES.items():
            for pn, (C, WR) in WEAK.items():
                for a in (0, 1):
                    for g in (0, 1, 2):
                        out.append((f"{m}_{pn}_a{a}_g{g}{suf}", [n, 0, 0, None, 1, 1000, 0, 3, 1, 0, 6, 9, W, R, 4, FM, 1, L, PF, 4, g, 3, C, WR,
                                                                   2, 12 if a else 0, NH, 8, None, HM, EV, 2, 24 if a else 0, 1, 2, 0, 2, rr]))
        for pn, (C, WR) in WEAK.items():                 # Exposed opening: weak point 2 rows lower
            for a in (0, 1):
                for g in (0, 1, 2):
                    out.append((f"exposed2_{pn}_a{a}_g{g}{suf}", [n, 0, 0, None, 1, 1000, 0, 3, 1, 0, 6, 9, 1, 3, 4, 3, 1, 0, 0, 4, g, 3, C, WR - 2,
                                                                    2, 12 if a else 0, 0, 8, None, 1, 0, 2, 24 if a else 0, 1, 2, 0, 2, rr]))
    return out

def build(job):
    import numpy as np
    stem, args, outdir = job
    final = os.path.join(outdir, stem + ".npy")
    if os.path.exists(final) and os.path.getsize(final) > 0: return stem, "kept"
    fd, txt = tempfile.mkstemp(dir=outdir, suffix=".txt"); os.close(fd)
    a = list(args); a[3] = os.path.join(HERE, "layout_plus.txt"); a[28] = txt
    subprocess.run([kwboard.simulator()] + [str(x) for x in a], check=True, stdout=subprocess.DEVNULL)
    fd, tmp = tempfile.mkstemp(dir=outdir, suffix=".npy"); os.close(fd)
    np.save(tmp, np.loadtxt(txt).astype(np.int64)); os.remove(txt); os.replace(tmp, final)
    return stem, "built"

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1); ap.add_argument("--only", default="")
    ap.add_argument("--out", default=os.path.join(HERE, "d4"))
    o = ap.parse_args(); os.makedirs(o.out, exist_ok=True)
    todo = [(s, a, o.out) for s, a in jobs() if o.only in s]
    print(f"simulator: {kwboard.simulator()} | {len(todo)} files | {o.workers} workers | output {o.out}", flush=True)
    t = time.time(); done = 0
    with mp.get_context("spawn").Pool(o.workers) as pool:
        for stem, what in pool.imap_unordered(build, todo):
            done += 1
            if done % 25 == 0 or done == len(todo): print(f"  {done}/{len(todo)} ({time.time()-t:.0f}s)", flush=True)
    print(f"done: {len([f for f in os.listdir(o.out) if f.endswith('.npy')])} .npy files in {o.out} ({time.time()-t:.0f}s)")
