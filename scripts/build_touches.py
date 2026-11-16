"""One pass over the tracking for every half-court touch.

For each touch: the ball handler, his defender for that action, the cushion series,
whether and when he was beaten, the defender's state 0.5 s after the catch, the help
picture at the catch and (for beats) at the crossing, and how fast help rotated.

Writes cache/touches.pkl, used by studies/beaten.py, help.py and shooter_types.py.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from acbtrack import geometry as geo  # noqa: E402
from acbtrack.config import CACHE, FPS, GAMES  # noqa: E402
from acbtrack.io import events, positions, stream_frames  # noqa: E402

HALF_SEC = 12   # frames after the catch where the closeout state is read (0.48 s)
TAIL = 25       # frames after the touch kept to see help rotate


def action_tags(ev):
    """touchId -> (action, defender id). The first table listed wins when a touch has several."""
    tag = {}

    def put(tid, name, defid):
        if tid and tid not in tag:
            tag[tid] = (name, defid)
    for c in ev["closeouts"]:
        put(c["touchId"], "closeout", c["ballhandlerDefId"])
    for p in ev["picks"]:
        put(p["touchId"], "pick", p["ballhandlerDefId"])
    for h in ev["handoffs"]:
        put(h["touchId"], "handoff", h.get("receiverDefId"))
    for x in ev["isolations"]:
        put(x["touchId"], "iso", x["ballhandlerDefId"])
    for x in ev["posts"]:
        put(x["touchId"], "post", x["ballhandlerDefId"])
    for x in ev["off_ball_screens"]:
        put(x["touchId"], "offball_screen", x.get("cutterDefId"))
    return tag


def touch_row(g, t, c, poss, ctx, defid, fr, drv, sht):
    a = t["startFrame"]
    b = max(t["endFrame"], a + 13)
    H = geo.hoop_for(poss)
    att = t["playerId"]
    n = b - a + 1
    A = np.full((n, 2), np.nan)
    D = np.full((n, 2), np.nan)
    det = np.zeros(n, int)
    for k, f in enumerate(range(a, b + 1)):
        P = positions(fr.get(f))
        if att in P and defid in P:
            A[k], D[k] = P[att][:2], P[defid][:2]
            det[k] = P[att][2] and P[defid][2]
    if np.isnan(A[:, 0]).mean() > 0.3:
        return None
    sm = geo.cushion(A, D, H)
    vA, vD = geo.rimward_speed(A, H), geo.rimward_speed(D, H)
    dv, s = drv.get(t["id"]), sht.get(t["id"])
    o = t["outcomes"] or []
    r = dict(game=g, touch=t["id"], chance=c["id"], off=t["offTeamId"], att=att, dfn=defid, ctx=ctx,
             period=c["period"], dur=(t["endFrame"] - t["startFrame"]) / FPS, pts=c["ptsScored"],
             start_cush=float(np.nanmean(sm[:3])),
             drive=int(dv is not None), sk_blowby=(int(bool(dv["blowby"])) if dv else None),
             drive_end=(dv["endType"] if dv else None),
             shot=int(s is not None), three=int(bool(s and s["three"])),
             own_pts=((3 if s["three"] else 2) * s["outcome"]) if s else 0,
             rim_shot=int(bool(s and s["region"] == "ra")),
             how=("shot" if s else "pass" if any(z.startswith(("PASS", "AST")) for z in o)
                  else "turnover" if "TO" in o else "other"))
    k = HALF_SEC
    if not np.isnan(A[k, 0]) and not np.isnan(D[k - 3, 0]):
        r["dist05"] = float(np.linalg.norm(A[k] - D[k]))
        r["closing05"] = geo.closing_speed(A, D, k)

    # help picture at the catch
    others = [p for p in c["defPlayerIds"] if p != defid]
    P0 = positions(fr.get(a))
    if att in P0:
        hs = [np.array(P0[o][:2]) for o in others if o in P0]
        if len(hs) >= 3:
            A0 = np.array(P0[att][:2])
            r["lane_catch"] = min(geo.segdist(h, A0, H) for h in hs)
            r["help_home"] = int(any(geo.segdist(h, A0, H) < 4 and np.linalg.norm(h - H) < 15 for h in hs))

    cross = geo.crossing(sm, det, 1.0, 5)
    r["beaten"] = int(cross is not None)
    r["beaten_strict"] = int(geo.crossing(sm, det, 2.0, 8) is not None)
    if cross is not None:
        j = geo.attack_start(cross, vA, vD)
        r.update(lead=(cross - j) / FPS, attack_t=j / FPS, cross_t=cross / FPS,
                 def_v_rim=float(vD[j]), att_v_rim=float(vA[j]))
        # help at the crossing, and how fast a helper got goal-side afterwards
        Pc = positions(fr.get(a + cross))
        if att in Pc:
            hs = [np.array(Pc[o][:2]) for o in others if o in Pc]
            if len(hs) >= 3:
                st = geo.help_state(Pc[att][:2], hs, H)
                r.update(c_path=st["path"], c_wall=st["wall"], c_inkey=st["inkey"], c_rim=st["rim"])
                t_help = None
                for f in range(a + cross, t["endFrame"] + TAIL + 1):
                    P = positions(fr.get(f))
                    if att not in P:
                        continue
                    Af = np.array(P[att][:2])
                    rimA = np.linalg.norm(Af - H)
                    if any(o in P and np.linalg.norm(np.array(P[o][:2]) - H) < rimA
                           and geo.segdist(P[o][:2], Af, H) < 4 and np.linalg.norm(np.array(P[o][:2]) - Af) < 6
                           for o in others):
                        t_help = (f - a - cross) / FPS
                        break
                r["t_help"] = t_help
    return r


def main():
    rows = []
    for g in GAMES:
        ev = events(g)
        ch = {c["id"]: c for c in ev["chances"]}
        poss = {p["id"]: p for p in ev["possessions"]}
        tag = action_tags(ev)
        drv, sht = {}, {}
        for x in ev["drives"]:
            drv.setdefault(x["touchId"], x)
        for x in ev["shots"]:
            sht.setdefault(x["touchId"], x)
        jobs, need = [], set()
        for t in ev["touches"]:
            c = ch.get(t["chanceId"])
            # half court only: usable, not transition, touch after the ball crossed half court
            if not c or c["transition"] or not c["usable"] or c["frontcourtFrame"] is None \
                    or t["startFrame"] < c["frontcourtFrame"]:
                continue
            ctx, defid = tag.get(t["id"], ("other", None))
            defid = defid or t["defenderId"]
            if defid is None:
                continue
            jobs.append((t, c, ctx, defid))
            need.update(range(t["startFrame"] - 3, max(t["endFrame"], t["startFrame"] + 13) + TAIL + 1))
        fr = stream_frames(g, need)
        n0 = len(rows)
        for t, c, ctx, defid in jobs:
            r = touch_row(g, t, c, poss[c["possessionId"]], ctx, defid, fr, drv, sht)
            if r:
                rows.append(r)
        print(f"{g}: {len(rows) - n0} touches", flush=True)
    df = pd.DataFrame(rows)
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_pickle(CACHE / "touches.pkl")
    print(f"saved {len(df)} touches -> {CACHE / 'touches.pkl'}")


if __name__ == "__main__":
    main()
