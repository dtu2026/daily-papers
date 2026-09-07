#!/usr/bin/env python3
"""Mini-replication / teaching demo for Harvey–Sancetta–Zhao (NBER 34898).

Downloads Ken French 5 factors + 10 industry portfolios (daily), mines many
random long-short industry 'factors', and shows rejection rates under
t=1.96 vs t=3.0–3.5 (multiple testing / factor zoo).
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "results.json"
UA = {"User-Agent": "DongjieReplicationBot/1.0 (educational)"}
FF5_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
IND_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/10_Industry_Portfolios_Daily_CSV.zip"


def download_zip_csv(url: str, cache_name: str) -> Path:
    zpath = DATA / cache_name
    if not zpath.exists():
        r = requests.get(url, headers=UA, timeout=120)
        r.raise_for_status()
        zpath.write_bytes(r.content)
    return zpath


def read_ff_daily(zpath: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zpath) as zf:
        name = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
        raw = zf.read(name).decode("latin-1")
    lines = raw.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip()[:8].isdigit())
    body = []
    for line in lines[start:]:
        if not line.strip() or not line.strip()[0].isdigit():
            break
        body.append(line)
    df = pd.read_csv(io.StringIO("\n".join(body)), header=None)
    df.columns = ["date", "MktRF", "SMB", "HML", "RMW", "CMA", "RF"][: df.shape[1]]
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d")
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna()


def read_ind_daily(zpath: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zpath) as zf:
        name = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
        raw = zf.read(name).decode("latin-1")
    lines = raw.splitlines()
    header_i = next(
        i
        for i, line in enumerate(lines)
        if any(ch.isalpha() for ch in line) and "," in line and not line.lower().startswith("this file")
        and ("NoDur" in line or "Food" in line or line.lower().startswith(","))
    )
    # if first csv header-like after comments:
    for i, line in enumerate(lines):
        if "NoDur" in line or (line.count(",") >= 5 and any(x.isalpha() for x in line.split(",")[1:3])):
            header_i = i
            break
    header = [h.strip() for h in lines[header_i].split(",")]
    body = []
    for line in lines[header_i + 1 :]:
        if not line.strip() or not line.strip()[0].isdigit():
            break
        body.append(line)
    df = pd.read_csv(io.StringIO("\n".join(body)), header=None)
    df.columns = header if len(header) == df.shape[1] else ["date"] + [f"I{i}" for i in range(df.shape[1] - 1)]
    if df.columns[0].lower() != "date":
        df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d")
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(how="all")


def ols_t(y: pd.Series, X: pd.DataFrame) -> float:
    Xc = sm.add_constant(X)
    m = sm.OLS(y, Xc, missing="drop").fit()
    return float(m.tvalues["const"])


def main():
    ff = read_ff_daily(download_zip_csv(FF5_URL, "ff5_daily.zip"))
    ind = read_ind_daily(download_zip_csv(IND_URL, "ff10ind_daily.zip"))
    start = pd.Timestamp("2010-01-01")
    ff = ff[ff["date"] >= start].copy()
    ind = ind[ind["date"] >= start].copy()
    df = ff.merge(ind, on="date", how="inner")
    factors = ["MktRF", "SMB", "HML", "RMW", "CMA"]
    ind_cols = [c for c in ind.columns if c != "date"]

    ts = []
    for c in ind_cols:
        y = df[c] - df["RF"]
        ts.append({"name": c, "t_alpha": ols_t(y, df[factors]), "abs_t": abs(ols_t(y, df[factors]))})
    # recompute once
    ts = []
    for c in ind_cols:
        t = ols_t(df[c] - df["RF"], df[factors])
        ts.append({"name": c, "t_alpha": t, "abs_t": abs(t)})
    tdf = pd.DataFrame(ts).sort_values("abs_t", ascending=False)

    rng = np.random.default_rng(42)
    n_fake = 500
    ind_mat = df[ind_cols].to_numpy()
    fake_ts = []
    for _ in range(n_fake):
        w = rng.normal(size=len(ind_cols))
        w = w - w.mean()
        w = w / (np.abs(w).sum() + 1e-12) * 2.0
        port = ind_mat @ w - df["RF"].to_numpy()
        fake_ts.append(ols_t(pd.Series(port, index=df.index), df[factors]))
    fake_ts = np.array(fake_ts)

    thr = {
        "t_1.96": float((np.abs(fake_ts) > 1.96).mean()),
        "t_3.00": float((np.abs(fake_ts) > 3.00).mean()),
        "t_3.50": float((np.abs(fake_ts) > 3.50).mean()),
    }
    # expected false discoveries if publish all |t|>1.96 from the search
    n_pub_196 = int((np.abs(fake_ts) > 1.96).sum())
    n_pub_300 = int((np.abs(fake_ts) > 3.00).sum())
    n_pub_350 = int((np.abs(fake_ts) > 3.50).sum())
    bonf = float(norm.ppf(1 - 0.025 / n_fake))

    results = {
        "sample_start": str(df["date"].min().date()),
        "sample_end": str(df["date"].max().date()),
        "n_days": int(len(df)),
        "industry_alphas": tdf.to_dict(orient="records"),
        "n_fake_factors": n_fake,
        "fake_t_mean": float(fake_ts.mean()),
        "fake_t_std": float(fake_ts.std()),
        "max_abs_t_in_search": float(np.max(np.abs(fake_ts))),
        "share_reject_fake": thr,
        "count_reject_fake": {"t_1.96": n_pub_196, "t_3.00": n_pub_300, "t_3.50": n_pub_350},
        "bonferroni_5pct_approx_t": bonf,
        "teaching_note": (
            "Mining 500 random industry long-shorts: many clear classical t=1.96. "
            "Harvey–Sancetta–Zhao argue practical factor thresholds near t=3.0–3.5 "
            "(LFDR tools that do not require knowing total N)."
        ),
        "data_urls": [FF5_URL, IND_URL],
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({k: results[k] for k in results if k != "industry_alphas"}, indent=2))
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
