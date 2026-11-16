"""Study 3: the beaten rule on every half-court touch.

On-ball sample = touches where the defender was goal-side by more than 1 ft at the catch
(players who caught it already past their man, mostly cutters and post seals, are excluded).
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from _common import load, out
from acbtrack.stats import effect, fisher, ols, write_table


def main():
    r = load("touches")
    q = r[~(r.start_cush <= 1.0)].copy()
    print(f"{len(r)} half-court touches; {len(r) - len(q)} caught already level or past; on-ball {len(q)}, "
          f"beaten {q.beaten.sum()} ({q.beaten.mean() * 100:.1f}%), strict {q.beaten_strict.sum()}")

    g = q.groupby("ctx")
    dr = q[q.drive == 1]
    t = pd.DataFrame({"touches": g.size(), "beaten": g.beaten.mean(), "beaten_strict": g.beaten_strict.mean(),
                      "drives": dr.groupby("ctx").size(), "beaten_per_drive": dr.groupby("ctx").beaten.mean()}
                     ).reset_index().sort_values("touches", ascending=False)
    write_table(t, out("beaten_by_action"), f"Beaten rate by action (on-ball touches, n = {len(q)})")
    print(t.round(3).to_string(index=False))

    # timing: attack start -> crossing
    b = q[q.beaten == 1]
    lead = b.lead.describe()
    moving_out = (b.def_v_rim < 0)
    t = pd.DataFrame([dict(beats=len(b), lead_median=lead["50%"], lead_q25=lead["25%"], lead_q75=lead["75%"],
                           defender_moving_away_from_rim=moving_out.mean(),
                           defender_moving_away_closeouts=moving_out[b.ctx == "closeout"].mean())])
    write_table(t, out("beaten_timing"), "Attack start to crossing (s); defender direction at attack start")
    print(t.round(3).to_string(index=False))

    # agreement with SkillCorner's blowby flag on drives
    ct = pd.crosstab(dr.sk_blowby, dr.beaten).reset_index()
    ct.columns = ["sk_blowby", "ours_not_beaten", "ours_beaten"]
    write_table(ct, out("beaten_vs_skillcorner"), "SkillCorner blowby vs our rule on drives")

    # momentum: defender still closing 0.5 s after the catch, drives without a screen
    rows = []
    for label, sub in [("All drives", dr), ("Drives without a screen", dr[~dr.ctx.isin(["pick", "handoff", "offball_screen"])]),
                       ("Pick/handoff drives", dr[dr.ctx.isin(["pick", "handoff"])])]:
        s = sub.dropna(subset=["closing05"])
        m = s.closing05.median()
        f, sl = s[s.closing05 >= m], s[s.closing05 < m]
        for col in ("beaten", "beaten_strict"):
            rows.append(dict(sample=label, rule=col, split_ft_s=m, fast=f[col].mean(), n_fast=len(f),
                             slow=sl[col].mean(), n_slow=len(sl), p=fisher(f[col], sl[col])))
    t = pd.DataFrame(rows)
    write_table(t, out("beaten_momentum"), "Beaten when he drives: defender still closing fast vs slowed (Fisher exact)")
    print(t.round(3).to_string(index=False))
    s = dr[~dr.ctx.isin(["pick", "handoff", "offball_screen"])].dropna(subset=["closing05", "dist05"])
    lg = smf.logit("beaten ~ closing05 + dist05 + C(ctx)", s).fit(disp=0)
    print(f"logit (no-screen drives): odds x{np.exp(3 * lg.params.closing05):.2f} per +3 ft/s (p={lg.pvalues.closing05:.4f}); "
          f"distance p={lg.pvalues.dist05:.2f}")

    # do beats score?
    bb, lo, hi, p = effect(ols("pts ~ beaten + C(ctx) + dur + C(game)", q, cluster="chance"), "beaten")
    print(f"chance points, beaten vs not: {q[q.beaten == 1].pts.mean():.2f} vs {q[q.beaten == 0].pts.mean():.2f}; "
          f"controlled {bb:+.3f} [{lo:+.3f}, {hi:+.3f}] p={p:.3f}")


if __name__ == "__main__":
    main()
