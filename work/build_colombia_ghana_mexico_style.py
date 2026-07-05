import csv
import html
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def fnum(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def topic(topics, title):
    return next(item for item in topics if item.get("title") == title)


def market(topic_obj, title):
    return next(item for item in topic_obj.get("markets", []) if item.get("title") == title)


def outcome(market_obj, name):
    return next(item for item in market_obj.get("outcomes", []) if item.get("name") == name)


def tmo(topics, topic_title, market_title, outcome_name):
    return outcome(market(topic(topics, topic_title), market_title), outcome_name)


def titan_rows(kind):
    data = load_json(WORK / f"titan_col_gha_kind{kind}.json")
    names = {
        1: "澳* / Macauslot",
        3: "Crow* / Crown",
        8: "36* / Bet365",
        12: "易* / Easybet",
        24: "12* / 12bet",
        47: "平* / Pinnacle",
    }
    rows = []
    for company in data.get("companies", []):
        cid = company.get("companyId")
        if cid not in names:
            continue
        detail = (company.get("details") or [{}])[0]
        rows.append(
            {
                "company": names[cid],
                "first_home": fnum(detail.get("firstHomeOdds")),
                "first_line": fnum(detail.get("firstDrawOdds")),
                "first_away": fnum(detail.get("firstAwayOdds")),
                "home": fnum(detail.get("homeOdds")),
                "line": fnum(detail.get("drawOdds")),
                "away": fnum(detail.get("awayOdds")),
                "modify": detail.get("modifyTime"),
            }
        )
    return rows


def avg(rows, key):
    vals = [row[key] for row in rows if row[key] is not None]
    return sum(vals) / len(vals) if vals else 0


def profit(stake, price):
    return stake / price - stake


topics = load_json(OUT / "binance-colombia-ghana-topics.json")
main_topic = topic(topics, "Colombia vs. Ghana")
exact_topic = topic(topics, "Colombia vs. Ghana - Exact Score")

col_win = tmo(topics, "Colombia vs. Ghana", "COL", "Yes")
draw = tmo(topics, "Colombia vs. Ghana", "Draw", "Yes")
gha_win = tmo(topics, "Colombia vs. Ghana", "GHA", "Yes")
col_advance = tmo(topics, "Colombia vs. Ghana - More Markets", "Team to Advance", "COL")
col_m15 = tmo(topics, "Colombia vs. Ghana - More Markets", "Colombia (-1.5)", "COL")
under25 = tmo(topics, "Colombia vs. Ghana - More Markets", "O/U 2.5", "Under")
over25 = tmo(topics, "Colombia vs. Ghana - More Markets", "O/U 2.5", "Over")
under35 = tmo(topics, "Colombia vs. Ghana - More Markets", "O/U 3.5", "Under")
btts_no = tmo(topics, "Colombia vs. Ghana - More Markets", "Both Teams to Score", "No")
corners_over = tmo(topics, "Colombia vs. Ghana - Total Corners", "Total Corners: O/U 8.5", "Over 8.5")
corners_under = tmo(topics, "Colombia vs. Ghana - Total Corners", "Total Corners: O/U 8.5", "Under 8.5")
luis_diaz_goal = tmo(topics, "Colombia vs Ghana - Player Props", "Luis Diaz Total Goals", "Over 0.5")
jordan_ayew_goal = tmo(topics, "Colombia vs Ghana - Player Props", "Jordan Ayew Total Goals", "Over 0.5")

asian = titan_rows(0)
total = titan_rows(1)
corners = titan_rows(3)

exact_scores = []
for m in exact_topic.get("markets", []):
    yes = outcome(m, "Yes")
    exact_scores.append((m.get("title"), float(yes.get("chance")), float(yes.get("price"))))
exact_scores = sorted(exact_scores, key=lambda x: x[1], reverse=True)[:8]

allocation = [
    ("COL 90分鐘勝", 40, float(col_win["price"])),
    ("小 2.5", 30, float(under25["price"])),
    ("BTTS No", 20, float(btts_no["price"])),
    ("COL -1.5", 10, float(col_m15["price"])),
]


def passed(score):
    col, gha = score
    total_goals = col + gha
    ok = set()
    if col > gha:
        ok.add("COL 90分鐘勝")
    if total_goals < 2.5:
        ok.add("小 2.5")
    if gha == 0:
        ok.add("BTTS No")
    if col - gha >= 2:
        ok.add("COL -1.5")
    return ok


scenarios = []
for score in [(1, 0), (2, 0), (2, 1), (3, 0), (0, 0), (1, 1), (0, 1), (3, 1)]:
    ok = passed(score)
    net = 0.0
    for name, stake, price in allocation:
        net += profit(stake, price) if name in ok else -stake
    scenarios.append((f"{score[0]}-{score[1]}", net, [name for name, _, _ in allocation if name in ok]))

snapshot_path = OUT / "colombia-ghana-mexico-style-snapshot.csv"
with snapshot_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["source", "market", "price_or_water", "chance_or_line", "note"])
    writer.writerow(["Binance", "COL 90min win", col_win["price"], col_win["chance"], "favorite but not huge return"])
    writer.writerow(["Binance", "Under 2.5", under25["price"], under25["chance"], "main value versus external low-score reads"])
    writer.writerow(["Binance", "BTTS No", btts_no["price"], btts_no["chance"], "Ghana scoring risk priced moderate"])
    writer.writerow(["Binance", "COL -1.5", col_m15["price"], col_m15["chance"], "small add-on only"])
    writer.writerow(["Titan", "Asian average line", avg(asian, "home"), avg(asian, "line"), "Colombia around -1.25"])
    writer.writerow(["Titan", "Total average line", avg(total, "home"), avg(total, "line"), "total around 2.25"])
    writer.writerow(["Titan", "Corners average line", avg(corners, "home"), avg(corners, "line"), "corners around 8.5"])


