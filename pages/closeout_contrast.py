"""Build the side-by-side closeout page: three closeouts where the defender flew out and got
beaten, three where he stayed under control and held, synced to the catch.

Needs cache/touches.pkl (scripts/build_touches.py).
Usage:  python pages/closeout_contrast.py   ->  pages/out/closeout-contrast.html
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
from acbtrack import geometry as geo  # noqa: E402
from acbtrack.config import CACHE, FPS  # noqa: E402
from acbtrack.io import events, game_data, roster, stream_frames  # noqa: E402

CLIPS = [("flew", "touch-191313-4-559"), ("flew", "touch-184439-3-396"), ("flew", "touch-179612-4-722"),
         ("control", "touch-179612-3-478"), ("control", "touch-184439-4-524"), ("control", "touch-178442-4-518")]


def clip(kind, x, ev, fr, players, teams, gd_date):
    T = {t["id"]: t for t in ev["touches"]}
    ch = {c["id"]: c for c in ev["chances"]}
    poss = {p["id"]: p for p in ev["possessions"]}
    co = {c["touchId"]: c for c in ev["closeouts"]}
    sh = {s["touchId"]: s for s in ev["shots"]}
    dr = {v["touchId"]: v for v in ev["drives"]}
    t, cc = T[x.touch], ch[x.chance]
    a, b = co[x.touch]["startFrame"] - 6, t["endFrame"] + 30
    k = geo.attack_sign(poss[cc["possessionId"]])
    att, dfn, offT = int(x.att), int(x.dfn), cc["offTeamId"]
    ids = sorted({p["playerId"] for f in range(a, b + 1) if f in fr for p in fr[f]["homePlayers"] + fr[f]["awayPlayers"]})
    tracks, ball, clock = {i: [] for i in ids}, [], []
    for f in range(a, b + 1):
        z = fr.get(f)
        pos = {p["playerId"]: p for p in (z["homePlayers"] + z["awayPlayers"])} if z else {}
        for i in ids:
            p = pos.get(i)
            tracks[i].append(None if not p else [round(k * p["xyz"][0], 2), round(k * p["xyz"][1], 2), int(p["isDetected"])])
        bx = z["ball"].get("xyz") if z else None
        ball.append(None if not bx else [round(k * bx[0], 2), round(k * bx[1], 2), round(bx[2], 2)])
        clock.append([z["gameClock"] if z else None, z["shotClock"] if z else None])
    H = np.array([-40.76, 0.0])
    A = np.array([v[:2] if v else [np.nan] * 2 for v in tracks[att]], float)
    D = np.array([v[:2] if v else [np.nan] * 2 for v in tracks[dfn]], float)
    det = np.array([(u[2] if u else 0) and (v[2] if v else 0) for u, v in zip(tracks[att], tracks[dfn])])
    cush = geo.cushion(A, D, H)
    dD = D[1:] - D[:-1]
    u = A[1:] - D[1:]
    u = u / np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-6)
    closing = geo.smooth(np.r_[np.nan, (dD * u).sum(1) * FPS], 7)
    vA, vD = geo.rimward_speed(A, H), geo.rimward_speed(D, H)
    catch, end = t["startFrame"] - a, t["endFrame"] - a
    cr = geo.crossing(np.r_[np.full(catch, np.nan), cush[catch:end + 1]], det, 1.0, 5)
    beat = geo.attack_start(cr, vA, vD, floor=catch) if cr is not None else None
    s, dv = sh.get(x.touch), dr.get(x.touch)
    if s:
        if s["outcome"]:
            res = "Made " + ("three" if s["three"] else "layup" if s["region"] == "ra" else "two")
        else:
            res = "Missed " + ("three" if s["three"] else "shot")
    else:
        o = t["outcomes"] or []
        res = "Passed" if any(z.startswith(("PASS", "AST")) for z in o) else ("Turnover" if "TO" in o else "No shot")
    clean = lambda arr: [None if np.isnan(v) else round(float(v), 2) for v in arr]  # noqa: E731
    return dict(kind=kind, id=x.touch, date=gd_date, period=cc["period"], offTeam=teams[offT], defTeam=teams[cc["defTeamId"]],
                att=att, dfn=dfn, attName=players[att]["name"], dfnName=players[dfn]["name"],
                players={str(i): dict(last=players[i]["last"], jersey=players[i]["jersey"], off=int(players[i]["team"] == offT)) for i in ids},
                ids=ids, tracks={str(i): tracks[i] for i in ids}, ball=ball, clock=clock, cush=clean(cush), closing=clean(closing),
                catch=catch, end=end, beat=beat, cross=cr, closing05=round(float(x.closing05), 1), dist05=round(float(x.dist05), 1),
                result=res, drive_end=dv["endType"] if dv else None)


def main():
    touches = pd.read_pickle(CACHE / "touches.pkl").set_index("touch")
    out = []
    by_game = {}
    for kind, tid in CLIPS:
        by_game.setdefault(int(tid.split("-")[1]), []).append((kind, tid))
    for g, lst in by_game.items():
        ev = events(g)
        players, teams = roster(g)
        date = game_data(g)["date"][:10]
        co = {c["touchId"]: c for c in ev["closeouts"]}
        T = {t["id"]: t for t in ev["touches"]}
        need = set()
        for _, tid in lst:
            need.update(range(co[tid]["startFrame"] - 6, T[tid]["endFrame"] + 31))
        fr = stream_frames(g, need)
        for kind, tid in lst:
            x = touches.loc[tid].copy()
            x["touch"] = tid
            out.append(clip(kind, x, ev, fr, players, teams, date))
    out.sort(key=lambda c: [t for _, t in CLIPS].index(c["id"]))
    tpl = (HERE / "templates" / "closeout_contrast.html").read_text()
    (HERE / "out").mkdir(exist_ok=True)
    path = HERE / "out" / "closeout-contrast.html"
    path.write_text(tpl.replace("__DATA__", json.dumps(out, separators=(",", ":"))))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
