"""
config.py (Root Re-export)
==========================
Re-export all definitions from eda.config to ensure 'import config' works from workspace root.
"""
import sys
from pathlib import Path

EDA_DIR = Path(__file__).resolve().parent / "eda"
if str(EDA_DIR) not in sys.path:
    sys.path.insert(0, str(EDA_DIR))

from eda.config import *
