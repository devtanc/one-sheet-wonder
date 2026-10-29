#!/usr/bin/env python3
"""One Sheet Wonder sheet generator: a small web server.

    python3 server.py                 # http://localhost:8000
    python3 server.py --port 8080 --workers 6

Open the page, optionally enter a seed (8 characters like 1a2b-3c4d, or a full code), pick a hero level and a
difficulty, and generate a printable map or hero. Sheets and map ratings are cached in cache/.
"""
import os, sys, json, threading, argparse, mimetypes, multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
SCEN = os.path.join(ROOT, "scen")
sys.path.insert(0, SCEN)
import osw_paths  # noqa: F401,E402
import parallel  # noqa: E402
import codes as C  # noqa: E402

WEB = os.path.join(ROOT, "web"); FONTS = os.path.join(ROOT, "fonts")

def _source_tag():
    """Fingerprint of everything that decides what a sheet prints: change the rules or layout, get fresh sheets."""
    import hashlib
    h = hashlib.sha256()
    for f in ("generate.py", "pools.py", "render_pdf.py", "render_hero.py", "render_rules.py", "steps.py", "difficulty.py", "playsim2.py", "codes.py"):
        h.update(open(os.path.join(SCEN, f), "rb").read())
    return h.hexdigest()[:10]

CACHE = os.path.join(ROOT, "cache", _source_tag()); SHEETS = os.path.join(CACHE, "sheets")
_pool = None; _pool_lock = threading.Lock(); _key_locks = {}; _key_guard = threading.Lock(); WORKERS = None

def pool():
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = ProcessPoolExecutor(max_workers=WORKERS or os.cpu_count(), mp_context=mp.get_context("spawn"),
                                        initializer=parallel._init, initargs=(None,))
        return _pool

def run_games(jobs):
    jobs = list(jobs); n = WORKERS or os.cpu_count() or 1
    return list(pool().map(parallel._job, jobs, chunksize=max(1, len(jobs) // (n * 4))))

def make_preview(pdf_path):
    """PNG of the sheet's first page for the page preview (phones can't show PDFs inline). None if no renderer."""
    png = pdf_path[:-4] + ".png"
    if os.path.exists(png): return png
    try:
        import pypdfium2
        doc = pypdfium2.PdfDocument(pdf_path); img = doc[0].render(scale=150 / 72).to_pil().convert("RGB"); doc.close()
        from PIL import Image
        img.quantize(colors=64, method=Image.Quantize.MEDIANCUT).save(png, optimize=True)   # flat line art: ~100 KB
        return png
    except ImportError:
        pass
    import shutil, subprocess
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-png", "-r", "150", "-singlefile", pdf_path, png[:-4]], check=True)
        return png if os.path.exists(png) else None
    return None

def with_preview(name, info):
    png = make_preview(os.path.join(SHEETS, name))
    return dict(info, preview=f"/sheets/{os.path.basename(png)}" if png else None)

def key_lock(key):
    with _key_guard:
        return _key_locks.setdefault(key, threading.Lock())

def make_sheet(kind, code):
    """Build (or reuse) the PDF for a code. Returns (filename, info dict)."""
    os.makedirs(SHEETS, exist_ok=True)
    name = f"{kind}-{code}.pdf"; path = os.path.join(SHEETS, name); meta = path + ".json"
    with key_lock(name):
        if os.path.exists(path) and os.path.exists(meta): return name, with_preview(name, json.load(open(meta)))
        if kind == "map":
            import difficulty, render_pdf
            k = difficulty.kit(code, run_games, CACHE)
            render_pdf.render([code], path, hp_scale=k["hp_scale"], dmg_add=k["dmg_add"], potions=k["potions"], content=k["content"])
            info = dict(kind="map", code=code, rating=round(k["rating"], 3), dmg_add=k["dmg_add"], potions=k["potions"],
                        hp_scale=k["hp_scale"], band=k["band"], difficulty=k["difficulty"])
        else:
            import render_hero
            _, h = render_hero.render(code, path)
            info = dict(kind="hero", code=code, cls=h["cls"], level=h["level"], branch=h["branch"], final=h["final"],
                        effects={r: [n for n, _ in v] for r, v in h["effects"].items()})
        json.dump(info, open(meta, "w"))
        return name, with_preview(name, info)

class Handler(BaseHTTPRequestHandler):
    server_version = "OneSheetWonder/1.0"

    def log_message(self, fmt, *args): sys.stderr.write("  %s\n" % (fmt % args))

    def send(self, status, body, ctype, extra=None):
        self.send_response(status); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if ctype.startswith("application/json") else "max-age=3600")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(body)

    def json(self, status, obj): self.send(status, json.dumps(obj).encode(), "application/json; charset=utf-8")

    def file(self, path, ctype=None, extra=None):
        if not os.path.isfile(path): return self.json(404, dict(error="Not found."))
        self.send(200, open(path, "rb").read(), ctype or mimetypes.guess_type(path)[0] or "application/octet-stream", extra)

    def do_GET(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"): return self.file(os.path.join(WEB, "index.html"), "text/html; charset=utf-8")
            if u.path.startswith("/fonts/"):
                return self.file(os.path.join(FONTS, os.path.basename(u.path)), "font/ttf")
            if u.path == "/api/code":
                return self.json(200, C.build(q.get("seed", ""), q.get("level", "low"), q.get("difficulty", "normal")))
            if u.path == "/api/generate":
                kind = q.get("kind", "map")
                if kind not in ("map", "hero"): return self.json(400, dict(error="Choose a map or a hero."))
                c = C.build(q.get("seed", ""), q.get("level", "low"), q.get("difficulty", "normal"))
                name, info = make_sheet(kind, c["code"])
                return self.json(200, dict(info, pdf=f"/sheets/{name}", random=c["random"]))
            if u.path == "/rules.pdf":
                path = os.path.join(CACHE, "one-sheet-wonder-rules.pdf")
                with key_lock("rules"):
                    if not os.path.exists(path):
                        import render_rules; os.makedirs(CACHE, exist_ok=True); render_rules.render(path)
                disp = ("attachment" if q.get("download") else "inline") + '; filename="one-sheet-wonder-rules.pdf"'
                return self.file(path, "application/pdf", {"Content-Disposition": disp})
            if u.path.startswith("/sheets/") and u.path.endswith(".png"):
                return self.file(os.path.join(SHEETS, os.path.basename(u.path)), "image/png")
            if u.path.startswith("/sheets/"):
                name = os.path.basename(u.path)
                disp = ("attachment" if q.get("download") else "inline") + f'; filename="{name}"'
                return self.file(os.path.join(SHEETS, name), "application/pdf", {"Content-Disposition": disp})
            return self.json(404, dict(error="Not found."))
        except C.CodeError as e:
            return self.json(400, dict(error=str(e)))
        except Exception as e:  # keep the server up; report the failure plainly
            import traceback; traceback.print_exc()
            return self.json(500, dict(error=f"The sheet couldn't be generated: {e}"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--workers", type=int, default=None, help="simulation processes (default: all cores)")
    a = ap.parse_args(); WORKERS = a.workers
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"One Sheet Wonder generator on http://{a.host}:{a.port}  (simulation workers: {WORKERS or os.cpu_count()})", flush=True)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        if _pool: _pool.shutdown(cancel_futures=True)
