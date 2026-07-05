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


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt_pct(value):
    return f"{float(value) * 100:.1f}%"


def profit(stake, price):
    return stake / price - stake


def pick_topic(topics, title):
    return next(topic for topic in topics if topic.get("title") == title)


def pick_market(topic, title):
    return next(market for market in topic.get("markets", []) if market.get("title") == title)


def pick_outcome(market, name):
    return next(outcome for outcome in market.get("outcomes", []) if outcome.get("name") == name)


def topic_market_outcome(topics, topic_title, market_title, outcome_name):
    return pick_outcome(pick_market(pick_topic(topics, topic_title), market_title), outcome_name)


def titan_companies(kind):
    data = load_json(WORK / f"titan_arg_cvi_kind{kind}.json")
    rows = []
    names = {
        1: "澳* / Macauslot",
        3: "Crow* / Crown",
        8: "36* / Bet365",
        12: "易* / Easybet",
        24: "12* / 12bet",
        47: "平* / Pinnacle",
    }
    for company in data.get("companies", []):
        cid = company.get("companyId")
        if cid not in names:
            continue
        detail = (company.get("details") or [{}])[0]
        rows.append(
            {
                "company": names[cid],
                "first_home": as_float(detail.get("firstHomeOdds")),
                "first_line": as_float(detail.get("firstDrawOdds")),
                "first_away": as_float(detail.get("firstAwayOdds")),
                "home": as_float(detail.get("homeOdds")),
                "line": as_float(detail.get("drawOdds")),
                "away": as_float(detail.get("awayOdds")),
                "modify": detail.get("modifyTime"),
            }
        )
    return rows


def avg_line(rows):
    vals = [row["line"] for row in rows if row["line"] is not None]
    return sum(vals) / len(vals) if vals else 0


def avg_home(rows):
    vals = [row["home"] for row in rows if row["home"] is not None]
    return sum(vals) / len(vals) if vals else 0


def avg_away(rows):
    vals = [row["away"] for row in rows if row["away"] is not None]
    return sum(vals) / len(vals) if vals else 0


topics = load_json(OUT / "binance-argentina-caboverde-topics.json")
main_topic = pick_topic(topics, "Argentina vs. Cabo Verde")
exact_topic = pick_topic(topics, "Argentina vs. Cabo Verde - Exact Score")

arg_win = topic_market_outcome(topics, "Argentina vs. Cabo Verde", "ARG", "Yes")
draw = topic_market_outcome(topics, "Argentina vs. Cabo Verde", "Draw", "Yes")
cvi_win = topic_market_outcome(topics, "Argentina vs. Cabo Verde", "CVI", "Yes")
arg_advance = topic_market_outcome(topics, "Argentina vs. Cabo Verde - More Markets", "Team to Advance", "ARG")
arg_m15 = topic_market_outcome(topics, "Argentina vs. Cabo Verde - More Markets", "Argentina (-1.5)", "ARG")
arg_m25 = topic_market_outcome(topics, "Argentina vs. Cabo Verde - More Markets", "Argentina (-2.5)", "ARG")
over25 = topic_market_outcome(topics, "Argentina vs. Cabo Verde - More Markets", "O/U 2.5", "Over")
under35 = topic_market_outcome(topics, "Argentina vs. Cabo Verde - More Markets", "O/U 3.5", "Under")
btts_no = topic_market_outcome(topics, "Argentina vs. Cabo Verde - More Markets", "Both Teams to Score", "No")
corners_under = topic_market_outcome(topics, "Argentina vs. Cabo Verde - Total Corners", "Total Corners: O/U 9.5", "Under 9.5")
messi_goal = topic_market_outcome(topics, "Argentina vs Cabo Verde - Player Props", "Lionel Messi Total Goals", "Over 0.5")

asian_rows = titan_companies(0)
total_rows = titan_companies(1)
corner_rows = titan_companies(3)

exact_scores = []
for market in exact_topic.get("markets", []):
    yes = pick_outcome(market, "Yes")
    exact_scores.append((market.get("title"), float(yes.get("chance")), float(yes.get("price"))))
exact_scores = sorted(exact_scores, key=lambda x: x[1], reverse=True)[:8]

allocation = [
    ("ARG -1.5", 45, float(arg_m15["price"])),
    ("小 3.5", 30, float(under35["price"])),
    ("BTTS No", 20, float(btts_no["price"])),
    ("ARG -2.5", 5, float(arg_m25["price"])),
]


def passed_bets(score):
    arg, cvi = score
    total = arg + cvi
    passed = set()
    if arg - cvi >= 2:
        passed.add("ARG -1.5")
    if total < 3.5:
        passed.add("小 3.5")
    if cvi == 0:
        passed.add("BTTS No")
    if arg - cvi >= 3:
        passed.add("ARG -2.5")
    return passed


scenario_scores = [(2, 0), (3, 0), (4, 0), (2, 1), (3, 1), (1, 0), (1, 1), (0, 0)]
scenario_rows = []
for score in scenario_scores:
    passed = passed_bets(score)
    net = 0.0
    for name, stake, price in allocation:
        net += profit(stake, price) if name in passed else -stake
    scenario_rows.append((f"{score[0]}-{score[1]}", net, [name for name, _, _ in allocation if name in passed]))


