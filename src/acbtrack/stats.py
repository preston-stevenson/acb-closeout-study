"""Small statistics helpers used by the studies."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import fisher_exact


def ols(formula, df, cluster=None):
    """Least squares with robust errors; clustered when `cluster` names a column
    (e.g. 'chance', because several snapshots can come from one possession)."""
    d = df.dropna(subset=[c for c in df.columns if c in formula])
    if cluster:
        return smf.ols(formula, d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d[cluster])[0]})
    return smf.ols(formula, d).fit(cov_type="HC1")


def effect(fit, term):
    """(coefficient, ci_low, ci_high, p) for one term."""
    lo, hi = fit.conf_int().loc[term]
    return float(fit.params[term]), float(lo), float(hi), float(fit.pvalues[term])


def boot_ci(x, n=3000, seed=0):
    """Mean with a bootstrap 95% interval."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    rng = np.random.default_rng(seed)
    bs = [rng.choice(x, len(x)).mean() for _ in range(n)]
    return x.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def fisher(a, b):
    """Two-sided Fisher exact test on two 0/1 arrays."""
    a, b = np.asarray(a), np.asarray(b)
    return fisher_exact([[a.sum(), len(a) - a.sum()], [b.sum(), len(b) - b.sum()]])[1]


def n_per_group(sd, gap, alpha_z=1.96, power_z=0.84):
    """Plays needed per group to detect `gap` with 80% power."""
    return int(2 * ((alpha_z + power_z) * sd / gap) ** 2)


def write_table(df, path, title=None, floatfmt=".3f"):
    """Save a table as CSV plus a Markdown copy for reading."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path.with_suffix(".csv"), index=False)
    with open(path.with_suffix(".md"), "w") as f:
        if title:
            f.write(f"## {title}\n\n")
        f.write(df.to_markdown(index=False, floatfmt=floatfmt))
        f.write("\n")
