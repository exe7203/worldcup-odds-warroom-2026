import csv
import html
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

TPE = timezone(timedelta(hours=8))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def find_topic(topics, title):
    return next(item for item in topics if item.get("title") == title)


def find_market(topic_obj, title):
    return next(item for item in topic_obj.get("markets", []) if item.get("title") == title)


def find_outcome(market_obj, name):
    return next(item for item in market_obj.get("outcomes", []) if item.get("name") == name)


def get_outcome(topics, topic_title, market_title, outcome_name):
    return find_outcome(find_market(find_topic(topics, topic_title), market_title), outcome_name)


def price(outcome):
    return float(outcome["price"])


def chance(outcome):
    return float(outcome["chance"])


def pct(outcome):
    return chance(outcome) * 100


def fmt_pct(value):
    return f"{value * 100:.1f}%"


def fmt_num(value):
    if value is None:
        return "-"
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def profit(stake, market_price):
    return stake / market_price - stake


def total_return(stake, market_price):
    return stake / market_price


def tpe_time_from_epoch(epoch):
    if not epoch:
        return "-"
    return datetime.fromtimestamp(int(epoch), timezone.utc).astimezone(TPE).strftime("%m/%d %H:%M")


TITAN_NAMES = {
    1: "Macauslot",
    3: "Crown",
    8: "Bet365",
    12: "Easybet",
    24: "12bet",
    31: "Sbobet",
    47: "Pinnacle",
    48: "HKJC",
}


