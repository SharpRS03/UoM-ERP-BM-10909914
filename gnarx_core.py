from __future__ import annotations

import numpy as np

__all__ = ["stage_weight_matrices", "GNARX"]


# --------------------------------------------------------------------------
def stage_weight_matrices(A: np.ndarray, max_stage: int, weighted: bool = True):

    A = np.asarray(A, dtype=float)
    n = A.shape[0]
    if A.shape[0] != A.shape[1]:
        raise ValueError("A must be square")
    if np.any(A < 0):
        raise ValueError("A must be non-negative")

    B = (A > 0).astype(float)
    np.fill_diagonal(B, 0.0)

    # shortest-path distance in number of hops
    dist = np.full((n, n), np.inf)
    np.fill_diagonal(dist, 0.0)
    reach = np.eye(n)
    for r in range(1, max_stage + 1):
        reach = ((reach @ B) > 0).astype(float)
        np.fill_diagonal(reach, 0.0)
        dist[(dist == np.inf) & (reach > 0)] = r

    Aw = A.copy()
    np.fill_diagonal(Aw, 0.0)
    out = []
    Apow = np.eye(n)
    for r in range(1, max_stage + 1):
        Apow = Apow @ (Aw if weighted else B)
        W = np.where(dist == r, Apow, 0.0)
        np.fill_diagonal(W, 0.0)
        rs = W.sum(axis=1, keepdims=True)
        W = np.divide(W, rs, out=np.zeros_like(W), where=rs > 0)
        out.append(W)
    return out


