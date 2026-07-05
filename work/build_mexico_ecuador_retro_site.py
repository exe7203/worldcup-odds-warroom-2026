import csv
import html
import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

KICKOFF = "20260701100000"
CUTOFF_0930 = "20260701093000"


def parse_odds_data(path):
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(r"var\s+oddsData\s*=\s*(\[.*?\]);", text, re.S)
    if not match:
        raise ValueError(f"No oddsData in {path}")
    data = json.loads(match.group(1))
    return [row for row in data if row.get("ModifyTime")]


def fmt_time(value):
    if not value or len(value) != 14:
        return value or "-"
    return f"{value[:4]}-{value[4:6]}-{value[6:8]} {value[8:10]}:{value[10:12]}:{value[12:14]}"


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def last_at_or_before(rows, cutoff):
    candidates = [r for r in rows if r["ModifyTime"] <= cutoff]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r["ModifyTime"])


def earliest(rows):
    return min(rows, key=lambda r: r["ModifyTime"])


def compact_series(rows, keys):
    pre = sorted([r for r in rows if r["ModifyTime"] < KICKOFF], key=lambda r: r["ModifyTime"])
    out = []
    last = None
    for row in pre:
        state = tuple(row.get(k) for k in keys)
        if state != last:
            out.append(row)
            last = state
    return out


def american_to_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)


def no_vig_probs(decimal_odds):
    inv = [1 / x for x in decimal_odds]
    total = sum(inv)
    return [x / total for x in inv]


def line_chart(series, specs, title, subtitle, y_label):
    width = 900
    height = 330
    pad_l, pad_r, pad_t, pad_b = 58, 24, 38, 54
    vals = []
    for row in series:
        for spec in specs:
            v = num(row.get(spec["key"]))
            if v is not None and math.isfinite(v):
                vals.append(v)
    if not series or not vals:
        return "<div class='empty'>沒有可畫的賽前資料</div>"
    y_min = min(vals)
    y_max = max(vals)
    if y_min == y_max:
        y_min -= 0.5
        y_max += 0.5
    span = y_max - y_min
    y_min -= span * 0.12
    y_max += span * 0.12

    def x_at(i):
        if len(series) == 1:
            return pad_l + (width - pad_l - pad_r) / 2
        return pad_l + i * (width - pad_l - pad_r) / (len(series) - 1)

    def y_at(v):
        return pad_t + (y_max - v) * (height - pad_t - pad_b) / (y_max - y_min)

    grid = []
    for i in range(5):
        y = pad_t + i * (height - pad_t - pad_b) / 4
        val = y_max - i * (y_max - y_min) / 4
        grid.append(f"<line x1='{pad_l}' y1='{y:.1f}' x2='{width-pad_r}' y2='{y:.1f}' class='gridline'/>")
        grid.append(f"<text x='12' y='{y+4:.1f}' class='axis'>{val:.2f}</text>")
    for i, row in enumerate(series):
        if i in {0, len(series) - 1} or row["ModifyTime"] <= CUTOFF_0930 <= series[min(i + 1, len(series) - 1)]["ModifyTime"]:
            x = x_at(i)
            grid.append(f"<line x1='{x:.1f}' y1='{pad_t}' x2='{x:.1f}' y2='{height-pad_b}' class='vgrid'/>")
    paths = []
    legend = []
    for spec in specs:
        points = []
        dots = []
        for i, row in enumerate(series):
            v = num(row.get(spec["key"]))
            if v is None:
                continue
            x, y = x_at(i), y_at(v)
            points.append(f"{x:.1f},{y:.1f}")
            dots.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3.2' fill='{spec['color']}'><title>{fmt_time(row['ModifyTime'])}: {spec['label']} {v}</title></circle>")
        if points:
            paths.append(f"<polyline points='{' '.join(points)}' fill='none' stroke='{spec['color']}' stroke-width='2.7' stroke-linejoin='round' stroke-linecap='round'/>")
            paths.extend(dots)
            legend.append(f"<span><i style='background:{spec['color']}'></i>{html.escape(spec['label'])}</span>")
    start_label = fmt_time(series[0]["ModifyTime"])[5:16]
    end_label = fmt_time(series[-1]["ModifyTime"])[5:16]
    return f"""
    <div class="chart-block">
      <div class="chart-head"><div><h3>{html.escape(title)}</h3><p>{html.escape(subtitle)}</p></div><div class="legend">{''.join(legend)}</div></div>
      <svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
        {''.join(grid)}
        <text x="{pad_l}" y="{height-18}" class="axis">{start_label}</text>
        <text x="{width-pad_r-92}" y="{height-18}" class="axis">{end_label}</text>
        <text x="{pad_l}" y="22" class="ylabel">{html.escape(y_label)}</text>
        {''.join(paths)}
      </svg>
    </div>
    """


