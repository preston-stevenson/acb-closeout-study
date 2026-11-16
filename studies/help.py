"""Study 4: does help defence erase the beat?

For each on-ball beat: help at the crossing, how fast a helper got goal-side, where the beat
happened, and what it produced. Then the closeout test: defender speed x help set at the catch.
"""
import numpy as np
import pandas as pd

from _common import load, out
from acbtrack.stats import boot_ci, effect, n_per_group, ols, write_table


def main():
    r = load("touches")
    q = r[~(r.start_cush <= 1.0)].copy()
    b = q[(q.beaten == 1) & q.c_path.notna()].copy()
    b["helper_set"] = (b.c_wall > 0).astype(int)
    print(f"{len(b)} beats | helper already goal-side at the crossing {b.helper_set.mean() * 100:.0f}% | "
          f"median helper distance to the lane {b.c_path.median():.1f} ft | help arrives {b.t_help.notna().mean() * 100:.0f}% "
          f"(median {b.t_help.median():.2f} s) | median crossing {b.c_rim.median():.1f} ft from the rim")

    rows = []
    for label, s in [("Within 20 ft of rim", b[b.c_rim < 20]), ("20+ ft from rim", b[b.c_rim >= 20])]:
        shots = s[s.how == "shot"]
        rows.append(dict(beat_location=label, n=len(s), helper_set=s.helper_set.mean(), chance_pts=s.pts.mean(),
                         own_shots_at_rim=shots.rim_shot.mean(),
                         pts_no_helper=s[s.helper_set == 0].pts.mean(), n_no_helper=(s.helper_set == 0).sum(),
                         pts_helper=s[s.helper_set == 1].pts.mean()))
    t = pd.DataFrame(rows)
    write_table(t, out("help_by_location"), f"Beats by location (not-beaten touches: {q[q.beaten == 0].pts.mean():.2f} pts per chance)")
    print(t.round(2).to_string(index=False))
    s = b[b.c_rim < 20].copy()
    s["no_helper"] = 1 - s.helper_set
    e = effect(ols("pts ~ no_helper + C(ctx)", s), "no_helper")
    print(f"inside 20 ft, no helper set: {e[0]:+.2f} pts (p={e[3]:.3f})")

    g = b.groupby("ctx")
    t = pd.DataFrame({"beats": g.size(), "crossed_20ft_plus": g.apply(lambda x: (x.c_rim >= 20).mean()),
                      "helper_set": g.helper_set.mean(), "chance_pts": g.pts.mean()}).reset_index()
    write_table(t, out("help_by_action"), "Beats by action")

    # closeouts: speed 0.5 s after the catch x help set at the catch
    c = q[(q.ctx == "closeout") & q.closing05.notna() & q.help_home.notna()].copy()
    c["fast"] = (c.closing05 >= c.closing05.median()).astype(int)
    c["beat_inside20"] = ((c.beaten == 1) & (c.c_rim < 20)).astype(int)
    rows = []
    for (h, f), g2 in c.groupby(["help_home", "fast"]):
        m, lo, hi = boot_ci(g2.pts)
        rows.append(dict(help_at_catch="home" if h else "not set", closeout="fast" if f else "slow", n=len(g2),
                         takes_three=g2.three.mean(), beaten=g2.beaten.mean(), beaten_inside_20ft=g2.beat_inside20.mean(),
                         chance_pts=m, ci_low=lo, ci_high=hi))
    t = pd.DataFrame(rows)
    write_table(t, out("help_x_closeout_speed"), f"Closeouts: speed x help at the catch (split at {c.closing05.median():.1f} ft/s)")
    print(t.round(2).to_string(index=False))
    for y in ("pts", "beaten", "three"):
        fit = ols(f"{y} ~ fast*help_home + dist05 + C(game)", c)
        print(f"  {y}: interaction {fit.params['fast:help_home']:+.3f} (p={fit.pvalues['fast:help_home']:.2f}); "
              f"fast {fit.params['fast']:+.3f} (p={fit.pvalues['fast']:.3f})")
    sd = c.pts.std()
    print(f"noise floor: points SD {sd:.2f}; 95% CI at n=120 is +/-{1.96 * sd / np.sqrt(120):.2f}; "
          f"{n_per_group(sd, 0.15)} per group to detect 0.15 pts")


if __name__ == "__main__":
    main()