snapshot_path = OUT / "argentina-caboverde-mexico-style-snapshot.csv"
with snapshot_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["source", "market", "price_or_water", "chance_or_line", "note"])
    writer.writerow(["Binance", "ARG 90min win", arg_win["price"], arg_win["chance"], "direction correct but low return"])
    writer.writerow(["Binance", "ARG -1.5", arg_m15["price"], arg_m15["chance"], "main bet candidate"])
    writer.writerow(["Binance", "Under 3.5", under35["price"], under35["chance"], "paired with control-win script"])
    writer.writerow(["Binance", "BTTS No", btts_no["price"], btts_no["chance"], "Cape Verde scoring risk low"])
    writer.writerow(["Titan", "Asian average line", avg_home(asian_rows), avg_line(asian_rows), "Argentina around -2"])
    writer.writerow(["Titan", "Total average line", avg_home(total_rows), avg_line(total_rows), "total around 3"])
    writer.writerow(["Titan", "Corners average line", avg_home(corner_rows), avg_line(corner_rows), "corners around 8.5-9.5"])


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


def source_rows():
    rows = [
        ("SportsGambler", "Argentina -2 亞洲盤；兩球勝退本金，贏三球以上全贏。", "深讓方向", "https://www.sportsgambler.com/betting-tips/football/argentina-vs-cape-verde-prediction-lineups-odds-2026-07-03/"),
        ("Racing Post", "阿根廷晉級賠率極低；主文方向偏阿根廷勝，並有小比分控制勝的 Bet Builder 思路。", "ARG + 小球", "https://www.racingpost.com/sport/football-tips/world-cup-2026/argentina-vs-cape-verde-world-cup-prediction-team-news-odds-betting-tips-and-bet-builder-aurGJ5y7Avbh/"),
        ("Pickswise", "Argentina -1.5；認為阿根廷至少贏兩球仍有價值。", "ARG -1.5", "https://www.pickswise.com/world-cup/games/argentina-cabo-verde-world-cup-26-2026-07-03-2200/picks/"),
        ("Covers", "Argentina -1.5 為主推，認為世界冠軍會拉開差距。", "ARG -1.5", "https://www.covers.com/world-cup/argentina-vs-cape-verde-prediction-picks-odds-friday-7-3-2026"),
        ("Action Network", "盤口顯示 Argentina -2.5 / Total 2.5 附近；市場一面倒阿根廷但價格已熱。", "注意過熱", "https://www.actionnetwork.com/worldcup-game/cape-verde-argentina-score-odds-july-3-2026/292409"),
    ]
    return "".join(
        f"<tr><td><a href='{html.escape(url)}'>{html.escape(src)}</a></td><td>{html.escape(read)}</td><td><span class='pill'>{html.escape(signal)}</span></td></tr>"
        for src, read, signal, url in rows
    )


def allocation_rows():
    return "".join(
        f"<tr><td>{html.escape(name)}</td><td>{stake}U</td><td>{price:.2f}</td><td>+{profit(stake, price):.2f}U</td></tr>"
        for name, stake, price in allocation
    )


def scenario_table():
    rows = []
    for score, net, passed in scenario_rows:
        cls = "good" if net > 0 else "bad"
        rows.append(
            f"<tr><td>{score}</td><td class='{cls}'>{net:+.2f}U</td><td>{html.escape(', '.join(passed) if passed else '無')}</td></tr>"
        )
    return "".join(rows)


def exact_score_bars():
    colors = ["#2563eb", "#7c3aed", "#059669", "#0891b2", "#d97706", "#dc2626", "#64748b", "#0f766e"]
    return "".join(bar(label, chance, colors[i % len(colors)]) for i, (label, chance, _) in enumerate(exact_scores))


