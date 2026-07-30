#!/usr/bin/env python3
"""Remove __pycache__ directories, .pyc files, and .egg-info dirs."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

removed = 0
for pycache in ROOT.rglob("__pycache__"):
    shutil.rmtree(pycache, ignore_errors=True)
    print(f"  rm -r {pycache.relative_to(ROOT)}")
    removed += 1

for pyc in ROOT.rglob("*.pyc"):
    pyc.unlink(missing_ok=True)
    removed += 1

for egg in ROOT.rglob("*.egg-info"):
    if egg.is_dir():
        shutil.rmtree(egg, ignore_errors=True)
        print(f"  rm -r {egg.relative_to(ROOT)}")
        removed += 1

print(f"\nCleaned {removed} items.")
