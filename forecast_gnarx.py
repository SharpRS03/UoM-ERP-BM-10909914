import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import re
import math
import itertools
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from gnarx_core import GNARX

# paths

ROOT = os.environ.get("AGL_ROOT", ".")


def P(*parts):
    return os.path.join(ROOT, *parts)


LEVELS_FILE  = P("Code Outputs", "Gap Interpolation Outputs",
                 "Unified_Interpolated_Levels.xlsx")
CLIMATE_FILE = P("Code Outputs", "Climate Data Extraction Outputs",
                 "Lake_Climate_Monthly.xlsx")
DMI_FILE     = P("Climate Indices", "dmi.csv")
LEADLAG_FILE = P("Code Outputs", "Climate EDA Outputs", "CLIM_06_delta_leadlag.csv")
ADJ_FILE     = P("Code Outputs", "CCM Outputs", "CCM_09_adjacency_top3_diff_train.csv")
BASE_PRED    = P("Code Outputs", "Baseline Outputs", "Baseline_predictions.csv")
FC4_FILE     = P("Code Outputs", "Forecast Var Outputs", "FC4_metrics.csv")
FC5_FILE     = P("Code Outputs", "SARIMAX Climate Outputs", "FC5_climate_metrics.csv")
FC6_FILE     = P("Code Outputs", "GNN Outputs", "FC6_gnn_metrics.csv")

OUT_DIR = P("Code Outputs", "GNARX Outputs")
os.makedirs(OUT_DIR, exist_ok=True)


def out(n):
    return os.path.join(OUT_DIR, n)



# canonical protocol constants 

START, END  = "1995-06-01", "2025-12-01"
TEST_MONTHS = 60
HORIZONS    = [1, 3, 6, 12]
EXPECTED_N  = {1: 60, 3: 58, 6: 55, 12: 49}

P_GRID      = [1, 2, 3]
MAX_STAGE   = 2
MODEL_TYPE  = "standard"      # node-specific alpha, shared beta and lambda
WEIGHTED    = True            # CCM rho-weighted neighbour means


def rmse(p, a):
    p, a = np.asarray(p, float), np.asarray(a, float)
    return float(np.sqrt(np.nanmean((p - a) ** 2)))


def mae(p, a):
    p, a = np.asarray(p, float), np.asarray(a, float)
    return float(np.nanmean(np.abs(p - a)))


print("=" * 74)
print("GNARX EVALUATION PIPELINE")
print("=" * 74)


# levels 

lev = pd.read_excel(LEVELS_FILE)
lev["Date"] = pd.to_datetime(lev["Date"])
L = (lev.pivot(index="Date", columns="Reservoir", values="Level_m")
        .sort_index().asfreq("MS").loc[START:END])
INTERP = (lev.pivot(index="Date", columns="Reservoir", values="is_interpolated")
             .sort_index().asfreq("MS").loc[START:END].astype(bool))

assert L.notna().all().all(), "NaNs in the canonical window"
LAKES = list(L.columns)
n = len(LAKES)
N = len(L)
split = N - TEST_MONTHS
targets = range(split, N)

assert N == 367, f"expected 367 months, got {N}"
assert split == 307, f"expected split at 307, got {split}"
print(f"\n[1] window {L.index[0].date()} .. {L.index[-1].date()}  "
      f"({N} months, {n} lakes, 0 NaNs)")
print(f"    training 1..{split}  test origins {split}..{N-1}")
print(f"    interpolated months inside the test window: "
      f"{int(INTERP.iloc[split:].values.sum())}  (expected 0)")


# differencing + per-lake training only seasonal climatology

dL = L.diff()                                   # row 0 is NaN by construction

# climatology of the differences, training rows only (rows 1..split-1)
_tr_d = dL.iloc[1:split]
seas_clim = _tr_d.groupby(_tr_d.index.month).mean()          # (12, n)
SEAS = pd.DataFrame(
    np.vstack([seas_clim.loc[m].values for m in L.index.month]),
    index=L.index, columns=LAKES)

dLd = dL - SEAS                                 # deseasonalised differences
D = dLd.values                                  # (N, n); row 0 is NaN
S = SEAS.values

print(f"\n[2] seasonal climatology from rows 1..{split-1} only "
      f"(training), per lake")

# exogenous blocks

clim = pd.read_excel(CLIMATE_FILE)
clim["Date"] = pd.to_datetime(clim["Date"])
wb = (clim.pivot(index="Date", columns="Reservoir", values="water_balance_mm")
          .sort_index().asfreq("MS").reindex(L.index))