asian_rows = parse_odds_data(WORK / "titan_mex_ecu_oddsdetail_type1.html")
total_rows = parse_odds_data(WORK / "titan_mex_ecu_oddsdetail_type2.html")
one_x_two_rows = parse_odds_data(WORK / "titan_mex_ecu_oddsdetail_type4.html")

snapshots = {
    "asian": {
        "label": "Titan Crow* 全場亞讓",
        "early": earliest(asian_rows),
        "cutoff": last_at_or_before(asian_rows, CUTOFF_0930),
        "prekick": last_at_or_before(asian_rows, KICKOFF),
    },
    "total": {
        "label": "Titan Crow* 全場總進球",
        "early": earliest(total_rows),
        "cutoff": last_at_or_before(total_rows, CUTOFF_0930),
        "prekick": last_at_or_before(total_rows, KICKOFF),
    },
    "one_x_two": {
        "label": "Titan Crow* 全場勝平負",
        "early": earliest(one_x_two_rows),
        "cutoff": last_at_or_before(one_x_two_rows, CUTOFF_0930),
        "prekick": last_at_or_before(one_x_two_rows, KICKOFF),
    },
}

csv_path = OUT / "mexico-ecuador-titan-prematch-snapshots.csv"
with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["market", "snapshot", "time", "home_or_over", "line_or_draw", "away_or_under", "score_label"])
    for key, info in snapshots.items():
        for snap_name, row in [("early", info["early"]), ("last_before_09_30", info["cutoff"]), ("last_before_kickoff", info["prekick"])]:
            writer.writerow([info["label"], snap_name, fmt_time(row["ModifyTime"]), row.get("HomeOdds"), row.get("PanKou"), row.get("AwayOdds"), row.get("Score")])

source_rows = [
    {
        "source": "FanDuel Research",
        "time": "2026-06-30",
        "prematch": "主推平局 +190；提到小 2.5 為 -225 但價格太重",
        "read": "方向偏向低比分與90分鐘不分勝負",
        "result": "平局失敗；小 2.5 成功",
        "url": "https://www.fanduel.com/research/world-cup-predictions-today-mexico-vs-ecuador-picks-best-bets-and-props-june-30",
        "grade": "mixed",
    },
    {
        "source": "RotoWire",
        "time": "2026-06-30 02:35 ET",
        "prematch": "小 1.5、墨西哥晉級、小 2.5、墨西哥零封勝；預測 1-0",
        "read": "低比分 + 墨西哥方向",
        "result": "墨西哥晉級、小 2.5、零封勝成功；小 1.5 和 1-0 失敗",
        "url": "https://www.rotowire.com/soccer/article/mexico-vs-ecuador-picks-tips-odds-best-bets-2026-world-cup-round-of-32-120373",
        "grade": "good",
    },
    {
        "source": "DraftKings Network",
        "time": "2026-06-30 15:00 ET",
        "prematch": "Mexico Moneyline +125",
        "read": "主場與防守支持墨西哥90分鐘勝",
        "result": "成功",
        "url": "https://dknetwork.draftkings.com/2026/06/30/mexico-vs-ecuador-prediction-pick-for-tuesday-6-30-26/",
        "grade": "hit",
    },
    {
        "source": "SportsGambler",
        "time": "2026-06-29 16:27",
        "prematch": "墨西哥勝 @2.25；正確比分 1-0；角球小 7.5",
        "read": "認為墨西哥勝率約50%，高於莊家隱含44.4%",
        "result": "墨西哥勝成功；1-0 失敗",
        "url": "https://www.sportsgambler.com/betting-tips/football/mexico-vs-ecuador-prediction-lineups-odds-2026-06-30/",
        "grade": "hit",
    },
    {
        "source": "CBS Sports",
        "time": "2026-06-30",
        "prematch": "墨西哥晉級 -178；全場小 2.5 -144",
        "read": "墨西哥品質較好，但比賽不會高比分",
        "result": "兩者皆成功",
        "url": "https://www.cbssports.com/soccer/news/mexico-vs-ecuador-prediction-picks-odds-betting-preview-start-time-for-2026-world-cup-match-on-tuesday/",
        "grade": "hit",
    },
    {
        "source": "WSN",
        "time": "2026-06-29 11:30 ET",
        "prematch": "平局、小 2.5、墨西哥晉級 + 墨西哥小 1.5 球",
        "read": "防守戰，首球關鍵，可能拖到延長或PK",
        "result": "小 2.5 成功；平局失敗；墨西哥隊進2球使組合單失敗",
        "url": "https://www.wsn.com/world-cup/mexico-vs-ecuador-2026-06-30/",
        "grade": "mixed",
    },
]

