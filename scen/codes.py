"""Scenario / hero codes: VVDD-XXXX-XXXX-C.

VV = engine version, DD = hero level band x difficulty (01-09), XXXXXXXX = the seed, C = Luhn mod 16 check.
"""
import re, secrets
from generate import check_char, make_code

ENGINE_VERSION = 1                         # what this toolkit generates
SUPPORTED_VERSIONS = {1}
BANDS = ["low", "mid", "high"]
DIFFS = ["easy", "normal", "hard"]

class CodeError(ValueError):
    pass

def dd_of(band, difficulty):
    return BANDS.index(band) * 3 + DIFFS.index(difficulty) + 1

def band_diff_of(dd):
    if not 1 <= dd <= 9: raise CodeError(f"Difficulty digits {dd:02d} are outside 01-09.")
    return BANDS[(dd - 1) // 3], DIFFS[(dd - 1) % 3]

def parse_input(text):
    """Seed box contents -> dict(seed, version, band, difficulty) where band/difficulty are None unless a full code was pasted.

    Accepts nothing (random seed), 8 hex characters (1a2b-3c4d), or a full code (0105-1a2b-3c4d-a)."""
    raw = re.sub(r"[\s\-]", "", (text or "").lower())
    if raw == "":
        return dict(seed=secrets.token_hex(4), version=ENGINE_VERSION, band=None, difficulty=None, random=True)
    if not re.fullmatch(r"[0-9a-f]+", raw):
        raise CodeError("Use only 0-9 and a-f: enter 8 characters like 1a2b-3c4d, or a full code like 0105-1a2b-3c4d-a.")
    if len(raw) == 8:
        return dict(seed=raw, version=ENGINE_VERSION, band=None, difficulty=None, random=False)
    if len(raw) == 13:
        if check_char(raw[:12]) != raw[12]:
            raise CodeError("That code's last character doesn't match the rest. Check it for a typo.")
        version, dd = int(raw[0:2]), int(raw[2:4])
        if version not in SUPPORTED_VERSIONS:
            raise CodeError(f"Code version {raw[0:2]} needs a different engine; this generator makes version {ENGINE_VERSION:02d}.")
        band, diff = band_diff_of(dd)
        return dict(seed=raw[4:12], version=version, band=band, difficulty=diff, random=False)
    raise CodeError("Enter 8 characters like 1a2b-3c4d, or a full 13-character code like 0105-1a2b-3c4d-a.")

def build(text, band="low", difficulty="normal"):
    """Resolve the seed box plus the chosen hero level and difficulty into a full code."""
    if band not in BANDS: raise CodeError(f"Hero level must be one of {', '.join(BANDS)}.")
    if difficulty not in DIFFS: raise CodeError(f"Difficulty must be one of {', '.join(DIFFS)}.")
    p = parse_input(text)
    code = make_code(p["version"], dd_of(band, difficulty), p["seed"])
    return dict(code=code, seed=p["seed"], version=p["version"], band=band, difficulty=difficulty, random=p["random"],
                pasted_band=p["band"], pasted_difficulty=p["difficulty"])

def content_code(code):
    """Same seed and version at Normal difficulty: the map's content never depends on the difficulty digits."""
    raw = code.replace("-", "")
    band, _ = band_diff_of(int(raw[2:4]))
    return make_code(int(raw[0:2]), dd_of(band, "normal"), raw[4:12])