def titan_rows(kind):
    data = load_json(WORK / f"titan_can_mar_kind{kind}.json")
    rows = []
    for company in data.get("companies", []):
        cid = company.get("companyId")
        if cid not in TITAN_NAMES:
            continue
        detail = (company.get("details") or [{}])[0]
        rows.append(
            {
                "company": TITAN_NAMES[cid],
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


def avg(rows, key):
    vals = [row[key] for row in rows if row.get(key) is not None]
    return sum(vals) / len(vals) if vals else 0


def handicap_text(line):
    if line is None:
        return "-"
    if line < 0:
        return f"摩洛哥 -{fmt_num(abs(line))} / 加拿大 +{fmt_num(abs(line))}"
    if line > 0:
        return f"加拿大 -{fmt_num(abs(line))} / 摩洛哥 +{fmt_num(abs(line))}"
    return "平手盤"


def bar(label, percent, color, note=""):
    width = max(1, min(100, percent))
    safe_note = html.escape(note) if note else f"{percent:.1f}%"
    return (
        "<div class='bar-row'>"
        f"<div class='bar-label'>{html.escape(label)}</div>"
        "<div class='bar-track'>"
        f"<div class='bar-fill' style='width:{width:.1f}%;background:{color}'></div>"
        "</div>"
        f"<div class='bar-note'>{safe_note}</div>"
        "</div>"
    )


def titan_table(rows, title, left_label, line_label, right_label, note):
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{html.escape(row['company'])}</td>"
            f"<td>{fmt_num(row['first_home'])}</td>"
            f"<td>{fmt_num(row['first_line'])}</td>"
            f"<td>{fmt_num(row['first_away'])}</td>"
            f"<td>{fmt_num(row['home'])}</td>"
            f"<td>{fmt_num(row['line'])}</td>"
            f"<td>{fmt_num(row['away'])}</td>"
            f"<td>{tpe_time_from_epoch(row['modify'])}</td>"
            "</tr>"
        )
    return (
        "<div class='table-card'>"
        f"<h3>{html.escape(title)}</h3>"
        f"<p>{html.escape(note)}</p>"
        "<table>"
        "<thead><tr>"
        "<th>公司</th>"
        f"<th>初盤{html.escape(left_label)}</th>"
        f"<th>初盤{html.escape(line_label)}</th>"
        f"<th>初盤{html.escape(right_label)}</th>"
        f"<th>即時{html.escape(left_label)}</th>"
        f"<th>即時{html.escape(line_label)}</th>"
        f"<th>即時{html.escape(right_label)}</th>"
        "<th>更新</th>"
        "</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table>"
        "</div>"
    )


topics = load_json(OUT / "binance-canada-morocco-topics.json")
main_topic = find_topic(topics, "Canada vs. Morocco")
exact_topic = find_topic(topics, "Canada vs. Morocco - Exact Score")
more_topic = find_topic(topics, "Canada vs. Morocco - More Markets")

match_start = datetime.fromtimestamp(main_topic["startDate"] / 1000, timezone.utc).astimezone(TPE)
generated_at = datetime.now(TPE)

mar_win = get_outcome(topics, "Canada vs. Morocco", "MAR", "Yes")
draw = get_outcome(topics, "Canada vs. Morocco", "Draw", "Yes")
can_win = get_outcome(topics, "Canada vs. Morocco", "CAN", "Yes")
mar_advance = get_outcome(topics, "Canada vs. Morocco - More Markets", "Team to Advance", "MAR")
can_advance = get_outcome(topics, "Canada vs. Morocco - More Markets", "Team to Advance", "CAN")
over15 = get_outcome(topics, "Canada vs. Morocco - More Markets", "O/U 1.5", "Over")
under25 = get_outcome(topics, "Canada vs. Morocco - More Markets", "O/U 2.5", "Under")
over25 = get_outcome(topics, "Canada vs. Morocco - More Markets", "O/U 2.5", "Over")
under35 = get_outcome(topics, "Canada vs. Morocco - More Markets", "O/U 3.5", "Under")
btts_yes = get_outcome(topics, "Canada vs. Morocco - More Markets", "Both Teams to Score", "Yes")
btts_no = get_outcome(topics, "Canada vs. Morocco - More Markets", "Both Teams to Score", "No")
mar_m15 = get_outcome(topics, "Canada vs. Morocco - More Markets", "Morocco (-1.5)", "MAR")
corners_over = get_outcome(topics, "Canada vs. Morocco - Total Corners", "Total Corners: O/U 8.5", "Over 8.5")
corners_under = get_outcome(topics, "Canada vs. Morocco - Total Corners", "Total Corners: O/U 8.5", "Under 8.5")
mar_first = get_outcome(topics, "Canada vs. Morocco - First Team to Score", "MAR", "Yes")
can_first = get_outcome(topics, "Canada vs. Morocco - First Team to Score", "CAN", "Yes")
saibari_goal = get_outcome(topics, "Canada vs. Morocco - Player Props", "Ismael Saibari Total Goals", "Over 0.5")
david_goal = get_outcome(topics, "Canada vs. Morocco - Player Props", "Jonathan David Total Goals", "Over 0.5")

asian = titan_rows(0)
total = titan_rows(1)
corner_handicap = titan_rows(2)
corner_total = titan_rows(3)

exact_scores = []
for market_obj in exact_topic.get("markets", []):
    yes = find_outcome(market_obj, "Yes")
    exact_scores.append((market_obj.get("title"), chance(yes), price(yes)))
exact_scores = sorted(exact_scores, key=lambda item: item[1], reverse=True)

allocation = [
    {"name": "摩洛哥 90 分鐘勝", "stake": 50, "price": price(mar_win)},
    {"name": "全場小 2.5 球", "stake": 30, "price": price(under25)},
    {"name": "全場小 3.5 球", "stake": 20, "price": price(under35)},
]


def passed_markets(score):
    can_goals, mar_goals = score
    total_goals = can_goals + mar_goals
    won = set()
    if mar_goals > can_goals:
        won.add("摩洛哥 90 分鐘勝")
    if total_goals < 2.5:
        won.add("全場小 2.5 球")
    if total_goals < 3.5:
        won.add("全場小 3.5 球")
    return won


scenario_scores = [(1, 1), (0, 1), (0, 2), (1, 2), (0, 0), (1, 0), (2, 1), (0, 3), (2, 2)]
scenarios = []
for score in scenario_scores:
    won = passed_markets(score)
    net = 0.0
    for bet in allocation:
        net += profit(bet["stake"], bet["price"]) if bet["name"] in won else -bet["stake"]
    scenarios.append((score, net, [bet["name"] for bet in allocation if bet["name"] in won]))

sources = [
    {
        "name": "Binance Prediction API",
        "url": "",
        "signal": "主盤",
        "read": f"MAR 90 分鐘勝 {pct(mar_win):.1f}%，摩洛哥晉級 {pct(mar_advance):.1f}%，小 2.5 球 {pct(under25):.1f}%，小 3.5 球 {pct(under35):.1f}%。",
    },
    {
        "name": "Titan007",
        "url": "https://live.titan007.com/asian/2907393.htm",
        "signal": "亞盤升摩洛哥",
        "read": f"主流公司從摩洛哥 -0.5 左右推到 {handicap_text(avg(asian, 'line'))}，大小球集中 2.25，角球總數 8.5。",
    },
    {
        "name": "Al Jazeera / Opta",
        "url": "https://www.aljazeera.com/sports/2026/7/3/canada-morocco-fifa-world-cup-round-of-16-saibari-prediction-schedule",
        "signal": "模型偏摩洛哥",
        "read": "Opta 模型賽前給摩洛哥 90 分鐘勝率 52.7%，加拿大 21.7%，進延長賽 25.6%。",
    },
    {
        "name": "SportsGambler",
        "url": "https://www.sportsgambler.com/betting-tips/football/canada-vs-morocco-prediction-lineups-odds-2026-07-04/",
        "signal": "摩洛哥勝",
        "read": "主推 Morocco To Win，市場價格約 1.78；其文內正確比分方向偏 0-2 摩洛哥。",
    },
    {
        "name": "Covers",
        "url": "https://www.covers.com/world-cup/canada-vs-morocco-prediction-picks-odds-saturday-7-4-2026",
        "signal": "小球 + 平局風險",
        "read": "總分方向推 Under 2.5；但晉級選擇偏加拿大，提醒 90 分鐘平局或延長賽風險不能忽略。",
    },
]

snapshot_path = OUT / "canada-morocco-mexico-style-snapshot.csv"
with snapshot_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["source", "market", "price_or_water", "chance_or_line", "note"])
    writer.writerow(["Binance", "MAR 90min win", price(mar_win), chance(mar_win), "main direction"])
    writer.writerow(["Binance", "Draw 90min", price(draw), chance(draw), "highest exact score includes 1-1"])
    writer.writerow(["Binance", "CAN 90min win", price(can_win), chance(can_win), "underdog"])
    writer.writerow(["Binance", "MAR advance", price(mar_advance), chance(mar_advance), "safer but low return"])
    writer.writerow(["Binance", "Under 2.5", price(under25), chance(under25), "goal-line value"])
    writer.writerow(["Binance", "Under 3.5", price(under35), chance(under35), "low return stabilizer"])
    writer.writerow(["Binance", "BTTS Yes", price(btts_yes), chance(btts_yes), "split market"])
    writer.writerow(["Binance", "MAR -1.5", price(mar_m15), chance(mar_m15), "aggressive add-on only"])
    writer.writerow(["Binance", "Corners Over 8.5", price(corners_over), chance(corners_over), "corner lean only"])
    writer.writerow(["Titan", "Asian line average", avg(asian, "home"), avg(asian, "line"), handicap_text(avg(asian, "line"))])
    writer.writerow(["Titan", "Total goals line average", avg(total, "home"), avg(total, "line"), "over water / line average"])
    writer.writerow(["Titan", "Corners total line average", avg(corner_total, "home"), avg(corner_total, "line"), "over water / line average"])
    for src in sources:
        writer.writerow([src["name"], src["signal"], "", "", src["read"]])