assert list(wb.columns) == LAKES, "climate lake order differs from levels"


def deseason_train_only(df):
    base = df.iloc[:split]
    monthly = base.groupby(base.index.month).mean()
    clim_mat = np.vstack([monthly.loc[m].values for m in df.index.month])
    return df - clim_mat


WB = deseason_train_only(wb)
# scale so the shared lambda is not dominated by units (mm vs metres)
WB_SCALE = float(WB.iloc[:split].values.std())
WB = WB / WB_SCALE
WB = WB.ffill().fillna(0.0)


def parse_index(path):
    """NOAA-style index reader. -9999 sentinels become NaN."""
    if not os.path.exists(path):
        return None
    recs = []
    for line in open(path):
        t = re.split(r"[,\s]+", line.strip())
        if not t or t == [""]:
            continue
        m = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", t[0])
        if m and len(t) >= 2:
            try:
                recs.append((pd.Timestamp(int(m[1]), int(m[2]), 1), float(t[1])))
            except ValueError:
                pass
        elif len(t) == 13 and re.fullmatch(r"\d{4}", t[0]):
            try:
                for mo, v in enumerate([float(x) for x in t[1:]], 1):
                    recs.append((pd.Timestamp(int(t[0]), mo, 1), v))
            except ValueError:
                pass
    if not recs:
        return None
    s = pd.Series(dict(recs)).sort_index()
    s[s < -90] = np.nan
    return s.asfreq("MS")


dmi_raw = parse_index(DMI_FILE)
assert dmi_raw is not None, "DMI file could not be parsed"
dmi = dmi_raw.reindex(L.index).ffill().fillna(0.0)
assert dmi.notna().all(), "DMI has NaNs after ffill"
print(f"[3] DMI parsed: {dmi_raw.dropna().index[0].date()} .. "
      f"{dmi_raw.dropna().index[-1].date()}; "
      f"{int(dmi_raw.reindex(L.index).isna().sum())} months needed ffill "
      f"inside the window")

ll = pd.read_csv(LEADLAG_FILE).set_index("Lake")
DMI_LAG = {lk: int(ll.loc[lk, "DMI_peak_lag"]) for lk in LAKES}
print("    DMI lead lags (months): "
      + ", ".join(f"{lk.replace('Lake ','')}={DMI_LAG[lk]}" for lk in LAKES))
assert min(DMI_LAG.values()) >= 2, (
    "a DMI lead lag below 2 would make the lake-specific block require a "
    "value that is not yet observed at the forecast origin")


def build_dmi_block(dmi_series):
    """Z[t, i] = DMI[t - (lag_i - 1)].

    The design matrix applies exog_lags=(1,) on top, so the value actually
    entering the equation for time t is DMI[t - lag_i], exactly the lake's
    own lead lag from CLIM_06. Every lag is >= 2, so nothing unobserved at
    the origin is ever used.
    """
    v = np.asarray(dmi_series, float)
    Z = np.zeros((N, n))
    for i, lk in enumerate(LAKES):
        sh = DMI_LAG[lk] - 1
        Z[sh:, i] = v[:N - sh] if sh > 0 else v
        Z[:sh, i] = v[0]
    return Z


DMI_FULL = build_dmi_block(dmi)
WB_FULL = WB.values

# adjacency  (A[i, j] > 0 means j influences i; rows = influenced)

adj = pd.read_csv(ADJ_FILE, index_col=0)
adj.index = [str(x) for x in adj.index]
adj = adj.reindex(index=LAKES, columns=LAKES)
assert adj.notna().all().all(), "adjacency does not cover all seven lakes"
A = adj.values.astype(float)
assert (A >= 0).all(), "negative adjacency weights"
np.fill_diagonal(A, 0.0)
print(f"\n[4] adjacency {os.path.basename(ADJ_FILE)}  "
      f"{int((A > 0).sum())} directed edges")
print("    orientation: A[i,j]>0 means j influences i (rows = influenced). "
      "NOT transposed here - gnarx_core uses this convention natively.")
print("    in-degree : "
      + ", ".join(f"{lk.replace('Lake ','')}={int((A[i] > 0).sum())}"
                  for i, lk in enumerate(LAKES)))

# shared baseline

bp = pd.read_csv(BASE_PRED, parse_dates=["Origin_Date", "Target_Date"])
assert set(bp["Lake"]) == set(LAKES), "baseline lakes differ from this script's"
idx_of = {d: i for i, d in enumerate(L.index)}

