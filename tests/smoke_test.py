#!/usr/bin/env python3
"""Smoke test: renders a hero sheet, the rules and a scenario sheet, checks each PDF, and checks the docs match the code.

    python3 tests/smoke_test.py

Needs only Python and requirements.txt (no Rust build, no attack data). Exits non-zero on failure.
"""
import os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = [  # (label, command, expected pages)
    ("hero sheet (level 1)", ["scen/render_hero.py", "0102-528c-4e6e-c"], 1),
    ("hero sheet (level 5)", ["scen/render_hero.py", "0108-f1ca-9d72-c"], 1),
    ("rules", ["scen/render_rules.py"], 2),
    ("scenario sheet", ["scen/render_pdf.py", "0105-a6a3-a450-7"], 1),
]

def pages(path):
    data = open(path, "rb").read()
    assert data.startswith(b"%PDF"), "not a PDF"
    return len(re.findall(rb"/Type\s*/Page[^s]", data))

def main():
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for i, (label, cmd, want) in enumerate(CASES):
            out = os.path.join(tmp, f"{i}.pdf")
            r = subprocess.run([sys.executable, *cmd, "-o", out], cwd=ROOT, capture_output=True, text=True)
            try:
                assert r.returncode == 0, (r.stderr or r.stdout).strip().splitlines()[-1:]
                got = pages(out)
                assert got == want, f"{got} pages, expected {want}"
                print(f"ok    {label}")
            except Exception as e:
                failed += 1; print(f"FAIL  {label}: {e}")
    r = subprocess.run([sys.executable, "scen/render_docs.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode == 0: print("ok    docs match the code")
    else: failed += 1; print(f"FAIL  docs: {r.stdout.strip() or r.stderr.strip()}")
    print("all passed" if not failed else f"{failed} failed")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
