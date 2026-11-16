"""Study 1: which spacing measures predict outcomes?

Ten measures at three levels (offense shape, floor control, defensive stretch), each
standardized and regressed on outcomes with shot-clock, ball-position and team controls.
Chance level uses one snapshot per chance (the earliest).
"""
import pandas as pd

from _common import load, out
from acbtrack.stats import effect, ols, write_table

METRICS = [("hull_area", "Shape"), ("mean_pair", "Shape"), ("n_out3", "Shape"), ("entropy", "Shape"),
           ("control", "Control"), ("control_w", "Control"),
           ("help_dist", "Stretch"), ("def_depth", "Stretch"), ("n_shooters_out", "Stretch"), ("w_stretch", "Stretch")]
OUTCOMES = [("pick", "pts", "Pick: chance points"), ("drive", "blowby", "Drive: SkillCorner blowby"),
            ("drive", "rim_end", "Drive: ends at rim"), ("drive", "pts", "Drive: chance points"),
            ("shot", "good_loc", "Shot: at rim or three"), ("shot", "def_dist", "Shot: defender distance (ft)"),
            ("shot", "shot_pts", "Shot: points")]


def main():
    r = load("snapshots")
    r["sc"] = pd.cut(r.shotClock.fillna(24), [-1, 4, 8, 14, 30], labels=["0-4", "4-8", "8-14", "14+"]).astype(str)

    # one snapshot per chance -> points per chance
    d = r.sort_values("frame").drop_duplicates("chance").copy()
    rows = []
    for m, level in METRICS:
        d["z"] = (d[m] - d[m].mean()) / d[m].std()
        b, lo, hi, p = effect(ols("pts ~ z + C(sc) + bh_rim + C(offTeam)", d), "z")
        q = pd.qcut(d[m].rank(method="first"), 3, labels=False)
        rows.append(dict(level=level, measure=m, effect_per_sd=b, ci_low=lo, ci_high=hi, p=p,
                         top_minus_bottom_third=d.pts[q == 2].mean() - d.pts[q == 0].mean()))
    t = pd.DataFrame(rows)
    write_table(t, out("spacing_chance_points"), f"Points per chance (n = {len(d)} chances, mean {d.pts.mean():.2f})")
    print(t.round(3).to_string(index=False))

    # every snapshot type x outcome
    rows = []
    for kind, y, label in OUTCOMES:
        s = r[r.kind == kind].dropna(subset=[y]).copy()
        for m, level in METRICS:
            s["z"] = (s[m] - s[m].mean()) / s[m].std()
            b, lo, hi, p = effect(ols(f"{y} ~ z + C(sc) + bh_rim + C(offTeam)", s, cluster="chance"), "z")
            rows.append(dict(outcome=label, n=len(s), measure=m, effect_per_sd=b, ci_low=lo, ci_high=hi, p=p))
    t2 = pd.DataFrame(rows)
    write_table(t2, out("spacing_all_outcomes"), "Every measure x outcome (per 1 SD, clustered by chance)")
    print(f"\n{(t2.p < .05).sum()} of {len(t2)} tests with p < .05 (about {len(t2) * .05:.1f} expected by chance)")


if __name__ == "__main__":
    main()
