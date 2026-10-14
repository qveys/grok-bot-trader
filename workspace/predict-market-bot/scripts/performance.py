#!/usr/bin/env python3
"""Ancien calcul (remplacé le 9 oct 2026). Délègue à scripts/update_performance.py (PM-Compound) pour ne plus
écraser state/performance.json avec des chiffres incomplets. Copie de l'ancien code : /workspace/backups/verdicts_20261009/performance.py.old"""
import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.argv = [str(Path(__file__).with_name("update_performance.py"))] + sys.argv[1:]
    runpy.run_path(sys.argv[0], run_name="__main__")