def bar(label, value, color):
    width = max(1, min(100, float(value) * 100))
    return (
        f"<div class='bar-row'><div class='bar-label'>{html.escape(label)}</div>"
        f"<div class='bar-track'><div class='bar-fill' style='width:{width:.1f}%;background:{color}'></div></div>"
        f"<div class='bar-note'>{width:.1f}%</div></div>"
    )


def table_titan(rows, title, a, b):
    body = []
    for row in rows:
        body.append(
            f"<tr><td>{html.escape(row['company'])}</td><td>{row['first_home']}</td><td>{row['first_line']}</td><td>{row['first_away']}</td>"
            f"<td>{row['home']}</td><td>{row['line']}</td><td>{row['away']}</td></tr>"
        )
    return (
        f"<div class='table-card'><h3>{html.escape(title)}</h3><table>"
        f"<thead><tr><th>公司</th><th>初 {a}</th><th>初盤</th><th>初 {b}</th><th>即 {a}</th><th>即盤</th><th>即 {b}</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def sources_table():
    rows = [
        (
            "Covers",
            "主推 Colombia 90分鐘勝，另推 Under 2.5；文中給 Colombia -199、Under 2.5 -149。",
            "COL + 小球",
            "https://www.covers.com/world-cup/colombia-vs-ghana-prediction-picks-odds-friday-7-3-2026",
        ),
        (
            "SportsGambler",
            "主推 Under 2.5，給 65-70% 實際機率；正確比分預測 1-0 Colombia，並提到 Colombia -1.25。",
            "小 2.5 / 1-0",
            "https://www.sportsgambler.com/betting-tips/football/colombia-vs-ghana-prediction-lineups-odds-2026-07-03/",
        ),
        (
            "Racing Post",
            "賠率列 Colombia 晉級 2-9、90分鐘勝 1-2，Ghana 13-2；隊伍消息顯示哥倫比亞陣容完整。",
            "COL 強熱門",
            "https://www.racingpost.com/sport/football-tips/world-cup-2026/colombia-vs-ghana-betting-tips-predictions-team-news-odds-bet-builder-asduK6L54DEi/",
        ),
        (
            "Pickswise",
            "主推 Colombia ML，認為哥倫比亞防守穩、能限制迦納並晉級。",
            "COL 勝",
            "https://www.pickswise.com/world-cup/games/colombia-ghana-world-cup-26-2026-07-04-0130/picks/",
        ),
        (
            "SI",
            "預測這場可能是細節戰，兩隊小組賽總進球不多，偏低比分。",
            "低比分",
            "https://www.si.com/soccer/colombia-vs-ghana-world-cup-preview-predictions-lineups-7-3-26",
        ),
    ]
    return "".join(
        f"<tr><td><a href='{html.escape(url)}'>{html.escape(src)}</a></td><td>{html.escape(read)}</td><td><span class='pill'>{html.escape(signal)}</span></td></tr>"
        for src, read, signal, url in rows
    )


def allocation_table():
    return "".join(
        f"<tr><td>{html.escape(name)}</td><td>{stake}U</td><td>{price:.2f}</td><td>+{profit(stake, price):.2f}U</td></tr>"
        for name, stake, price in allocation
    )


def scenario_table():
    body = []
    for score, net, ok in scenarios:
        cls = "good" if net > 0 else "bad"
        body.append(f"<tr><td>{score}</td><td class='{cls}'>{net:+.2f}U</td><td>{html.escape(', '.join(ok) if ok else '無')}</td></tr>")
    return "".join(body)


def exact_score_bars():
    colors = ["#2563eb", "#7c3aed", "#059669", "#d97706", "#0891b2", "#dc2626", "#64748b", "#0f766e"]
    return "".join(bar(label, chance, colors[i % len(colors)]) for i, (label, chance, _) in enumerate(exact_scores))


doc = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>哥倫比亞 vs 迦納 賽前盤勢分析</title>
  <style>
    :root {{
      --bg:#f3f6fb; --panel:#fff; --ink:#172033; --muted:#647084; --line:#d9e2ef;
      --blue:#2563eb; --green:#059669; --amber:#d97706; --red:#dc2626; --violet:#7c3aed; --cyan:#0891b2;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Arial,"Microsoft JhengHei",sans-serif; background:var(--bg); color:var(--ink); }}
    header {{ padding:34px 28px 24px; background:#101827; color:#fff; }}
    header h1 {{ margin:0 0 8px; font-size:30px; letter-spacing:0; }}
    header p {{ margin:0; color:#cbd5e1; max-width:1040px; line-height:1.65; }}
    main {{ max-width:1180px; margin:0 auto; padding:22px; }}
    section {{ margin:18px 0; }}
    .grid {{ display:grid; gap:14px; grid-template-columns:repeat(4,minmax(0,1fr)); }}
    .two-col {{ display:grid; gap:14px; grid-template-columns:1.05fr .95fr; }}
    .three-col {{ display:grid; gap:14px; grid-template-columns:repeat(3,1fr); }}
    .card,.chart-card,.table-card,.callout {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; box-shadow:0 1px 2px rgba(15,23,42,.04); }}
    .card h2 {{ margin:0 0 8px; font-size:15px; color:var(--muted); font-weight:700; }}
    .metric {{ font-size:26px; font-weight:800; margin-bottom:6px; }}
    .card p,.small {{ margin:0; line-height:1.55; color:var(--muted); font-size:13px; }}
    .section-title {{ display:flex; align-items:end; justify-content:space-between; gap:12px; margin:24px 0 10px; }}
    .section-title h2 {{ margin:0; font-size:20px; }}
    .section-title p {{ margin:0; color:var(--muted); font-size:13px; }}
    .callout {{ border-left:4px solid var(--blue); background:#eff6ff; line-height:1.65; }}
    .callout strong {{ color:#1e3a8a; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    th,td {{ text-align:left; padding:10px 9px; border-bottom:1px solid var(--line); vertical-align:top; }}
    th {{ color:#475569; background:#f8fafc; font-size:13px; }}
    td a {{ color:var(--blue); text-decoration:none; }}
    .bar-row {{ display:grid; grid-template-columns:150px 1fr 68px; gap:10px; align-items:center; margin:10px 0; }}
    .bar-label {{ font-size:13px; font-weight:700; }}
    .bar-track {{ height:13px; background:#e9eef6; border-radius:99px; overflow:hidden; }}
    .bar-fill {{ height:100%; border-radius:99px; }}
    .bar-note {{ font-size:12px; color:var(--muted); text-align:right; }}
    .pill {{ display:inline-block; padding:3px 8px; border-radius:99px; background:#e0ecff; color:#1d4ed8; font-weight:700; font-size:12px; white-space:nowrap; }}
    .good {{ color:#047857; font-weight:800; }}
    .bad {{ color:#b91c1c; font-weight:800; }}
    ul.clean {{ margin:0; padding-left:18px; line-height:1.7; }}
    @media (max-width:900px) {{
      .grid,.two-col,.three-col {{ grid-template-columns:1fr; }}
      header h1 {{ font-size:24px; }}
      .bar-row {{ grid-template-columns:1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>哥倫比亞 vs 迦納：賽前盤勢分析</h1>
    <p>比照墨西哥 vs 厄瓜多頁的格式整理。資料來源為 Binance Prediction、Titan007 2907391、Covers、SportsGambler、Racing Post、Pickswise、SI。更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}。</p>
  </header>
  <main>
    <section class="grid">
      <div class="card"><h2>主結論</h2><div class="metric">COL + 小球</div><p>哥倫比亞勝方向一致，但盤面更像 1-0 / 2-0，不是大開大合。</p></div>
      <div class="card"><h2>Binance COL 勝</h2><div class="metric">{float(col_win['chance'])*100:.1f}%</div><p>價格 {float(col_win['price']):.2f}，比晉級有報酬。</p></div>
      <div class="card"><h2>小 2.5</h2><div class="metric">{float(under25['chance'])*100:.1f}%</div><p>Binance 機率低於外部小球估值，是本場重點。</p></div>
      <div class="card"><h2>Titan 主盤</h2><div class="metric">COL -1.25</div><p>哥倫比亞讓深，但水位不支持無腦追 -1.5。</p></div>
    </section>

    <section>
      <div class="section-title"><h2>盤勢結論</h2><p>先看盤口，再看下注</p></div>
      <div class="callout">
        <strong>最合理劇本是哥倫比亞 1-0 或 2-0。</strong>
        Binance 的 COL 勝是 68.5%，Titan 亞洲盤推到 -1.25，但外部來源與大小球盤更偏低比分。
        所以我不把 COL -1.5 當主單，只把它當 10U 的加碼單。
      </div>
    </section>

    <section class="three-col">
      <div class="chart-card">
        <h3>Binance 90分鐘勝平負</h3>
        {bar("COL 勝", col_win["chance"], "#2563eb")}
        {bar("平局", draw["chance"], "#d97706")}
        {bar("GHA 勝", gha_win["chance"], "#dc2626")}
      </div>
      <div class="chart-card">
        <h3>Binance 可操作項目</h3>
        {bar("COL 勝", col_win["chance"], "#2563eb")}
        {bar("小 2.5", under25["chance"], "#059669")}
        {bar("BTTS No", btts_no["chance"], "#0891b2")}
        {bar("COL -1.5", col_m15["chance"], "#7c3aed")}
      </div>
      <div class="chart-card">
        <h3>正確比分前段</h3>
        {exact_score_bars()}
      </div>
    </section>

    <section>
      <div class="section-title"><h2>Titan007 快照</h2><p>初盤 vs 即時盤，非賽後資料</p></div>
      <div class="three-col">
        {table_titan(asian, "亞讓：哥倫比亞讓球", "COL", "GHA")}
        {table_titan(total, "大小球：總進球", "大", "小")}
        {table_titan(corners, "角球：總角球", "大", "小")}
      </div>
    </section>

    <section class="two-col">
      <div class="table-card">
        <div class="section-title"><h2>外部來源</h2><p>多來源方向一致性</p></div>
        <table><thead><tr><th>來源</th><th>賽前看法</th><th>訊號</th></tr></thead><tbody>{sources_table()}</tbody></table>
      </div>
      <div class="table-card">
        <div class="section-title"><h2>Binance 價格門檻</h2><p>方向對不代表值得重壓</p></div>
        <table>
          <thead><tr><th>項目</th><th>目前價格</th><th>判斷</th></tr></thead>
          <tbody>
            <tr><td>COL 晉級</td><td>{float(col_advance['price']):.2f}</td><td>穩但太貴，收益低。</td></tr>
            <tr><td>COL 90分鐘勝</td><td>{float(col_win['price']):.2f}</td><td>主單之一，比晉級更可操作。</td></tr>
            <tr><td>小 2.5</td><td>{float(under25['price']):.2f}</td><td>本場最有價值的盤，外部更偏小球。</td></tr>
            <tr><td>BTTS No</td><td>{float(btts_no['price']):.2f}</td><td>配合 1-0 / 2-0 劇本。</td></tr>
            <tr><td>COL -1.5</td><td>{float(col_m15['price']):.2f}</td><td>只能小注；1-0 會輸。</td></tr>
            <tr><td>角球大 8.5</td><td>{float(corners_over['price']):.2f}</td><td>接近五五波，不列主單。</td></tr>
            <tr><td>Luis Diaz 進球</td><td>{float(luis_diaz_goal['price']):.2f}</td><td>可玩但非主線。</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="two-col">
      <div class="table-card">
        <div class="section-title"><h2>100U 分配</h2><p>一單一單下，不串關</p></div>
        <table><thead><tr><th>下注項目</th><th>本金</th><th>Binance 價格</th><th>過關淨利</th></tr></thead><tbody>{allocation_table()}</tbody></table>
        <p class="small" style="margin-top:10px">這組押的是哥倫比亞常規時間勝、低比分、迦納不進球；COL -1.5 只放 10U。</p>
      </div>
      <div class="table-card">
        <div class="section-title"><h2>比分情境</h2><p>依 100U 分配估算</p></div>
        <table><thead><tr><th>比分</th><th>理論淨損益</th><th>會過的項目</th></tr></thead><tbody>{scenario_table()}</tbody></table>
      </div>
    </section>

    <section class="table-card">
      <div class="section-title"><h2>最後判斷</h2><p>本場比阿根廷那場更偏保守</p></div>
      <ul class="clean">
        <li>主線：COL 90分鐘勝 + 小 2.5。外部與 Binance/Titan 都支持哥倫比亞方向，但比分預期偏低。</li>
        <li>搭配：BTTS No。迦納進球價格偏低，外部也多看哥倫比亞零封或低比分勝。</li>
        <li>小注：COL -1.5。Titan -1.25 有支持，但 1-0 是很合理比分，所以不重押。</li>
        <li>不建議：COL 晉級，太貴；角球 8.5 接近五五波；球員進球波動高。</li>
      </ul>
    </section>
  </main>
</body>
</html>
"""

out_path = OUT / "colombia-ghana-mexico-style-analysis.html"
out_path.write_text(doc, encoding="utf-8")
print(out_path)
print(snapshot_path)
