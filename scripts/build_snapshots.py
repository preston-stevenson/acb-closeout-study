"""Spacing snapshots: the 10 players' positions at the first pick of each chance, every
drive start, and 1 s before every shot, in half-court chances. For each snapshot, three
levels of spacing measures are computed. Writes cache/snapshots.pkl for studies/spacing.py.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from acbtrack import geometry as geo  # noqa: E402
from acbtrack.config import CACHE, GAMES, HOOP_X  # noqa: E402
from acbtrack.io import events, stream_frames  # noqa: E402
from acbtrack.players import aliases, shrunk_threat  # noqa: E402

HX = -HOOP_X   # plays are rotated so the offense attacks this hoop


def value_map(grid):
    """Points per shot by 2-ft distance band from the 10 games, used to weight floor control."""
    bins = np.arange(0, 32, 2)
    pts, n = np.zeros(len(bins)), np.zeros(len(bins))
    for g in GAMES:
        for s in events(g)["shots"]:
            if s["fouled"] or s["distance"] is None or s["distance"] > 31:
                continue
            b = int(s["distance"] // 2)
            n[b] += 1
            pts[b] += (3 if s["three"] else 2) * s["outcome"]
    pps = np.where(n >= 15, pts / np.maximum(n, 1), 0)
    gd = np.hypot(grid[:, 0] - HX, grid[:, 1])
    w = np.array([pps[min(int(v // 2), len(bins) - 1)] if v < 31 else 0 for v in gd])
    w[(np.abs(grid[:, 1]) >= 21.65) & (grid[:, 0] < HX + 9.8)] = pps[11]   # corners are threes
    return w


def spacing_metrics(off, dfn, bh, grid, gval, thr):
    O, D = np.array(list(off.values())), np.array(list(dfn.values()))
    H = np.array([HX, 0.0])
    offball = {k: v for k, v in off.items() if k != bh}
    m = {"hull_area": geo.hull_area(O),
         "mean_pair": float(np.mean([np.linalg.norm(O[i] - O[j]) for i in range(5) for j in range(i + 1, 5)])),
         "n_out3": sum(geo.is_three(p) for p in offball.values())}
    zs = {}
    for p in off.values():
        z = geo.zone(p)
        zs[z] = zs.get(z, 0) + 1
    m["entropy"] = -sum(c / 5 * math.log2(c / 5) for c in zs.values())
    m["control"] = geo.floor_control(O, D, grid)
    m["control_w"] = geo.floor_control(O, D, grid, gval)
    b = off[bh]
    bdef = min(dfn, key=lambda k: math.dist(dfn[k], b))
    helpers = {k: v for k, v in dfn.items() if k != bdef}
    m["help_dist"] = min(geo.segdist(v, b, H) for v in helpers.values())
    m["def_depth"] = float(np.mean([math.hypot(v[0] - HX, v[1]) for v in helpers.values()]))
    m["n_shooters_out"] = sum(1 for k, p in offball.items() if geo.is_three(p) and thr(k)["credible"])
    m["w_stretch"] = sum(3 * thr(k)["p3"] for k, p in offball.items() if geo.is_three(p))
    m["bh_rim"] = math.hypot(b[0] - HX, b[1])
    return m


def main():
    grid = geo.frontcourt_grid()
    gval = value_map(grid)
    threat, L3 = shrunk_threat()
    alias = aliases()

    def thr(pid):
        return threat.get(alias.get(pid, pid), dict(p3=L3 * 0.85, pg=0, credible=False))

    rows = []
    for g in GAMES:
        ev = events(g)
        poss = {p["id"]: p for p in ev["possessions"]}
        ch = {c["id"]: c for c in ev["chances"]}
        snaps, seen = [], set()
        for p in ev["picks"]:                     # first pick of each chance
            if p["chanceId"] not in seen:
                seen.add(p["chanceId"])
                snaps.append((p["frame"], "pick", p, p["ballhandlerId"]))
        snaps += [(v["startFrame"], "drive", v, v["ballhandlerId"]) for v in ev["drives"]]
        snaps += [(s["startFrame"] - 25, "shot", s, s["shooterId"]) for s in ev["shots"]]
        frames = stream_frames(g, {f for f, *_ in snaps})
        for f, kind, e, bh in snaps:
            c = ch.get(e["chanceId"])
            if not c or c["transition"] or not c["usable"] or f < (c["frontcourtFrame"] or 10 ** 9):
                continue
            fr = frames.get(f)
            if not fr:
                continue
            pl = fr["homePlayers"] + fr["awayPlayers"]
            if len(pl) != 10 or sum(p["isDetected"] for p in pl) < 7:
                continue
            k = geo.attack_sign(poss[c["possessionId"]])
            pos = {p["playerId"]: (k * p["xyz"][0], k * p["xyz"][1]) for p in pl}
            offids = set(c["offPlayerIds"])
            off = {i: v for i, v in pos.items() if i in offids}
            dfn = {i: v for i, v in pos.items() if i not in offids}
            if len(off) != 5 or len(dfn) != 5 or bh not in off:
                continue
            if np.mean([v[0] for v in off.values()]) > -5:      # offense not set in the frontcourt
                continue
            r = dict(game=g, kind=kind, chance=c["id"], offTeam=c["offTeamId"], frame=f,
                     shotClock=fr["shotClock"], pts=c["ptsScored"],
                     **spacing_metrics(off, dfn, bh, grid, gval, thr))
            if kind == "drive":
                r.update(blowby=int(bool(e["blowby"])), rim_end=int(e["endType"] == "shotNearBasket"))
            if kind == "shot":
                r.update(good_loc=int(e["three"] or e["region"] == "ra"), def_dist=e["closestDefDist"],
                         shot_pts=(3 if e["three"] else 2) * e["outcome"])
            rows.append(r)
        print(f"{g}: {sum(1 for x in rows if x['game'] == g)} snapshots", flush=True)
    df = pd.DataFrame(rows)
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_pickle(CACHE / "snapshots.pkl")
    print(f"saved {len(df)} snapshots")


if __name__ == "__main__":
    main()
