#!/usr/bin/env python3
"""DESIGN DRILL for Hagenberg et al. (RAST) — NOT a paper replication.

1) Real pull: Eastmoney announcements for a small A-share sample (API returns
   recent filings only on this box — typically ~2025–2026). Count forecast-like
   titles (业绩预告/快报/说明会 etc.).
2) Mock DiD: synthetic pre/post × treated/control counts that demonstrate the
   regression equation Dongjie would run after a documented liquidity shock.
   MOCK rows are labeled; do not cite as empirical findings.
"""
from __future__ import annotations

import json
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
UA = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}

SAMPLE = ["600519", "000858", "601318", "600036", "000001", "002475", "300015", "002241"]
KEYWORDS = ("预告", "快报", "业绩说明", "盈利预警", "业绩预报")


def eastmoney_notices(stock: str, pages: int = 2) -> list[dict]:
    cache = DATA / f"em_ann_{stock}.json"
    if cache.exists() and cache.stat().st_size > 10:
        return json.loads(cache.read_text())
    url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
    out = []
    for page in range(1, pages + 1):
        params = {
            "page_size": 50,
            "page_index": page,
            "ann_type": "A",
            "client_source": "web",
            "stock_list": stock,
            "f_node": "0",
            "s_node": "0",
        }
        try:
            r = requests.get(url, params=params, headers=UA, timeout=20)
            r.raise_for_status()
            rows = (r.json().get("data") or {}).get("list") or []
        except Exception as e:
            print("warn", stock, e)
            break
        if not rows:
            break
        for row in rows:
            title = row.get("title") or row.get("notice_title") or ""
            dt = (row.get("notice_date") or row.get("display_time") or "")[:10]
            out.append({"title": title, "date": dt, "stock": stock})
        time.sleep(0.5)
    cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def main():
    real_rows = []
    for code in SAMPLE:
        anns = eastmoney_notices(code)
        dates = [a["date"] for a in anns if a.get("date")]
        hits = [a for a in anns if any(k in (a.get("title") or "") for k in KEYWORDS)]
        real_rows.append(
            {
                "code": code,
                "n_anns_pulled": len(anns),
                "date_min": min(dates) if dates else None,
                "date_max": max(dates) if dates else None,
                "n_forecast_like": len(hits),
                "examples": [h["title"][:70] for h in hits[:5]],
            }
        )
        print(code, "anns", len(anns), "forecast_like", len(hits))

    # --- MOCK DiD panel (teaching only) ---
    rng = np.random.default_rng(7)
    mock = []
    # treated: liquidity improved → voluntary forecasts fall (Hagenberg direction)
    for code in ["T1", "T2", "T3", "T4", "T5", "T6"]:
        pre = int(rng.integers(2, 6))
        post = max(0, pre - int(rng.integers(1, 3)))
        mock += [
            {"code": code, "treated": 1, "period": 0, "n_forecast_like": pre, "mock": True},
            {"code": code, "treated": 1, "period": 1, "n_forecast_like": post, "mock": True},
        ]
    for code in ["C1", "C2", "C3", "C4", "C5", "C6"]:
        pre = int(rng.integers(2, 6))
        post = pre + int(rng.integers(-1, 2))
        mock += [
            {"code": code, "treated": 0, "period": 0, "n_forecast_like": pre, "mock": True},
            {"code": code, "treated": 0, "period": 1, "n_forecast_like": max(0, post), "mock": True},
        ]
    panel = pd.DataFrame(mock)
    panel["did"] = panel["period"] * panel["treated"]
    m = sm.OLS(
        panel["n_forecast_like"].astype(float),
        sm.add_constant(panel[["treated", "period", "did"]]),
    ).fit(cov_type="HC1")

    def mean_cell(t, p):
        return float(panel[(panel.treated == t) & (panel.period == p)]["n_forecast_like"].mean())

    results = {
        "label": "DESIGN DRILL — not Hagenberg replication",
        "shock_intended": {
            "date": "2019-08-19",
            "description": "Intended A-share analogue: margin-trading underlying expansion (两融标的扩容). Paper uses 1997 Nasdaq Order Handling Rules.",
            "data_gap": (
                "Eastmoney notice API on this box only returns recent filings "
                f"(observed ~{min(r['date_min'] for r in real_rows if r['date_min'])} to "
                f"{max(r['date_max'] for r in real_rows if r['date_max'])}); cannot DiD the 2019 shock here."
            ),
        },
        "real_announcement_pull": real_rows,
        "mock_did": {
            "warning": "SYNTHETIC panel for teaching the DiD equation only — not real 2019 data.",
            "means": {
                "treated_pre": mean_cell(1, 0),
                "treated_post": mean_cell(1, 1),
                "control_pre": mean_cell(0, 0),
                "control_post": mean_cell(0, 1),
                "simple_did": (mean_cell(1, 1) - mean_cell(1, 0)) - (mean_cell(0, 1) - mean_cell(0, 0)),
            },
            "regression": {
                "n": int(m.nobs),
                "params": {k: float(v) for k, v in m.params.items()},
                "tvalues": {k: float(v) for k, v in m.tvalues.items()},
                "rsquared": float(m.rsquared),
            },
            "panel": panel.to_dict(orient="records"),
        },
        "how_you_would_did_this": [
            "1) Document a microstructure shock that moves spreads/depth without mandating disclosure (e.g. 两融扩容, tick-size pilot).",
            "2) Treated = newly eligible / venue hit by rule; control = similar firms not hit.",
            "3) Outcome: annual/quarterly count of 业绩预告/快报 from cninfo (need historical archive, not recent-only API).",
            "4) Spec: Y_it = a + b Treat_i + c Post_t + d (Treat×Post)_it + FE + controls; cluster by firm.",
            "5) Show parallel pre-trends; placebo dates; check IA vs non-IA spread components like Hagenberg.",
        ],
        "data_sources": [
            "https://np-anotice-stock.eastmoney.com/api/security/ann",
            "http://www.cninfo.com.cn/ (preferred for deep history; often blocked from overseas IPs)",
        ],
    }
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "real_n_codes": len(real_rows),
        "real_forecast_counts": {r["code"]: r["n_forecast_like"] for r in real_rows},
        "mock_means": results["mock_did"]["means"],
        "mock_reg": results["mock_did"]["regression"],
    }, indent=2, ensure_ascii=False))
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
