"""Puts the combat engine on the import path, wherever the toolkit lives.

The engine (engine2.py, kwboard.py, cs5, d4/) is found in this order: the OSW_ENGINE_DIR environment variable, this
folder, then the parent folder. Import this module first in any script.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def _find():
    for d in (os.environ.get("OSW_ENGINE_DIR"), HERE, os.path.dirname(HERE)):
        if d and os.path.exists(os.path.join(d, "engine2.py")): return d
    raise RuntimeError("engine2.py not found: set OSW_ENGINE_DIR to the folder that holds the combat engine")
ENGINE_DIR = _find()
for d in (HERE, ENGINE_DIR):
    if d not in sys.path: sys.path.insert(0, d)
