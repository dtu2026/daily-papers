#!/usr/bin/env python3
"""Mini-replication for Da–Peng–Xu–Zheng AI & A-H premium (SSRN 5234282).

Public Yahoo prices for A (.SS/.SZ) and H (.HK), construct A-H premium, event
window around 2023-08-31. Design clone — no LLM attention instrument.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "results.json"
EVENT = pd.Timestamp("2023-08-31")
UA = {"User-Agent": "Mozilla/5.0"}

PAIRS = [
    {"a": "601318.SS", "h": "2318.HK", "name": "Ping An"},
    {"a": "600036.SS", "h": "3968.HK", "name": "CMB"},
    {"a": "601398.SS", "h": "1398.HK", "name": "ICBC"},
    {"a": "601288.SS", "h": "1288.HK", "name": "ABC"},
    {"a": "600028.SS", "h": "0386.HK", "name": "Sinopec"},
    {"a": "601857.SS", "h": "0857.HK", "name": "PetroChina"},
]


def yahoo(ticker: str, start="2019-01-01", end="2026-09-01") -> pd.DataFrame:
    cache = DATA / f"yahoo_{ticker.replace('=', '_').replace('.', '_')}.csv"
    if cache.exists():
        return pd.read_csv(cache, parse_dates=["date"])
    p1 = int(pd.Timestamp(start).timestamp())
    p2 = int(pd.Timestamp(end).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={p1}&period2={p2}&interval=1d"
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    res = r.json()["chart"]["result"]
    if not res:
        raise RuntimeError(f"no data {ticker}")
    j = res[0]
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(j["timestamp"], unit="s").tz_localize(None).normalize(),
            "close": j["indicators"]["quote"][0]["close"],
        }
    ).dropna()
    df.to_csv(cache, index=False)
    time.sleep(0.25)
    return df


def fx() -> pd.DataFrame:
    usdcny = yahoo("CNY=X")
    usdcny = usdcny.rename(columns={"close": "usdcny"})
    usdcny["cny_per_hkd"] = usdcny["usdcny"] / 7.8
    return usdcny


def premium(a, h, fxdf):
    m = a.rename(columns={"close": "a_close"}).merge(
        h.rename(columns={"close": "h_close"}), on="date", how="inner"
    )
    m = m.merge(fxdf[["date", "cny_per_hkd"]], on="date", how="left")
    m["cny_per_hkd"] = m["cny_per_hkd"].ffill().bfill()
    m["h_cny"] = m["h_close"] * m["cny_per_hkd"]
    m["ah_premium"] = m["a_close"] / m["h_cny"] - 1.0
    return m


def event_study(prem: pd.Series, dates: pd.Series, event: pd.Timestamp, pre=20):
    idx = dates.searchsorted(event)
    if idx >= len(dates):
        idx = len(dates) - 1
    pos = int(idx)
    base = prem.iloc[max(0, pos - pre) : pos].mean()
    post5 = prem.iloc[pos : pos + 6].mean()
    return {
        "event_pos_date": str(dates.iloc[pos].date()),
        "pre_mean_premium": float(base),
        "post5_mean_premium": float(post5),
        "delta_post5_minus_pre": float(post5 - base),
    }


def main():
    fxdf = fx()
    panels = []
    event_rows = []
    for p in PAIRS:
        try:
            a = yahoo(p["a"])
            h = yahoo(p["h"])
            m = premium(a, h, fxdf)
            m["name"] = p["name"]
            panels.append(m)
            es = event_study(m["ah_premium"], m["date"], EVENT)
            event_rows.append({"name": p["name"], "a": p["a"], "h": p["h"], **es, "n": len(m)})
            print("OK", p["name"], len(m), "mean_prem", round(m["ah_premium"].mean(), 4), es)
        except Exception as e:
            print("FAIL", p["name"], e)

    if not panels:
        raise SystemExit("no panels")

    allp = pd.concat(panels, ignore_index=True)
    cs = allp.groupby("date", as_index=False)["ah_premium"].mean().sort_values("date")
    es_cs = event_study(cs["ah_premium"], cs["date"], EVENT)

    allp["post"] = (allp["date"] >= EVENT).astype(int)
    allp["dd"] = (allp["date"] - EVENT).dt.days
    sub = allp[allp["dd"].between(-90, 90)].copy()
    reg = None
    if len(sub) > 20 and sub["post"].nunique() > 1:
        sub["y"] = sub["ah_premium"] - sub.groupby("name")["ah_premium"].transform("mean")
        sub["x"] = sub["post"] - sub.groupby("name")["post"].transform("mean")
        if sub["x"].abs().sum() > 0:
            m = sm.OLS(sub["y"], sm.add_constant(sub["x"])).fit(
                cov_type="cluster", cov_kwds={"groups": sub["name"]}
            )
            reg = {
                "panel_post_coef": float(m.params["x"]),
                "panel_post_t": float(m.tvalues["x"]),
                "panel_n": int(m.nobs),
            }

    results = {
        "event_date": str(EVENT.date()),
        "n_pairs": len(event_rows),
        "pairs_event": event_rows,
        "cross_section_event": es_cs,
        "regression_pm90": reg,
        "sample_premium_mean": float(allp["ah_premium"].mean()),
        "sample_start": str(allp["date"].min().date()),
        "sample_end": str(allp["date"].max().date()),
        "caveat": (
            "Paper links LLM/AI attention to A-H premium. We only build public-price "
            "A-H premium and a crude post-2023-08-31 window — no LLM attention instrument. "
            "FX uses USD/CNY with HKD peg ≈7.8."
        ),
        "related_deep_read": "/workspace/research/papers/da_llm_lop_explained.html",
        "data_sources": ["https://query1.finance.yahoo.com/v8/finance/chart/"],
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