def exact_score_bars():
    colors = ["#0f766e", "#2563eb", "#7c3aed", "#d97706", "#0891b2", "#dc2626", "#475569", "#16a34a"]
    rows = []
    for i, (label, score_chance, score_price) in enumerate(exact_scores[:10]):
        rows.append(bar(label, score_chance * 100, colors[i % len(colors)], f"{score_chance * 100:.1f}% / 價格 {score_price:.3f}"))
    return "".join(rows)


def allocation_table():
    rows = []
    for bet in allocation:
        rows.append(
            "<tr>"
            f"<td>{html.escape(bet['name'])}</td>"
            f"<td>{bet['stake']}U</td>"
            f"<td>{bet['price']:.2f}</td>"
            f"<td>{total_return(bet['stake'], bet['price']):.2f}U</td>"
            f"<td class='good'>+{profit(bet['stake'], bet['price']):.2f}U</td>"
            "</tr>"
        )
    return "".join(rows)


def scenario_table():
    rows = []
    for (can_goals, mar_goals), net, won in scenarios:
        cls = "good" if net > 0 else "bad"
        label = f"CAN {can_goals}-{mar_goals} MAR"
        won_text = ", ".join(won) if won else "全倒"
        rows.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td class='{cls}'>{net:+.2f}U</td>"
            f"<td>{html.escape(won_text)}</td>"
            "</tr>"
        )
    return "".join(rows)


