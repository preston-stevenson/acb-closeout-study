#!/usr/bin/env bash
# Reproduce every table and page from the raw SkillCorner data.
set -euo pipefail
cd "$(dirname "$0")"
python scripts/download_tracking.py
python scripts/build_closeouts.py
python scripts/build_touches.py
python scripts/build_snapshots.py
for s in spacing closeout_distance beaten help shooter_types; do
  echo "== $s"; python studies/$s.py
done
python pages/huertas_replay.py
python pages/closeout_contrast.py
