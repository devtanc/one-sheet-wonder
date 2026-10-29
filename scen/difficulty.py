"""Difficulty kit for a scenario code: rate its map, buy visible steps, then fine-tune enemy HP (see steps.py).

The map's content always comes from the seed at Normal difficulty (codes.content_code); only the numbers change by tier.
Ratings use the level-1 reference hero (a Warrior with dealt effects, Balanced play). Mid and High bands use the same
rating until heroes for those levels are designed.

Cost per new map: 300 rating games, then 3 x 150 games per tier for the HP fine-tune (all cached).
"""
import os, json, math, threading
from codes import content_code, band_diff_of
from steps import plan, TARGET

RATING_GAMES, TUNE_GAMES, TUNE_GRID = 300, 150, (0.85, 1.0, 1.18)
HP_MIN, HP_MAX = 0.75, 1.33
_lock = threading.Lock()

def _load(path):
    return json.load(open(path)) if os.path.exists(path) else {}

def _store(path, key, value):
    with _lock:
        d = _load(path); d[key] = value; os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"; json.dump(d, open(tmp, "w")); os.replace(tmp, path)

def rating(code, run_games, cache_dir):
    """Win rate of the reference hero on this code's map at base numbers (cached per map)."""
    cc = content_code(code); path = os.path.join(cache_dir, "ratings.json")
    with _lock:
        hit = _load(path).get(cc)
    if hit is not None: return hit
    R = run_games([(cc, 91000 + i, {}) for i in range(RATING_GAMES)])
    r = sum(x["win"] for x in R) / len(R); _store(path, cc, r); return r

def _logit(p): p = min(max(p, 0.02), 0.98); return math.log(p / (1 - p))

def kit(code, run_games, cache_dir, precise=True):
    raw = code.replace("-", ""); band, diff = band_diff_of(int(raw[2:4])); tier = diff.capitalize()
    path = os.path.join(cache_dir, "kits.json"); key = f"{code}|{'precise' if precise else 'plan'}"
    with _lock:
        hit = _load(path).get(key)
    if hit: return hit
    cc = content_code(code); r = rating(code, run_games, cache_dir); p = plan(min(max(r, 0.02), 0.98), tier)
    hp = p["hp_scale"]; tuned = None
    if precise:
        kw = dict(dmg_add=p["dmg_add"], potions=p["potions"])
        grid = [round(hp * m, 3) for m in TUNE_GRID]
        R = run_games([(cc, 93000 + i, dict(kw, hp_scale=s)) for s in grid for i in range(TUNE_GAMES)])
        w = [sum(x["win"] for x in R[k * TUNE_GAMES:(k + 1) * TUNE_GAMES]) / TUNE_GAMES for k in range(len(grid))]
        xs = [math.log(s) for s in grid]; ys = [_logit(v) for v in w]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxx = sum((x - mx) ** 2 for x in xs); b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
        if b < -0.5:                                           # win rate falls as HP rises, as it should: solve for the target
            a = my - b * mx; hp = math.exp((_logit(TARGET[tier]) - a) / b)
        hp = round(min(max(hp, HP_MIN), HP_MAX), 2); tuned = dict(grid=grid, wins=w)
    out = dict(rating=r, band=band, difficulty=diff, dmg_add=p["dmg_add"], potions=p["potions"], hp_scale=hp, content=cc, tune=tuned)
    _store(path, key, out); return out
