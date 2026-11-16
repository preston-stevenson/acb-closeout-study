"""Paths, game list and court constants.

Paths can be overridden with environment variables:
  ACB_DATA      the `data/` folder of a clone of SkillCorner/opendata-basketball
  ACB_TRACKING  folder holding the downloaded tracking files ({gameId}_tracking_data.jsonl.gz)
  ACB_CACHE     intermediate tables built by scripts/
  ACB_RESULTS   tables written by studies/
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("ACB_DATA", ROOT / "opendata-basketball" / "data"))
TRACKING = Path(os.environ.get("ACB_TRACKING", ROOT / "tracking"))
CACHE = Path(os.environ.get("ACB_CACHE", ROOT / "cache"))
RESULTS = Path(os.environ.get("ACB_RESULTS", ROOT / "results"))

# The 10 ACB 2025-26 games published with full tracking.
GAMES = [114243, 114234, 114169, 114099, 114086, 178442, 179612, 184439, 188630, 191313]

FPS = 25                 # tracking frame rate
HOOP_X = 40.76           # rim centre, feet from half court (FIBA: 1.575 m from the baseline)
BASELINE_X = 45.93       # half the FIBA court length (28 m)
ARC_R = 22.15            # three-point radius (6.75 m)
CORNER_Y = 21.65         # corner three line, feet from the court's centre line
KEY_HALF_W = 8.04        # half the key width (4.9 m)
KEY_LEN = 19.03          # key length from the baseline (5.8 m)
