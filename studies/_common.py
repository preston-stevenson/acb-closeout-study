import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from acbtrack.config import CACHE, RESULTS  # noqa: E402


def load(name):
    p = CACHE / f"{name}.pkl"
    if not p.exists():
        raise SystemExit(f"Missing {p}. Run scripts/build_{name}.py first.")
    return pd.read_pickle(p)


def out(name):
    RESULTS.mkdir(parents=True, exist_ok=True)
    return RESULTS / name


def pct(x):
    return f"{x * 100:.0f}%"