def sources_table():
    rows = []
    for src in sources:
        name = html.escape(src["name"])
        if src["url"]:
            name = f"<a href='{html.escape(src['url'])}' target='_blank' rel='noopener'>{name}</a>"
        rows.append(
            "<tr>"
            f"<td>{name}</td>"
            f"<td>{html.escape(src['read'])}</td>"
            f"<td><span class='pill'>{html.escape(src['signal'])}</span></td>"
            "</tr>"
        )
    return "".join(rows)


one_x_two_chart = "".join(
    [
        bar("摩洛哥 90 分鐘勝", pct(mar_win), "#0f766e", f"{pct(mar_win):.1f}% / 價格 {price(mar_win):.2f}"),
        bar("90 分鐘平局", pct(draw), "#d97706", f"{pct(draw):.1f}% / 價格 {price(draw):.2f}"),
        bar("加拿大 90 分鐘勝", pct(can_win), "#dc2626", f"{pct(can_win):.1f}% / 價格 {price(can_win):.2f}"),
    ]
)

goal_chart = "".join(
    [
        bar("大 1.5 球", pct(over15), "#2563eb", f"{pct(over15):.1f}% / 價格 {price(over15):.2f}"),
        bar("小 2.5 球", pct(under25), "#0f766e", f"{pct(under25):.1f}% / 價格 {price(under25):.2f}"),
        bar("小 3.5 球", pct(under35), "#7c3aed", f"{pct(under35):.1f}% / 價格 {price(under35):.2f}"),
        bar("BTTS Yes", pct(btts_yes), "#0891b2", f"{pct(btts_yes):.1f}% / 價格 {price(btts_yes):.2f}"),
        bar("BTTS No", pct(btts_no), "#64748b", f"{pct(btts_no):.1f}% / 價格 {price(btts_no):.2f}"),
    ]
)

side_chart = "".join(
    [
        bar("摩洛哥晉級", pct(mar_advance), "#0f766e", f"{pct(mar_advance):.1f}% / 價格 {price(mar_advance):.2f}"),
        bar("加拿大晉級", pct(can_advance), "#dc2626", f"{pct(can_advance):.1f}% / 價格 {price(can_advance):.2f}"),
        bar("摩洛哥先進球", pct(mar_first), "#2563eb", f"{pct(mar_first):.1f}% / 價格 {price(mar_first):.2f}"),
        bar("加拿大先進球", pct(can_first), "#d97706", f"{pct(can_first):.1f}% / 價格 {price(can_first):.2f}"),
        bar("角球大 8.5", pct(corners_over), "#7c3aed", f"{pct(corners_over):.1f}% / 價格 {price(corners_over):.2f}"),
        bar("角球小 8.5", pct(corners_under), "#64748b", f"{pct(corners_under):.1f}% / 價格 {price(corners_under):.2f}"),
    ]
)

