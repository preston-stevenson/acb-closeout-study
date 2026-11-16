"""Season-level player profiles from SkillCorner's aggregate files (293 ACB games).

Shooter types follow a common college closeout framework:
  Korver    - high-volume, accurate shooter who rarely drives     (close out at all costs)
  Curry     - high-volume, accurate shooter who also drives       (get to his body, chop your feet)
  Westbrook - heavy driver, credible shooter                      (expect the drive, still contest)
  Rondo     - heavy driver, rare or poor shooter                  (give space, expect drive or pass)
  Low threat - everyone else (mostly bigs and low-usage players)
"""
import csv

import numpy as np
import pandas as pd

from .config import DATA

PRIOR_ATTEMPTS = 100   # shrink 3P% toward the league rate by this many imaginary attempts


def aliases():
    """playerId -> canonical playerId (9 players appear under two ids across the season)."""
    return {int(r["player_id"]): int(r["canonical_player_id"])
            for r in csv.DictReader(open(DATA / "player_id_aliases.csv"))}


def _load(fname, cols, alias):
    d = pd.read_csv(DATA / "aggregates" / fname)
    d = d[d.team_name != "total"].copy()          # per-team rows only; 'total' rows would double count
    d["pid"] = d.player_id.map(lambda x: alias.get(x, x))
    return d.groupby("pid").agg({**{c: "sum" for c in cols}, "player_name": "first"})


def season_profiles(min_games=8):
    alias = aliases()
    s = _load("acb_shotsaggregates_20252026.csv",
              ["games_played", "three_attempts", "three_mades", "cns_three_attempts"], alias)
    d = _load("acb_drivesaggregates_20252026.csv", ["total_drives"], alias)
    p = s.join(d[["total_drives"]], how="left").fillna(0)
    p = p[p.games_played >= min_games].copy()
    league3 = p.three_mades.sum() / p.three_attempts.sum()   # league rate among the players kept
    p["p3"] = (p.three_mades + PRIOR_ATTEMPTS * league3) / (p.three_attempts + PRIOR_ATTEMPTS)
    p["three_pg"] = p.three_attempts / p.games_played.clip(lower=1)
    p["drives_pg"] = p.total_drives / p.games_played.clip(lower=1)
    p.attrs["league3"] = league3
    return p


def shooter_types(min_games=8):
    """Add `shoot`, `drive` tiers and the closeout `type` to the season profiles."""
    p = season_profiles(min_games)
    L3 = p.attrs["league3"]
    p["shoot"] = np.select([(p.three_pg >= 2.5) & (p.p3 >= L3 + 0.01),
                            (p.three_pg >= 1.5) & (p.p3 >= L3 - 0.015)], ["high", "some"], "low")
    p["drive"] = np.where(p.drives_pg >= p.drives_pg.quantile(0.67), "high", "low")
    p["type"] = np.select([(p.shoot == "high") & (p.drive == "low"),
                           (p.shoot == "high") & (p.drive == "high"),
                           (p.shoot == "some") & (p.drive == "high"),
                           (p.shoot == "low") & (p.drive == "high")],
                          ["Korver", "Curry", "Westbrook", "Rondo"], "Low threat")
    return p


def shrunk_threat(min_games=0):
    """playerId -> dict(p3, pg, credible) used by the spacing study's shooter weighting."""
    p = season_profiles(min_games=min_games)
    L3 = p.attrs["league3"]
    return {pid: dict(p3=r.p3, pg=r.three_pg, credible=bool(r.three_pg >= 1.5 and r.p3 >= L3))
            for pid, r in p.iterrows()}, L3