# --------------------------------------------------------------------------
class GNARX:

    def __init__(self, A, p, s, exog_lags=(), model_type="standard",
                 weighted=True):
        self.A = np.asarray(A, float)
        self.n = self.A.shape[0]
        self.p = int(p)
        self.s = np.asarray(s, dtype=int)
        if self.s.size != self.p:
            raise ValueError("s must have length p")
        self.exog_lags = tuple(int(l) for l in exog_lags)
        self.model_type = model_type
        if model_type not in ("standard", "global"):
            raise ValueError("model_type must be 'standard' or 'global'")
        self.max_stage = int(self.s.max()) if self.s.size and self.s.max() > 0 else 0
        self.W = (stage_weight_matrices(self.A, self.max_stage, weighted)
                  if self.max_stage > 0 else [])
        self.coef_ = None
        self.names_ = None

    # design
    def _min_lag(self):
        return max([self.p] + [max(self.exog_lags) if self.exog_lags else 0])

    def _row_block(self, X, Zex, t):
        """Design rows for all n nodes at time t. Returns (n, k)."""
        n, p = self.n, self.p
        blocks = []

        # --- autoregressive own lags
        own = np.zeros((n, n * p)) if self.model_type == "standard" \
            else np.zeros((n, p))
        for j in range(1, p + 1):
            v = X[t - j]                                   # (n,)
            if self.model_type == "standard":
                for i in range(n):
                    own[i, (j - 1) * n + i] = v[i]
            else:
                own[:, j - 1] = v
        blocks.append(own)

        # neighbour terms, shared across nodes
        if self.max_stage > 0:
            nb = np.zeros((n, int(self.s.sum())))
            c = 0
            for j in range(1, p + 1):
                for r in range(1, self.s[j - 1] + 1):
                    nb[:, c] = self.W[r - 1] @ X[t - j]
                    c += 1
            blocks.append(nb)

        # exogenous, shared across nodes
        if self.exog_lags and Zex is not None:
            ex = np.zeros((n, len(Zex) * len(self.exog_lags)))
            c = 0
            for Z in Zex:
                for l in self.exog_lags:
                    ex[:, c] = Z[t - l]
                    c += 1
            blocks.append(ex)

        return np.hstack(blocks)

    def _names(self, n_exog):
        nm = []
        if self.model_type == "standard":
            nm += [f"alpha_lag{j}_node{i}" for j in range(1, self.p + 1)
                   for i in range(self.n)]
        else:
            nm += [f"alpha_lag{j}" for j in range(1, self.p + 1)]
        for j in range(1, self.p + 1):
            for r in range(1, self.s[j - 1] + 1):
                nm.append(f"beta_lag{j}_stage{r}")
        for h in range(n_exog):
            for l in self.exog_lags:
                nm.append(f"lambda_exog{h}_lag{l}")
        return nm

    # fit
    def fit(self, X, Zex=None, demean=True):
        """X: (T, n) array. Zex: list of (T, n) exogenous arrays, or None."""
        X = np.asarray(X, float)
        if X.shape[1] != self.n:
            raise ValueError(f"X has {X.shape[1]} columns, expected {self.n}")
        Zex = [np.asarray(z, float) for z in (Zex or [])]
        for z in Zex:
            if z.shape != X.shape:
                raise ValueError("each exogenous array must match X's shape")

        self.mean_ = X.mean(axis=0) if demean else np.zeros(self.n)
        Xc = X - self.mean_

        t0 = self._min_lag()
        rows, ys = [], []
        for t in range(t0, X.shape[0]):
            rows.append(self._row_block(Xc, Zex, t))
            ys.append(Xc[t])
        D = np.vstack(rows)
        y = np.concatenate(ys)

        beta, *_ = np.linalg.lstsq(D, y, rcond=None)
        self.coef_ = beta
        self.names_ = self._names(len(Zex))
        resid = y - D @ beta
        self.df_resid_ = D.shape[0] - D.shape[1]
        self.sigma2_ = float(resid @ resid / max(self.df_resid_, 1))
        self.nobs_ = D.shape[0]
        self.n_params_ = D.shape[1]
        self.rss_ = float(resid @ resid)
        return self

    # predict
    def forecast(self, X, Zex_future=None, h=1, Zex_hist=None):

        if self.coef_ is None:
            raise RuntimeError("fit() first")
        X = np.asarray(X, float)
        Xc = list(X - self.mean_)
        hist = [np.asarray(z, float) for z in (Zex_hist or [])]
        fut = [np.asarray(z, float) for z in (Zex_future or [])]
        if self.exog_lags and len(fut) != len(hist):
            raise ValueError("Zex_future and Zex_hist must have the same length")
        Zfull = [np.vstack([hist[k], fut[k]]) for k in range(len(hist))] \
            if hist else []

        out = []
        for step in range(h):
            Xa = np.asarray(Xc)
            t = Xa.shape[0]
            row = self._row_block(Xa, Zfull, t) if not Zfull else \
                self._row_block_mixed(Xa, Zfull, t)
            pred = row @ self.coef_
            Xc.append(pred)
            out.append(pred + self.mean_)
        return np.asarray(out)

    def _row_block_mixed(self, X, Zfull, t):
        """As _row_block but exogenous arrays are the concatenated
        history+future, indexed on the same time axis as X."""
        return self._row_block(X, Zfull, t)

    # ---------------------------------------------------------------- info
    def aic(self):
        return self.nobs_ * np.log(self.rss_ / self.nobs_) + 2 * self.n_params_

    def bic(self):
        return (self.nobs_ * np.log(self.rss_ / self.nobs_)
                + np.log(self.nobs_) * self.n_params_)

    def summary(self):
        lines = [f"GNARX(p={self.p}, s={list(self.s)}, "
                 f"exog_lags={list(self.exog_lags)}, {self.model_type})",
                 f"  nobs={self.nobs_}  params={self.n_params_}  "
                 f"sigma2={self.sigma2_:.6f}  AIC={self.aic():.2f}"]
        for nm, c in zip(self.names_, self.coef_):
            if not nm.startswith("alpha_lag") or self.model_type == "global":
                lines.append(f"    {nm:28s} {c:+.5f}")
        return "\n".join(lines)