preds, loaded = {}, 0
for r in bp.itertuples(index=False):
    if r.Model not in ("RandomWalk", "SARIMA"):
        continue
    t = idx_of.get(r.Target_Date)
    if t is None:
        continue
    preds[(r.Model, r.Lake, t, r.Horizon_m)] = r.Pred_m
    loaded += 1
expect = n * 2 * sum(EXPECTED_N.values())
print(f"\n[5] loaded {loaded} shared-baseline predictions "
      f"(RandomWalk + SARIMA), expected {expect}")
assert loaded == expect, "baseline window mismatch"

# ablation definitions

ABLATIONS = {
    "GNAR":         [],
    "GNARX_wb":     ["wb"],
    "GNARX_wb_dmi": ["wb", "dmi"],
}
EXOG_ARRAYS = {"wb": WB_FULL, "dmi": DMI_FULL}
EXOG_LAGS = (1,)


def s_grid(p):
    """Stage vectors of length p, entries in 0..MAX_STAGE, non-increasing,
    with at least one neighbour stage at lag 1."""
    g = []
    for s in itertools.product(range(MAX_STAGE + 1), repeat=p):
        if s[0] < 1:
            continue
        if any(s[k] > s[k - 1] for k in range(1, p)):
            continue
        g.append(list(s))
    return g


def exog_slices(keys, lo, hi):
    return [EXOG_ARRAYS[k][lo:hi] for k in keys]


def fit_gnarx(keys, p, s, lo, hi, adj=None):
    """Fit on rows [lo:hi) of the deseasonalised differenced series.

    `adj` defaults to the primary CCM adjacency. It is a parameter only so that
    gnarx_sensitivity.py can drive the same estimator and the same rolling loop
    with a different graph.
    """
    m = GNARX(A if adj is None else adj, p=p, s=s,
              exog_lags=EXOG_LAGS if keys else (),
              model_type=MODEL_TYPE, weighted=WEIGHTED)
    m.fit(D[lo:hi], Zex=exog_slices(keys, lo, hi) if keys else None,
          demean=True)
    return m


# order selection by BIC on the training portion only

print("\n[6] order selection by BIC (training rows 1..%d only)" % (split - 1))
CHOSEN, order_rows = {}, []
for name, keys in ABLATIONS.items():
    best = None
    for p in P_GRID:
        for s in s_grid(p):
            m = fit_gnarx(keys, p, s, 1, split)
            b = m.bic()
            order_rows.append({"Model": name, "p": p, "s": str(s),
                               "n_params": m.n_params_, "nobs": m.nobs_,
                               "AIC": round(m.aic(), 3), "BIC": round(b, 3)})
            if best is None or b < best[0]:
                best = (b, p, s, m)
    CHOSEN[name] = (best[1], best[2])
    print(f"    {name:14s} p={best[1]}  s={best[2]}  "
          f"params={best[3].n_params_}  BIC={best[0]:.2f}")

pd.DataFrame(order_rows).to_csv(out("FC7_gnarx_orders.csv"), index=False)

# rolling-origin forecasting

def future_exog(keys, o, H):
    outs = []
    for k in keys:
        if k == "wb":
            outs.append(np.zeros((H, n)))
        elif k == "dmi":
            held = dmi.copy()
            held.iloc[o:] = np.nan
            held = held.ffill()
            outs.append(build_dmi_block(held)[o:o + H])
        else:
            raise KeyError(k)
    return outs


def run(name, keys, refit, adj=None, order=None, store=None, label=None):
    """Roll the model forward over all 60 origins and record level forecasts.

    adj / order / store / label exist so gnarx_sensitivity.py can reuse this
    exact loop with an alternative graph.
    """
    p, s = CHOSEN[name] if order is None else order
    label = (name + ("_refit" if refit else "")) if label is None else label
    box = preds if store is None else store
    model = None if refit else fit_gnarx(keys, p, s, 1, split, adj)
    for o in targets:
        m = fit_gnarx(keys, p, s, 1, o, adj) if refit else model
        H = min(max(HORIZONS), N - o)
        fc = m.forecast(D[1:o], h=H,
                        Zex_hist=exog_slices(keys, 1, o) if keys else None,
                        Zex_future=future_exog(keys, o, H) if keys else None)
        # undo the deseasonalisation, then integrate differences to levels
        fc_diff = fc + S[o:o + H]
        cum = L.values[o - 1] + np.cumsum(fc_diff, axis=0)
        for h in HORIZONS:
            if h <= H:
                for j, lk in enumerate(LAKES):
                    box[(label, lk, o + h - 1, h)] = cum[h - 1, j]
    return label


