#!/usr/bin/env python3
"""Mini-replication for Goetzmann–Manninen–Tyler (NBER 34903) bubble definitions
on a long public US market index (Yahoo ^GSPC daily → monthly).

Transparent boom/crash rules; numbers from THIS run. Design clone — not exact
paper tables (paper uses reconstructed 1792–2024 series).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "results.json"

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"


def load_spx_monthly() -> pd.DataFrame:
    cache = DATA / "spx_daily_yahoo.csv"
    if not cache.exists():
        # max range via period1 ~ 1950
        p1 = int(pd.Timestamp("1950-01-01").timestamp())
        p2 = int(pd.Timestamp("2026-09-01").timestamp())
        url = f"{YAHOO}?period1={p1}&period2={p2}&interval=1d"
        r = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        j = r.json()["chart"]["result"][0]
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(j["timestamp"], unit="s").tz_localize(None),
                "Close": j["indicators"]["quote"][0]["close"],
            }
        ).dropna()
        df.to_csv(cache, index=False)
    else:
        df = pd.read_csv(cache, parse_dates=["Date"])
    df = df.sort_values("Date").dropna(subset=["Close"])
    # month-end close
    df["ym"] = df["Date"].dt.to_period("M")
    m = df.groupby("ym", as_index=False).tail(1).copy()
    m["Date"] = m["ym"].dt.to_timestamp("M")
    return m[["Date", "Close"]].reset_index(drop=True)


def detect_events(df: pd.DataFrame, horizon: int = 12, boom_th: float = 0.80, crash_th: float = -0.35):
    px = df["Close"].astype(float)
    ret_h = px / px.shift(horizon) - 1.0
    boom_raw = ret_h >= boom_th
    crash_raw = ret_h <= crash_th

    def cluster(mask: pd.Series) -> list[dict]:
        events = []
        vals = mask.fillna(False).to_numpy()
        i = 0
        while i < len(vals):
            if not vals[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(vals) and vals[j + 1]:
                j += 1
            window = ret_h.iloc[i : j + 1]
            k = int(window.abs().idxmax())
            events.append(
                {
                    "end_date": str(pd.Timestamp(df.loc[k, "Date"]).date()),
                    "horizon_months": horizon,
                    "cum_ret": float(ret_h.loc[k]),
                    "start_date": str(pd.Timestamp(df.loc[max(0, k - horizon), "Date"]).date()),
                }
            )
            i = j + 1
        return events

    return cluster(boom_raw), cluster(crash_raw), ret_h


def main():
    df = load_spx_monthly()
    specs = [
        {"horizon": 12, "boom_th": 0.50, "crash_th": -0.25},
        {"horizon": 24, "boom_th": 0.80, "crash_th": -0.35},
        {"horizon": 36, "boom_th": 1.00, "crash_th": -0.45},
    ]
    runs = []
    for sp in specs:
        booms, crashes, ret_h = detect_events(df, **sp)
        runs.append(
            {
                **sp,
                "n_booms": len(booms),
                "n_crashes": len(crashes),
                "boom_share_months": float((ret_h >= sp["boom_th"]).mean()),
                "crash_share_months": float((ret_h <= sp["crash_th"]).mean()),
                "booms": booms[:15],
                "crashes": crashes[:15],
            }
        )
    pref = runs[1]
    results = {
        "index": "S&P 500 (Yahoo ^GSPC daily → month-end)",
        "url": YAHOO,
        "sample_start": str(pd.Timestamp(df["Date"].min()).date()),
        "sample_end": str(pd.Timestamp(df["Date"].max()).date()),
        "n_months": int(len(df)),
        "preferred_spec": {
            "horizon_months": 24,
            "boom_threshold": "+80% / 24m",
            "crash_threshold": "-35% / 24m",
            "n_booms": pref["n_booms"],
            "n_crashes": pref["n_crashes"],
            "example_booms": pref["booms"][:8],
            "example_crashes": pref["crashes"][:8],
        },
        "all_specs": runs,
        "caveat": (
            "Exact paper uses reconstructed US market 1792–2024 and specific "
            "boom/crash definitions in NBER 34903. Our numbers are from Yahoo "
            "S&P monthly with transparent thresholds — a mini design clone."
        ),
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results["preferred_spec"], indent=2))
    print("n_months", results["n_months"], results["sample_start"], results["sample_end"])
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
