"""Run many scenario games across every CPU core.

    from parallel import run_games, play_many
    results = play_many("0105-a6a3-a450-7", 300, seed0=5000, offers=None, hp_scale=1.1)
    results = run_games([(code, seed, {"dmg_add": 1}) for ...], overrides={"DIFFICULTY.Normal.cap": 20})

Every game carries its own seed, so results are identical to a serial run regardless of core count or scheduling.
Worker processes use the "spawn" start method (the macOS default), so anything changed in memory in the calling
script (for example a pools setting) must be passed through `overrides`; it is applied in every worker.
Set OSW_WORKERS to force a worker count (1 = serial).
"""
import os, sys, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osw_paths  # noqa: F401  (puts the engine on the path)

def _apply(overrides):
    """overrides: {"DIFFICULTY.Normal.cap": 20, "FUSE_STEER": 2.0, ...} applied to the pools module."""
    import pools
    undo = []
    for path, value in (overrides or {}).items():
        keys = path.split("."); obj = pools
        for k in keys[:-1]: obj = getattr(obj, k) if not isinstance(obj, dict) else obj[k]
        last = keys[-1]
        if isinstance(obj, dict): undo.append((obj, last, obj.get(last), True)); obj[last] = value
        else: undo.append((obj, last, getattr(obj, last, None), False)); setattr(obj, last, value)
    return undo

def _undo(undo):
    for obj, k, v, is_dict in reversed(undo):
        if is_dict: obj[k] = v
        else: setattr(obj, k, v)

def _init(overrides):
    _apply(overrides)

def _job(job):
    from playsim2 import play
    code, seed, kw = job
    return play(code, seed, **kw)

def default_workers():
    env = os.environ.get("OSW_WORKERS")
    return max(1, int(env)) if env else max(1, os.cpu_count() or 1)

def run_games(jobs, workers=None, overrides=None, chunksize=None):
    """jobs: list of (code, seed, kwargs). Returns results in the same order as jobs."""
    jobs = list(jobs); workers = workers or default_workers()
    if workers <= 1 or len(jobs) <= 1:
        undo = _apply(overrides)
        try: return [_job(j) for j in jobs]
        finally: _undo(undo)
    chunksize = chunksize or max(1, len(jobs) // (workers * 8))
    with mp.get_context("spawn").Pool(workers, initializer=_init, initargs=(overrides,)) as pool:
        return pool.map(_job, jobs, chunksize)

def play_many(code, n, seed0=0, workers=None, overrides=None, **kw):
    """n games of one scenario with consecutive seeds seed0, seed0+1, ..."""
    return run_games([(code, seed0 + i, kw) for i in range(n)], workers=workers, overrides=overrides)

if __name__ == "__main__":
    import time
    code = sys.argv[1] if len(sys.argv) > 1 else "0105-a6a3-a450-7"; n = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    t = time.time(); a = play_many(code, n, workers=1); ts = time.time() - t
    t = time.time(); b = play_many(code, n); tp = time.time() - t
    same = all((x["result"], x["hp_at_boss"], x["money_final"]) == (y["result"], y["hp_at_boss"], y["money_final"]) for x, y in zip(a, b))
    print(f"{n} games: serial {ts:.1f}s | {default_workers()} workers {tp:.1f}s ({ts/tp:.1f}x) | identical results: {same}")