print("\n[7] rolling origin, %d origins" % len(targets))
MODEL_ORDER = ["RandomWalk", "SARIMA"]
for name, keys in ABLATIONS.items():
    for refit in (False, True):
        lab = run(name, keys, refit)
        MODEL_ORDER.append(lab)
        print(f"    {lab} done")

# scoring

Lv = {lk: L[lk].values for lk in LAKES}
Iv = {lk: INTERP[lk].values for lk in LAKES}

rows = []
for lk in LAKES:
    for model in MODEL_ORDER:
        for h in HORIZONS:
            Pv, Av = [], []
            for o in targets:
                tgt = o + h - 1
                if tgt >= N:
                    continue
                if Iv[lk][tgt]:
                    continue
                key = (model, lk, tgt, h)
                if key in preds:
                    Pv.append(preds[key])
                    Av.append(Lv[lk][tgt])
            rows.append({"Lake": lk, "Model": model, "Horizon_m": h,
                         "RMSE_m": round(rmse(Pv, Av), 4),
                         "MAE_m": round(mae(Pv, Av), 4),
                         "n_scored": len(Pv)})

metrics = pd.DataFrame(rows)

bad = metrics[metrics.apply(lambda r: r.n_scored != EXPECTED_N[r.Horizon_m],
                            axis=1)]
assert bad.empty, ("forecast counts do not match the canonical protocol:\n"
                   + bad.to_string())
print("\n[8] forecast counts verified: 60 / 58 / 55 / 49 per lake per horizon")

sar = metrics[metrics.Model == "SARIMA"].set_index(["Lake", "Horizon_m"])["RMSE_m"]
metrics["skill_vs_SARIMA_%"] = metrics.apply(
    lambda r: round(100 * (sar[(r.Lake, r.Horizon_m)] - r.RMSE_m)
                    / sar[(r.Lake, r.Horizon_m)], 1), axis=1)
metrics.to_csv(out("FC7_gnarx_metrics.csv"), index=False)

# coefficients from the fit-once training fit, with time-clustered SEs

def design_matrix(m, X, Zex):
    t0 = m._min_lag()
    rows_, ys_, ts_ = [], [], []
    Xc = X - m.mean_
    Zl = [np.asarray(z, float) for z in (Zex or [])]
    for t in range(t0, X.shape[0]):
        rows_.append(m._row_block(Xc, Zl, t))
        ys_.append(Xc[t])
        ts_.append(np.full(m.n, t))
    return np.vstack(rows_), np.concatenate(ys_), np.concatenate(ts_)


coef_rows = []
for name, keys in ABLATIONS.items():
    p, s = CHOSEN[name]
    m = fit_gnarx(keys, p, s, 1, split)
    Dm, y, tid = design_matrix(m, D[1:split],
                               exog_slices(keys, 1, split) if keys else None)
    u = y - Dm @ m.coef_
    XtX_inv = np.linalg.pinv(Dm.T @ Dm)
    se_ols = np.sqrt(np.diag(XtX_inv) * m.sigma2_)
    # cluster by time: the seven lakes at one date are contemporaneously
    # correlated, so naive OLS standard errors are too small
    meat = np.zeros((Dm.shape[1], Dm.shape[1]))
    for t in np.unique(tid):
        sel = tid == t
        g = Dm[sel].T @ u[sel]
        meat += np.outer(g, g)
    G = len(np.unique(tid))
    k = Dm.shape[1]
    scale = (G / max(G - 1, 1)) * ((Dm.shape[0] - 1) / max(Dm.shape[0] - k, 1))
    V = XtX_inv @ meat @ XtX_inv * scale
    se_cl = np.sqrt(np.clip(np.diag(V), 0, None))
    for nm, c, s1, s2 in zip(m.names_, m.coef_, se_ols, se_cl):
        z = c / s2 if s2 > 0 else np.nan
        coef_rows.append({
            "Model": name, "p": p, "s": str(s), "term": nm,
            "coef": round(float(c), 6),
            "se_ols": round(float(s1), 6),
            "se_clustered_by_time": round(float(s2), 6),
            "z_clustered": round(float(z), 3),
            "p_value_clustered": round(
                float(2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))), 4)
            if np.isfinite(z) else np.nan,
            "n_params": m.n_params_, "nobs": m.nobs_,
            "sigma2": round(m.sigma2_, 8),
            "AIC": round(m.aic(), 3), "BIC": round(m.bic(), 3),
        })