doc = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>阿根廷 vs 維德角 賽前盤勢分析</title>
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
    <h1>阿根廷 vs 維德角：賽前盤勢分析</h1>
    <p>比照墨西哥 vs 厄瓜多頁的格式整理。這份是賽前分析，不吃賽後數據；資料來源為 Binance Prediction、Titan007 2907390、以及公開預測網站。更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}。</p>
  </header>
  <main>
    <section class="grid">
      <div class="card"><h2>主結論</h2><div class="metric">ARG -1.5</div><p>比阿根廷勝/晉級更有賠率，且貼近 Titan -2 主盤。</p></div>
      <div class="card"><h2>Binance 核心價</h2><div class="metric">66.5%</div><p>ARG -1.5 的市場機率；不是便宜到誇張，但比買主勝合理。</p></div>
      <div class="card"><h2>Titan 主盤</h2><div class="metric">ARG -2</div><p>多數公司即時盤集中在阿根廷讓 2 球。</p></div>
      <div class="card"><h2>總進球</h2><div class="metric">3 球</div><p>小球水位偏低，盤勢不支持無腦追大 3.5。</p></div>
    </section>

    <section>
      <div class="section-title"><h2>盤勢結論</h2><p>像墨西哥頁一樣，先看盤口推論</p></div>
      <div class="callout">
        <strong>最合理劇本是阿根廷 2-0 或 3-0 控場勝。</strong>
        市場不是只說「阿根廷會贏」，而是把主盤推到 -2，代表至少兩球差的期待很高；
        但總進球停在 3 且小球低水，所以 4 球以上並不是最舒服的主線。
      </div>
    </section>

    <section class="three-col">
      <div class="chart-card">
        <h3>Binance 90分鐘勝平負</h3>
        {bar("ARG 勝", arg_win["chance"], "#2563eb")}
        {bar("平局", draw["chance"], "#d97706")}
        {bar("CVI 勝", cvi_win["chance"], "#dc2626")}
      </div>
      <div class="chart-card">
        <h3>Binance 可操作項目</h3>
        {bar("ARG -1.5", arg_m15["chance"], "#7c3aed")}
        {bar("小 3.5", under35["chance"], "#059669")}
        {bar("BTTS No", btts_no["chance"], "#0891b2")}
        {bar("ARG -2.5", arg_m25["chance"], "#2563eb")}
      </div>
      <div class="chart-card">
        <h3>正確比分前段</h3>
        {exact_score_bars()}
      </div>
    </section>

    <section>
      <div class="section-title"><h2>Titan007 快照</h2><p>初盤 vs 即時盤，非賽後資料</p></div>
      <div class="three-col">
        {table_titan(asian_rows, "亞讓：阿根廷讓球", "ARG", "CVI")}
        {table_titan(total_rows, "大小球：總進球", "大", "小")}
        {table_titan(corner_rows, "角球：總角球", "大", "小")}
      </div>
    </section>

    <section class="two-col">
      <div class="table-card">
        <div class="section-title"><h2>外部來源</h2><p>多來源方向一致性</p></div>
        <table><thead><tr><th>來源</th><th>賽前看法</th><th>訊號</th></tr></thead><tbody>{source_rows()}</tbody></table>
      </div>
      <div class="table-card">
        <div class="section-title"><h2>Binance 價格門檻</h2><p>不是方向對就一定值得買</p></div>
        <table>
          <thead><tr><th>項目</th><th>目前價格</th><th>判斷</th></tr></thead>
          <tbody>
            <tr><td>ARG 晉級</td><td>{float(arg_advance['price']):.2f}</td><td>太貴，除非只想壓低風險。</td></tr>
            <tr><td>ARG 90分鐘勝</td><td>{float(arg_win['price']):.2f}</td><td>方向正確，但收益偏低。</td></tr>
            <tr><td>ARG -1.5</td><td>{float(arg_m15['price']):.2f}</td><td>主單，價格和盤口最匹配。</td></tr>
            <tr><td>小 3.5</td><td>{float(under35['price']):.2f}</td><td>適合搭配阿根廷控場勝。</td></tr>
            <tr><td>BTTS No</td><td>{float(btts_no['price']):.2f}</td><td>CVI 進球風險低，可搭。</td></tr>
            <tr><td>角球小 9.5</td><td>{float(corners_under['price']):.2f}</td><td>有方向，但不是主線。</td></tr>
            <tr><td>Messi 進球</td><td>{float(messi_goal['price']):.2f}</td><td>熱度很高，價格偏貴。</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="two-col">
      <div class="table-card">
        <div class="section-title"><h2>100U 分配</h2><p>一單一單下，不串關</p></div>
        <table><thead><tr><th>下注項目</th><th>本金</th><th>Binance 價格</th><th>過關淨利</th></tr></thead><tbody>{allocation_rows()}</tbody></table>
        <p class="small" style="margin-top:10px">這組不是保本組合，主要押阿根廷至少贏兩球、CVI 不進球、總進球不爆到 4+。</p>
      </div>
      <div class="table-card">
        <div class="section-title"><h2>比分情境</h2><p>依 100U 分配估算</p></div>
        <table><thead><tr><th>比分</th><th>理論淨損益</th><th>會過的項目</th></tr></thead><tbody>{scenario_table()}</tbody></table>
      </div>
    </section>

    <section class="table-card">
      <div class="section-title"><h2>最後判斷</h2><p>照盤口不是照名氣</p></div>
      <ul class="clean">
        <li>主線：ARG -1.5，因為 Titan 主盤 -2，Binance -1.5 還有 0.67 價格。</li>
        <li>搭配：小 3.5，因為總進球盤在 3 且多數公司小球水位偏低。</li>
        <li>防守路徑：BTTS No，符合 2-0 / 3-0 的主劇本。</li>
        <li>不重壓：ARG 晉級、ARG 90分鐘勝，價格太低，賺太少。</li>
        <li>小注可玩：ARG -2.5，只適合押 3-0 / 4-0，2-0 會輸。</li>
      </ul>
    </section>
  </main>
</body>
</html>
"""

out_path = OUT / "argentina-caboverde-mexico-style-analysis.html"
out_path.write_text(doc, encoding="utf-8")
print(out_path)
print(snapshot_path)
