#!/usr/bin/env python3
"""Mini-replication for Kim–Muhn–Nikolaev 'Bloated Disclosures'.

We do NOT call GPT. Instead: download a small set of 10-K filings from EDGAR,
extract a crude MD&A / Item 7 text block (or full submission text fallback),
compute simple bloat proxies (length, gzip compression ratio, unique-token ratio),
and optionally merge Yahoo daily returns around filing dates for a tiny CAR check.
"""
from __future__ import annotations

import gzip
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "results.json"

UA = {
    "User-Agent": "DongjieResearchBot contact@example.edu",
    "Accept-Encoding": "gzip, deflate",
}

# Small diversified sample of large US filers (CIK, ticker)
SAMPLE = [
    ("0000320193", "AAPL"),
    ("0000789019", "MSFT"),
    ("0001652044", "GOOGL"),
    ("0001018724", "AMZN"),
    ("0001324424", "META"),
    ("0001318605", "TSLA"),
    ("0001045810", "NVDA"),
    ("0000051143", "IBM"),
    ("0000019617", "JPM"),
    ("0000070858", "BAC"),
    ("0000097745", "T"),
    ("0000731766", "UAL"),
    ("0000037996", "F"),
    ("0000104169", "WMT"),
    ("0000886982", "GS"),
    ("0000063908", "MCD"),
    ("0000097745", "TMO"),  # may fail; keep diversified
    ("0000310158", "MMM"),
    ("0000078003", "PFE"),
    ("0000354950", "CSCO"),
    ("0000858877", "ORCL"),
    ("0001403161", "V"),
    ("0001141391", "MA"),
    ("0001559720", "ABBV"),
    ("0000004962", "AXP"),
]


def edgar_submissions(cik: str) -> dict:
    path = DATA / f"submissions_{cik}.json"
    if path.exists():
        return json.loads(path.read_text())
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    path.write_text(r.text, encoding="utf-8")
    time.sleep(0.3)
    return r.json()


def latest_10k(meta: dict) -> dict | None:
    recent = meta.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    for i, form in enumerate(forms):
        if form in ("10-K", "10-K/A"):
            return {
                "form": form,
                "accession": recent["accessionNumber"][i].replace("-", ""),
                "accession_dashed": recent["accessionNumber"][i],
                "primary": recent["primaryDocument"][i],
                "filingDate": recent["filingDate"][i],
                "reportDate": recent.get("reportDate", [None] * len(forms))[i],
            }
    return None


def download_filing(cik: str, info: dict) -> Path:
    cik_int = str(int(cik))
    fname = info["primary"]
    out = DATA / f"{cik}_{info['filingDate']}_{fname.replace('/', '_')}"
    if out.exists() and out.stat().st_size > 1000:
        return out
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{info['accession']}/{fname}"
    r = requests.get(url, headers=UA, timeout=120)
    r.raise_for_status()
    out.write_bytes(r.content)
    time.sleep(0.4)
    return out


def extract_text(html_bytes: bytes) -> str:
    text = html_bytes.decode("utf-8", errors="ignore")
    # strip scripts/styles
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_mda(full: str) -> str:
    # crude Item 7 hunt
    m = re.search(
        r"(item\s*7[\.\s:\-].{0,80}management.?s?\s+discussion[\s\S]{200,})",
        full,
        re.I,
    )
    if not m:
        return full[:200000]  # fallback truncated full text
    chunk = m.group(1)
    # cut at Item 8 if present
    m2 = re.search(r"item\s*8[\.\s:\-]", chunk[200:], re.I)
    if m2:
        chunk = chunk[: 200 + m2.start()]
    return chunk[:300000]


def bloat_proxies(text: str) -> dict:
    tokens = re.findall(r"[A-Za-z]{2,}", text.lower())
    n = len(tokens)
    uniq = len(set(tokens))
    raw = text.encode("utf-8", errors="ignore")
    comp = gzip.compress(raw, compresslevel=9)
    return {
        "chars": len(text),
        "tokens": n,
        "unique_tokens": uniq,
        "unique_ratio": (uniq / n) if n else None,
        "gzip_ratio": (len(comp) / len(raw)) if raw else None,  # lower = more redundant
        "compression_savings": 1 - (len(comp) / len(raw)) if raw else None,
    }