top_exact = exact_scores[0]
main_all_pass_profit = sum(profit(bet["stake"], bet["price"]) for bet in allocation)

html_doc = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>加拿大 vs 摩洛哥 盤口綜合分析</title>
  <style>
    :root {{
      --bg:#f4f7fb;
      --panel:#ffffff;
      --ink:#172033;
      --muted:#647084;
      --line:#d9e2ef;
      --good:#0f766e;
      --bad:#dc2626;
      --blue:#2563eb;
      --amber:#d97706;
      --violet:#7c3aed;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Arial,"Microsoft JhengHei",sans-serif; background:var(--bg); color:var(--ink); }}
    header {{ padding:34px 28px 24px; background:#111827; color:#fff; }}
    header h1 {{ margin:0 0 8px; font-size:30px; letter-spacing:0; }}
    header p {{ margin:0; color:#cbd5e1; max-width:1120px; line-height:1.65; }}
    main {{ max-width:1180px; margin:0 auto; padding:22px; }}
    section {{ margin:18px 0; }}
    .grid {{ display:grid; gap:14px; grid-template-columns:repeat(4,minmax(0,1fr)); }}
    .two-col {{ display:grid; gap:14px; grid-template-columns:1.04fr .96fr; }}
    .three-col {{ display:grid; gap:14px; grid-template-columns:repeat(3,1fr); }}
    .card,.chart-card,.table-card,.callout {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; box-shadow:0 1px 2px rgba(15,23,42,.04); }}
    .card h2 {{ margin:0 0 8px; font-size:15px; color:var(--muted); font-weight:700; }}
    .metric {{ font-size:26px; font-weight:800; margin-bottom:6px; }}
    .card p,.table-card p,.small {{ margin:0; line-height:1.55; color:var(--muted); font-size:13px; }}
    .section-title {{ display:flex; align-items:end; justify-content:space-between; gap:12px; margin:24px 0 10px; }}
    .section-title h2 {{ margin:0; font-size:20px; }}
    .section-title span {{ color:var(--muted); font-size:13px; }}
    .callout {{ border-left:5px solid var(--good); }}
    .callout h2 {{ margin:0 0 8px; font-size:20px; }}
    .callout p {{ margin:8px 0 0; line-height:1.7; }}
    .pill {{ display:inline-block; padding:3px 8px; border-radius:999px; background:#e9eef7; color:#334155; font-size:12px; font-weight:700; white-space:nowrap; }}
    .bar-row {{ display:grid; grid-template-columns:142px 1fr 132px; gap:10px; align-items:center; margin:10px 0; min-height:26px; }}
    .bar-label {{ font-size:13px; color:#334155; }}
    .bar-track {{ height:12px; background:#e7edf6; border-radius:999px; overflow:hidden; }}
    .bar-fill {{ height:100%; border-radius:999px; }}
    .bar-note {{ font-size:12px; color:#475569; text-align:right; white-space:nowrap; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th,td {{ padding:9px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ color:#475569; background:#f8fafc; font-weight:800; }}
    tr:last-child td {{ border-bottom:0; }}
    a {{ color:#1d4ed8; text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
    .good {{ color:var(--good); font-weight:800; }}
    .bad {{ color:var(--bad); font-weight:800; }}
    .warn {{ color:var(--amber); font-weight:800; }}
    .muted {{ color:var(--muted); }}
    .decision {{ display:grid; gap:12px; grid-template-columns:1fr 1fr 1fr; }}
    .decision div {{ border-top:3px solid var(--blue); padding-top:10px; }}
    .decision b {{ display:block; margin-bottom:6px; }}
    footer {{ padding:22px; color:#647084; font-size:12px; max-width:1180px; margin:0 auto; }}
    @media (max-width: 900px) {{
      main {{ padding:14px; }}
      .grid,.two-col,.three-col,.decision {{ grid-template-columns:1fr; }}
      .bar-row {{ grid-template-columns:110px 1fr; }}
      .bar-note {{ grid-column:2; text-align:left; }}
      table {{ font-size:12px; }}
      th,td {{ padding:8px 6px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>加拿大 vs 摩洛哥 盤口綜合分析</h1>
    <p>比賽時間：{match_start.strftime("%Y-%m-%d %H:%M")} 台灣時間。資料彙整 Binance Prediction、Titan007 亞盤/大小球/角球，以及外部賽前預測來源。產生時間：{generated_at.strftime("%Y-%m-%d %H:%M")}。</p>
  </header>

  <main>
    <section class="grid">
      <div class="card">
        <h2>Binance 90 分鐘主盤</h2>
        <div class="metric">MAR {pct(mar_win):.1f}%</div>
        <p>摩洛哥勝價格 {price(mar_win):.2f}；平局 {pct(draw):.1f}%，加拿大勝 {pct(can_win):.1f}%。</p>
      </div>
      <div class="card">
        <h2>晉級盤</h2>
        <div class="metric">MAR {pct(mar_advance):.1f}%</div>
        <p>晉級價格 {price(mar_advance):.2f}，比 90 分鐘勝安全，但報酬明顯低。</p>
      </div>
      <div class="card">
        <h2>Titan 亞讓主線</h2>
        <div class="metric">{handicap_text(avg(asian, "line"))}</div>
        <p>多家公司從 -0.5 一帶推到 -0.75，主流方向仍偏摩洛哥。</p>
      </div>
      <div class="card">
        <h2>總進球主線</h2>
        <div class="metric">2.25 / 2.5</div>
        <p>Binance 小 2.5 為 {pct(under25):.1f}%，小 3.5 為 {pct(under35):.1f}%。</p>
      </div>
    </section>

    <section class="callout">
      <h2>主結論</h2>
      <p>這場我不會把重點放在高賠比分或球員進球，主線是 <b>摩洛哥 90 分鐘勝 + 小球區間</b>。理由是 Binance、Titan 亞盤、Opta/SportsGambler 的方向都偏摩洛哥；但 Binance 精確比分第一名是 {html.escape(top_exact[0])}（{top_exact[1] * 100:.1f}%），代表 1-1 平局風險不小，所以不適合重壓單一「摩洛哥 90 分鐘勝」。</p>
      <p>如果用 100U 拆單，我會先用 <b>50U 摩洛哥 90 分鐘勝、30U 小 2.5、20U 小 3.5</b>。這組不是追最高賠率，而是瞄準 0-1、0-2、1-2、0-3 這類盤口最像的比分帶；若摩洛哥 90 分鐘贏且總球不超過 3 球，理論上多數情境為正收益。</p>
    </section>

    <section>
      <div class="section-title">
        <h2>Binance 盤口機率</h2>
        <span>價格愈低代表市場認為機率愈高；收益用花費 U / 價格估算。</span>
      </div>
      <div class="three-col">
        <div class="chart-card">
          <h3>90 分鐘勝平負</h3>
          {one_x_two_chart}
        </div>
        <div class="chart-card">
          <h3>進球與 BTTS</h3>
          {goal_chart}
        </div>
        <div class="chart-card">
          <h3>晉級、先進球、角球</h3>
          {side_chart}
        </div>
      </div>
    </section>

    <section>
      <div class="section-title">
        <h2>精確比分分布</h2>
        <span>最高不是摩洛哥勝，而是 1-1，這是本場最大風險提示。</span>
      </div>
      <div class="chart-card">
        {exact_score_bars()}
      </div>
    </section>

    <section>
      <div class="section-title">
        <h2>100U 拆單試算</h2>
        <span>以下是單關拆單，不是串關。</span>
      </div>
      <div class="two-col">
        <div class="table-card">
          <h3>建議拆法</h3>
          <table>
            <thead><tr><th>項目</th><th>下注</th><th>Binance 價格</th><th>命中返還</th><th>扣本金後淨利</th></tr></thead>
            <tbody>{allocation_table()}</tbody>
          </table>
          <p class="small">三單全部命中時，合計淨利約 <b class="good">+{main_all_pass_profit:.2f}U</b>。如果你想更激進，可以把小 3.5 的 10U 改成摩洛哥 -1.5，但 1 球小勝時會少一層保護。</p>
        </div>
        <div class="table-card">
          <h3>常見比分結果</h3>
          <table>
            <thead><tr><th>90 分鐘比分</th><th>理論淨利</th><th>命中項目</th></tr></thead>
            <tbody>{scenario_table()}</tbody>
          </table>
          <p class="small">角球盤獨立性較高，這版沒有放進主倉。若臨場 Titan 角球仍維持 8.5 且 Over 低水，可小注追蹤，但不建議把它當主判斷。</p>
        </div>
      </div>
    </section>

    <section>
      <div class="section-title">
        <h2>外部來源判讀</h2>
        <span>只採用賽前文章、賽前盤口或模型資訊。</span>
      </div>
      <div class="table-card">
        <table>
          <thead><tr><th>來源</th><th>判讀</th><th>訊號</th></tr></thead>
          <tbody>{sources_table()}</tbody>
        </table>
      </div>
    </section>

    <section>
      <div class="section-title">
        <h2>Titan007 盤口走勢</h2>
        <span>負讓球以 Titan 主隊盤格式呈現；此場等價解讀為摩洛哥讓球。</span>
      </div>
      <div class="two-col">
        {titan_table(asian, "亞讓盤", "加拿大水位", "盤口", "摩洛哥水位", "盤口由摩洛哥 -0.5 一帶升到 -0.75，一般代表市場更支持摩洛哥方向。")}
        {titan_table(total, "大小球", "大球水位", "球數", "小球水位", "主線多在 2.25，少數到 2.5；與 Binance 小 2.5 / 小 3.5 的方向相容。")}
      </div>
      <div class="two-col" style="margin-top:14px;">
        {titan_table(corner_handicap, "角球讓分", "加拿大角球水位", "盤口", "摩洛哥角球水位", "角球讓分多在摩洛哥 -1 左右，代表角球也稍偏摩洛哥。")}
        {titan_table(corner_total, "角球總數", "大角水位", "角球數", "小角水位", "角球總數集中 8.5，Binance 大 8.5 僅 52.5%，屬可觀察不適合重倉。")}
      </div>
    </section>

    <section>
      <div class="section-title">
        <h2>最後決策框架</h2>
        <span>下注前 30 分鐘要重新看一次盤口。</span>
      </div>
      <div class="callout">
        <div class="decision">
          <div>
            <b>照目前盤勢</b>
            <span>主推仍是摩洛哥 90 分鐘勝，搭小 2.5 / 小 3.5 做比分區間保護。</span>
          </div>
          <div>
            <b>要避開的盤</b>
            <span>BTTS 幾乎 50/50，球員進球樣本太薄；摩洛哥 -1.5 只有 {pct(mar_m15):.1f}% 市場機率，適合小注不適合主倉。</span>
          </div>
          <div>
            <b>臨場變盤條件</b>
            <span>若摩洛哥勝降到 52% 以下或平局升破 32%，我會降低摩洛哥勝倉位，改把部分資金挪到摩洛哥晉級或小 3.5。</span>
          </div>
        </div>
      </div>
    </section>
  </main>

  <footer>
    本頁為盤口與公開資訊整理，不代表保證獲利。Binance Prediction 價格會快速變動，下注前請以你畫面上的即時價格重新計算返還。
  </footer>
</body>
</html>
"""

out_path = OUT / "canada-morocco-mexico-style-analysis.html"
out_path.write_text(html_doc, encoding="utf-8")
print(out_path)
print(snapshot_path)
