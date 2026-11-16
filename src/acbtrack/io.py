"""Reading SkillCorner files.

Tracking files are ~150k frames per game (one JSON object per line, gzipped).
Analyses only need a few thousand frames, so `stream_frames` scans the file and
fully parses only the requested frame indices.
"""
import gzip
import json

from .config import DATA, TRACKING


def events(game_id):
    """All Dynamic Events tables for a game, keyed by table name."""
    return json.load(open(DATA / "matches" / str(game_id) / f"{game_id}_dynamic_events.json"))


def game_data(game_id):
    """Game metadata and both rosters."""
    return json.load(open(DATA / "matches" / str(game_id) / f"{game_id}_game_data.json"))


def tracking_path(game_id):
    """The downloaded tracking file, falling back to the repo copy if it is not an LFS pointer."""
    p = TRACKING / f"{game_id}_tracking_data.jsonl.gz"
    if p.exists():
        return p
    repo = DATA / "matches" / str(game_id) / f"{game_id}_tracking_data.jsonl.gz"
    if repo.exists() and repo.stat().st_size > 10_000:
        return repo
    raise FileNotFoundError(f"Tracking for game {game_id} not found. Run scripts/download_tracking.py first.")


def stream_frames(game_id, need):
    """Return {frameIdx: parsed frame} for the frame indices in `need`."""
    need = set(need)
    out = {}
    with gzip.open(tracking_path(game_id), "rt") as fh:
        for line in fh:
            i = line.find('"frameIdx":')
            fi = int(line[i + 11: line.find(",", i)])  # read the index without parsing the line
            if fi in need:
                out[fi] = json.loads(line)
    return out


def positions(frame):
    """{playerId: (x, y, isDetected, speed)} for one parsed frame (empty on dead-ball frames)."""
    if not frame:
        return {}
    return {p["playerId"]: (p["xyz"][0], p["xyz"][1], p["isDetected"], p["speed"])
            for p in frame["homePlayers"] + frame["awayPlayers"]}


def roster(game_id):
    """{playerId: dict(name, last, jersey, team)} plus {teamId: teamName}."""
    g = game_data(game_id)
    players, teams = {}, {}
    for side in ("homeTeam", "awayTeam"):
        teams[g[side]["teamId"]] = g[side]["teamName"]
        for p in g[side]["players"]:
            players[p["playerId"]] = dict(name=f"{p['firstName']} {p['lastName']}", last=p["lastName"],
                                          jersey=p["jersey"], team=g[side]["teamId"])
    return players, teams