def yahoo_returns(ticker: str, start: str, end: str) -> pd.DataFrame:
    cache = DATA / f"yahoo_{ticker}.csv"
    if cache.exists():
        df = pd.read_csv(cache, parse_dates=["Date"])
        return df
    # use Yahoo chart API (no yfinance dependency required at runtime if fails)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={int(pd.Timestamp(start).timestamp())}"
        f"&period2={int(pd.Timestamp(end).timestamp())}"
        f"&interval=1d&events=div%7Csplit"
    )
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    r.raise_for_status()
    j = r.json()["chart"]["result"][0]
    ts = pd.to_datetime(j["timestamp"], unit="s")
    close = j["indicators"]["quote"][0]["close"]
    df = pd.DataFrame({"Date": ts, "Close": close}).dropna()
    df["ret"] = df["Close"].pct_change()
    df.to_csv(cache, index=False)
    time.sleep(0.2)
    return df


def car_around(df: pd.DataFrame, event: pd.Timestamp, window=(0, 1)) -> float | None:
    df = df.sort_values("Date").reset_index(drop=True)
    # find first trading day on/after event
    idx = df.index[df["Date"] >= event]
    if len(idx) == 0:
        return None
    i0 = int(idx[0])
    i1 = i0 + window[1]
    if i1 >= len(df):
        return None
    return float(df.loc[i0:i1, "ret"].sum())


def main():
    rows = []
    for cik, ticker in SAMPLE:
        try:
            meta = edgar_submissions(cik)
            info = latest_10k(meta)
            if not info:
                continue
            path = download_filing(cik, info)
            full = extract_text(path.read_bytes())
            mda = extract_mda(full)
            prox = bloat_proxies(mda)
            row = {
                "cik": cik,
                "ticker": ticker,
                "filingDate": info["filingDate"],
                "form": info["form"],
                "used_mda_heuristic": bool(
                    re.search(r"item\s*7", mda[:80], re.I)
                ),
                **prox,
            }
            # CAR [0,1] vs market crude: stock return only (not excess) for teaching
            try:
                px = yahoo_returns(ticker, "2022-01-01", "2026-09-01")
                row["car_0_1"] = car_around(px, pd.Timestamp(info["filingDate"]), (0, 1))
            except Exception as e:
                row["car_0_1"] = None
                row["car_error"] = str(e)[:120]
            rows.append(row)
            print("OK", ticker, info["filingDate"], prox["tokens"], prox["gzip_ratio"])
        except Exception as e:
            print("FAIL", ticker, e)

    df = pd.DataFrame(rows)
    # simple cross-section: CAR on bloat proxies
    reg = None
    if df["car_0_1"].notna().sum() >= 8:
        sub = df.dropna(subset=["car_0_1", "compression_savings", "tokens"]).copy()
        sub["log_tokens"] = np.log(sub["tokens"].clip(lower=1))
        y = sub["car_0_1"]
        X = sm.add_constant(sub[["compression_savings", "log_tokens"]])
        m = sm.OLS(y, X).fit()
        reg = {
            "n": int(m.nobs),
            "params": {k: float(v) for k, v in m.params.items()},
            "tvalues": {k: float(v) for k, v in m.tvalues.items()},
            "rsquared": float(m.rsquared),
        }

    results = {
        "n_filings": int(len(df)),
        "mean_tokens": float(df["tokens"].mean()) if len(df) else None,
        "mean_gzip_ratio": float(df["gzip_ratio"].mean()) if len(df) else None,
        "mean_compression_savings": float(df["compression_savings"].mean()) if len(df) else None,
        "mean_unique_ratio": float(df["unique_ratio"].mean()) if len(df) else None,
        "corr_compression_car": (
            float(df[["compression_savings", "car_0_1"]].corr().iloc[0, 1])
            if df["car_0_1"].notna().sum() > 3
            else None
        ),
        "regression": reg,
        "table": df.to_dict(orient="records"),
        "caveat": (
            "Paper uses GPT summaries to define Bloat=(len_raw-len_summary)/len_raw and "
            "links bloat to asymmetry. We only compute mechanical redundancy proxies and a tiny CAR horse-race — NOT a GPT replication."
        ),
        "data_urls": [
            "https://www.sec.gov/edgar",
            "https://data.sec.gov/submissions/",
            "https://query1.finance.yahoo.com/v8/finance/chart/",
        ],
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({k: results[k] for k in results if k != "table"}, indent=2))
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