sources_csv = OUT / "mexico-ecuador-source-readback.csv"
with sources_csv.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["source", "time", "prematch", "read", "result", "url", "grade"])
    writer.writeheader()
    writer.writerows(source_rows)

one_x_two_cut = snapshots["one_x_two"]["cutoff"]
one_x_two_probs = no_vig_probs([num(one_x_two_cut["HomeOdds"]), num(one_x_two_cut["PanKou"]), num(one_x_two_cut["AwayOdds"])])

american_market = [
    ("Mexico", +125, +130, +120, +119),
    ("Draw", +190, +200, +200, +197),
    ("Ecuador", +270, +270, +260, +260),
]
avg_american_probs = []
for name, *odds in american_market:
    probs = [american_to_prob(o) for o in odds]
    avg_american_probs.append((name, sum(probs) / len(probs)))
market_total = sum(p for _, p in avg_american_probs)
avg_no_vig = [(name, p / market_total) for name, p in avg_american_probs]


def pill(text, cls=""):
    return f"<span class='pill {cls}'>{html.escape(text)}</span>"


def snapshot_table():
    rows = []
    labels = {
        "asian": ("亞讓", "墨西哥水位", "讓球", "厄瓜多水位", "解讀"),
        "total": ("總進球", "大球水位", "盤口", "小球水位", "解讀"),
        "one_x_two": ("勝平負", "墨西哥", "平局", "厄瓜多", "解讀"),
    }
    interpretations = {
        "asian": {
            "early": "墨西哥 -0/0.5 早盤偏熱",
            "cutoff": "09:30前仍是墨西哥 -0/0.5，但水位已升，市場對墨西哥降溫",
            "prekick": "封盤前仍維持墨西哥小讓",
        },
        "total": {
            "early": "早盤 2/2.5",
            "cutoff": "降到 1.5/2，市場強烈往小球修正",
            "prekick": "封盤前最後可見仍是 1.5/2",
        },
        "one_x_two": {
            "early": "墨西哥明顯小熱門",
            "cutoff": "平局被大幅壓低，市場更怕低比分僵局",
            "prekick": "封盤前最後可見勝平負同 09:30前快照",
        },
    }
    for key in ["asian", "total", "one_x_two"]:
        market, h, d, a, note = labels[key]
        for snap, snap_label in [("early", "早盤"), ("cutoff", "09:30前最後"), ("prekick", "開賽前最後")]:
            r = snapshots[key][snap]
            rows.append(
                f"<tr><td>{market}</td><td>{snap_label}</td><td>{fmt_time(r['ModifyTime'])}</td>"
                f"<td>{r.get('HomeOdds')}</td><td>{r.get('PanKou')}</td><td>{r.get('AwayOdds')}</td>"
                f"<td>{html.escape(interpretations[key][snap])}</td></tr>"
            )
    return "".join(rows)


def source_table():
    rows = []
    for r in source_rows:
        cls = {"hit": "good", "good": "good", "mixed": "warn"}.get(r["grade"], "")
        rows.append(
            f"<tr><td><a href='{html.escape(r['url'])}'>{html.escape(r['source'])}</a></td>"
            f"<td>{html.escape(r['prematch'])}</td><td>{html.escape(r['read'])}</td>"
            f"<td>{html.escape(r['result'])}</td><td>{pill(r['grade'], cls)}</td></tr>"
        )
    return "".join(rows)


