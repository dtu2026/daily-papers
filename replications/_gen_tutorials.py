#!/usr/bin/env python3
import json, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = "https://dtu2026.github.io/daily-papers"
CSS = """
:root{--ink:#1c1917;--muted:#57534e;--line:#e7e5e4;--paper:#faf7f2;--card:#fff;--accent:#9a3412;--tag:#f5e6d3}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.7 "Source Han Serif SC","Noto Serif SC","Songti SC","SimSun",Georgia,serif}
.wrap{max-width:780px;margin:0 auto;padding:48px 22px 80px}header h1{font-size:26px;font-weight:650;margin:0 0 8px}
.meta{color:var(--muted);font-size:14px;margin-bottom:22px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px;margin:0 0 22px}
h2{font-size:19px;margin:0 0 10px;color:var(--accent);font-family:ui-sans-serif,system-ui,sans-serif}
h3{font-size:15px;margin:18px 0 6px;color:var(--accent);font-family:ui-sans-serif,system-ui,sans-serif}
p{margin:0 0 10px}ul,ol{margin:0 0 10px;padding-left:1.2em}li{margin:3px 0}
.qual{background:#f4f1ea;border-left:3px solid var(--accent);padding:10px 14px;font-size:15px;margin:10px 0 14px}
table{width:100%;border-collapse:collapse;font-size:14px;margin:10px 0 14px;font-family:ui-sans-serif,system-ui,sans-serif}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left}th{background:#f4f1ea}
code,pre{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px}
pre{background:#1c1917;color:#faf7f2;padding:12px 14px;border-radius:10px;overflow:auto}
a{color:var(--accent)}footer{color:var(--muted);font-size:13px;margin-top:18px;font-family:ui-sans-serif,system-ui,sans-serif}
.tag{display:inline-block;background:var(--tag);color:var(--accent);font-size:12px;padding:2px 8px;border-radius:999px;margin-right:6px;font-family:ui-sans-serif,system-ui,sans-serif}
"""

def page(title, body, meta):
    return (
        "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class=\"wrap\">"
        f"<header><h1>{html.escape(title)}</h1><p class=\"meta\">{meta}</p></header>"
        f"{body}"
        f"<footer>回到 <a href=\"../index.html\">复现教程索引</a> · "
        f"<a href=\"{SITE}/\">{SITE}</a></footer></div></body></html>"
    )

def load(slug):
    return json.loads((ROOT / slug / "results.json").read_text())

def write(slug, title, body, meta):
    (ROOT / slug / "tutorial.html").write_text(page(title, body, meta), encoding="utf-8")
    print("wrote", slug)

