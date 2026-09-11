from __future__ import annotations

import numpy as np

__all__ = [
    "delay_embed",
    "simplex_predict",
    "cross_map_rho",
    "select_E",
    "ccm_convergence",
    "ebisuzaki_surrogates",
]



# embedding
def delay_embed(x: np.ndarray, E: int, tau: int = 1):
    """Return (M, t_idx) where M[i] = [x(t), x(t-tau), ..., x(t-(E-1)tau)]
    and t_idx[i] = t is the index into the original series."""
    x = np.asarray(x, dtype=float)
    n = x.size
    start = (E - 1) * tau
    if start >= n:
        raise ValueError(f"series too short for E={E}, tau={tau}")
    t_idx = np.arange(start, n)
    M = np.column_stack([x[t_idx - k * tau] for k in range(E)])
    return M, t_idx


# simplex projection

def _neighbour_weights(dists: np.ndarray) -> np.ndarray:
    """Sugihara exponential weights w_i = exp(-d_i / d_1), normalised."""
    d1 = dists[0]
    if d1 <= 1e-12:
        # degenerate: an exact match, put all weight on it
        w = np.zeros_like(dists)
        w[0] = 1.0
        return w
    w = np.exp(-dists / d1)
    s = w.sum()
    return w / s if s > 0 else np.full_like(dists, 1.0 / dists.size)


def simplex_predict(
    M: np.ndarray,
    t_idx: np.ndarray,
    target: np.ndarray,
    lib_pos: np.ndarray,
    pred_pos: np.ndarray,
    E: int,
    exclusion_radius: int = 0,
    tp: int = 0,
):
    """Predict target[t_idx[p] + tp] for each p in pred_pos, using the E+1
    nearest neighbours of M[p] drawn from lib_pos.

    exclusion_radius r excludes library points with |t_lib - t_pred| <= r.
    r=0 therefore excludes only the point itself (matches pyEDM's default).

    Returns (obs, pred) with NaNs already dropped.
    """
    k = E + 1
    n_target = target.size
    t_lib = t_idx[lib_pos]
    t_pred = t_idx[pred_pos]

    # keep only library points whose target value exists and is finite
    lib_tgt_time = t_lib + tp
    lib_ok = (lib_tgt_time >= 0) & (lib_tgt_time < n_target)
    lib_ok[lib_ok] &= np.isfinite(target[lib_tgt_time[lib_ok]])
    lib_pos = lib_pos[lib_ok]
    t_lib = t_lib[lib_ok]
    if lib_pos.size < k + 1:
        return np.empty(0), np.empty(0)
    lib_vals = target[t_lib + tp]

    # keep only prediction points with a finite observation
    pred_tgt_time = t_pred + tp
    pred_ok = (pred_tgt_time >= 0) & (pred_tgt_time < n_target)
    pred_ok[pred_ok] &= np.isfinite(target[pred_tgt_time[pred_ok]])
    pred_pos = pred_pos[pred_ok]
    t_pred = t_pred[pred_ok]
    if pred_pos.size == 0:
        return np.empty(0), np.empty(0)
    obs = target[t_pred + tp]

    # full distance matrix (n_pred x n_lib), Theiler-masked
    A, B = M[pred_pos], M[lib_pos]
    D = np.sqrt(np.maximum(
        (A * A).sum(1)[:, None] + (B * B).sum(1)[None, :] - 2.0 * A @ B.T, 0.0))
    D[np.abs(t_pred[:, None] - t_lib[None, :]) <= exclusion_radius] = np.inf

    # k nearest, sorted
    part = np.argpartition(D, k - 1, axis=1)[:, :k]
    dk = np.take_along_axis(D, part, axis=1)
    srt = np.argsort(dk, axis=1)
    nn = np.take_along_axis(part, srt, axis=1)
    dk = np.take_along_axis(dk, srt, axis=1)

    valid = np.isfinite(dk).all(axis=1)          # enough non-excluded neighbours
    if not valid.any():
        return np.empty(0), np.empty(0)

    d1 = dk[:, [0]]
    degen = d1[:, 0] <= 1e-12
    with np.errstate(divide="ignore", invalid="ignore"):
        W = np.exp(-dk / np.where(d1 <= 1e-12, 1.0, d1))
    W[degen] = 0.0
    W[degen, 0] = 1.0                            # exact match -> all weight there
    W /= W.sum(axis=1, keepdims=True)

    pred = (W * lib_vals[nn]).sum(axis=1)
    return obs[valid], pred[valid]


