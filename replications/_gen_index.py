#!/usr/bin/env python3
import json, html
from pathlib import Path
ROOT = Path(__file__).resolve().parent
cat = json.loads((ROOT / "catalog.json").read_text())
counts = cat["counts"]
SITE = "https://dtu2026.github.io/daily-papers"
CSS = """
:root{--ink:#1c1917;--muted:#57534e;--line:#e7e5e4;--paper:#faf7f2;--card:#fff;--accent:#9a3412;--tag:#f5e6d3}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.7 "Source Han Serif SC","Noto Serif SC","Songti SC","SimSun",Georgia,serif}
.wrap{max-width:960px;margin:0 auto;padding:48px 22px 80px}header h1{font-size:26px;font-weight:650;margin:0 0 8px}
.meta{color:var(--muted);font-size:14px;margin-bottom:22px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:0 0 16px}
h2{font-size:18px;margin:0 0 8px;color:var(--accent);font-family:ui-sans-serif,system-ui,sans-serif}
p{margin:0 0 8px}a{color:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:13px;margin:10px 0;font-family:ui-sans-serif,system-ui,sans-serif}
th,td{border:1px solid var(--line);padding:5px 7px;text-align:left;vertical-align:top}th{background:#f4f1ea}
.badge{font-size:11px;padding:2px 7px;border-radius:999px;font-family:ui-sans-serif,system-ui,sans-serif;white-space:nowrap}
.b-full{background:#dcfce7;color:#14532d}.b-mini{background:#fef3c7;color:#92400e}
.b-prop{background:#fee2e2;color:#991b1b}.b-pay{background:#e0e7ff;color:#3730a3}.b-unk{background:#f5f5f4;color:#57534e}
button{margin:0 4px 6px 0;padding:4px 10px;border:1px solid var(--line);border-radius:8px;background:#fff;cursor:pointer;font-size:13px}
footer{color:var(--muted);font-size:13px;margin-top:18px;font-family:ui-sans-serif,system-ui,sans-serif}
"""
tutorials = [
    ("harvey-factor-threshold", "Harvey–Sancetta–Zhao 因子 t 门槛", "public_fullish", "方法教学金矿"),
    ("bloated-disclosures", "Bloated Disclosures 机械代理", "public_mini", "非 GPT"),
    ("da-ah-premium", "Da 等 A-H 溢价", "public_mini", "无 LLM 工具"),
    ("hagenberg-liquidity-disclosure", "Hagenberg 流动性×披露", "public_mini", "DESIGN DRILL + MOCK"),
    ("goetzmann-bubbles", "Goetzmann 泡沫/崩盘", "public_mini", "SPX 实跑计数"),
]
cards = []
for slug, title, status, note in tutorials:
    bclass = "b-full" if "full" in status else "b-mini"
    cards.append(
        f'<div class="card"><h2><a href="{slug}/tutorial.html">{html.escape(title)}</a></h2>'
        f'<p><span class="badge {bclass}">{status}</span> {html.escape(note)}</p>'
        f'<p><code>python replications/{slug}/replicate.py</code></p></div>'
    )
badge = {
    "public_fullish": "b-full",
    "public_mini": "b-mini",
    "proprietary": "b-prop",
    "paywall_crsp": "b-pay",
    "unknown": "b-unk",
}
rows = []
for p in cat["papers"]:
    st = p["data_status"]
    tp = p["tutorial_path"]
    link = f'<a href="{html.escape(tp)}">教程</a>' if tp else "—"
    brief = f'<a href="{SITE}/{p["brief_path"]}">{p["date_brief"]}</a>'
    rows.append(
        f'<tr data-status="{st}"><td>{brief}</td><td>{html.escape(p["title"][:90])}</td>'
        f'<td>{html.escape(p["authors"][:55])}</td>'
        f'<td><span class="badge {badge.get(st, "b-unk")}">{st}</span></td>'
        f'<td>{html.escape((p.get("reason") or "")[:70])}</td><td>{link}</td>'
        f'<td>{p["priority_for_dongjie"]}</td></tr>'
    )
html_out = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>复现教程索引 · Jeff daily papers</title><style>{CSS}</style></head>
<body><div class="wrap">
<header><h1>复现 / 迷你复现教程</h1>
<p class="meta">Jeff 实证简报 2026-08-18–09-02 · 诚实标注专有数据</p></header>
<div class="card">
<p>面向董杰（本科计量）：只对<strong>公开可取</strong>的数据写可跑教程。</p>
<p>计数：total={counts['total']} · full-ish={counts['public_fullish']} · mini={counts['public_mini']} · proprietary={counts['proprietary']} · paywall_crsp={counts['paywall_crsp']} · unknown={counts['unknown']} · 已有教程={counts['with_tutorial']}</p>
</div>
<h2>Batch 1 教程</h2>
{''.join(cards)}
<h2>全目录</h2>
<p>
<button type="button" onclick="filt('all')">全部</button>
<button type="button" onclick="filt('public_fullish')">full-ish</button>
<button type="button" onclick="filt('public_mini')">mini</button>
<button type="button" onclick="filt('proprietary')">proprietary</button>
<button type="button" onclick="filt('paywall_crsp')">paywall</button>
<button type="button" onclick="filt('unknown')">unknown</button>
· <a href="catalog.json">catalog.json</a>
</p>
<table id="cat"><thead><tr><th>简报</th><th>标题</th><th>作者</th><th>data_status</th><th>原因</th><th>教程</th><th>优先级</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody></table>
<script>
function filt(s){{
  document.querySelectorAll('#cat tbody tr').forEach(function(tr){{
    tr.style.display = (s==='all' || tr.getAttribute('data-status')===s) ? '' : 'none';
  }});
}}
</script>
<footer>站点 <a href="{SITE}/">{SITE}</a></footer>
</div></body></html>
"""
(ROOT / "index.html").write_text(html_out, encoding="utf-8")
print("wrote index.html", (ROOT / "index.html").stat().st_size)
