"""Study 2: closeout distance and speed vs what the catcher does next.

Uses SkillCorner's closeout events: `endDistance` is the defender-to-catcher gap when the
closeout ends; defender speed at that frame comes from tracking. Half-court only.
"""
import pandas as pd

from _common import load, out
from acbtrack.stats import boot_ci, ols, write_table


def summarize(r, by):
    rows = []
    for b, g in r.groupby(by, observed=True):
        m, lo, hi = boot_ci(g.pts)
        drives = g[g.drive == 1]
        threes = g[g.shot_three == 1]
        rows.append({by: str(b), "n": len(g), "shoots": (g.action == "shot").mean(), "drives": g.drive.mean(),
                     "blowby_per_drive": drives.blowby.mean() if len(drives) else None, "n_drives": len(drives),
                     "three_pct": threes.made.mean() if len(threes) else None,
                     "chance_pts": m, "ci_low": lo, "ci_high": hi})
    return pd.DataFrame(rows)


def main():
    r = load("closeouts")
    r = r[(r.transition == False) & r.endDist.notna() & r.defSpeed.notna()].copy()  # noqa: E712
    r["dbin"] = pd.cut(r.endDist, [0, 3, 4.5, 6, 8, 30], labels=["<3", "3-4.5", "4.5-6", "6-8", "8+"])
    r["sbin"] = pd.cut(r.defSpeed, [0, 5, 8, 11, 30], labels=["<5", "5-8", "8-11", "11+"])

    t = summarize(r, "dbin")
    write_table(t, out("closeout_by_distance"), f"By end-of-closeout distance (n = {len(r)})")
    print(t.round(2).to_string(index=False))
    t = summarize(r, "sbin")
    write_table(t, out("closeout_by_speed"), "By defender speed when the closeout ends (ft/s)")

    fit = ols('pts ~ C(dbin, Treatment("3-4.5")) + touchDist + three_loc + C(game)', r)
    terms = [k for k in fit.params.index if "dbin" in k]
    t = pd.DataFrame(dict(term=[k.split("[T.")[1].rstrip("]") for k in terms],
                          vs_3_to_4_5ft=[fit.params[k] for k in terms], p=[fit.pvalues[k] for k in terms]))
    write_table(t, out("closeout_distance_controlled"),
                "Chance points vs 3-4.5 ft, controlling start distance, two/three location and game")
    print(t.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
