"""Build the single-play replay page: Huertas' pull-up three vs Real Madrid
(game 184439, chance 4-186), with the play-by-play and a frame-by-frame separation trace.

Usage:  python pages/huertas_replay.py   ->  pages/out/huertas-replay.html
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
from acbtrack.io import events, game_data, stream_frames  # noqa: E402

GAME, CHANCE = 184439, "chance-184439-4-186"
START, END = 131745, 132290              # frames: just before the inbound to ~1.3 s after the make
SHOOTER, PRIMARY_DEF = 59122, 34982      # Huertas, Campazzo
COVER = {"under": "goes under the screen", "over": "fights over the screen", "soft": "sags back", "show": "steps out to show"}


def main():
    g, d = game_data(GAME), events(GAME)
    c = next(x for x in d["chances"] if x["id"] == CHANCE)
    shot = next(s for s in d["shots"] if s["chanceId"] == CHANCE)
    players = {p["playerId"]: dict(side=side, jersey=p["jersey"], first=p["firstName"], last=p["lastName"])
               for side, t in (("home", "homeTeam"), ("away", "awayTeam")) for p in g[t]["players"]}
    nm = lambda i: players[int(i)]["last"]  # noqa: E731

    fr = stream_frames(GAME, range(START, END + 1))
    frames = [fr[f] for f in range(START, END + 1) if f in fr]
    ids = sorted({p["playerId"] for f in frames for p in f["homePlayers"] + f["awayPlayers"]})
    tracks, ball, clock = {i: [] for i in ids}, [], []
    for f in frames:
        pos = {p["playerId"]: p for p in f["homePlayers"] + f["awayPlayers"]}
        for i in ids:
            p = pos.get(i)
            tracks[i].append(None if p is None else [round(p["xyz"][0], 2), round(p["xyz"][1], 2), round(p["speed"], 1), p["isDetected"]])
        bx = f["ball"].get("xyz")
        ball.append(None if not bx else [round(v, 2) for v in bx])
        clock.append([round(f["gameClock"], 2), None if f["shotClock"] is None else round(f["shotClock"], 2)])

    ev = []
    for p in d["passes"]:
        if p["chanceId"] == CHANCE or (START <= p["startFrame"] < c["startFrame"] and p["offTeamId"] == c["offTeamId"]):
            ev.append(dict(frame=p["startFrame"], kind="pass", title=f"{nm(p['passerId'])} → {nm(p['receiverId'])}",
                           body="Inbound pass" if p["inbounds"] else "Pass", actors=[p["passerId"], p["receiverId"]]))
    for p in d["picks"]:
        if p["chanceId"] == CHANCE:
            ev.append(dict(frame=p["frame"], kind="pick", title=f"{nm(p['screenerId'])} screens for {nm(p['ballhandlerId'])}",
                           body=f"{nm(p['ballhandlerDefId'])} {COVER.get(p['bhrDefType'], p['bhrDefType'])}; "
                                f"{nm(p['screenerDefId'])} {COVER.get(p['scrDefType'], p['scrDefType'])}.",
                           actors=[p["ballhandlerId"], p["screenerId"]]))
    for p in d["off_ball_screens"]:
        if p["chanceId"] == CHANCE:
            ev.append(dict(frame=p.get("frame", p.get("startFrame")), kind="screen",
                           title=f"{nm(p['screenerId'])} screens for {nm(p['cutterId'])}",
                           body=f"Off-ball screen away from the ball; {nm(p['screenerDefId'])} guards the screener.",
                           actors=[p["cutterId"], p["screenerId"]]))
    ev.append(dict(frame=shot["startFrame"], kind="shot", title=f"{nm(shot['shooterId'])} pull-up three",
                   body=f"{shot['dribblesBefore']} dribbles, {shot['distance']:.1f} ft from the rim. Nearest defender "
                        f"{nm(shot['closestDefId'])} at {shot['closestDefDist']:.1f} ft, graded {shot['contestLevel']}.",
                   actors=[shot["shooterId"]]))
    ev.append(dict(frame=shot["endFrame"], kind="make", title="Good. Tenerife leads 86–81",
                   body="Tenerife extends a two-point lead to five with 2:30 left.", actors=[shot["shooterId"]]))
    ev.sort(key=lambda e: e["frame"])

    home = [i for i in ids if players[i]["side"] == "home"]
    sep, camp = [], []
    for k in range(len(frames)):
        h = tracks[SHOOTER][k]
        if not h:
            sep.append(None); camp.append(None); continue  # noqa: E702
        ds = [math.hypot(h[0] - tracks[i][k][0], h[1] - tracks[i][k][1]) for i in home if tracks[i][k]]
        sep.append(round(min(ds), 2))
        cp = tracks[PRIMARY_DEF][k]
        camp.append(round(math.hypot(h[0] - cp[0], h[1] - cp[1]), 2) if cp else None)

    data = dict(meta=dict(gameId=GAME, period=c["period"], homeScore=c["homeStartScore"], awayScore=c["awayStartScore"],
                          fps=25, startFrame=START, shotFrame=shot["startFrame"], makeFrame=shot["endFrame"],
                          shooter=SHOOTER, primaryDef=PRIMARY_DEF, offSide="away"),
                players={str(i): players[i] for i in ids}, ids=ids, tracks={str(i): tracks[i] for i in ids},
                ball=ball, clock=clock, events=ev, sep=sep, camp=camp)
    tpl = (HERE / "templates" / "huertas_replay.html").read_text()
    (HERE / "out").mkdir(exist_ok=True)
    path = HERE / "out" / "huertas-replay.html"
    path.write_text(tpl.replace("__DATA__", json.dumps(data, separators=(",", ":"))))
    print(f"wrote {path} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