consensus_hits = [
    ("墨西哥晉級 / 方向", 5, 1, "#2563eb"),
    ("小 2.5", 5, 0, "#059669"),
    ("墨西哥90分鐘勝", 2, 0, "#7c3aed"),
    ("平局", 2, 0, "#dc2626"),
    ("小 1.5", 1, 0, "#d97706"),
    ("墨西哥零封勝", 1, 0, "#0891b2"),
]


def consensus_bars():
    bars = []
    for label, mentions, hits, color in consensus_hits:
        pct = mentions / max(x[1] for x in consensus_hits) * 100
        hit_text = "命中" if hits else "未命中"
        bars.append(
            f"<div class='bar-row'><div class='bar-label'>{html.escape(label)}</div>"
            f"<div class='bar-track'><div class='bar-fill' style='width:{pct:.0f}%;background:{color}'></div></div>"
            f"<div class='bar-note'>{mentions} 來源 / {hit_text}</div></div>"
        )
    return "".join(bars)


html_out = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>墨西哥 vs 厄瓜多 賽前盤勢回測</title>
  <style>
    :root {{
      --bg:#f3f6fb; --panel:#fff; --ink:#172033; --muted:#647084; --line:#d9e2ef;
      --blue:#2563eb; --green:#059669; --amber:#d97706; --red:#dc2626; --violet:#7c3aed; --cyan:#0891b2;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family: Arial, "Microsoft JhengHei", sans-serif; background:var(--bg); color:var(--ink); }}
    header {{ padding:34px 28px 24px; background:#101827; color:#fff; }}
    header h1 {{ margin:0 0 8px; font-size:30px; letter-spacing:0; }}
    header p {{ margin:0; color:#cbd5e1; max-width:980px; line-height:1.65; }}
    main {{ max-width:1180px; margin:0 auto; padding:22px; }}
    section {{ margin:18px 0; }}
    .grid {{ display:grid; gap:14px; grid-template-columns:repeat(4,minmax(0,1fr)); }}
    .card, .chart-block, .table-card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; box-shadow:0 1px 2px rgba(15,23,42,.04); }}
    .card h2 {{ margin:0 0 8px; font-size:15px; color:var(--muted); font-weight:700; }}
    .metric {{ font-size:26px; font-weight:800; margin-bottom:6px; }}
    .card p {{ margin:0; line-height:1.55; color:var(--muted); font-size:14px; }}
    .section-title {{ display:flex; align-items:end; justify-content:space-between; gap:12px; margin:24px 0 10px; }}
    .section-title h2 {{ margin:0; font-size:20px; }}
    .section-title p {{ margin:0; color:var(--muted); font-size:13px; }}
    .chart-block {{ padding:12px 14px 8px; margin-bottom:14px; }}
    .chart-head {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }}
    .chart-head h3 {{ margin:0 0 4px; font-size:16px; }}
    .chart-head p {{ margin:0; color:var(--muted); font-size:13px; }}
    .legend {{ display:flex; flex-wrap:wrap; gap:10px; font-size:13px; color:var(--muted); justify-content:flex-end; }}
    .legend span {{ display:flex; align-items:center; gap:5px; }}
    .legend i {{ width:11px; height:11px; display:inline-block; border-radius:50%; }}
    svg {{ width:100%; height:auto; }}
    .gridline {{ stroke:#e5edf7; stroke-width:1; }}
    .vgrid {{ stroke:#edf2f8; stroke-width:1; stroke-dasharray:3 4; }}
    .axis, .ylabel {{ fill:#647084; font-size:12px; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    th, td {{ text-align:left; padding:10px 9px; border-bottom:1px solid var(--line); vertical-align:top; }}
    th {{ color:#475569; background:#f8fafc; font-size:13px; }}
    td a {{ color:var(--blue); text-decoration:none; }}
    .pill {{ display:inline-block; padding:3px 8px; border-radius:999px; background:#e5e7eb; color:#374151; font-size:12px; font-weight:700; white-space:nowrap; }}
    .pill.good {{ background:#dcfce7; color:#166534; }}
    .pill.warn {{ background:#fef3c7; color:#92400e; }}
    .pill.bad {{ background:#fee2e2; color:#991b1b; }}
    .two-col {{ display:grid; gap:14px; grid-template-columns:1.1fr .9fr; }}
    .bar-row {{ display:grid; grid-template-columns:145px 1fr 120px; gap:10px; align-items:center; margin:10px 0; }}
    .bar-label {{ font-size:13px; font-weight:700; }}
    .bar-track {{ height:13px; background:#e9eef6; border-radius:99px; overflow:hidden; }}
    .bar-fill {{ height:100%; border-radius:99px; }}
    .bar-note {{ font-size:12px; color:var(--muted); }}
    .callout {{ border-left:4px solid var(--blue); background:#eff6ff; padding:13px 14px; border-radius:6px; line-height:1.65; }}
    .callout strong {{ color:#1e3a8a; }}
    .small {{ color:var(--muted); font-size:13px; line-height:1.55; }}
    ul.clean {{ margin:0; padding-left:18px; line-height:1.7; }}
    @media (max-width:900px) {{
      .grid, .two-col {{ grid-template-columns:1fr; }}
      .bar-row {{ grid-template-columns:1fr; }}
      header h1 {{ font-size:24px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>墨西哥 vs 厄瓜多：賽前盤勢回測</h1>
    <p>比賽已結束，最終 2-0。這份頁面只拿賽前資料做回測，核心快照採用 Titan007 / Crow* 在 2026-07-01 09:30 前最後可見盤口；賽中與賽後變化已排除。</p>
  </header>
  <main>
    <section class="grid">
      <div class="card"><h2>最終比分</h2><div class="metric">墨西哥 2-0</div><p>半場 2-0，全場 2 球，厄瓜多未進球。</p></div>
      <div class="card"><h2>09:30 前總進球</h2><div class="metric">1.75 球</div><p>從早盤 2.25 下修到 1.75，市場強烈往低比分修正。</p></div>
      <div class="card"><h2>09:30 前勝平負</h2><div class="metric">2.35 / 2.73 / 4.00</div><p>墨西哥仍是小熱門，但平局賠率被壓低很多。</p></div>
      <div class="card"><h2>Binance 回查</h2><div class="metric">未找到已結算 topic</div><p>API 搜尋目前只回可見/近期 topic，沒有 Mexico vs Ecuador 已結算市場。</p></div>
    </section>

    <section>
      <div class="section-title"><h2>回測結論</h2><p>只看賽前，不吃賽後答案</p></div>
      <div class="callout">
        <strong>當時盤勢最穩的判斷是「低比分 + 墨西哥不敗/晉級」，而不是單押平局。</strong>
        盤口確實往平局與小球靠，但 90 分鐘平局被低估了「墨西哥主場先進球後控場」的路徑。
        最終結果驗證：小 2.5、墨西哥晉級、墨西哥 -0.25、墨西哥勝、BTTS No 都對；小 1.5、平局、1-0 正確比分錯。
      </div>
    </section>

    <section>
      <div class="section-title"><h2>Titan007 賽前盤口</h2><p>來源：Titan007 Crow* 現場數據，切到 09:30 前與開賽前</p></div>
      {line_chart(compact_series(one_x_two_rows, ['HomeOdds','PanKou','AwayOdds']), [
        {'key':'HomeOdds','label':'墨西哥勝','color':'#2563eb'},
        {'key':'PanKou','label':'平局','color':'#d97706'},
        {'key':'AwayOdds','label':'厄瓜多勝','color':'#dc2626'}
      ], '勝平負賠率走勢', '墨西哥從 2.12 漂到 2.35，平局從 3.25 壓到 2.73。', '十進位賠率')}
      {line_chart(compact_series(total_rows, ['PanKou']), [
        {'key':'PanKou','label':'總進球盤口','color':'#059669'}
      ], '總進球盤口走勢', '2.25 下修到 1.75，是全場最明顯的盤勢訊號。', '球數盤口')}
      {line_chart(compact_series(asian_rows, ['HomeOdds','AwayOdds']), [
        {'key':'HomeOdds','label':'墨西哥讓球水位','color':'#7c3aed'},
        {'key':'AwayOdds','label':'厄瓜多受讓水位','color':'#0891b2'}
      ], '亞讓水位走勢', '讓球維持墨西哥 -0/0.5，但墨西哥水位上升，代表熱度降溫。', '香港水位')}
    </section>

    <section class="table-card">
      <div class="section-title"><h2>關鍵快照表</h2><p>CSV: {html.escape(csv_path.name)}</p></div>
      <table>
        <thead><tr><th>市場</th><th>快照</th><th>時間</th><th>主/大</th><th>盤口/平</th><th>客/小</th><th>解讀</th></tr></thead>
        <tbody>{snapshot_table()}</tbody>
      </table>
      <p class="small">註：亞讓正數在 Titan 顯示語境下按主隊讓 -0.25 解讀；總進球 1.75 代表 1.5/2 亞洲大小盤。</p>
    </section>

    <section class="two-col">
      <div class="table-card">
        <div class="section-title"><h2>外部來源賽前看法</h2><p>只列開賽前發布/保留的內容</p></div>
        <table>
          <thead><tr><th>來源</th><th>賽前項目</th><th>當時邏輯</th><th>結果</th><th>評估</th></tr></thead>
          <tbody>{source_table()}</tbody>
        </table>
      </div>
      <div class="table-card">
        <div class="section-title"><h2>訊號命中率</h2><p>按來源提及方向粗略統計</p></div>
        {consensus_bars()}
        <hr style="border:none;border-top:1px solid var(--line);margin:16px 0">
        <h3 style="margin:0 0 8px;font-size:16px;">09:30 前勝平負隱含機率</h3>
        <ul class="clean">
          <li>Titan Crow* 去水：墨西哥 {one_x_two_probs[0]*100:.1f}% / 平 {one_x_two_probs[1]*100:.1f}% / 厄瓜多 {one_x_two_probs[2]*100:.1f}%</li>
          <li>WSN 四家平均去水：墨西哥 {avg_no_vig[0][1]*100:.1f}% / 平 {avg_no_vig[1][1]*100:.1f}% / 厄瓜多 {avg_no_vig[2][1]*100:.1f}%</li>
          <li>兩邊共同訊號：墨西哥是小熱門，但平局機率不可忽視。</li>
        </ul>
      </div>
    </section>

    <section class="table-card">
      <div class="section-title"><h2>如果當時放到 Binance 判斷</h2><p>因歷史 topic 查不到，只能給合理價格門檻</p></div>
      <table>
        <thead><tr><th>項目</th><th>賽前合理區間</th><th>下在 Binance 的判斷門檻</th><th>賽果</th></tr></thead>
        <tbody>
          <tr><td>小 2.5</td><td>約 68% - 72%</td><td>若 Binance Yes 價格 ≤ 0.68~0.70 才算有價值</td><td>{pill('過', 'good')}</td></tr>
          <tr><td>墨西哥晉級</td><td>約 63% - 66%</td><td>若 Binance Mexico Advance ≤ 0.63~0.65 可買</td><td>{pill('過', 'good')}</td></tr>
          <tr><td>墨西哥90分鐘勝</td><td>約 40% - 45%</td><td>若 Binance Mexico Win ≤ 0.42 左右才有明顯價值</td><td>{pill('過', 'good')}</td></tr>
          <tr><td>平局</td><td>約 32% - 35%</td><td>若價格高於 0.34 其實沒有便宜，雖有盤勢但不該重壓</td><td>{pill('沒過', 'bad')}</td></tr>
          <tr><td>小 1.5</td><td>高賠但容錯低</td><td>除非價格明顯低於市場，不適合當主單</td><td>{pill('沒過', 'bad')}</td></tr>
        </tbody>
      </table>
    </section>

    <section class="table-card">
      <div class="section-title"><h2>資料取捨</h2><p>避免賽後污染</p></div>
      <ul class="clean">
        <li>採用：Titan007 `OddsDetail.aspx` 中 `ModifyTime` 小於 `20260701100000` 的資料，並以 `20260701093000` 做半小時快照。</li>
        <li>排除：HappenTime 有比賽分鐘、Score 是即時比分、或 ModifyTime 在開賽後的資料。</li>
        <li>角球：Titan 角球頁可見初盤，但保留的即時盤混入賽中變化，沒有可靠 09:30 詳細序列，所以未納入主要結論。</li>
        <li>Binance：API 搜尋未回 Mexico vs Ecuador 已結算 topic，因此本頁不假造 Binance 歷史價格。</li>
      </ul>
    </section>
  </main>
</body>
</html>
"""

out_path = OUT / "mexico-ecuador-retro-odds-analysis.html"
out_path.write_text(html_out, encoding="utf-8")

print(out_path)
print(csv_path)
print(sources_csv)