# A
r = load("harvey-factor-threshold")
ana = r["analytical_independent_null"]
rows = "".join(
    f"<tr><td>{html.escape(x['name'])}</td><td>{x['t_alpha']:.3f}</td></tr>"
    for x in r["industry_alphas"][:8]
)
body = f"""
<div class="card">
<span class="tag">public_fullish · 方法教学</span>
<div class="qual"><strong>一句话：</strong>可以用公开 Ken French 因子库完整演示多重检验下 t=1.96 vs t=3.0–3.5；不能声称复现作者对 29,314 个会计因子的 FDR 全表。</div>
<h3>数据来源</h3>
<ul>
<li>FF5 daily：<a href="{r['data_urls'][0]}">Ken French FTP</a></li>
<li>10 Industry daily：<a href="{r['data_urls'][1]}">Ken French FTP</a></li>
</ul>
<h3>识别 / 在比什么</h3>
<p>同一个 t 在「测 1 次」与「挖 N=500 次」时虚假发现含义不同。怕：相关因子让零假设不再是 N(0,1)。</p>
<h3>规格</h3>
<p><code>R_i,t - R_f,t = α_i + β'F_t + e</code>，看 α 的 t。中文：FF5 回归截距的 t；再问挖了 500 个组合还能不能用 1.96。</p>
<h3>怎么跑</h3>
<pre>cd replications/harvey-factor-threshold
source ../.venv/bin/activate && python replicate.py</pre>
<h3>实跑结果</h3>
<p>样本 {r['sample_start']} → {r['sample_end']}，N={r['n_days']} 日；挖掘 {r['n_fake_factors']} 个随机行业多空。</p>
<table><tr><th>门槛</th><th>实证拒绝份额</th><th>个数</th><th>独立正态期望假发现(N=500)</th></tr>
<tr><td>|t|&gt;1.96</td><td>{r['share_reject_fake']['t_1.96']:.3f}</td><td>{r['count_reject_fake']['t_1.96']}</td><td>{ana['t_1.96']['expected_false_discoveries_out_of_N']:.1f}</td></tr>
<tr><td>|t|&gt;3.00</td><td>{r['share_reject_fake']['t_3.00']:.3f}</td><td>{r['count_reject_fake']['t_3.00']}</td><td>{ana['t_3.0']['expected_false_discoveries_out_of_N']:.1f}</td></tr>
<tr><td>|t|&gt;3.50</td><td>{r['share_reject_fake']['t_3.50']:.3f}</td><td>{r['count_reject_fake']['t_3.50']}</td><td>{ana['t_3.5']['expected_false_discoveries_out_of_N']:.1f}</td></tr>
</table>
<p>max |t|={r['max_abs_t_in_search']:.2f}；Bonferroni≈{r['bonferroni_5pct_approx_t']:.2f}。论文建议因子研究 t≈3.0–3.5。</p>
<table><tr><th>行业</th><th>FF5-α t</th></tr>{rows}</table>
<p class="qual">{html.escape(r['teaching_note'])}</p>
<h3>坑</h3>
<ul><li>FF5 残差后行业组合不易假显著——务必对照解析表。</li>
<li>有制度故事的 DiD 与数据挖掘因子不要同一门槛。</li></ul>
<h3>链接</h3>
<p><a href="{SITE}/jeff/2026-09-01.html#p4">简报 2026-09-01</a> · <a href="https://www.nber.org/papers/w34898">NBER w34898</a></p>
</div>"""
write("harvey-factor-threshold", "Harvey–Sancetta–Zhao：因子检验该用多高的 t？", body, "NBER WP 34898 · public_fullish · 方法教学")

# B
r = load("bloated-disclosures")
reg = r.get("regression") or {}
params, tvals = reg.get("params", {}), reg.get("tvalues", {})
tab_parts = []
for x in r["table"][:12]:
    car = "" if x.get("car_0_1") is None else f"{x['car_0_1']:.4f}"
    tab_parts.append(
        f"<tr><td>{html.escape(x['ticker'])}</td><td>{x['filingDate']}</td><td>{x['tokens']}</td>"
        f"<td>{x['gzip_ratio']:.3f}</td><td>{x['unique_ratio']:.3f}</td><td>{car}</td></tr>"
    )
tab = "".join(tab_parts)
body = f"""
<div class="card">
<span class="tag">public_mini · 披露文本</span>
<div class="qual"><strong>一句话：</strong>可从 EDGAR 拉 10-K 算长度/压缩率/独特词比并试小样本 CAR；不能复现 GPT-Bloat 与 PIN/价差主表。</div>
<h3>数据来源</h3>
<ul><li>https://data.sec.gov/submissions/</li>
<li>https://www.sec.gov/Archives/edgar/data/</li>
<li>Yahoo chart API（CAR）</li></ul>
<h3>识别</h3>
<p>论文：raw vs GPT summary。我们：公司间机械冗余代理 vs 短窗收益——相关非因果，且无 GPT。</p>
<h3>规格</h3>
<p><code>CAR[0,1] = a + b·CompressionSavings + c·log(Tokens) + e</code></p>
<h3>怎么跑</h3>
<pre>cd replications/bloated-disclosures
source ../.venv/bin/activate && python replicate.py</pre>
<h3>实跑结果</h3>
<p>n={r['n_filings']} 份 10-K；均 tokens={r['mean_tokens']:.0f}；gzip_ratio={r['mean_gzip_ratio']:.3f}；unique_ratio={r['mean_unique_ratio']:.3f}；corr(compression,CAR)={r['corr_compression_car']:.3f}。</p>
<table><tr><th>Ticker</th><th>Filing</th><th>Tokens</th><th>gzip</th><th>unique</th><th>CAR[0,1]</th></tr>{tab}</table>
<p>回归 n={reg.get('n')}：b_comp={params.get('compression_savings', float('nan')):.4f} (t={tvals.get('compression_savings', float('nan')):.2f})；
b_logtok={params.get('log_tokens', float('nan')):.4f} (t={tvals.get('log_tokens', float('nan')):.2f})；R²={reg.get('rsquared', float('nan')):.3f}。</p>
<p class="qual">{html.escape(r['caveat'])}</p>
<h3>坑</h3>
<ul><li>Item 7 启发式抽取。</li><li>CAR 未扣市场。</li><li>A 股中文需重做 LLM prompt。</li></ul>
<p><a href="{SITE}/jeff/2026-09-02.html#p2">简报 2026-09-02</a> · <a href="https://arxiv.org/pdf/2306.10224.pdf">arXiv PDF</a></p>
</div>"""
write("bloated-disclosures", "Kim–Muhn–Nikolaev：膨胀的披露（机械代理版）", body, "SSRN 4425527 · public_mini")

