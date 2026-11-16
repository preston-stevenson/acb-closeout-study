"""Study 5: closeouts by shooter type.

Q1: do ACB defenders close out differently by type?
Q2: within each type, does getting there (within 6 ft 0.5 s after the catch) work better?
Robustness: (A) defender closer than the median at the catch, which is set before the shooter
decides; (B) tight at 0.5 s, only touches held 0.6 s or longer, so quick releases can't make a
closeout look loose.
"""
import pandas as pd
from scipy.stats import kruskal

from _common import load, out
from acbtrack.players import aliases, shooter_types
from acbtrack.stats import effect, ols, write_table

ORDER = ["Korver", "Curry", "Westbrook", "Rondo", "Low threat"]


def main():
    types = shooter_types()
    alias = aliases()
    summary = types.groupby("type").agg(players=("player_name", "size"), three_pg=("three_pg", "median"),
                                        three_pct=("p3", "median"), drives_pg=("drives_pg", "median")).reindex(ORDER).reset_index()
    write_table(summary, out("types_players"), f"Shooter types (players with 8+ games, n = {len(types)})")
    print(summary.round(3).to_string(index=False))

    t = load("touches")
    co = load("closeouts")[["touch", "endDist", "touchDist"]].drop_duplicates("touch")
    q = t[~(t.start_cush <= 1.0) & (t.ctx == "closeout")].dropna(subset=["closing05", "dist05"]).merge(co, on="touch")
    q["type"] = q.att.map(lambda a: types["type"].get(alias.get(int(a), int(a)), "Unclassified"))
    q = q[q.type != "Unclassified"].copy()

    rows = []
    for ty in ORDER:
        g = q[q.type == ty]
        rows.append(dict(type=ty, n=len(g), end_dist=g.endDist.median(), dist_05s=g.dist05.median(),
                         closing_05s=g.closing05.median(), takes_three=g.three.mean(), drives=g.drive.mean(),
                         beaten=g.beaten.mean()))
    t1 = pd.DataFrame(rows)
    p_d = kruskal(*[q[q.type == ty].endDist.dropna() for ty in ORDER]).pvalue
    p_s = kruskal(*[q[q.type == ty].closing05 for ty in ORDER]).pvalue
    write_table(t1, out("types_how_defenders_close"),
                f"Q1: closeouts by catcher type (Kruskal p: distance {p_d:.2f}, speed {p_s:.2f})")
    print(t1.round(2).to_string(index=False), f"\nKruskal p: distance {p_d:.2f}, speed {p_s:.2f}")

    q["tight"] = (q.dist05 < 6).astype(int)
    q["close_at_catch"] = (q.touchDist < q.touchDist.median()).astype(int)
    held = q[q.dur >= 0.6]
    rows = []
    for ty in ORDER:
        g = held[held.type == ty]
        T, L = g[g.tight == 1], g[g.tight == 0]
        rows.append(dict(type=ty, n=len(g), n_tight=len(T),
                         three_tight=T.three.mean(), three_loose=L.three.mean(),
                         drive_tight=T.drive.mean(), drive_loose=L.drive.mean(),
                         beaten_tight=T.beaten.mean(), beaten_loose=L.beaten.mean(),
                         own_pts_tight=T.own_pts.mean(), own_pts_loose=L.own_pts.mean(),
                         chance_pts_tight=T.pts.mean(), chance_pts_loose=L.pts.mean()))
    t2 = pd.DataFrame(rows)
    write_table(t2, out("types_tight_vs_loose"), "Q2: tight vs loose by type (touches held 0.6 s+)")
    print(t2.round(2).to_string(index=False))

    rows = []
    for label, d, x in [("A: closer than median at the catch", q, "close_at_catch"), ("B: tight at 0.5 s, held 0.6 s+", held, "tight")]:
        for y in ("three", "beaten", "own_pts", "pts"):
            b, lo, hi, p = effect(ols(f"{y} ~ {x} + C(type) + C(game)", d), x)
            rows.append(dict(version=label, outcome=y, effect=b, ci_low=lo, ci_high=hi, p=p))
    t3 = pd.DataFrame(rows)
    write_table(t3, out("types_pooled"), "Pooled effect of getting there, with type and game controls")
    print(t3.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
