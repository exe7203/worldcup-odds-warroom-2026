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


def n(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def pct(value):
    return f"{value * 100:.1f}%"


def price_profit(stake, price):
    return stake / price - stake


def no_vig(decimal_odds):
    inv = [1 / x for x in decimal_odds]
    total = sum(inv)
    return [x / total for x in inv]


def topic_by_title(topics, title):
    for topic in topics:
        if topic.get("title") == title:
            return topic
    return None


def market(topic, title):
    for item in topic.get("markets", []):
        if item.get("title") == title:
            return item
    return None


def outcome(market_item, name):
    for item in market_item.get("outcomes", []):
        if item.get("name") == name:
            return item
    return None


def top_titan(kind):
    data = load_json(WORK / f"titan_arg_cvi_kind{kind}.json")
    wanted = {}
    for c in data.get("companies", []):
        if c.get("companyId") in {1, 3, 8, 12, 24, 47}:
            d = (c.get("details") or [{}])[0]
            wanted[c.get("nameEn") or c.get("nameCn")] = {
                "company_id": c.get("companyId"),
                "name": c.get("nameCn"),
                "name_en": c.get("nameEn"),
                "first_home": n(d.get("firstHomeOdds")),
                "first_line": n(d.get("firstDrawOdds")),
                "first_away": n(d.get("firstAwayOdds")),
                "home": n(d.get("homeOdds")),
                "line": n(d.get("drawOdds")),
                "away": n(d.get("awayOdds")),
                "modify": d.get("modifyTime"),
            }
    return wanted


topics = load_json(OUT / "binance-argentina-caboverde-topics.json")
main_topic = topic_by_title(topics, "Argentina vs. Cabo Verde")
more_topic = topic_by_title(topics, "Argentina vs. Cabo Verde - More Markets")
score_topic = topic_by_title(topics, "Argentina vs. Cabo Verde - Exact Score")
corner_topic = topic_by_title(topics, "Argentina vs. Cabo Verde - Total Corners")
half_topic = topic_by_title(topics, "Argentina vs. Cabo Verde - Halftime Result")
first_topic = topic_by_title(topics, "Argentina vs. Cabo Verde - First Team to Score")
player_topic = topic_by_title(topics, "Argentina vs Cabo Verde - Player Props")

binance_1x2 = {
    item["title"]: outcome(item, "Yes")
    for item in main_topic.get("markets", [])
}

def yes_market(title, name):
    m = market(more_topic, title)
    return outcome(m, name)


binance_rows = [
    ("ARG 90分鐘勝", "1X2", binance_1x2["ARG"]["price"], binance_1x2["ARG"]["chance"], "太貴，只能當方向，不是價值單"),
    ("平局", "1X2", binance_1x2["Draw"]["price"], binance_1x2["Draw"]["chance"], "外部盤不支持重押"),
    ("CVI 90分鐘勝", "1X2", binance_1x2["CVI"]["price"], binance_1x2["CVI"]["chance"], "冷門極深，不建議"),
    ("ARG 晉級", "晉級", yes_market("Team to Advance", "ARG")["price"], yes_market("Team to Advance", "ARG")["chance"], "很穩但報酬太低"),
    ("ARG -1.5", "讓分", yes_market("Argentina (-1.5)", "ARG")["price"], yes_market("Argentina (-1.5)", "ARG")["chance"], "主單候選，和外部推薦/Titan -2 方向一致"),
    ("ARG -2.5", "讓分", yes_market("Argentina (-2.5)", "ARG")["price"], yes_market("Argentina (-2.5)", "ARG")["chance"], "可小注，2-0 會死、3-0 才過"),
    ("大 2.5", "大小", yes_market("O/U 2.5", "Over")["price"], yes_market("O/U 2.5", "Over")["chance"], "不便宜，外部意見分歧"),
    ("小 3.5", "大小", yes_market("O/U 3.5", "Under")["price"], yes_market("O/U 3.5", "Under")["chance"], "主單候選，和總進球3/小球低水一致"),
    ("BTTS No", "雙方進球", yes_market("Both Teams to Score", "No")["price"], yes_market("Both Teams to Score", "No")["chance"], "主單候選，CVI 進球預期低"),
]

asian = top_titan(0)
ou = top_titan(1)
corner_total = top_titan(3)

source_rows = [
    {
        "source": "SportsGambler",
        "read": "主推 Argentina -2 亞洲盤；認為阿根廷有大勝空間；比分傾向 4-0。",
        "signal": "阿根廷讓深盤、CVI 難進球",
        "url": "https://www.sportsgambler.com/betting-tips/football/argentina-vs-cape-verde-prediction-lineups-odds-2026-07-03/",
        "grade": "ARG -2",
    },
    {
        "source": "Racing Post",
        "read": "最佳投注 Argentina & Under 3.5；提到 CVI 對西班牙 0-0、對沙烏地 0-0，但面對阿根廷品質差距大。",
        "signal": "阿根廷勝 + 小 3.5",
        "url": "https://www.racingpost.com/sport/football-tips/world-cup-2026/argentina-vs-cape-verde-world-cup-prediction-team-news-odds-betting-tips-and-bet-builder-aurGJ5y7Avbh/",
        "grade": "ARG + U3.5",
    },
    {
        "source": "Pickswise",
        "read": "主推 Argentina -1.5，理由是阿根廷小組賽三場都至少贏兩球。",
        "signal": "阿根廷 -1.5",
        "url": "https://www.pickswise.com/world-cup/games/argentina-cabo-verde-world-cup-26-2026-07-03-2200/picks/",
        "grade": "ARG -1.5",
    },
    {
        "source": "Action Network",
        "read": "公開市場顯示投注/資金極度偏向阿根廷；傷停列 CVI 中場 Nuno Da Costa、Telmo Arcanjo out。",
        "signal": "市場一面倒阿根廷，注意價格過熱",
        "url": "https://www.actionnetwork.com/worldcup-game/cape-verde-argentina-score-odds-july-3-2026/292409",
        "grade": "ARG熱",
    },
    {
        "source": "Binance Prediction",
        "read": "ARG 90分鐘勝 85.5%，ARG -1.5 66.5%，小3.5 63.5%，BTTS No 68.5%。",
        "signal": "可買讓分/小3.5/BTTS No，避免買太低報酬的ARG晉級",
        "url": "https://www.binance.com/",
        "grade": "盤口",
    },
]

alloc = [
    ("ARG -1.5", 45, float(yes_market("Argentina (-1.5)", "ARG")["price"])),
    ("小 3.5", 30, float(yes_market("O/U 3.5", "Under")["price"])),
    ("BTTS No", 20, float(yes_market("Both Teams to Score", "No")["price"])),
    ("ARG -2.5", 5, float(yes_market("Argentina (-2.5)", "ARG")["price"])),
]

def pass_set(score):
    a, c = score
    total = a + c
    passed = set()
    if a - c >= 2:
        passed.add("ARG -1.5")
    if total < 3.5:
        passed.add("小 3.5")
    if c == 0:
        passed.add("BTTS No")
    if a - c >= 3:
        passed.add("ARG -2.5")
    return passed


scenario_scores = [(2, 0), (3, 0), (4, 0), (2, 1), (3, 1), (1, 0), (1, 1)]
scenario_rows = []
for score in scenario_scores:
    passed = pass_set(score)
    net = 0
    for name, stake, price in alloc:
        if name in passed:
            net += price_profit(stake, price)
        else:
            net -= stake
    scenario_rows.append((f"{score[0]}-{score[1]}", net, ", ".join(name for name, *_ in alloc if name in passed) or "無"))


snapshot_csv = OUT / "argentina-caboverde-market-snapshot.csv"
with snapshot_csv.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["source", "market", "line", "home_or_yes", "away_or_no", "note"])
    for name, kind, price, chance, note in binance_rows:
        writer.writerow(["Binance", name, kind, price, chance, note])
    for label, data in [("Titan Asian", asian), ("Titan Total", ou), ("Titan Corners", corner_total)]:
        for company, row in data.items():
            writer.writerow([label, company, row["line"], row["home"], row["away"], f"first line {row['first_line']}"])