# C
r = load("da-ah-premium")
prows = "".join(
    f"<tr><td>{html.escape(x['name'])}</td><td>{x['pre_mean_premium']:.4f}</td>"
    f"<td>{x['post5_mean_premium']:.4f}</td><td>{x['delta_post5_minus_pre']:.4f}</td></tr>"
    for x in r["pairs_event"]
)
reg = r.get("regression_pm90") or {}
cs = r["cross_section_event"]
body = f"""
<div class="card">
<span class="tag">public_mini · A/H</span>
<div class="qual"><strong>一句话：</strong>可用公开行情构造 AH 溢价并在 2023-08-31 附近做事件窗；不能复现 LLM 注意力工具变量。</div>
<h3>数据</h3>
<ul><li>Yahoo：A <code>*.SS</code> / H <code>*.HK</code> / <code>CNY=X</code></li>
<li>深读：/workspace/research/papers/da_llm_lop_explained.html</li></ul>
<h3>规格</h3>
<p><code>Premium = A/(H×CNY_per_HKD) - 1</code>；±90 日 post 虚拟变量（公司去均值）。</p>
<pre>cd replications/da-ah-premium && source ../.venv/bin/activate && python replicate.py</pre>
<h3>实跑</h3>
<p>{r['sample_start']}→{r['sample_end']}，{r['n_pairs']} 对；均溢价 {r['sample_premium_mean']:.4f}。</p>
<p>等权溢价：事前 {cs['pre_mean_premium']:.4f}，事后5日 {cs['post5_mean_premium']:.4f}，Δ=<strong>{cs['delta_post5_minus_pre']:.4f}</strong>。</p>
<table><tr><th>公司</th><th>事前</th><th>事后5日</th><th>Δ</th></tr>{prows}</table>
<p>±90 日 post 系数={reg.get('panel_post_coef', float('nan')):.4f}，t={reg.get('panel_post_t', float('nan')):.2f}，n={reg.get('panel_n')}（不显著——符合预期）。</p>
<p class="qual">{html.escape(r['caveat'])}</p>
<p><a href="{SITE}/jeff/2026-08-19.html#p2">简报 2026-08-19</a></p>
</div>"""
write("da-ah-premium", "Da 等：AI 与 A-H 溢价（价格迷你版）", body, "SSRN 5234282 · public_mini")

