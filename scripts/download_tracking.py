"""Download the 10 tracking files (Git LFS objects, ~35 MB each) from GitHub's media host.

Usage:  python scripts/download_tracking.py
Writes  tracking/{gameId}_tracking_data.jsonl.gz  (or $ACB_TRACKING)
"""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from acbtrack.config import GAMES, TRACKING  # noqa: E402

URL = "https://media.githubusercontent.com/media/SkillCorner/opendata-basketball/main/data/matches/{g}/{g}_tracking_data.jsonl.gz"


def main():
    TRACKING.mkdir(parents=True, exist_ok=True)
    for g in GAMES:
        out = TRACKING / f"{g}_tracking_data.jsonl.gz"
        if out.exists() and out.stat().st_size > 10_000_000:
            print(f"{g}: already downloaded")
            continue
        print(f"{g}: downloading...", flush=True)
        urllib.request.urlretrieve(URL.format(g=g), out)
        print(f"{g}: {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