def bar_chart(rows, title):
    items = []
    for label, value, color in rows:
        items.append(
            f"<div class='bar-row'><div class='bar-label'>{html.escape(label)}</div>"
            f"<div class='bar-track'><div class='bar-fill' style='width:{value*100:.1f}%;background:{color}'></div></div>"
            f"<div class='bar-note'>{value*100:.1f}%</div></div>"
        )
    return f"<div class='chart-card'><h3>{html.escape(title)}</h3>{''.join(items)}</div>"


def titan_table(data, title, side1, side2):
    rows = []
    for company in ["Crown", "Bet365", "Macauslot", "pinnacle", "12bet", "Easybet"]:
        row = data.get(company)
        if not row:
            continue
        rows.append(
            f"<tr><td>{html.escape(company)}</td><td>{row['first_home']}</td><td>{row['first_line']}</td><td>{row['first_away']}</td>"
            f"<td>{row['home']}</td><td>{row['line']}</td><td>{row['away']}</td></tr>"
        )
    return (
        f"<div class='table-card'><h3>{html.escape(title)}</h3><table>"
        f"<thead><tr><th>公司</th><th>初 {side1}</th><th>初盤</th><th>初 {side2}</th><th>即 {side1}</th><th>即盤</th><th>即 {side2}</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def binance_table():
    rows = []
    for name, kind, price, chance, note in binance_rows:
        rows.append(f"<tr><td>{html.escape(name)}</td><td>{html.escape(kind)}</td><td>{float(price):.3f}</td><td>{float(chance)*100:.1f}%</td><td>{html.escape(note)}</td></tr>")
    return "".join(rows)


def source_table():
    rows = []
    for r in source_rows:
        rows.append(
            f"<tr><td><a href='{html.escape(r['url'])}'>{html.escape(r['source'])}</a></td>"
            f"<td>{html.escape(r['read'])}</td><td>{html.escape(r['signal'])}</td><td><span class='pill'>{html.escape(r['grade'])}</span></td></tr>"
        )
    return "".join(rows)


def allocation_rows():
    rows = []
    for name, stake, price in alloc:
        rows.append(f"<tr><td>{html.escape(name)}</td><td>{stake}U</td><td>{price:.2f}</td><td>+{price_profit(stake, price):.2f}U</td></tr>")
    return "".join(rows)


def scenario_table():
    rows = []
    for score, net, passed in scenario_rows:
        cls = "good" if net > 0 else "bad"
        rows.append(f"<tr><td>{score}</td><td class='{cls}'>{net:+.2f}U</td><td>{html.escape(passed)}</td></tr>")
    return "".join(rows)


html_doc = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>阿根廷 vs 維德角 Binance 盤口分析</title>
  <style>
    :root {{ --bg:#f4f6fa; --panel:#fff; --ink:#172033; --muted:#647084; --line:#d9e2ef; --blue:#2563eb; --green:#059669; --amber:#d97706; --red:#dc2626; --violet:#7c3aed; --cyan:#0891b2; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Arial,"Microsoft JhengHei",sans-serif; background:var(--bg); color:var(--ink); }}
    header {{ padding:34px 28px 24px; background:#101827; color:#fff; }}
    header h1 {{ margin:0 0 8px; font-size:30px; }}
    header p {{ margin:0; color:#cbd5e1; line-height:1.65; max-width:1040px; }}
    main {{ max-width:1180px; margin:0 auto; padding:22px; }}
    .grid {{ display:grid; gap:14px; grid-template-columns:repeat(4,minmax(0,1fr)); }}
    .card,.chart-card,.table-card,.callout {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; box-shadow:0 1px 2px rgba(15,23,42,.04); }}
    .card h2 {{ margin:0 0 8px; font-size:14px; color:var(--muted); }}
    .metric {{ font-size:26px; font-weight:800; margin-bottom:6px; }}
    .card p,.small {{ margin:0; color:var(--muted); line-height:1.55; font-size:13px; }}
    .section-title {{ display:flex; justify-content:space-between; align-items:end; gap:12px; margin:24px 0 10px; }}
    .section-title h2 {{ margin:0; font-size:20px; }}
    .section-title p {{ margin:0; color:var(--muted); font-size:13px; }}
    .two-col {{ display:grid; gap:14px; grid-template-columns:1fr 1fr; }}
    .three-col {{ display:grid; gap:14px; grid-template-columns:repeat(3,1fr); }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    th,td {{ text-align:left; padding:10px 9px; border-bottom:1px solid var(--line); vertical-align:top; }}
    th {{ color:#475569; background:#f8fafc; font-size:13px; }}
    td a {{ color:var(--blue); text-decoration:none; }}
    .bar-row {{ display:grid; grid-template-columns:150px 1fr 70px; gap:10px; align-items:center; margin:10px 0; }}
    .bar-label {{ font-size:13px; font-weight:700; }}
    .bar-track {{ height:13px; background:#e9eef6; border-radius:99px; overflow:hidden; }}
    .bar-fill {{ height:100%; border-radius:99px; }}
    .bar-note {{ font-size:12px; color:var(--muted); text-align:right; }}
    .pill {{ display:inline-block; padding:3px 8px; border-radius:99px; background:#e0ecff; color:#1d4ed8; font-weight:700; font-size:12px; white-space:nowrap; }}
    .good {{ color:#047857; font-weight:800; }}
    .bad {{ color:#b91c1c; font-weight:800; }}
    .callout {{ border-left:4px solid var(--blue); line-height:1.65; background:#eff6ff; }}
    ul.clean {{ margin:0; padding-left:18px; line-height:1.7; }}
    @media (max-width:900px) {{ .grid,.two-col,.three-col {{ grid-template-columns:1fr; }} header h1 {{ font-size:24px; }} .bar-row {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>阿根廷 vs 維德角：Binance 盤口分析</h1>
    <p>比賽時間：台灣時間 2026-07-04 06:00。資料整合 Binance Prediction、Titan007、SportsGambler、Racing Post、Pickswise、Action Network。頁面產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}。</p>
  </header>
  <main>
    <section class="grid">
      <div class="card"><h2>Binance 主勝</h2><div class="metric">ARG 85.5%</div><p>方向很穩，但價格太高，單買報酬低。</p></div>
      <div class="card"><h2>主盤</h2><div class="metric">ARG -2</div><p>Titan 多數公司集中在阿根廷讓 2 球。</p></div>
      <div class="card"><h2>大小球</h2><div class="metric">3 球</div><p>Over 水位偏高、Under 水位偏低，市場不追 4+。</p></div>
      <div class="card"><h2>主結論</h2><div class="metric">ARG -1.5</div><p>比 ARG 勝/晉級更有報酬，且和 Titan -2 主盤一致。</p></div>
    </section>

    <section>
      <div class="section-title"><h2>下注方向</h2><p>以 Binance 單注市場判斷</p></div>
      <div class="callout">
        <strong>主單：阿根廷 -1.5。</strong>
        搭配 <strong>小 3.5</strong> 和 <strong>BTTS No</strong>，是比較符合盤口的組合。
        不建議重買阿根廷晉級，因為 0.94 價格太貴；阿根廷 -2.5 可以小注，但 2-0 會輸。
      </div>
    </section>

    <section class="three-col">
      {bar_chart([
        ('ARG 90分鐘勝', float(binance_1x2['ARG']['chance']), '#2563eb'),
        ('平局', float(binance_1x2['Draw']['chance']), '#d97706'),
        ('CVI 勝', float(binance_1x2['CVI']['chance']), '#dc2626'),
      ], 'Binance 90分鐘勝平負')}
      {bar_chart([
        ('ARG -1.5', float(yes_market('Argentina (-1.5)', 'ARG')['chance']), '#7c3aed'),
        ('ARG -2.5', float(yes_market('Argentina (-2.5)', 'ARG')['chance']), '#2563eb'),
        ('小 3.5', float(yes_market('O/U 3.5', 'Under')['chance']), '#059669'),
        ('BTTS No', float(yes_market('Both Teams to Score', 'No')['chance']), '#0891b2'),
      ], 'Binance 核心下注項目')}
      {bar_chart([
        ('2-0', 0.1865, '#2563eb'),
        ('3-0', 0.1655, '#7c3aed'),
        ('1-0', 0.1165, '#0891b2'),
        ('2-1', 0.075, '#d97706'),
        ('3-1', 0.0715, '#dc2626'),
      ], 'Binance 正確比分前段')}
    </section>

    <section>
      <div class="section-title"><h2>Binance 價格表</h2><p>價格越低代表要付更多成本，報酬越低</p></div>
      <div class="table-card">
        <table><thead><tr><th>項目</th><th>分類</th><th>價格</th><th>機率</th><th>判斷</th></tr></thead><tbody>{binance_table()}</tbody></table>
      </div>
    </section>

    <section>
      <div class="section-title"><h2>Titan007 盤口快照</h2><p>初盤 vs 即時盤</p></div>
      <div class="three-col">
        {titan_table(asian, '亞讓：阿根廷讓球', 'ARG', 'CVI')}
        {titan_table(ou, '大小球：總進球', '大', '小')}
        {titan_table(corner_total, '角球：總角球', '大', '小')}
      </div>
    </section>

    <section class="two-col">
      <div class="table-card">
        <div class="section-title"><h2>外部來源</h2><p>公開預測與盤口方向</p></div>
        <table><thead><tr><th>來源</th><th>內容</th><th>訊號</th><th>標籤</th></tr></thead><tbody>{source_table()}</tbody></table>
      </div>
      <div class="table-card">
        <div class="section-title"><h2>100U 分配</h2><p>一單一單分開，不串關</p></div>
        <table><thead><tr><th>下注項目</th><th>本金</th><th>Binance 價格</th><th>過關淨利</th></tr></thead><tbody>{allocation_rows()}</tbody></table>
        <p class="small" style="margin-top:10px">這組不是保本組合；它押的是 2-0 / 3-0 / 4-0 這類阿根廷控場勝的路徑。</p>
      </div>
    </section>

    <section class="table-card">
      <div class="section-title"><h2>比分情境損益</h2><p>按上面的 100U 分配估算，未扣平台其他費用</p></div>
      <table><thead><tr><th>比分</th><th>理論淨損益</th><th>會過的項目</th></tr></thead><tbody>{scenario_table()}</tbody></table>
    </section>

    <section class="table-card">
      <div class="section-title"><h2>最後判斷</h2><p>可操作但不要買最貴的方向</p></div>
      <ul class="clean">
        <li>最合理：ARG -1.5。Titan 主盤在 -2，Binance -1.5 只有 66.5%，相對有吸引力。</li>
        <li>次合理：小 3.5。Titan 總進球 3 且小球低水，外部也有 Argentina & Under 3.5 方向。</li>
        <li>可搭配：BTTS No。CVI 小組 3 場只進 2 球，阿根廷近況零封率高。</li>
        <li>不建議重壓：ARG 晉級、ARG 90分鐘勝，方向正確但 Binance 價格太貴。</li>
        <li>小注高波動：ARG -2.5，只適合想押 3-0 / 4-0 劇本。</li>
      </ul>
    </section>
  </main>
</body>
</html>
"""

out_path = OUT / "argentina-caboverde-binance-analysis.html"
out_path.write_text(html_doc, encoding="utf-8")
print(out_path)
print(snapshot_csv)