def _rho(obs, pred):
    if obs.size < 3:
        return np.nan
    if np.std(obs) < 1e-12 or np.std(pred) < 1e-12:
        return np.nan
    return float(np.corrcoef(obs, pred)[0, 1])



# E selection (univariate simplex, one step ahead)

def select_E(x: np.ndarray, E_range=range(1, 11), tau: int = 1,
             exclusion_radius: int = 0, tol: float = 0.01):
    """Leave-one-out simplex self-prediction at tp=1.

    Selection rule: the SMALLEST E whose rho is within `tol` of the maximum
    ("one-standard-error"-style parsimony), not the argmax.
    """
    curve = {}
    x = np.asarray(x, dtype=float)
    for E in E_range:
        try:
            M, t_idx = delay_embed(x, E, tau)
        except ValueError:
            continue
        pos = np.arange(t_idx.size)
        obs, pred = simplex_predict(M, t_idx, x, pos, pos, E,
                                    exclusion_radius=exclusion_radius, tp=1)
        curve[E] = _rho(obs, pred)

    finite = {e: r for e, r in curve.items() if np.isfinite(r)}
    if not finite:
        return None, np.nan, curve
    rho_max = max(finite.values())
    best_E = min(e for e, r in finite.items() if r >= rho_max - tol)
    return best_E, finite[best_E], curve


# cross mapping

def cross_map_rho(x, y, E, tau=1, lib_size=None, n_boot=100,
                  exclusion_radius=0, rng=None, replace=False):
    """rho for "x xmap y" -- evidence that y -> x.

    Library points are sampled (size lib_size) from the embedding of x;
    predictions are made at all embedding points.
    """
    rng = np.random.default_rng() if rng is None else rng
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    M, t_idx = delay_embed(x, E, tau)
    n = t_idx.size
    all_pos = np.arange(n)

    if lib_size is None or lib_size >= n:
        obs, pred = simplex_predict(M, t_idx, y, all_pos, all_pos, E,
                                    exclusion_radius=exclusion_radius, tp=0)
        return _rho(obs, pred), 0.0

    rs = []
    for _ in range(n_boot):
        lib_pos = rng.choice(all_pos, size=lib_size, replace=replace)
        lib_pos = np.sort(lib_pos)
        obs, pred = simplex_predict(M, t_idx, y, lib_pos, all_pos, E,
                                    exclusion_radius=exclusion_radius, tp=0)
        r = _rho(obs, pred)
        if np.isfinite(r):
            rs.append(r)
    if not rs:
        return np.nan, np.nan
    return float(np.mean(rs)), float(np.std(rs))


def ccm_convergence(x, y, E, lib_sizes, tau=1, n_boot=100,
                    exclusion_radius=0, seed=0):
    """rho vs library size for "x xmap y". Returns list of dicts."""
    rng = np.random.default_rng(seed)
    out = []
    for L in lib_sizes:
        m, s = cross_map_rho(x, y, E, tau=tau, lib_size=L, n_boot=n_boot,
                             exclusion_radius=exclusion_radius, rng=rng)
        out.append({"lib_size": int(L), "rho_mean": m, "rho_sd": s})
    return out



# surrogates

def ebisuzaki_surrogates(x, n_surr=200, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    n = x.size
    mu, sd = x.mean(), x.std()
    xc = x - mu
    F = np.fft.rfft(xc)
    amp = np.abs(F)
    out = np.empty((n_surr, n))
    for i in range(n_surr):
        phases = rng.uniform(0, 2 * np.pi, size=amp.size)
        phases[0] = 0.0
        if n % 2 == 0:
            phases[-1] = 0.0                      # Nyquist term must stay real
        Fs = amp * np.exp(1j * phases)
        s = np.fft.irfft(Fs, n=n)
        ssd = s.std()
        out[i] = mu + (s / ssd * sd if ssd > 1e-12 else s)
    return out