# D
r = load("hagenberg-liquidity-disclosure")
mock = r["mock_did"]
means, reg = mock["means"], mock["regression"]
params, tvals = reg["params"], reg["tvalues"]
rrows = "".join(
    f"<tr><td>{x['code']}</td><td>{x['n_anns_pulled']}</td><td>{x['date_min']}→{x['date_max']}</td>"
    f"<td>{x['n_forecast_like']}</td></tr>"
    for x in r["real_announcement_pull"]
)
how = "".join(f"<li>{html.escape(x)}</li>" for x in r["how_you_would_did_this"])
body = f"""
<div class="card">
<span class="tag">public_mini · DESIGN DRILL</span>
<div class="qual"><strong>一句话：</strong>不是 Hagenberg 复现。演示 A 股 DiD 设计 + 真实拉取近期末公告；2019 冲击无法在此做真 DiD，回归为 <em>MOCK</em>。</div>
<h3>你该怎么做</h3><ol>{how}</ol>
<p>拟冲击：{r['shock_intended']['date']} 两融扩容。缺口：{html.escape(r['shock_intended']['data_gap'])}</p>
<pre>cd replications/hagenberg-liquidity-disclosure && source ../.venv/bin/activate && python replicate.py</pre>
<table><tr><th>代码</th><th>公告数</th><th>日期</th><th>预告类</th></tr>{rrows}</table>
<h3>MOCK DiD（禁止当结论）</h3>
<p>simple DiD=<strong>{means['simple_did']:.2f}</strong>；d̂={params['did']:.3f} (t={tvals['did']:.2f})；n={reg['n']}。</p>
<table><tr><th></th><th>Pre</th><th>Post</th></tr>
<tr><td>Treated</td><td>{means['treated_pre']:.2f}</td><td>{means['treated_post']:.2f}</td></tr>
<tr><td>Control</td><td>{means['control_pre']:.2f}</td><td>{means['control_post']:.2f}</td></tr></table>
<p class="qual">{html.escape(mock['warning'])}</p>
<p><a href="{SITE}/jeff/2026-08-31.html#p3">简报 2026-08-31</a></p>
</div>"""
write("hagenberg-liquidity-disclosure", "Hagenberg 等：流动性与自愿披露（A股设计演练）", body, "RAST · DESIGN DRILL")

# E
r = load("goetzmann-bubbles")
pref = r["preferred_spec"]
booms = "".join(
    f"<tr><td>{b['start_date']}→{b['end_date']}</td><td>{b['cum_ret']*100:.1f}%</td></tr>"
    for b in pref["example_booms"]
)
crashes = "".join(
    f"<tr><td>{c['start_date']}→{c['end_date']}</td><td>{c['cum_ret']*100:.1f}%</td></tr>"
    for c in pref["example_crashes"]
)
allspecs = "".join(
    f"<tr><td>{s['horizon']}m / +{s['boom_th']*100:.0f}% / {s['crash_th']*100:.0f}%</td>"
    f"<td>{s['n_booms']}</td><td>{s['n_crashes']}</td></tr>"
    for s in r["all_specs"]
)
body = f"""
<div class="card">
<span class="tag">public_mini · 泡沫</span>
<div class="qual"><strong>一句话：</strong>可在公开标普月度序列上实现透明暴涨/暴跌定义并计数；不能声称复现 1792–2024 重建指数全表。</div>
<pre>cd replications/goetzmann-bubbles && source ../.venv/bin/activate && python replicate.py</pre>
<p>{html.escape(r['index'])}；{r['sample_start']}→{r['sample_end']}，{r['n_months']} 个月。</p>
<p>主规格 24m / +80% / −35%：暴涨 <strong>{pref['n_booms']}</strong>，暴跌 <strong>{pref['n_crashes']}</strong>。</p>
<table><tr><th>规格</th><th>#booms</th><th>#crashes</th></tr>{allspecs}</table>
<p>暴涨例</p><table><tr><th>窗口</th><th>收益</th></tr>{booms}</table>
<p>暴跌例</p><table><tr><th>窗口</th><th>收益</th></tr>{crashes}</table>
<p class="qual">{html.escape(r['caveat'])}</p>
<p><a href="{SITE}/jeff/2026-08-25.html#p4">简报 2026-08-25</a> · <a href="https://www.nber.org/papers/w34903">w34903</a></p>
</div>"""
write("goetzmann-bubbles", "Goetzmann 等：美股泡沫与崩盘（公开指数迷你版）", body, "NBER WP 34903 · public_mini")

print("done")
