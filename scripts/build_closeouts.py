"""Closeout events joined to tracking: the defender's speed when the closeout ends, plus the
shot or drive that followed on the same touch. Writes cache/closeouts.pkl for
studies/closeout_distance.py and studies/shooter_types.py.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from acbtrack.config import CACHE, FPS, GAMES  # noqa: E402
from acbtrack.io import events, positions, stream_frames  # noqa: E402


def main():
    rows = []
    for g in GAMES:
        ev = events(g)
        ch = {c["id"]: c for c in ev["chances"]}
        drv, sht = {}, {}
        for x in ev["drives"]:
            drv.setdefault(x["touchId"], x)
        for x in ev["shots"]:
            sht.setdefault(x["touchId"], x)
        fr = stream_frames(g, {c["endFrame"] for c in ev["closeouts"]})
        for c in ev["closeouts"]:
            cc = ch.get(c["chanceId"], {})
            P = positions(fr.get(c["endFrame"]))
            s, dv = sht.get(c["touchId"]), drv.get(c["touchId"])
            r = dict(game=g, touch=c["touchId"], chance=c["chanceId"], action=c["bhrAction"],
                     transition=cc.get("transition"), pts=cc.get("ptsScored"),
                     region=c["region"], three_loc=int("three" in (c["region"] or "")),
                     touchDist=c["touchDistance"], startDist=c["startDistance"], endDist=c["endDistance"],
                     dur=(c["endFrame"] - c["startFrame"]) / FPS,
                     defSpeed=P[c["ballhandlerDefId"]][3] if c["ballhandlerDefId"] in P else None,
                     drive=int(dv is not None), blowby=(int(bool(dv["blowby"])) if dv else None),
                     shot=int(s is not None))
            if s:
                r.update(shot_three=int(s["three"]), made=int(s["outcome"]),
                         shot_pts=(3 if s["three"] else 2) * s["outcome"], shot_def=s["closestDefDist"])
            rows.append(r)
        print(f"{g}: {len(ev['closeouts'])} closeouts", flush=True)
    df = pd.DataFrame(rows)
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_pickle(CACHE / "closeouts.pkl")
    print(f"saved {len(df)} closeouts")


if __name__ == "__main__":
    main()