pd.DataFrame(coef_rows).to_csv(out("FC7_gnarx_coeffs.csv"), index=False)

# report

print("\n" + "=" * 74)
print("MEAN skill vs SARIMA (%) by model x horizon   (positive = beats SARIMA)")
print("=" * 74)
piv = (metrics.pivot_table(index="Model", columns="Horizon_m",
                           values="skill_vs_SARIMA_%", aggfunc="mean")
       .reindex(MODEL_ORDER).round(1))
print(piv.to_string())

print("\nParameter counts (fit-once, training window):")
cp = pd.DataFrame(coef_rows).groupby("Model")[["n_params", "nobs"]].first()
for name in ABLATIONS:
    print(f"    {name:14s} {int(cp.loc[name,'n_params']):3d} parameters "
          f"on {int(cp.loc[name,'nobs'])} stacked observations")
print("    unrestricted VAR(1) on 7 nodes -> 49 (+7 intercepts)")

print("\nExogenous coefficients (clustered by time):")
cdf = pd.DataFrame(coef_rows)
ex = cdf[cdf.term.str.startswith(("beta_", "lambda_"))]
print(ex[["Model", "term", "coef", "se_clustered_by_time",
          "z_clustered", "p_value_clustered"]].to_string(index=False))

print("\nRefit advantage (refit minus fit-once, mean skill points):")
for name in ABLATIONS:
    a = piv.loc[name]
    b = piv.loc[name + "_refit"]
    print(f"    {name:14s} " + "  ".join(
        f"h={h}: {b[h]-a[h]:+.1f}" for h in HORIZONS))

# figure

ctx = []
for f, keep in ((FC4_FILE, ["VAR", "VARX"]), (FC5_FILE, ["SARIMAX"]),
                (FC6_FILE, ["GNN"])):
    if os.path.exists(f):
        d = pd.read_csv(f)
        ctx.append(d[d.Model.isin(keep)][["Lake", "Model", "Horizon_m",
                                          "RMSE_m", "skill_vs_SARIMA_%"]])
CTX = pd.concat(ctx) if ctx else pd.DataFrame(columns=metrics.columns)

show = ["RandomWalk", "SARIMA", "VAR", "VARX", "SARIMAX", "GNN",
        "GNAR", "GNARX_wb", "GNARX_wb_dmi"]
allm = pd.concat([metrics[["Lake", "Model", "Horizon_m", "RMSE_m",
                           "skill_vs_SARIMA_%"]], CTX])
allm = allm[allm.Model.isin(show)]

fig, axes = plt.subplots(1, 3, figsize=(22, 6))
for ax, h in zip(axes[:2], [1, 6]):
    sub = (allm[allm.Horizon_m == h]
           .pivot(index="Lake", columns="Model", values="RMSE_m"))
    sub = sub[[c for c in show if c in sub.columns]]
    sub.plot(kind="bar", ax=ax)
    ax.set_title(f"RMSE at horizon {h} months", fontweight="bold")
    ax.set_ylabel("RMSE (m)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=7)

ax = axes[2]
for mname in show:
    d = allm[allm.Model == mname].groupby("Horizon_m")["skill_vs_SARIMA_%"].mean()
    if len(d):
        ax.plot(d.index, d.values, marker="o", label=mname)
ax.axhline(0, color="k", lw=1)
ax.set_xlabel("horizon (months)")
ax.set_ylabel("mean skill vs SARIMA (%)")
ax.set_title("Mean skill vs SARIMA", fontweight="bold")
ax.legend(fontsize=7)
plt.suptitle("GNARX vs the pipeline: does a parsimonious network model "
             "beat a tuned single-lake SARIMA?", fontweight="bold")
plt.tight_layout()
plt.savefig(out("FC7_compare.png"), dpi=200)
plt.close()

print("\nWritten to", OUT_DIR)
for f in ("FC7_gnarx_metrics.csv", "FC7_gnarx_coeffs.csv",
          "FC7_gnarx_orders.csv", "FC7_compare.png"):
    print("   ", f)
print("\nRun Metrics.ipynb (add_scaled_metrics) over FC7_gnarx_metrics.csv LAST.")