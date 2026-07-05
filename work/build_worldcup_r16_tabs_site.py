import csv
import html
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
WORK = ROOT / "work"
PUBLIC = ROOT / "site-canada-morocco" / "public"
LOCK_PATH = WORK / "locked_bet_allocations.json"
TPE = timezone(timedelta(hours=8))
SITE_NAME = "世足盤口戰情室"
SITE_TAGLINE = "World Cup Odds Desk"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_json_optional(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return default


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


def out(topics, topic_title, market_title, outcome_name):
    return find_outcome(find_market(find_topic(topics, topic_title), market_title), outcome_name)


def price(outcome):
    return float(outcome["price"])


def chance(outcome):
    return float(outcome["chance"])


def pct(outcome):
    return chance(outcome) * 100


def profit(stake, p):
    return stake / p - stake


def ret(stake, p):
    return stake / p


def locked_allocation(match_key, fallback):
    lock = LOCKED_ALLOCATIONS.get(match_key)
    if not lock or not lock.get("locked"):
        return fallback, None

    rows = []
    for item in lock.get("allocation", []):
        name = item.get("name")
        stake = as_float(item.get("stake"))
        p = as_float(item.get("price"))
        if name and stake is not None and p:
            rows.append((name, stake, p))
    return (rows or fallback), lock


def lock_note(match):
    lock = match.get("allocation_lock")
    if not lock:
        return ""
    locked_at = lock.get("lockedAt") or "未標記時間"
    note = lock.get("note") or "後續盤口更新不會覆蓋此組下注金額與價格。"
    return (
        "<p class='odds-note'>"
        f"<b>鎖定配置</b>：{safe(locked_at)} 鎖定。{safe(note)}"
        "</p>"
    )


def fmt_pct(value):
    return f"{value:.1f}%"


def tpe_start(topic):
    return datetime.fromtimestamp(topic["startDate"] / 1000, timezone.utc).astimezone(TPE)


def safe(value):
    return html.escape(str(value))


def bar(label, percent, color, note=None):
    width = max(1, min(100, percent))
    note = note if note is not None else f"{percent:.1f}%"
    return (
        "<div class='bar-row'>"
        f"<div class='bar-label'>{safe(label)}</div>"
        "<div class='bar-track'>"
        f"<div class='bar-fill' style='width:{width:.1f}%;background:{color}'></div>"
        "</div>"
        f"<div class='bar-note'>{safe(note)}</div>"
        "</div>"
    )


def market_bars(rows):
    colors = ["#0f766e", "#2563eb", "#d97706", "#7c3aed", "#dc2626", "#0891b2", "#475569"]
    return "".join(
        bar(label, pct(o), colors[i % len(colors)], f"{pct(o):.1f}% / 價格 {price(o):.2f}")
        for i, (label, o) in enumerate(rows)
    )


def exact_scores(topics, title, count=8):
    exact_topic = find_topic(topics, title)
    scores = []
    for market in exact_topic.get("markets", []):
        yes = find_outcome(market, "Yes")
        scores.append((market.get("title"), chance(yes), price(yes)))
    return sorted(scores, key=lambda item: item[1], reverse=True)[:count]


def exact_bars(scores):
    colors = ["#0f766e", "#2563eb", "#7c3aed", "#d97706", "#0891b2", "#dc2626", "#475569", "#16a34a"]
    return "".join(
        bar(label, c * 100, colors[i % len(colors)], f"{c * 100:.1f}% / 價格 {p:.3f}")
        for i, (label, c, p) in enumerate(scores)
    )


def allocation_table(allocation):
    return "".join(
        "<tr>"
        f"<td>{safe(name)}</td><td>{stake}U</td><td>{p:.2f}</td>"
        f"<td>{ret(stake, p):.2f}U</td><td class='good'>+{profit(stake, p):.2f}U</td>"
        "</tr>"
        for name, stake, p in allocation
    )


def scenario_table(allocation, scenarios):
    rows = []
    for label, won in scenarios:
        net = 0.0
        for name, stake, p in allocation:
            net += profit(stake, p) if name in won else -stake
        cls = "good" if net > 0 else "bad"
        rows.append(
            "<tr>"
            f"<td>{safe(label)}</td><td class='{cls}'>{net:+.2f}U</td>"
            f"<td>{safe(', '.join(won) if won else '全倒')}</td>"
            "</tr>"
        )
    return "".join(rows)


def source_rows(sources):
    return "".join(
        "<tr>"
        f"<td><a href='{safe(url)}' target='_blank' rel='noopener'>{safe(name)}</a></td>"
        f"<td>{safe(read)}</td><td><span class='pill'>{safe(signal)}</span></td>"
        "</tr>"
        for name, url, read, signal in sources
    )


def card(title, metric, note):
    return f"<div class='card'><h3>{safe(title)}</h3><div class='metric'>{safe(metric)}</div><p>{safe(note)}</p></div>"


can_topics = load_json(OUT / "binance-canada-morocco-topics.json")
par_topics = load_json(OUT / "binance-paraguay-france-topics.json")
bra_topics = load_json(OUT / "binance-brazil-norway-topics.json")
mex_topics = load_json(OUT / "binance-mexico-england-topics.json")
LOCKED_ALLOCATIONS = load_json_optional(LOCK_PATH, {})

can_main = find_topic(can_topics, "Canada vs. Morocco")
par_main = find_topic(par_topics, "Paraguay vs. France")
bra_main = find_topic(bra_topics, "Brazil vs. Norway")
mex_main = find_topic(mex_topics, "Mexico vs. England")

can = {
    "key": "can-mar",
    "title": "加拿大 vs 摩洛哥",
    "subtitle": "摩洛哥方向 + 小球，但 1-1 平局風險高",
    "time": tpe_start(can_main),
    "venue": "Houston Stadium",
    "teams": ("CAN", "MAR"),
    "main": [
        ("摩洛哥 90 分鐘勝", out(can_topics, "Canada vs. Morocco", "MAR", "Yes")),
        ("90 分鐘平局", out(can_topics, "Canada vs. Morocco", "Draw", "Yes")),
        ("加拿大 90 分鐘勝", out(can_topics, "Canada vs. Morocco", "CAN", "Yes")),
    ],
    "markets": [
        ("摩洛哥晉級", out(can_topics, "Canada vs. Morocco - More Markets", "Team to Advance", "MAR")),
        ("小 2.5 球", out(can_topics, "Canada vs. Morocco - More Markets", "O/U 2.5", "Under")),
        ("小 3.5 球", out(can_topics, "Canada vs. Morocco - More Markets", "O/U 3.5", "Under")),
        ("BTTS Yes", out(can_topics, "Canada vs. Morocco - More Markets", "Both Teams to Score", "Yes")),
        ("角球大 8.5", out(can_topics, "Canada vs. Morocco - Total Corners", "Total Corners: O/U 8.5", "Over 8.5")),
    ],
    "allocation": [
        ("摩洛哥 90 分鐘勝", 50, price(out(can_topics, "Canada vs. Morocco", "MAR", "Yes"))),
        ("全場小 2.5 球", 30, price(out(can_topics, "Canada vs. Morocco - More Markets", "O/U 2.5", "Under"))),
        ("全場小 3.5 球", 20, price(out(can_topics, "Canada vs. Morocco - More Markets", "O/U 3.5", "Under"))),
    ],
    "scenarios": [
        ("CAN 0-1 MAR", {"摩洛哥 90 分鐘勝", "全場小 2.5 球", "全場小 3.5 球"}),
        ("CAN 0-2 MAR", {"摩洛哥 90 分鐘勝", "全場小 2.5 球", "全場小 3.5 球"}),
        ("CAN 1-2 MAR", {"摩洛哥 90 分鐘勝", "全場小 3.5 球"}),
        ("CAN 1-1 MAR", {"全場小 2.5 球", "全場小 3.5 球"}),
        ("CAN 1-0 MAR", {"全場小 2.5 球", "全場小 3.5 球"}),
        ("CAN 2-2 MAR", set()),
    ],
    "exact": exact_scores(can_topics, "Canada vs. Morocco - Exact Score"),
    "take": "主線仍是摩洛哥 90 分鐘勝，但不要單壓；小 2.5 / 小 3.5 是用來保護 0-1、0-2、1-1 這種低比分帶。",
    "sources": [
        ("Binance Prediction", "https://www.binance.com/", f"MAR 90 分鐘勝 {pct(out(can_topics, 'Canada vs. Morocco', 'MAR', 'Yes')):.1f}%，小 2.5 {pct(out(can_topics, 'Canada vs. Morocco - More Markets', 'O/U 2.5', 'Under')):.1f}%。", "盤口"),
        ("Titan007", "https://live.titan007.com/asian/2907393.htm", "既有快照顯示亞盤約摩洛哥 -0.75，大小球約 2.25/2.5。", "亞盤"),
        ("Al Jazeera / Opta", "https://www.aljazeera.com/sports/2026/7/3/canada-morocco-fifa-world-cup-round-of-16-saibari-prediction-schedule", "Opta 賽前給摩洛哥 90 分鐘勝率 52.7%，平局/延長風險仍在。", "模型"),
        ("SportsGambler", "https://www.sportsgambler.com/betting-tips/football/canada-vs-morocco-prediction-lineups-odds-2026-07-04/", "主推 Morocco To Win，正確比分偏 0-2 摩洛哥。", "外部預測"),
    ],
}

par = {
    "key": "par-fra",
    "title": "巴拉圭 vs 法國",
    "subtitle": "法國強熱門，盤口核心是勝出與讓球",
    "time": tpe_start(par_main),
    "venue": "Philadelphia Stadium",
    "teams": ("PAR", "FRA"),
    "main": [
        ("法國 90 分鐘勝", out(par_topics, "Paraguay vs. France", "FRA", "Yes")),
        ("90 分鐘平局", out(par_topics, "Paraguay vs. France", "Draw", "Yes")),
        ("巴拉圭 90 分鐘勝", out(par_topics, "Paraguay vs. France", "PAR", "Yes")),
    ],
    "markets": [
        ("法國晉級", out(par_topics, "Paraguay vs. France - More Markets", "Team to Advance", "FRA")),
        ("法國 -1.5", out(par_topics, "Paraguay vs. France - More Markets", "France (-1.5)", "FRA")),
        ("大 2.5 球", out(par_topics, "Paraguay vs. France - More Markets", "O/U 2.5", "Over")),
        ("BTTS No", out(par_topics, "Paraguay vs. France - More Markets", "Both Teams to Score", "No")),
        ("Mbappe 進球", out(par_topics, "Paraguay vs France - Player Props", "Kylian Mbappe Total Goals", "Over 0.5")),
    ],
    "allocation": [
        ("法國 90 分鐘勝", 50, price(out(par_topics, "Paraguay vs. France", "FRA", "Yes"))),
        ("法國 -1.5", 20, price(out(par_topics, "Paraguay vs. France - More Markets", "France (-1.5)", "FRA"))),
        ("BTTS No", 20, price(out(par_topics, "Paraguay vs. France - More Markets", "Both Teams to Score", "No"))),
        ("全場大 2.5 球", 10, price(out(par_topics, "Paraguay vs. France - More Markets", "O/U 2.5", "Over"))),
    ],
    "scenarios": [
        ("PAR 0-2 FRA", {"法國 90 分鐘勝", "法國 -1.5", "BTTS No"}),
        ("PAR 0-3 FRA", {"法國 90 分鐘勝", "法國 -1.5", "BTTS No", "全場大 2.5 球"}),
        ("PAR 0-1 FRA", {"法國 90 分鐘勝", "BTTS No"}),
        ("PAR 1-2 FRA", {"法國 90 分鐘勝", "全場大 2.5 球"}),
        ("PAR 1-1 FRA", set()),
        ("PAR 1-0 FRA", set()),
    ],
    "exact": exact_scores(par_topics, "Paraguay vs. France - Exact Score"),
    "take": "法國盤口太熱，法國 90 分鐘勝只能當底倉；真正收益來自法國 -1.5、BTTS No、或 0-2/0-3 方向。1 球小勝會讓收益變薄。",
    "sources": [
        ("Binance Prediction", "https://www.binance.com/", f"FRA 90 分鐘勝 {pct(out(par_topics, 'Paraguay vs. France', 'FRA', 'Yes')):.1f}%，法國 -1.5 {pct(out(par_topics, 'Paraguay vs. France - More Markets', 'France (-1.5)', 'FRA')):.1f}%。", "盤口"),
        ("The Analyst / Opta", "https://theanalyst.com/articles/paraguay-vs-france-prediction-world-cup-2026-match-preview", "Opta 賽前模擬給法國 90 分鐘勝率約 79.7%，重度偏法國。", "模型"),
        ("Al Jazeera", "https://www.aljazeera.com/sports/2026/7/4/france-vs-paraguay-world-cup-round-of-16-mbappe-prediction-kickoff", "賽前預覽認為法國是本屆目前最強勢球隊之一，巴拉圭則靠爆冷德國晉級。", "賽前資訊"),
        ("SportsGambler", "https://www.sportsgambler.com/betting-tips/football/paraguay-vs-france-prediction-lineups-odds-2026-07-04/", "市場約給法國 85% 勝率，價格極低，需用讓球或比分方向提高報酬。", "外部預測"),
        ("Covers", "https://www.covers.com/world-cup/france-vs-paraguay-prediction-picks-odds-saturday-7-4-2026", "法國大熱門，文章主線偏 Les Bleus 持續強勢。", "外部預測"),
    ],
}

bra_default_allocation = [
    ("巴西晉級", 40, price(out(bra_topics, "Brazil vs. Norway - More Markets", "Team to Advance", "BRA"))),
    ("BTTS Yes", 25, price(out(bra_topics, "Brazil vs. Norway - More Markets", "Both Teams to Score", "Yes"))),
    ("全場小 3.5 球", 25, price(out(bra_topics, "Brazil vs. Norway - More Markets", "O/U 3.5", "Under"))),
    ("巴西 90 分鐘勝", 10, price(out(bra_topics, "Brazil vs. Norway", "BRA", "Yes"))),
]
bra_allocation, bra_allocation_lock = locked_allocation("bra-nor", bra_default_allocation)

bra = {
    "key": "bra-nor",
    "title": "巴西 vs 挪威",
    "subtitle": "巴西小熱門，但挪威進球風險不能忽略",
    "time": tpe_start(bra_main),
    "venue": "New York/New Jersey Stadium",
    "teams": ("BRA", "NOR"),
    "main": [
        ("巴西 90 分鐘勝", out(bra_topics, "Brazil vs. Norway", "BRA", "Yes")),
        ("90 分鐘平局", out(bra_topics, "Brazil vs. Norway", "Draw", "Yes")),
        ("挪威 90 分鐘勝", out(bra_topics, "Brazil vs. Norway", "NOR", "Yes")),
    ],
    "markets": [
        ("巴西晉級", out(bra_topics, "Brazil vs. Norway - More Markets", "Team to Advance", "BRA")),
        ("BTTS Yes", out(bra_topics, "Brazil vs. Norway - More Markets", "Both Teams to Score", "Yes")),
        ("小 3.5 球", out(bra_topics, "Brazil vs. Norway - More Markets", "O/U 3.5", "Under")),
        ("大 2.5 球", out(bra_topics, "Brazil vs. Norway - More Markets", "O/U 2.5", "Over")),
        ("Haaland 進球", out(bra_topics, "Brazil vs. Norway - Player Props", "Erling Haaland Total Goals", "Over 0.5")),
    ],
    "allocation": bra_allocation,
    "allocation_lock": bra_allocation_lock,
    "scenarios": [
        ("BRA 2-1 NOR", {"巴西晉級", "Brazil -1.5 選 NOR（挪威 +1.5）", "BTTS Yes", "全場小 3.5 球"}),
        ("BRA 1-1 NOR，巴西晉級", {"巴西晉級", "Brazil -1.5 選 NOR（挪威 +1.5）", "BTTS Yes", "全場小 3.5 球"}),
        ("BRA 1-1 NOR，挪威晉級", {"Brazil -1.5 選 NOR（挪威 +1.5）", "BTTS Yes", "全場小 3.5 球"}),
        ("BRA 1-0 NOR", {"巴西晉級", "Brazil -1.5 選 NOR（挪威 +1.5）", "全場小 3.5 球"}),
        ("BRA 2-0 NOR", {"巴西晉級", "全場小 3.5 球"}),
        ("BRA 1-2 NOR", {"Brazil -1.5 選 NOR（挪威 +1.5）", "BTTS Yes", "全場小 3.5 球"}),
        ("BRA 2-2 NOR，巴西晉級", {"巴西晉級", "Brazil -1.5 選 NOR（挪威 +1.5）", "BTTS Yes"}),
        ("BRA 2-2 NOR，挪威晉級", {"Brazil -1.5 選 NOR（挪威 +1.5）", "BTTS Yes"}),
        ("BRA 3-1 NOR", {"巴西晉級", "BTTS Yes"}),
        ("BRA 0-1 NOR", {"Brazil -1.5 選 NOR（挪威 +1.5）", "全場小 3.5 球"}),
    ],
    "exact": exact_scores(bra_topics, "Brazil vs. Norway - Exact Score"),
    "take": "這場不是法國那種重熱門。巴西晉級比 90 分鐘勝更適合當主倉，搭 BTTS Yes 和小 3.5，等於承認挪威有進球能力但不追大比分失控。",
    "sources": [
        ("Binance Prediction", "https://www.binance.com/", f"BRA 90 分鐘勝 {pct(out(bra_topics, 'Brazil vs. Norway', 'BRA', 'Yes')):.1f}%，巴西晉級 {pct(out(bra_topics, 'Brazil vs. Norway - More Markets', 'Team to Advance', 'BRA')):.1f}%。", "盤口"),
        ("SportsGambler", "https://www.sportsgambler.com/betting-tips/football/brazil-vs-norway-prediction-lineups-odds-2026-07-05/", "市場約給巴西 55% 的 90 分鐘勝率，屬小熱門而非碾壓盤。", "外部預測"),
        ("Robinhood Prediction Market", "https://robinhood.com/us/en/prediction-markets/soccer/events/round-of-16-brazil-vs-norway-to-advance-jul-05-2026/", "晉級市場約巴西 68¢、挪威 34¢，與 Binance 晉級盤接近。", "對照盤"),
        ("SportsLine", "https://www.sportsline.com/insiders/brazil-vs-norway-odds-predictions-2026-world-cup-round-of-16-picks-from-proven-soccer-expert/", "公開摘要列巴西 90 分鐘勝為小熱門，總球 2.5 附近。", "外部賠率"),
        ("Total Football Analysis", "https://totalfootballanalysis.com/competitions/fifa-world-cup-2026/world-cup-round-of-16-match-3-predictions", "判讀巴西仍是熱門，但挪威對戰背景和進攻能力帶來不確定性。", "戰術觀點"),
    ],
}

mex = {
    "key": "mex-eng",
    "title": "墨西哥 vs 英格蘭",
    "subtitle": "英格蘭小熱門，但高原主場與低比分盤讓晉級路徑接近五五波",
    "time": tpe_start(mex_main),
    "venue": "Estadio Banorte",
    "teams": ("MEX", "ENG"),
    "main": [
        ("英格蘭 90 分鐘勝", out(mex_topics, "Mexico vs. England", "ENG", "Yes")),
        ("90 分鐘平局", out(mex_topics, "Mexico vs. England", "Draw", "Yes")),
        ("墨西哥 90 分鐘勝", out(mex_topics, "Mexico vs. England", "MEX", "Yes")),
    ],
    "markets": [
        ("英格蘭晉級", out(mex_topics, "Mexico vs. England - More Markets", "Team to Advance", "ENG")),
        ("墨西哥晉級", out(mex_topics, "Mexico vs. England - More Markets", "Team to Advance", "MEX")),
        ("小 2.5 球", out(mex_topics, "Mexico vs. England - More Markets", "O/U 2.5", "Under")),
        ("小 3.5 球", out(mex_topics, "Mexico vs. England - More Markets", "O/U 3.5", "Under")),
        ("BTTS No", out(mex_topics, "Mexico vs. England - More Markets", "Both Teams to Score", "No")),
        ("Kane 進球", out(mex_topics, "Mexico vs. England - Player Props", "Harry Kane: Total Goals", "Over 0.5")),
    ],
    "allocation": [
        ("英格蘭晉級", 30, price(out(mex_topics, "Mexico vs. England - More Markets", "Team to Advance", "ENG"))),
        ("England -1.5 選 MEX（墨西哥 +1.5）", 25, price(out(mex_topics, "Mexico vs. England - More Markets", "England (-1.5)", "MEX"))),
        ("全場小 3.5 球", 25, price(out(mex_topics, "Mexico vs. England - More Markets", "O/U 3.5", "Under"))),
        ("全場小 2.5 球", 20, price(out(mex_topics, "Mexico vs. England - More Markets", "O/U 2.5", "Under"))),
    ],
    "scenarios": [
        ("MEX 0-1 ENG", {"英格蘭晉級", "England -1.5 選 MEX（墨西哥 +1.5）", "全場小 3.5 球", "全場小 2.5 球"}),
        ("MEX 1-1 ENG，英格蘭晉級", {"英格蘭晉級", "England -1.5 選 MEX（墨西哥 +1.5）", "全場小 3.5 球", "全場小 2.5 球"}),
        ("MEX 1-1 ENG，墨西哥晉級", {"England -1.5 選 MEX（墨西哥 +1.5）", "全場小 3.5 球", "全場小 2.5 球"}),
        ("MEX 1-0 ENG", {"England -1.5 選 MEX（墨西哥 +1.5）", "全場小 3.5 球", "全場小 2.5 球"}),
        ("MEX 1-2 ENG", {"英格蘭晉級", "England -1.5 選 MEX（墨西哥 +1.5）", "全場小 3.5 球"}),
        ("MEX 0-2 ENG", {"英格蘭晉級", "全場小 3.5 球", "全場小 2.5 球"}),
        ("MEX 2-1 ENG", {"England -1.5 選 MEX（墨西哥 +1.5）", "全場小 3.5 球"}),
        ("MEX 2-2 ENG，英格蘭晉級", {"英格蘭晉級", "England -1.5 選 MEX（墨西哥 +1.5）"}),
        ("MEX 2-2 ENG，墨西哥晉級", {"England -1.5 選 MEX（墨西哥 +1.5）"}),
    ],
    "exact": exact_scores(mex_topics, "Mexico vs. England - Exact Score"),
    "take": "這場不是英格蘭碾壓盤。90 分鐘英格蘭略優，但主場高原與比分盤都偏低比分拉鋸；主倉用英格蘭晉級，防守倉用墨西哥 +1.5 與小球，比單押英格蘭 90 分鐘勝合理。",
    "sources": [
        ("Binance Prediction", "https://www.binance.com/", f"ENG 90 分鐘勝 {pct(out(mex_topics, 'Mexico vs. England', 'ENG', 'Yes')):.1f}%，英格蘭晉級 {pct(out(mex_topics, 'Mexico vs. England - More Markets', 'Team to Advance', 'ENG')):.1f}%。", "盤口"),
        ("SportsGambler", "https://www.sportsgambler.com/betting-tips/football/mexico-vs-england-prediction-lineups-odds-2026-07-05/", "外部賠率顯示英格蘭只是小熱門，且平局與墨西哥路徑都不低。", "外部盤"),
        ("Racing Post", "https://www.racingpost.com/sport/football-tips/world-cup-2026/mexico-vs-england-world-cup-prediction-team-news-odds-betting-tips-and-bet-builder-axk4R2P3FCRE/", "資格賽/晉級盤偏英格蘭，但 90 分鐘勝負並非單邊。", "賽前資訊"),
        ("The Guardian", "https://www.theguardian.com/football/2026/jul/04/mexico-england-world-cup-2026-pace-football-altitude", "提醒英格蘭要處理阿茲特克高原、墨西哥慢節奏與主場壓力。", "戰術背景"),
    ],
}

matches = [can, par, bra, mex]

DETAILS = {
    "can-mar": {
        "confidence": "中高",
        "primary": "摩洛哥 90 分鐘勝是主線，但平局機率接近三成，不能用重倉單壓。",
        "value": "Binance 的摩洛哥價格比 Opta 52.7% 略熱，優勢不算便宜；小球盤比較像保護低比分路徑。",
        "risk": "最怕 1-1 或加拿大先進球。若臨場摩洛哥 90 分鐘勝率被推過 60%，性價比會變薄。",
        "trigger": "若 O/U 2.5 從小球偏熱轉向大球，代表市場開始買進對攻，原本小球保護要降權重。",
        "avoid": "不建議把摩洛哥晉級和摩洛哥 90 分鐘勝同時重倉，兩者方向高度重疊。",
    },
    "par-fra": {
        "confidence": "高但賠率薄",
        "primary": "法國勝面最清楚，問題不是誰強，而是低價熱門要靠讓球或零封方向拉收益。",
        "value": "Binance 法國 90 分鐘勝接近 84%，和外部模型大致一致，不是明顯便宜盤。",
        "risk": "法國 1 球小勝會打掉 -1.5 與大 2.5 的報酬，這是本組合最大斷點。",
        "trigger": "若法國 -1.5 上升但 BTTS No 下滑，代表市場偏向 2-1/3-1，不宜同時過重壓零封。",
        "avoid": "法國晉級價格太低，除非只是保守底倉，否則資金效率不佳。",
    },
    "bra-nor": {
        "confidence": "中",
        "primary": "巴西是小熱門，不是碾壓盤。晉級比 90 分鐘勝更適合當主倉。",
        "value": "巴西晉級在 Binance 與 Robinhood 對照接近，算合理價；BTTS Yes 是承認挪威進球能力的搭配。",
        "risk": "Haaland 進球或挪威先進球會讓巴西 90 分鐘勝壓力變大，但不一定打掉巴西晉級。",
        "trigger": "若 BTTS Yes 續升、巴西 90 分鐘勝續跌，盤口會更像 1-1/2-1，而不是 1-0/2-0。",
        "avoid": "避免把巴西 90 分鐘勝壓太重，因為平局延長路徑在這場比法國場更實際。",
    },
    "mex-eng": {
        "confidence": "中低",
        "primary": "英格蘭 90 分鐘略優，但不是壓倒性熱門；晉級盤比 90 分鐘勝更適合當主軸。",
        "value": "小 2.5 / 小 3.5 與 Mexico +1.5 比單壓英格蘭更貼近盤口密集區。",
        "risk": "阿茲特克主場、高原與墨西哥防守節奏可能把比賽拖成 0-0 / 1-1。",
        "trigger": "若英格蘭晉級跌破 52% 或 Under 2.5 升過 64%，代表市場更偏五五波小球。",
        "avoid": "避免重壓英格蘭 90 分鐘勝或 England -1.5 選 ENG；這不是大勝盤。",
    },
}

for match in matches:
    match["detail"] = DETAILS[match["key"]]

PREMATCH_ROOM = {
    "can-mar": {
        "status": "預計先發，非官方確認；加拿大 Davies 是否先發仍是賽前變數。",
        "lineups": [
            {
                "team": "CAN",
                "name": "加拿大",
                "formation": "4-4-2",
                "source": "Al Jazeera / RotoWire",
                "players": [
                    ("GK", "Maxime Crepeau"),
                    ("DF", "Alistair Johnston, Moise Bombito, Derek Cornelius, Richie Laryea"),
                    ("MF", "Tajon Buchanan, Nathan Saliba, Stephen Eustaquio, Liam Millar"),
                    ("FW", "Tani Oluwaseyi, Jonathan David"),
                ],
                "notes": ["Ismael Kone 傷缺", "Davies 已恢復替補出場，是否改變左路配置需等賽前確認"],
            },
            {
                "team": "MAR",
                "name": "摩洛哥",
                "formation": "4-2-3-1",
                "source": "Al Jazeera / RotoWire",
                "players": [
                    ("GK", "Bono"),
                    ("DF", "Achraf Hakimi, Issa Diop, Chadi Riad, Noussair Mazraoui"),
                    ("DM", "Ayyoub Bouaddi, Neil El Aynaoui"),
                    ("AM", "Brahim Diaz, Azzedine Ounahi, Bilal El Khannouss"),
                    ("FW", "Ismael Saibari"),
                ],
                "notes": ["公開報導稱摩洛哥暫無主要傷病", "Saibari 是進攻核心，也是目前市場關注球員"],
            },
        ],
        "history": [
            ("加拿大世界盃脈絡", "2026 已創隊史：首度進入淘汰賽，並在 32 強靠 Eustaquio 補時進球淘汰南非。"),
            ("摩洛哥世界盃脈絡", "2022 第四名，成為第一支打進世界盃四強的非洲與阿拉伯球隊；1986 也曾成為第一支小組第一出線的非洲/阿拉伯隊。"),
            ("交手背景", "Al Jazeera 賽前統計：兩隊過去 4 次交手，摩洛哥 3 勝 1 和，加拿大尚未擊敗摩洛哥。"),
            ("2026 晉級路徑", "加拿大小組 4 分、32 強 1-0 南非；摩洛哥小組 7 分、32 強點球淘汰荷蘭。"),
        ],
        "key_players": [
            ("CAN", "Jonathan David", "ESPN scoreboard 列為加拿大本屆 3 球；若摩洛哥壓上，他是反擊第一落點。"),
            ("CAN", "Stephen Eustaquio", "32 強補時致勝，對加拿大中場節奏與定位球都關鍵。"),
            ("MAR", "Ismael Saibari", "Al Jazeera 指出他是摩洛哥 3 球射手，也踢進淘汰荷蘭的關鍵點球。"),
            ("MAR", "Achraf Hakimi", "右路推進與定位球威脅會直接考驗加拿大左路配置。"),
        ],
        "source_links": [
            ("Al Jazeera", "https://www.aljazeera.com/sports/2026/7/3/canada-morocco-fifa-world-cup-round-of-16-saibari-prediction-schedule"),
            ("RotoWire", "https://www.rotowire.com/soccer/article/canada-vs-morocco-preview-predicted-lineups-team-news-tactical-analysis-2026-world-cup-round-of-16-120851"),
            ("FIFA Canada profile", "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/canada-team-profile-history"),
            ("FIFA Morocco profile", "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/morocco-team-profile-history"),
        ],
    },
    "par-fra": {
        "status": "預計先發，法國左路 Barcola / Doue、後腰 Kone / Tchouameni 有不同媒體版本。",
        "lineups": [
            {
                "team": "PAR",
                "name": "巴拉圭",
                "formation": "4-4-2",
                "source": "SportsGambler / Action Network / VSiN",
                "players": [
                    ("GK", "Orlando Gill"),
                    ("DF", "Juan Caceres, Gustavo Gomez, Jose Maria Canale, Junior Alonso"),
                    ("MF", "Miguel Almiron, Andres Cubas, Damian Bobadilla, Diego Gomez / Matias Galarza"),
                    ("FW", "Julio Enciso, Gabriel Avalos / Matias Galarza"),
                ],
                "notes": ["Enciso 有傷情觀察但多數預測仍列先發", "Diego Gomez 解禁復出，可能改變中場配置"],
            },
            {
                "team": "FRA",
                "name": "法國",
                "formation": "4-2-3-1",
                "source": "SportsGambler / Action Network / VSiN",
                "players": [
                    ("GK", "Mike Maignan"),
                    ("DF", "Jules Kounde, William Saliba, Dayot Upamecano, Lucas Digne"),
                    ("CM", "Aurelien Tchouameni / Manu Kone, Adrien Rabiot"),
                    ("AM", "Ousmane Dembele, Michael Olise, Bradley Barcola / Desire Doue"),
                    ("FW", "Kylian Mbappe"),
                ],
                "notes": ["Mbappe 預計先發", "法國若要更穩，可能改三中場壓制巴拉圭反擊"],
            },
        ],
        "history": [
            ("巴拉圭世界盃脈絡", "2010 八強是隊史最佳；2026 是自 2010 後重返世界盃並再次打進淘汰賽。"),
            ("法國世界盃脈絡", "1998、2018 兩度奪冠；2006、2022 亞軍，是本屆盤口最強熱門之一。"),
            ("2026 晉級路徑", "巴拉圭點球淘汰德國；法國 32 強 3-0 瑞典，前場狀態與盤口都偏強。"),
            ("戰術核心", "巴拉圭靠低位防守與 Gill 撲救支撐，法國則靠 Mbappe、Olise、Dembele 的速度與肋部攻擊。"),
        ],
        "key_players": [
            ("PAR", "Orlando Gill", "VSiN 提到他對德國有高水準撲救與點球戰表現，是爆冷基礎。"),
            ("PAR", "Julio Enciso", "對德國進球，若健康先發，是巴拉圭最有威脅的前場點。"),
            ("FRA", "Kylian Mbappe", "法國核心射手；多個來源確認他預計先發。"),
            ("FRA", "Michael Olise / Ousmane Dembele", "兩側與中路串聯會決定法國能不能早段破低位。"),
        ],
        "source_links": [
            ("SportsGambler", "https://www.sportsgambler.com/betting-tips/football/paraguay-vs-france-prediction-lineups-odds-2026-07-04/"),
            ("Action Network", "https://www.actionnetwork.com/soccer/paraguay-vs-france-prediction-pick-odds-for-world-cup-saturday-july-4"),
            ("VSiN", "https://vsin.com/soccer/paraguay-vs-france-same-game-parlay-prediction-2026-fifa-world-cup-picks/"),
            ("FIFA France profile", "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/france-world-cup-team-profile-history"),
            ("FIFA Paraguay profile", "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/paraguay-profile-history"),
        ],
    },
    "bra-nor": {
        "status": "預計先發；巴西右路與中前場仍有媒體版本差異，挪威 4-3-3 較一致。",
        "lineups": [
            {
                "team": "BRA",
                "name": "巴西",
                "formation": "4-3-3",
                "source": "Tips.GG / SportsGambler",
                "players": [
                    ("GK", "Alisson Becker"),
                    ("DF", "Danilo, Marquinhos, Gabriel Magalhaes, Douglas Santos"),
                    ("MF", "Casemiro, Bruno Guimaraes, Lucas Paqueta"),
                    ("FW", "Vinicius Junior, Matheus Cunha, Rayan Simplicio"),
                ],
                "notes": ["Casemiro 是中場錨點，需注意累積黃牌風險", "Vinicius 與 Cunha 是主要進攻終結點"],
            },
            {
                "team": "NOR",
                "name": "挪威",
                "formation": "4-3-3",
                "source": "SportsGambler",
                "players": [
                    ("GK", "Orjan Haaskjold Nyland"),
                    ("DF", "Marcus Holmgren Pedersen, Kristoffer Vassbakk Ajer, Torbjorn Lysaker Heggem, David Moller Wolfe"),
                    ("MF", "Martin Odegaard, Sander Berge, Patrick Berg"),
                    ("FW", "Alexander Sorloth, Erling Haaland, Antonio Nusa"),
                ],
                "notes": ["Haaland 與 Sorloth 提供禁區壓迫", "Odegaard 是由守轉攻第一拍"],
            },
        ],
        "history": [
            ("巴西世界盃脈絡", "五冠與全勤參賽底蘊仍是最大品牌優勢；2026 小組/32 強進攻火力穩。"),
            ("挪威世界盃脈絡", "FIFA 指出挪威睽違 28 年重返世界盃，Haaland 在資格賽火力強勢。"),
            ("特殊交手背景", "11v11 統計：挪威對巴西 2 勝 2 和，巴西正式與友誼賽都尚未擊敗挪威。"),
            ("2026 近況", "SportsGambler 記錄巴西 2-1 日本晉級；挪威 2-1 象牙海岸晉級。"),
        ],
        "key_players": [
            ("BRA", "Vinicius Junior", "巴西邊路爆點，若早段製造一對一優勢，會削弱挪威反擊出球。"),
            ("BRA", "Casemiro", "攻守轉換與二點球關鍵；Tips.GG 特別提醒黃牌風險。"),
            ("NOR", "Erling Haaland", "禁區終結能力是 BTTS Yes 與巴西失球風險的核心原因。"),
            ("NOR", "Martin Odegaard", "挪威能否把低位防守轉成有效進攻，取決於他的第一腳傳導。"),
        ],
        "source_links": [
            ("SportsGambler", "https://www.sportsgambler.com/betting-tips/football/brazil-vs-norway-prediction-lineups-odds-2026-07-05/"),
            ("Tips.GG", "https://tips.gg/article/brazil-vs-norway-05-07-2026/"),
            ("FIFA Norway profile", "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/norway-team-profile-history"),
            ("FIFA Brazil profile", "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/brazil-team-profile-history"),
            ("11v11 H2H", "https://www.11v11.com/teams/norway/tab/opposingTeams/opposition/Brazil/"),
        ],
    },
    "mex-eng": {
        "status": "預計先發，非官方確認；英格蘭需處理墨西哥主場高原與低節奏壓迫。",
        "lineups": [
            {
                "team": "MEX",
                "name": "墨西哥",
                "formation": "4-3-3",
                "source": "Racing Post / SportsGambler",
                "players": [
                    ("GK", "Raul Rangel"),
                    ("DF", "Jorge Sanchez, Cesar Montes, Johan Vasquez, Jesus Gallardo"),
                    ("MF", "Gilberto Mora, Erik Lira, Luis Romo"),
                    ("FW", "Roberto Alvarado, Raul Jimenez, Julian Quinones"),
                ],
                "notes": ["主場高原與慢節奏是最大環境優勢", "Jimenez 與 Alvarado 是反擊和禁區終結重點"],
            },
            {
                "team": "ENG",
                "name": "英格蘭",
                "formation": "4-2-3-1",
                "source": "Racing Post / SportsGambler",
                "players": [
                    ("GK", "Jordan Pickford"),
                    ("DF", "Djed Spence, Ezri Konsa, Marc Guehi, Nico O'Reilly"),
                    ("CM", "Elliot Anderson, Declan Rice"),
                    ("AM", "Bukayo Saka, Jude Bellingham, Anthony Gordon"),
                    ("FW", "Harry Kane"),
                ],
                "notes": ["Kane 是進球盤核心，但價格不便宜", "Rice 與 Bellingham 需要控制高原下的攻守節奏"],
            },
        ],
        "history": [
            ("墨西哥主場脈絡", "Guardian 與多家預覽都把阿茲特克高原視為英格蘭最大外部變數。"),
            ("防守近況", "外部預覽指出墨西哥本屆防守數據強，這支撐小球與受讓路徑。"),
            ("英格蘭狀態", "英格蘭紙面實力仍高，但市場只給小熱門，表示莊家沒有把它定成碾壓盤。"),
            ("盤口結構", "Binance 目前小 3.5 明顯偏熱，小 2.5 也在多數方，比分盤集中 1-1、0-1、1-0、0-0。"),
        ],
        "key_players": [
            ("MEX", "Raul Jimenez", "禁區支點和定位球威脅，若墨西哥要爆冷通常需要他參與終結。"),
            ("MEX", "Gilberto Mora", "中場串接與節奏控制，是墨西哥把比賽拖慢的關鍵。"),
            ("ENG", "Harry Kane", "英格蘭最穩定終結點，也是 Kane 進球盤定價偏熱的主因。"),
            ("ENG", "Jude Bellingham", "英格蘭打破低位和高原慢節奏的主要推進點。"),
        ],
        "source_links": [
            ("SportsGambler", "https://www.sportsgambler.com/betting-tips/football/mexico-vs-england-prediction-lineups-odds-2026-07-05/"),
            ("Racing Post", "https://www.racingpost.com/sport/football-tips/world-cup-2026/mexico-vs-england-world-cup-prediction-team-news-odds-betting-tips-and-bet-builder-axk4R2P3FCRE/"),
            ("The Guardian", "https://www.theguardian.com/football/2026/jul/04/mexico-england-world-cup-2026-pace-football-altitude"),
            ("ESPN", "https://www.espn.com/soccer/story/_/id/49260461/how-england-overcome-mexico-altitude-world-cup-round-16"),
        ],
    },
}

for match in matches:
    match["prematch_room"] = PREMATCH_ROOM[match["key"]]

MONITOR_STATE_PATH = WORK / "worldcup-r16-monitor-state.json"


def load_monitor_state():
    if not MONITOR_STATE_PATH.exists():
        return {"matches": {}}
    try:
        return json.loads(MONITOR_STATE_PATH.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {"matches": {}}


def monitor_item(monitor_state, match):
    return monitor_state.get("matches", {}).get(match["key"], {})


def display_value(value, fallback="尚未更新"):
    return fallback if value in (None, "") else str(value)


def phase_for_match(match, item, now):
    if item.get("completed") or item.get("status") == "finished" or item.get("espnState") == "post":
        return "已完賽"
    if item.get("espnState") == "in":
        return "賽中"
    if now < match["time"]:
        return "賽前"
    if now < match["time"] + timedelta(minutes=150):
        return "賽中 / 待比分確認"
    return "賽後確認中"


def next_rule_for_phase(phase):
    if phase == "已完賽":
        return "停止抓取"
    if "賽中" in phase:
        return "每 5 分鐘"
    return "每 30 分鐘"


def is_completed_match(match):
    item = monitor_item(monitor_state, match)
    return bool(item.get("completed") or item.get("status") == "finished" or item.get("espnState") == "post")


def is_active_deep_match(match, now):
    item = monitor_item(monitor_state, match)
    if is_completed_match(match):
        return False
    if item.get("espnState") == "in":
        return True
    starts_in = match["time"] - now
    return timedelta(0) <= starts_in <= timedelta(hours=24)


generated_at = datetime.now(TPE)
monitor_state = load_monitor_state()

snapshot_path = OUT / "worldcup-r16-tabs-snapshot.csv"
with snapshot_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["match", "taiwan_time", "market", "price", "chance", "note"])
    for m in matches:
        for label, outcome in m["main"] + m["markets"]:
            writer.writerow([m["title"], m["time"].strftime("%Y-%m-%d %H:%M"), label, price(outcome), chance(outcome), m["subtitle"]])


def monitor_table(matches, monitor_state, now):
    rows = []
    for m in matches:
        item = monitor_item(monitor_state, m)
        phase = phase_for_match(m, item, now)
        summary = item.get("resultSummary") or item.get("note") or "尚無賽後總結"
        rows.append(
            "<tr>"
            f"<td>{safe(m['title'])}</td>"
            f"<td>{safe(phase)}</td>"
            f"<td>{safe(display_value(item.get('scoreDisplay'), '0-0 / 未開賽'))}</td>"
            f"<td>{safe(display_value(item.get('espnStatus')))}</td>"
            f"<td>{safe(display_value(item.get('lastOddsUpdate')))}</td>"
            f"<td>{safe(display_value(item.get('lastScoreCheck')))}</td>"
            f"<td>{safe(next_rule_for_phase(phase))}</td>"
            f"<td>{safe(summary)}</td>"
            "</tr>"
        )
    return "".join(rows)


def format_live_status(item, phase):
    score = display_value(item.get("scoreDisplay"), "0-0 / 未開賽")
    status = display_value(item.get("espnStatus"), phase)
    clock = item.get("clock")
    return f"{score} · {clock or status}"


def live_event_icon(event):
    if event.get("redCard"):
        return "RC"
    if event.get("yellowCard"):
        return "YC"
    if event.get("scoringPlay"):
        return "G"
    if event.get("penaltyKick"):
        return "PK"
    return "EV"


def live_event_rows(item, compact=False):
    events = item.get("liveEvents") or []
    if not events:
        return "<p class='muted-note'>目前尚無進球、紅黃牌或重要事件。</p>"
    selected = events[-6:] if compact else events[-14:]
    return "".join(
        "<div class='event-row'>"
        f"<span class='event-time'>{safe(event.get('time') or '-')}</span>"
        f"<span class='event-icon {'card-red' if event.get('redCard') else 'card-yellow' if event.get('yellowCard') else 'goal' if event.get('scoringPlay') else ''}'>{safe(live_event_icon(event))}</span>"
        f"<div><b>{safe(event.get('team') or '')} {safe(event.get('type') or '')}</b><p>{safe(event.get('player') or event.get('rawType') or '')}</p></div>"
        "</div>"
        for event in selected
    )


def live_stat_table(item):
    stats = item.get("liveStats") or {}
    rows = stats.get("rows") or []
    teams = stats.get("teams") or []
    if not rows or len(teams) < 2:
        message = "技術統計會在 ESPN 提供後顯示，通常開賽後才會更新。"
        if stats.get("sourceError"):
            message = f"技術統計暫時抓不到：{stats.get('sourceError')}"
        return f"<p class='muted-note'>{safe(message)}</p>"
    body = "".join(
        "<tr>"
        f"<td>{safe(row.get('label'))}</td>"
        + "".join(f"<td>{safe((row.get('values') or {}).get(team, '-'))}</td>" for team in teams[:2])
        + "</tr>"
        for row in rows
    )
    head = "".join(f"<th>{safe(team)}</th>" for team in teams[:2])
    return f"<table><thead><tr><th>項目</th>{head}</tr></thead><tbody>{body}</tbody></table>"


def card_count_line(item):
    counts = item.get("cardCounts") or {}
    parts = []
    for team, values in counts.items():
        yellow = (values or {}).get("yellow", 0)
        red = (values or {}).get("red", 0)
        parts.append(f"{team} 黃 {yellow} / 紅 {red}")
    return " · ".join(parts) if parts else "紅黃牌統計待開賽"


def live_center_cards(matches, monitor_state, now):
    cards = []
    for match in matches:
        item = monitor_item(monitor_state, match)
        phase = phase_for_match(match, item, now)
        is_live = "賽中" in phase or phase in {"已完賽", "賽後確認中"}
        cards.append(
            f"""
            <article class="live-card {'is-live' if is_live else ''}">
              <div class="live-card-head">
                <div>
                  <span class="tile-phase">{safe(phase)}</span>
                  <h3>{safe(match['title'])}</h3>
                  <p>{safe(match['time'].strftime('%m/%d %H:%M'))} 台灣 · {safe(display_value(item.get('espnStatus'), 'Scheduled'))}</p>
                </div>
                <strong>{safe(display_value(item.get('scoreDisplay'), '0-0'))}</strong>
              </div>
              <div class="live-meta-line">{safe(card_count_line(item))}</div>
              <div class="mini-events">{live_event_rows(item, compact=True)}</div>
            </article>
            """
        )
    return "".join(cards)


def live_match_panel(match):
    item = monitor_item(monitor_state, match)
    phase = phase_for_match(match, item, generated_at)
    return f"""
      <div class="section-title sub"><h2>即時資訊</h2><span>{safe(format_live_status(item, phase))}</span></div>
      <div class="live-detail-grid">
        <div class="table-card live-events">
          <h3>事件時間線</h3>
          {live_event_rows(item)}
        </div>
        <div class="table-card live-stats">
          <h3>技術統計</h3>
          {live_stat_table(item)}
          <p class="odds-note">更新時間：{safe(display_value(item.get('liveDataUpdatedAt')))}</p>
        </div>
      </div>
    """


def insight_cards(match):
    detail = match["detail"]
    items = [
        ("信心", detail["confidence"]),
        ("主軸", detail["primary"]),
        ("價格品質", detail["value"]),
        ("主要風險", detail["risk"]),
    ]
    return "".join(
        f"<div class='insight-card'><h3>{safe(title)}</h3><p>{safe(text)}</p></div>"
        for title, text in items
    )


def detail_points(match):
    detail = match["detail"]
    rows = [
        ("臨場觀察", detail["trigger"]),
        ("不要重複曝險", detail["avoid"]),
        ("比分密集區", "精確比分前段若集中在 1 球差或平局，讓球盤就要更保守；若 0-2 / 0-3 類比分升高，讓球與零封才更有價值。"),
        ("盤口驗算", "Binance 的價格代表市場隱含機率。價格越低，命中後返還越少；不是熱門就一定值得下。"),
    ]
    return "".join(
        "<tr>"
        f"<td>{safe(label)}</td><td>{safe(text)}</td>"
        "</tr>"
        for label, text in rows
    )


def stake_calculator(match):
    rows = []
    for name, stake, p in match["allocation"]:
        rows.append(
            "<tr "
            f"data-base='{stake}' data-price='{p:.6f}'>"
            f"<td>{safe(name)}</td>"
            f"<td class='calc-stake'>{stake:.2f}U</td>"
            f"<td>{p:.2f}</td>"
            f"<td class='calc-return'>{ret(stake, p):.2f}U</td>"
            f"<td class='calc-profit good'>+{profit(stake, p):.2f}U</td>"
            "</tr>"
        )
    return (
        "<div class='stake-calc'>"
        "<label>總下注 U <input class='calc-input' type='number' value='100' min='0' step='5'></label>"
        "<table><thead><tr><th>項目</th><th>下注</th><th>價格</th><th>命中返還</th><th>淨利</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "</div>"
    )


TEAM_NAME_ALIASES = {
    "can-mar": {"加拿大": "CAN", "摩洛哥": "MAR"},
    "par-fra": {"巴拉圭": "PAR", "法國": "FRA"},
    "bra-nor": {"巴西": "BRA", "挪威": "NOR"},
    "mex-eng": {"墨西哥": "MEX", "英格蘭": "ENG", "Mexico": "MEX", "England": "ENG"},
}

TEAM_INFO = {
    "CAN": {"name": "加拿大", "flag": "🇨🇦"},
    "MAR": {"name": "摩洛哥", "flag": "🇲🇦"},
    "PAR": {"name": "巴拉圭", "flag": "🇵🇾"},
    "FRA": {"name": "法國", "flag": "🇫🇷"},
    "BRA": {"name": "巴西", "flag": "🇧🇷"},
    "NOR": {"name": "挪威", "flag": "🇳🇴"},
    "MEX": {"name": "墨西哥", "flag": "🇲🇽"},
    "ENG": {"name": "英格蘭", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "POR": {"name": "葡萄牙", "flag": "🇵🇹"},
    "ESP": {"name": "西班牙", "flag": "🇪🇸"},
    "USA": {"name": "美國", "flag": "🇺🇸"},
    "BEL": {"name": "比利時", "flag": "🇧🇪"},
    "ARG": {"name": "阿根廷", "flag": "🇦🇷"},
    "EGY": {"name": "埃及", "flag": "🇪🇬"},
    "SUI": {"name": "瑞士", "flag": "🇨🇭"},
    "CHE": {"name": "瑞士", "flag": "🇨🇭"},
    "COL": {"name": "哥倫比亞", "flag": "🇨🇴"},
}

ENGLISH_TEAM_ALIASES = {
    "Brazil": "BRA",
    "Norway": "NOR",
    "Mexico": "MEX",
    "England": "ENG",
    "France": "FRA",
    "Paraguay": "PAR",
    "Canada": "CAN",
    "Morocco": "MAR",
}


def parse_match_score(match, item=None):
    item = item or monitor_item(monitor_state, match)
    text = item.get("scoreDisplay") or ""
    scores = {}
    for team in match["teams"]:
        found = re.search(rf"\b{re.escape(team)}\s+(\d+)\b", text)
        if found:
            scores[team] = int(found.group(1))
    return scores if len(scores) == len(match["teams"]) else None


def team_from_bet_label(match, label):
    team = team_code_from_text(match, label)
    if team:
        return team
    return None


def team_code_from_text(match, text):
    for name, team in TEAM_NAME_ALIASES.get(match["key"], {}).items():
        if name in text:
            return team
    for team in match["teams"]:
        if re.search(rf"\b{re.escape(team)}\b", text):
            return team
    for name, team in ENGLISH_TEAM_ALIASES.items():
        if name in text and team in match["teams"]:
            return team
    return None


def opposite_team(match, team):
    return next((candidate for candidate in match["teams"] if candidate != team), None)


def evaluate_bet(match, label, scores, item):
    if not scores:
        return None, "尚未取得完整比分"
    total_goals = sum(scores.values())

    if "BTTS Yes" in label:
        return all(score > 0 for score in scores.values()), "兩隊是否都有進球"
    if "BTTS No" in label:
        return not all(score > 0 for score in scores.values()), "兩隊沒有同時進球"

    total_match = re.search(r"(小|大)\s*(\d+(?:\.\d+)?)", label)
    if total_match:
        direction, line_text = total_match.groups()
        line = float(line_text)
        if direction == "小":
            return total_goals < line, f"總進球 {total_goals}，小於 {line_text}"
        return total_goals > line, f"總進球 {total_goals}，大於 {line_text}"

    selected_spread = re.search(r"(.+?)\s*(-\d+(?:\.\d+)?)\s*選\s*(.+)", label)
    if selected_spread:
        market_text, line_text, selected_text = selected_spread.groups()
        market_team = team_code_from_text(match, market_text)
        selected_team = team_code_from_text(match, selected_text)
        opponent = opposite_team(match, market_team)
        if not market_team or not selected_team or not opponent:
            return None, "讓球選項隊伍無法判定"
        line = abs(float(line_text))
        margin = scores.get(market_team, 0) - scores.get(opponent, 0)
        if selected_team == market_team:
            return margin > line, f"{market_team} -{line:g}：{market_team} 淨勝 {margin} 球"
        return margin <= line, f"{market_team} -{line:g} 選 {selected_team}：{market_team} 淨勝 {margin} 球，未超過 {line:g} 才命中"

    spread_match = re.search(r"(-\d+(?:\.\d+)?)", label)
    if spread_match:
        team = team_from_bet_label(match, label)
        opponent = opposite_team(match, team)
        if not team or not opponent:
            return None, "讓球隊伍無法判定"
        line = abs(float(spread_match.group(1)))
        margin = scores.get(team, 0) - scores.get(opponent, 0)
        return margin > line, f"{team} 淨勝 {margin} 球，門檻 {line:g}"

    if "晉級" in label:
        team = team_from_bet_label(match, label)
        winner = item.get("winner")
        if winner:
            return winner == team, f"ESPN 勝方/晉級方：{winner}"
        opponent = opposite_team(match, team)
        if team and opponent and scores[team] != scores[opponent]:
            return scores[team] > scores[opponent], "以完賽比分推定晉級"
        return None, "平手或延長/PK，需以 Binance 結算為準"

    if "90 分鐘勝" in label:
        team = team_from_bet_label(match, label)
        opponent = opposite_team(match, team)
        if not team or not opponent:
            return None, "90 分鐘隊伍無法判定"
        return scores[team] > scores[opponent], "以 ESPN 完賽比分初判；若有延長/PK，90 分鐘盤需人工確認"

    return None, "此盤口尚未建立自動判定"


def settlement_data(match):
    item = monitor_item(monitor_state, match)
    completed = bool(item.get("completed") or item.get("status") == "finished")
    scores = parse_match_score(match, item)
    rows = []
    total_stake = sum(stake for _, stake, _ in match["allocation"])
    total_return = 0.0
    total_net = 0.0
    pending = 0

    for name, stake, p in match["allocation"]:
        if not completed:
            rows.append((name, stake, p, "待結算", None, None, "soft", "比賽尚未完賽"))
            pending += 1
            continue

        won, note = evaluate_bet(match, name, scores, item)
        if won is None:
            rows.append((name, stake, p, "待確認", None, None, "soft", note))
            pending += 1
            continue

        returned = ret(stake, p) if won else 0.0
        net = returned - stake
        total_return += returned
        total_net += net
        rows.append((name, stake, p, "命中" if won else "未中", returned, net, "good" if won else "bad", note))

    if not completed:
        verdict = "待結算"
        verdict_class = "soft"
        headline = "比賽尚未完賽，先保留 100U 建議組合。"
    elif pending:
        verdict = "部分待確認"
        verdict_class = "warn"
        headline = f"已完賽，但有 {pending} 張涉及晉級/90 分鐘規則需以 Binance 結算確認。"
    else:
        verdict = f"{total_net:+.2f}U"
        verdict_class = "good" if total_net >= 0 else "bad"
        headline = f"100U 組合結算淨利 {total_net:+.2f}U，總返還 {total_return:.2f}U。"

    return {
        "item": item,
        "completed": completed,
        "scores": scores,
        "rows": rows,
        "stake": total_stake,
        "return": total_return,
        "net": total_net,
        "pending": pending,
        "verdict": verdict,
        "verdict_class": verdict_class,
        "headline": headline,
    }


def settlement_table(match):
    data = settlement_data(match)
    body = []
    for name, stake, p, state, returned, net, cls, note in data["rows"]:
        return_text = "—" if returned is None else f"{returned:.2f}U"
        net_text = "—" if net is None else f"{net:+.2f}U"
        body.append(
            "<tr>"
            f"<td>{safe(name)}</td>"
            f"<td>{stake:.0f}U</td>"
            f"<td>{p:.2f}</td>"
            f"<td><span class='status-chip {safe(cls)}'>{safe(state)}</span></td>"
            f"<td>{return_text}</td>"
            f"<td class='{safe(cls)}'>{net_text}</td>"
            f"<td>{safe(note)}</td>"
            "</tr>"
        )
    score = display_value(data["item"].get("scoreDisplay"), "待確認")
    updated = display_value(data["item"].get("lastScoreCheck") or data["item"].get("liveDataUpdatedAt"), "尚未更新")
    return f"""
      <div class="settlement-detail">
        <div class="settlement-head">
          <div>
            <span class="panel-label">100U 結算</span>
            <h3>{safe(match['title'])}</h3>
            <p>目前比分：{safe(score)} · 狀態：{safe(phase_for_match(match, data['item'], generated_at))} · 更新 {safe(updated)}</p>
          </div>
          <strong class="{safe(data['verdict_class'])}">{safe(data['verdict'])}</strong>
        </div>
        <p class="settlement-note">{safe(data['headline'])}</p>
        <div class="settlement-table-wrap">
          <table>
            <thead><tr><th>項目</th><th>下注</th><th>價格</th><th>狀態</th><th>返還</th><th>淨利</th><th>判定依據</th></tr></thead>
            <tbody>{''.join(body)}</tbody>
          </table>
        </div>
      </div>
    """


def settlement_overview_cards(matches):
    cards = []
    combined_net = 0.0
    completed_count = 0
    for match in matches:
        data = settlement_data(match)
        if data["completed"] and not data["pending"]:
            combined_net += data["net"]
            completed_count += 1
        score = display_value(data["item"].get("scoreDisplay"), "待確認")
        cards.append(
            "<article class='settlement-card'>"
            f"<div><span class='panel-label'>100U 組合</span><h3>{safe(match['title'])}</h3></div>"
            f"<strong class='{safe(data['verdict_class'])}'>{safe(data['verdict'])}</strong>"
            f"<p>{safe(score)} · {safe(data['headline'])}</p>"
            f"<button type='button' class='settlement-jump' data-tab='{safe(match['key'])}'>看逐單明細</button>"
            "</article>"
        )
    if completed_count:
        summary = f"已完整結算 {completed_count} 場，累計淨利 {combined_net:+.2f}U。"
    else:
        summary = "目前尚無完整完賽場次，會在比賽結束後自動換算。"
    return summary, "".join(cards)


TEAM_COLORS = {
    "CAN": ("#d71920", "#ffffff"),
    "MAR": ("#0b8f4d", "#ffffff"),
    "PAR": ("#d71920", "#ffffff"),
    "FRA": ("#1d4ed8", "#ffffff"),
    "BRA": ("#facc15", "#12351c"),
    "NOR": ("#ba0c2f", "#ffffff"),
    "MEX": ("#006847", "#ffffff"),
    "ENG": ("#ffffff", "#1f2937"),
    "POR": ("#006847", "#ffffff"),
    "PRT": ("#006847", "#ffffff"),
    "ESP": ("#f1bf00", "#7f1d1d"),
    "USA": ("#1d4ed8", "#ffffff"),
    "BEL": ("#111827", "#facc15"),
    "ARG": ("#75aadb", "#102a43"),
    "EGY": ("#ce1126", "#ffffff"),
    "SUI": ("#d52b1e", "#ffffff"),
    "CHE": ("#d52b1e", "#ffffff"),
    "COL": ("#facc15", "#1e3a8a"),
}


def badge(team):
    bg, fg = TEAM_COLORS.get(team, ("#334155", "#ffffff"))
    return f"<span class='team-badge' style='--team-bg:{bg};--team-fg:{fg}'>{safe(team)}</span>"


EXTRA_MATCH_META = [
    {
        "key": "mex-eng",
        "title": "墨西哥 vs 英格蘭",
        "topic": "Mexico vs. England",
        "file": "binance-mexico-england-topics.json",
        "time": "2026-07-06T08:00:00+08:00",
        "venue": "Estadio Banorte",
        "teams": ("MEX", "ENG"),
        "subtitle": "英格蘭小熱門，但墨西哥晉級盤咬得很近",
        "main": [("英格蘭 90 分鐘勝", "ENG"), ("90 分鐘平局", "Draw"), ("墨西哥 90 分鐘勝", "MEX")],
        "advance": ("ENG", "MEX"),
    },
    {
        "key": "por-esp",
        "title": "葡萄牙 vs 西班牙",
        "topic": "Portugal vs. Spain",
        "file": "binance-portugal-spain-topics.json",
        "time": "2026-07-07T03:00:00+08:00",
        "venue": "AT&T Stadium",
        "teams": ("POR", "ESP"),
        "subtitle": "西班牙偏熱門，BTTS 與大 2.5 都有支撐",
        "main": [("西班牙 90 分鐘勝", "ESP"), ("90 分鐘平局", "Draw"), ("葡萄牙 90 分鐘勝", "PRT")],
        "advance": ("ESP", "PRT"),
    },
    {
        "key": "usa-bel",
        "title": "美國 vs 比利時",
        "topic": "United States vs. Belgium",
        "file": "binance-usa-belgium-topics.json",
        "time": "2026-07-07T08:00:00+08:00",
        "venue": "Lumen Field",
        "teams": ("USA", "BEL"),
        "subtitle": "90 分鐘偏比利時，晉級盤幾乎五五波",
        "main": [("比利時 90 分鐘勝", "BEL"), ("美國 90 分鐘勝", "USA"), ("90 分鐘平局", "Draw")],
        "advance": ("USA", "BEL"),
    },
    {
        "key": "arg-egy",
        "title": "阿根廷 vs 埃及",
        "topic": "Argentina vs. Egypt",
        "file": "binance-argentina-egypt-topics.json",
        "time": "2026-07-08T00:00:00+08:00",
        "venue": "Mercedes-Benz Stadium",
        "teams": ("ARG", "EGY"),
        "subtitle": "阿根廷重熱門，讓球與小 3.5 是後續觀察點",
        "main": [("阿根廷 90 分鐘勝", "ARG"), ("90 分鐘平局", "Draw"), ("埃及 90 分鐘勝", "EGY")],
        "advance": ("ARG", "EGY"),
    },
    {
        "key": "sui-col",
        "title": "瑞士 vs 哥倫比亞",
        "topic": "Switzerland vs. Colombia",
        "file": "binance-switzerland-colombia-topics.json",
        "time": "2026-07-08T04:00:00+08:00",
        "venue": "BC Place",
        "teams": ("SUI", "COL"),
        "subtitle": "哥倫比亞小熱門，小球與 1-1 密集度高",
        "main": [("哥倫比亞 90 分鐘勝", "COL"), ("90 分鐘平局", "Draw"), ("瑞士 90 分鐘勝", "CHE")],
        "advance": ("COL", "CHE"),
    },
]


def lineup_rows(lineup):
    return "".join(
        "<div class='line-row'>"
        f"<span>{safe(pos)}</span><p>{safe(names)}</p>"
        "</div>"
        for pos, names in lineup["players"]
    )


def lineup_notes(lineup):
    return "".join(f"<li>{safe(note)}</li>" for note in lineup.get("notes", []))


def lineup_boards(match):
    boards = []
    for lineup in match["prematch_room"]["lineups"]:
        boards.append(
            "<div class='lineup-board'>"
            "<div class='lineup-top'>"
            f"{badge(lineup['team'])}"
            "<div>"
            f"<h3>{safe(lineup['name'])}</h3>"
            f"<p>{safe(lineup['formation'])} · {safe(lineup['source'])}</p>"
            "</div>"
            "</div>"
            f"{lineup_rows(lineup)}"
            f"<ul class='lineup-notes'>{lineup_notes(lineup)}</ul>"
            "</div>"
        )
    return "".join(boards)


def history_items(match):
    return "".join(
        "<div class='fact-line'>"
        f"<b>{safe(label)}</b>"
        f"<p>{safe(text)}</p>"
        "</div>"
        for label, text in match["prematch_room"]["history"]
    )


def key_player_rows(match):
    return "".join(
        "<tr>"
        f"<td>{badge(team)}</td><td><b>{safe(player)}</b></td><td>{safe(read)}</td>"
        "</tr>"
        for team, player, read in match["prematch_room"]["key_players"]
    )


def room_source_links(match):
    return " ".join(
        f"<a href='{safe(url)}' target='_blank' rel='noopener'>{safe(name)}</a>"
        for name, url in match["prematch_room"]["source_links"]
    )


def prematch_room(match):
    room = match["prematch_room"]
    return f"""
      <div class="section-title sub"><h2>賽前資料室</h2><span>{safe(room['status'])}</span></div>
      <div class="data-room">
        <div class="lineup-grid">
          {lineup_boards(match)}
        </div>
        <div class="history-room">
          <div class="history-panel">
            <h3>歷史與晉級脈絡</h3>
            {history_items(match)}
          </div>
          <div class="table-card key-table">
            <h3>關鍵球員</h3>
            <table><thead><tr><th>隊</th><th>球員</th><th>觀察重點</th></tr></thead><tbody>{key_player_rows(match)}</tbody></table>
          </div>
        </div>
        <p class="source-note">資料來源：{room_source_links(match)}。先發為公開媒體預測，正式名單仍以賽前確認為準。</p>
      </div>
    """


def load_topics_if_exists(filename):
    path = OUT / filename
    if not path.exists():
        return []
    return load_json(path)


def find_topic_opt(topics, title):
    return next((item for item in topics if item.get("title") == title), None)


def find_market_opt(topic_obj, title):
    if not topic_obj:
        return None
    return next((item for item in topic_obj.get("markets", []) if item.get("title") == title), None)


def find_outcome_opt(market_obj, name):
    if not market_obj:
        return None
    return next((item for item in market_obj.get("outcomes", []) if item.get("name") == name), None)


def out_opt(topics, topic_title, market_title, outcome_name):
    return find_outcome_opt(find_market_opt(find_topic_opt(topics, topic_title), market_title), outcome_name)


def best_side(topic, market_title):
    market = find_market_opt(topic, market_title)
    if not market:
        return None
    outcomes = [o for o in market.get("outcomes", []) if as_float(o.get("chance")) is not None]
    if not outcomes:
        return None
    return max(outcomes, key=lambda o: chance(o))


def compact_exact_scores(topic, count=5):
    if not topic:
        return []
    scores = []
    for market in topic.get("markets", []):
        yes = find_outcome_opt(market, "Yes")
        if yes and as_float(yes.get("chance")) is not None:
            scores.append((market.get("title"), chance(yes), price(yes)))
    return sorted(scores, key=lambda item: item[1], reverse=True)[:count]


def build_extra_matches():
    built = []
    deep_match_keys = {match["key"] for match in matches}
    for meta in EXTRA_MATCH_META:
        if meta["key"] in deep_match_keys:
            continue
        topics = load_topics_if_exists(meta["file"])
        main_topic = find_topic_opt(topics, meta["topic"])
        more_topic = find_topic_opt(topics, f"{meta['topic']} - More Markets")
        exact_topic = find_topic_opt(topics, f"{meta['topic']} - Exact Score")
        corners_topic = find_topic_opt(topics, f"{meta['topic']} - Total Corners")
        main_rows = []
        for label, market_name in meta["main"]:
            outcome = out_opt(topics, meta["topic"], market_name, "Yes")
            if outcome:
                main_rows.append((label, outcome))

        selected = []
        if more_topic:
            advance_market = find_market_opt(more_topic, "Team to Advance")
            advance_outcomes = [find_outcome_opt(advance_market, name) for name in meta["advance"]]
            advance_outcomes = [o for o in advance_outcomes if o]
            if advance_outcomes:
                best = max(advance_outcomes, key=lambda o: chance(o))
                selected.append(("晉級", best))

            for market_title, label in [("O/U 2.5", "大小 2.5"), ("O/U 3.5", "大小 3.5"), ("Both Teams to Score", "BTTS")]:
                best = best_side(more_topic, market_title)
                if best:
                    selected.append((f"{label}: {best.get('name')}", best))

        if corners_topic:
            first_market = (corners_topic.get("markets") or [None])[0]
            if first_market:
                best = max(first_market.get("outcomes", []), key=lambda o: chance(o))
                selected.append((f"角球: {best.get('name')}", best))

        liquidity = as_float(main_topic.get("liquidity")) if main_topic else None
        volume = as_float(main_topic.get("tradeVolume")) if main_topic else None
        quality = "正常觀察"
        if liquidity is None:
            quality = "未抓到 Binance 主盤"
        elif liquidity < 500000:
            quality = "低流動性，先看方向不下結論"
        elif volume is not None and volume < 10000:
            quality = "成交量偏低，後續需重抓"

        built.append(
            {
                **meta,
                "time": datetime.fromisoformat(meta["time"]),
                "topics": topics,
                "main_topic": main_topic,
                "more_topic": more_topic,
                "main": main_rows,
                "selected": selected,
                "exact": compact_exact_scores(exact_topic),
                "liquidity": liquidity,
                "volume": volume,
                "quality": quality,
            }
        )
    return built


def selected_market_chips(extra):
    if not extra["selected"]:
        return "<p class='muted-note'>尚未抓到延伸盤。</p>"
    return "".join(
        f"<span class='market-chip'><b>{safe(label)}</b><em>{pct(outcome):.1f}% / 價格 {price(outcome):.2f}</em></span>"
        for label, outcome in extra["selected"][:5]
    )


def exact_score_chips(extra):
    if not extra["exact"]:
        return "<span class='tiny-chip'>尚無比分盤</span>"
    return "".join(
        f"<span class='tiny-chip'>{safe(label)} · {chance_value * 100:.1f}%</span>"
        for label, chance_value, _ in extra["exact"][:5]
    )


def radar_cards(extra_matches):
    cards = []
    for extra in extra_matches:
        item = monitor_item(monitor_state, extra)
        phase = phase_for_match(extra, item, generated_at)
        main_html = market_bars(extra["main"]) if extra["main"] else "<p class='muted-note'>尚未抓到 Binance 90 分鐘勝平負。</p>"
        odds_note = espn_odds_note(extra)
        liquidity = "N/A" if extra["liquidity"] is None else f"{extra['liquidity']:,.0f}"
        volume = "N/A" if extra["volume"] is None else f"{extra['volume']:,.0f}"
        cards.append(
            f"""
            <article class="radar-card">
              <div class="radar-head">
                <div>
                  <span class="tile-phase">{safe(phase)}</span>
                  <h3>{safe(extra['title'])}</h3>
                  <p>{safe(extra['time'].strftime('%Y-%m-%d %H:%M'))} 台灣時間 · {safe(extra['venue'])}</p>
                </div>
                <div class="radar-teams">{badge(extra['teams'][0])}<b>vs</b>{badge(extra['teams'][1])}</div>
              </div>
              <p class="radar-subtitle">{safe(extra['subtitle'])}</p>
              <div class="radar-main">{main_html}</div>
              <div class="market-chip-row">{selected_market_chips(extra)}</div>
              <div class="exact-strip">{exact_score_chips(extra)}</div>
              <div class="radar-meta">
                <span>Binance liquidity: {safe(liquidity)}</span>
                <span>Volume: {safe(volume)}</span>
                <span>{safe(extra['quality'])}</span>
              </div>
              <p class="odds-note">ESPN 參考盤：{safe(odds_note)}</p>
            </article>
            """
        )
    return "".join(cards)


def espn_odds_note(match):
    item = monitor_item(monitor_state, match)
    odds = item.get("espnOdds")
    if not odds:
        return "ESPN / DraftKings 盤口尚未寫入本地狀態；下一次監控抓取後會補上。"
    parts = []
    for key, label in [("moneyline", "1X2"), ("spread", "讓球"), ("total", "大小")]:
        if odds.get(key):
            parts.append(f"{label}: {odds[key]}")
    return "；".join(parts) if parts else "已讀到 ESPN 賽事，但盤口欄位暫無可用摘要。"


MARKET_SOURCE_STATUS = [
    (
        "Binance Prediction",
        "主下注點",
        "已自動抓取",
        "用本機加密查詢憑證更新市場題目、價格、機率與流動性；下注前仍要以你畫面即時價重算。",
        "https://www.binance.com/",
    ),
    (
        "台灣運彩",
        "台灣官方參考盤",
        "已接公開 JSON",
        "抓取世界盃公開盤：1X2、總分 2.5、單雙與正確比數。倍率用 1 + pu/pd 呈現。",
        "https://www.sportslottery.com.tw/sportsbook/world-cup",
    ),
    (
        "ESPN / DraftKings",
        "美系盤口參考",
        "已自動抓取",
        "透過 ESPN scoreboard 讀取 1X2、讓球與大小球收盤/參考線，用來校對外部市場方向。",
        "https://www.espn.com/espn/betting/story/_/id/48386952/espn-soccer-futbol-world-cup-betting-odds-championship-groups",
    ),
    (
        "香港賽馬會足智彩",
        "香港公開盤候選",
        "待解析",
        "有公開賽程、賠率與分析頁；下一步可針對 1X2、讓球、入球大細做解析。",
        "https://football.hkjc.com/zh-hk/home",
    ),
    (
        "賠率彙整 / 預測站",
        "市場輔助",
        "半自動",
        "SportsGambler、Action Network、Covers、Oddschecker 等適合抓預測與主流盤口快照，但需防止賽後資料污染。",
        "https://www.sportsgambler.com/",
    ),
    (
        "地下盤 / 非公開盤",
        "排除",
        "不抓取",
        "不使用非法、非公開或需繞過限制的來源；只保留合法公開資料與你主要下注點 Binance 比較。",
        "",
    ),
]


def source_status_cards():
    cards = []
    for name, role, status, note, url in MARKET_SOURCE_STATUS:
        title = f"<a href='{safe(url)}' target='_blank' rel='noopener'>{safe(name)}</a>" if url else safe(name)
        cards.append(
            "<article class='source-card'>"
            f"<div class='source-top'><h3>{title}</h3><span>{safe(status)}</span></div>"
            f"<b>{safe(role)}</b>"
            f"<p>{safe(note)}</p>"
            "</article>"
        )
    return "".join(cards)


def best_binance_signal(match):
    rows = [row for row in match.get("main", []) if row and row[1]]
    if not rows:
        return "尚未抓到 Binance 主盤"
    label, outcome = max(rows, key=lambda row: chance(row[1]))
    return f"{label} {pct(outcome):.1f}% / 價格 {price(outcome):.2f}"


def secondary_binance_signal(match):
    rows = match.get("markets") or match.get("selected") or []
    rows = [row for row in rows if row and row[1]]
    if not rows:
        return "尚未抓到延伸盤"
    preferred = [
        row
        for row in rows
        if any(keyword in row[0] for keyword in ["晉級", "大小", "小", "大", "BTTS"])
    ]
    selected = (preferred or rows)[:2]
    return "；".join(f"{label} {pct(outcome):.1f}% / {price(outcome):.2f}" for label, outcome in selected)


def taiwan_odds_note(match):
    item = monitor_item(monitor_state, match)
    data = item.get("taiwanSportsLottery") or {}
    status = data.get("status")
    if status == "ok":
        markets = data.get("markets") or {}
        parts = []
        if data.get("boardName"):
            parts.append(f"盤面 {data['boardName']}")
        if markets.get("1x2"):
            parts.append(f"1X2 {markets['1x2']}")
        if markets.get("total2.5"):
            parts.append(f"總分2.5 {markets['total2.5']}")
        if markets.get("correctScoreShort"):
            parts.append(f"低賠比分 {markets['correctScoreShort']}")
        return "；".join(parts)
    if status:
        return f"{status}: {data.get('error', '暫無資料')}"
    return "尚未抓取台灣運彩公開 JSON"


def market_comparison_rows(matches):
    rows = []
    for match in matches:
        rows.append(
            "<tr>"
            f"<td><b>{safe(match['title'])}</b><br><span class='soft'>{safe(match['time'].strftime('%m/%d %H:%M'))} 台灣</span></td>"
            f"<td>{safe(best_binance_signal(match))}</td>"
            f"<td>{safe(secondary_binance_signal(match))}</td>"
            f"<td>{safe(espn_odds_note(match))}</td>"
            f"<td>{safe(taiwan_odds_note(match))}</td>"
            "</tr>"
        )
    return "".join(rows)


def countdown_label(match, now):
    delta = match["time"] - now
    if delta.total_seconds() > 0:
        minutes = int(delta.total_seconds() // 60)
        hours, mins = divmod(minutes, 60)
        if hours >= 24:
            days, hours = divmod(hours, 24)
            return f"{days} 天 {hours} 小時後開賽"
        if hours > 0:
            return f"{hours} 小時 {mins} 分後開賽"
        return f"{mins} 分後開賽"
    item = monitor_item(monitor_state, match)
    phase = phase_for_match(match, item, now)
    return phase


def next_focus_match(matches, now):
    candidates = []
    for match in matches:
        item = monitor_item(monitor_state, match)
        if item.get("completed") or item.get("status") == "finished":
            continue
        if match["time"] + timedelta(hours=4) >= now:
            candidates.append(match)
    return sorted(candidates, key=lambda match: match["time"])[0] if candidates else sorted(matches, key=lambda match: match["time"])[0]


def today_window_matches(matches, now, hours=30):
    end = now + timedelta(hours=hours)
    selected = [match for match in matches if now - timedelta(hours=2) <= match["time"] <= end]
    return sorted(selected or matches[:3], key=lambda match: match["time"])


def compact_espn_signal(match):
    odds = monitor_item(monitor_state, match).get("espnOdds") or {}
    moneyline = odds.get("moneyline")
    total = odds.get("total")
    spread = odds.get("spread")
    if moneyline and total:
        return f"{moneyline} · {total}"
    if moneyline:
        return moneyline
    if spread:
        return spread
    return "ESPN / DK 尚未回傳盤口"


def compact_taiwan_signal(match):
    data = monitor_item(monitor_state, match).get("taiwanSportsLottery") or {}
    if data.get("status") != "ok":
        return "台灣運彩尚未回傳"
    markets = data.get("markets") or {}
    one_x_two = markets.get("1x2", "")
    total = markets.get("total2.5", "")
    if one_x_two and total:
        return f"{one_x_two} · {total}"
    return one_x_two or total or "已抓到賽事，盤口空白"


def confidence_tone(match):
    rows = [row for row in match.get("main", []) if row and row[1]]
    if not rows:
        return ("資料不足", "neutral")
    _, outcome = max(rows, key=lambda row: chance(row[1]))
    value = pct(outcome)
    if value >= 70:
        return ("市場強烈傾斜", "hot")
    if value >= 55:
        return ("市場方向明確", "good")
    return ("接近五五波", "warn")


def market_tiles(match):
    tiles = [
        ("Binance 主盤", best_binance_signal(match), "交易價格"),
        ("Binance 延伸", secondary_binance_signal(match), "晉級 / 大小 / BTTS"),
        ("台灣運彩", compact_taiwan_signal(match), "官方公開倍率"),
        ("ESPN / DK", compact_espn_signal(match), "美系參考盤"),
    ]
    return "".join(
        "<div class='market-tile'>"
        f"<span>{safe(source)}</span>"
        f"<b>{safe(value)}</b>"
        f"<em>{safe(note)}</em>"
        "</div>"
        for source, value, note in tiles
    )


def focus_dashboard(focus, today_matches, now):
    item = monitor_item(monitor_state, focus)
    phase = phase_for_match(focus, item, now)
    tone_text, tone = confidence_tone(focus)
    risk = focus.get("detail", {}).get("risk") or focus.get("subtitle")
    primary = focus.get("detail", {}).get("primary") or focus.get("subtitle")
    today_cards = "".join(today_match_card(match, now) for match in today_matches)
    return f"""
      <section class="command-center">
        <div class="today-rail">
          <div class="panel-label">今日 / 近 30 小時</div>
          {today_cards}
        </div>
        <article class="focus-card">
          <div class="focus-top">
            <div>
              <span class="panel-label">下一場</span>
              <h2>{safe(focus['title'])}</h2>
              <p>{safe(focus['time'].strftime('%m/%d %H:%M'))} 台灣 · {safe(focus['venue'])}</p>
            </div>
            <div class="score-box">
              <span>{safe(phase)}</span>
              <strong>{safe(display_value(item.get('scoreDisplay'), '0-0'))}</strong>
              <em>{safe(countdown_label(focus, now))}</em>
            </div>
          </div>
          <div class="focus-verdict">
            <span class="tone {safe(tone)}">{safe(tone_text)}</span>
            <b>{safe(primary)}</b>
            <p>{safe(risk)}</p>
          </div>
          <div class="market-tile-grid">{market_tiles(focus)}</div>
        </article>
        <aside class="consensus-card">
          <div class="panel-label">市場判讀</div>
          <h3>盤口共識</h3>
          <div class="consensus-stack">
            <div><span>主訊號</span><b>{safe(best_binance_signal(focus))}</b></div>
            <div><span>價格品質</span><b>{safe(focus.get('detail', {}).get('value', '先看多市場是否同向'))}</b></div>
            <div><span>臨場觸發</span><b>{safe(focus.get('detail', {}).get('trigger', '等待開賽前最後一次盤口'))}</b></div>
          </div>
        </aside>
      </section>
    """


def today_match_card(match, now):
    item = monitor_item(monitor_state, match)
    phase = phase_for_match(match, item, now)
    button_attr = f" data-tab='{safe(match['key'])}'" if match in matches else ""
    return (
        f"<button class='today-match'{button_attr}>"
        f"<span>{safe(match['time'].strftime('%H:%M'))}</span>"
        f"<b>{safe(match['title'])}</b>"
        f"<em>{safe(display_value(item.get('scoreDisplay'), '0-0'))} · {safe(phase)}</em>"
        "</button>"
    )


def sidebar_match_list(schedule_matches, now):
    items = []
    for match in sorted(schedule_matches, key=lambda row: row["time"]):
        item = monitor_item(monitor_state, match)
        phase = phase_for_match(match, item, now)
        score = display_value(item.get("scoreDisplay"), "0-0")
        signal = best_binance_signal(match)
        content = (
            f"<span class='side-time'>{safe(match['time'].strftime('%m/%d %H:%M'))}</span>"
            f"<b>{safe(match['title'])}</b>"
            f"<em>{safe(score)} · {safe(phase)}</em>"
            f"<small>{safe(signal)}</small>"
        )
        if match in matches:
            items.append(
                f"<button type='button' class='side-match is-clickable' data-tab='{safe(match['key'])}'>{content}</button>"
            )
        else:
            items.append(f"<div class='side-match'>{content}</div>")
    return "".join(items)


def consensus_match_cards(matches):
    cards = []
    for match in matches:
        tone_text, tone = confidence_tone(match)
        cards.append(
            "<article class='consensus-match'>"
            f"<div><span class='tone {safe(tone)}'>{safe(tone_text)}</span><h3>{safe(match['title'])}</h3></div>"
            f"<p>{safe(best_binance_signal(match))}</p>"
            f"<small>{safe(compact_taiwan_signal(match))}</small>"
            "</article>"
        )
    return "".join(cards)


ROUND_OF_16_KEYS = [
    "can-mar",
    "par-fra",
    "bra-nor",
    "mex-eng",
    "por-esp",
    "usa-bel",
    "arg-egy",
    "sui-col",
]

QUARTERFINAL_SLOTS = [
    ("qf-a", "8強 A", ("can-mar", "par-fra")),
    ("qf-b", "8強 B", ("bra-nor", "mex-eng")),
    ("qf-c", "8強 C", ("por-esp", "usa-bel")),
    ("qf-d", "8強 D", ("arg-egy", "sui-col")),
]

SEMIFINAL_SLOTS = [
    ("sf-a", "4強 A", ("8強 A 勝方", "8強 B 勝方")),
    ("sf-b", "4強 B", ("8強 C 勝方", "8強 D 勝方")),
]


def team_info(team):
    return TEAM_INFO.get(team, {"name": team or "待定", "flag": "○"})


def bracket_match_map(schedule_matches):
    return {match["key"]: match for match in schedule_matches}


def bracket_winner(match):
    item = monitor_item(monitor_state, match)
    winner = item.get("winner")
    if winner:
        return winner
    if not (item.get("completed") or item.get("status") == "finished"):
        return None
    scores = parse_match_score(match, item)
    if not scores:
        return None
    first, second = match["teams"]
    if scores[first] == scores[second]:
        return None
    return first if scores[first] > scores[second] else second


def bracket_score(match, team):
    item = monitor_item(monitor_state, match)
    show_score = bool(
        item.get("completed")
        or item.get("status") == "finished"
        or item.get("espnState") == "in"
        or item.get("clock")
    )
    if not show_score:
        return "—"
    scores = parse_match_score(match, item)
    if not scores:
        return "—"
    return str(scores.get(team, "—"))


def bracket_team_row(team, score="—", winner=False, eliminated=False, note=""):
    info = team_info(team)
    cls = "bracket-team"
    if winner:
        cls += " is-winner"
    if eliminated:
        cls += " is-eliminated"
    return (
        f"<div class='{cls}'>"
        f"<span class='flag'>{safe(info['flag'])}</span>"
        "<span class='team-copy'>"
        f"<b>{safe(team or 'TBD')}</b>"
        f"<em>{safe(info['name'])}</em>"
        "</span>"
        f"<strong>{safe(score)}</strong>"
        f"<small>{safe(note)}</small>"
        "</div>"
    )


def bracket_placeholder(label):
    return (
        "<div class='bracket-team placeholder'>"
        "<span class='flag'>○</span>"
        "<span class='team-copy'><b>TBD</b>"
        f"<em>{safe(label)}</em></span>"
        "<strong>—</strong><small>待定</small>"
        "</div>"
    )


def bracket_round16_card(match):
    item = monitor_item(monitor_state, match)
    winner = bracket_winner(match)
    completed = bool(item.get("completed") or item.get("status") == "finished")
    phase = phase_for_match(match, item, generated_at)
    state_cls = " is-complete" if completed else " is-pending"
    click_attr = f" data-tab='{safe(match['key'])}'" if match in matches else ""
    rows = []
    for team in match["teams"]:
        rows.append(
            bracket_team_row(
                team,
                bracket_score(match, team),
                winner == team,
                completed and winner and winner != team,
                "晉級" if winner == team else ("出局" if completed and winner else ""),
            )
        )
    score_line = display_value(item.get("scoreDisplay"), "尚未開賽")
    return (
        f"<article class='bracket-match{state_cls}'{click_attr}>"
        "<div class='bracket-match-head'>"
        f"<span>{safe(match['time'].strftime('%m/%d %H:%M'))}</span>"
        f"<b>{safe(phase)}</b>"
        "</div>"
        f"{''.join(rows)}"
        f"<p>{safe(score_line)}</p>"
        "</article>"
    )


def bracket_slot_card(title, teams, notes):
    ready = [team for team in teams if team]
    rows = []
    for index, team in enumerate(teams):
        if team:
            rows.append(bracket_team_row(team, "—", False, False, "已取得席位"))
        else:
            rows.append(bracket_placeholder(notes[index]))
    state = " is-ready" if len(ready) == 2 else (" is-half" if ready else "")
    return (
        f"<article class='bracket-slot{state}'>"
        f"<div class='bracket-slot-title'>{safe(title)}</div>"
        f"{''.join(rows)}"
        "</article>"
    )


def bracket_view(schedule_matches):
    by_key = bracket_match_map(schedule_matches)
    r16_cards = []
    winners = {}
    for key in ROUND_OF_16_KEYS:
        match = by_key.get(key)
        if not match:
            continue
        winners[key] = bracket_winner(match)
        r16_cards.append(bracket_round16_card(match))

    qf_cards = []
    qf_winner_placeholders = {}
    for slot_key, title, source_keys in QUARTERFINAL_SLOTS:
        teams = [winners.get(source_keys[0]), winners.get(source_keys[1])]
        notes = []
        for source_key in source_keys:
            source = by_key.get(source_key)
            notes.append(f"{source['title']} 勝方" if source else "16 強勝方")
        qf_cards.append(bracket_slot_card(title, teams, notes))
        qf_winner_placeholders[slot_key] = f"{title} 勝方"

    sf_cards = []
    for slot_key, title, source_notes in SEMIFINAL_SLOTS:
        sf_cards.append(bracket_slot_card(title, [None, None], list(source_notes)))

    final_card = bracket_slot_card("決賽", [None, None], ["4強 A 勝方", "4強 B 勝方"])
    champion_card = (
        "<article class='bracket-champion'>"
        "<div class='bracket-slot-title'>冠軍</div>"
        "<div class='champion-cup'>🏆</div>"
        "<b>待定</b>"
        "<p>決賽完賽後自動帶入冠軍。</p>"
        "</article>"
    )

    advanced = [team for team in winners.values() if team]
    advanced_text = "、".join(f"{team_info(team)['flag']} {team_info(team)['name']}" for team in advanced) or "尚未確定"
    return f"""
      <div class="bracket-summary">
        <div><span>已確定晉級</span><b>{len(advanced)} / 8</b></div>
        <p>{safe(advanced_text)}</p>
      </div>
      <div class="bracket-scroll">
        <div class="bracket-board">
          <section class="bracket-round r16"><h3>16 強</h3>{''.join(r16_cards)}</section>
          <section class="bracket-round"><h3>8 強</h3>{''.join(qf_cards)}</section>
          <section class="bracket-round compact"><h3>4 強</h3>{''.join(sf_cards)}</section>
          <section class="bracket-round compact"><h3>決賽</h3>{final_card}</section>
          <section class="bracket-round champion-round"><h3>冠軍</h3>{champion_card}</section>
        </div>
      </div>
    """


def match_panel(m, active=False):
    main_html = market_bars(m["main"])
    markets_html = market_bars(m["markets"])
    exact_html = exact_bars(m["exact"])
    all_profit = sum(profit(stake, p) for _, stake, p in m["allocation"])
    return f"""
    <section id="{m['key']}" class="match-panel{' active' if active else ''}">
      <div class="match-head">
        <div>
          <h2>{safe(m['title'])}</h2>
          <p>{m['time'].strftime('%Y-%m-%d %H:%M')} 台灣時間 · {safe(m['venue'])}</p>
        </div>
        <span class="tag">{safe(m['subtitle'])}</span>
      </div>

      <div class="callout">
        <h3>判斷</h3>
        <p>{safe(m['take'])}</p>
      </div>

      {live_match_panel(m)}

      <div class="grid four insight-grid">
        {insight_cards(m)}
      </div>

      {prematch_room(m)}

      <div class="grid two">
        <div class="chart-card">
          <h3>90 分鐘勝平負</h3>
          {main_html}
        </div>
        <div class="chart-card">
          <h3>延伸盤口</h3>
          {markets_html}
        </div>
      </div>

      <div class="grid two">
        <div class="chart-card">
          <h3>精確比分前段</h3>
          {exact_html}
        </div>
        <div class="table-card">
          <h3>100U 拆單</h3>
          <table>
            <thead><tr><th>項目</th><th>下注</th><th>價格</th><th>命中返還</th><th>淨利</th></tr></thead>
            <tbody>{allocation_table(m['allocation'])}</tbody>
          </table>
          <p>全部命中時理論淨利約 <b class="good">+{all_profit:.2f}U</b>。這些都是單關拆分，不是串關。</p>
          {lock_note(m)}
        </div>
      </div>

      {settlement_table(m)}

      <div class="grid two">
        <div class="table-card">
          <h3>盤口細節與觸發條件</h3>
          <table><thead><tr><th>項目</th><th>判讀</th></tr></thead><tbody>{detail_points(m)}</tbody></table>
          <p class="odds-note">ESPN 參考盤：{safe(espn_odds_note(m))}</p>
        </div>
        <div class="table-card">
          <h3>資金縮放試算</h3>
          {stake_calculator(m)}
        </div>
      </div>

      <div class="grid two">
        <div class="table-card">
          <h3>常見比分收益</h3>
          <table>
            <thead><tr><th>情境</th><th>理論淨利</th><th>命中項目</th></tr></thead>
            <tbody>{scenario_table(m['allocation'], m['scenarios'])}</tbody>
          </table>
        </div>
        <div class="table-card">
          <h3>來源判讀</h3>
          <table>
            <thead><tr><th>來源</th><th>重點</th><th>訊號</th></tr></thead>
            <tbody>{source_rows(m['sources'])}</tbody>
          </table>
        </div>
      </div>
    </section>
    """


def tab_buttons(match_list, active_first=False):
    return "".join(
        f"<button class='tab{' active' if active_first and i == 0 else ''}' data-tab='{m['key']}'>{safe(m['title'])}</button>"
        for i, m in enumerate(match_list)
    )


def deep_file_notice(title, message):
    return (
        "<div class='callout deep-notice'>"
        f"<h3>{safe(title)}</h3>"
        f"<p>{safe(message)}</p>"
        "</div>"
    )


def archived_file_cards(match_list):
    if not match_list:
        return deep_file_notice("賽後回顧", "目前還沒有完賽場次可回顧。")
    cards = []
    for match in match_list:
        item = monitor_item(monitor_state, match)
        score = display_value(item.get("scoreDisplay"), "待確認")
        cards.append(
            "<button type='button' class='archive-card settlement-jump' "
            f"data-tab='{safe(match['key'])}'>"
            f"<span>賽後回顧</span><b>{safe(match['title'])}</b>"
            f"<em>{safe(score)} · {safe(display_value(item.get('winner'), '勝方待確認'))}</em>"
            "</button>"
        )
    return f"<div class='archive-card-grid'>{''.join(cards)}</div>"


def parked_file_note(match_list):
    if not match_list:
        return ""
    names = "、".join(match["title"] for match in match_list)
    return deep_file_notice("待進 24 小時", f"{names} 已有基礎資料；進入開賽前 24 小時後才會移到主賽前檔案。")


extra_matches = build_extra_matches()
all_schedule_matches = matches + extra_matches

active_deep_matches = [m for m in matches if is_active_deep_match(m, generated_at)]
completed_deep_matches = [m for m in matches if is_completed_match(m)]
parked_deep_matches = [m for m in matches if m not in active_deep_matches and m not in completed_deep_matches]

active_tabs = tab_buttons(active_deep_matches, active_first=True)
active_panels = "".join(match_panel(m, i == 0) for i, m in enumerate(active_deep_matches))
archive_tabs = tab_buttons(completed_deep_matches, active_first=False)
archive_panels = "".join(match_panel(m, False) for m in completed_deep_matches)
parked_panels = "".join(match_panel(m, False) for m in parked_deep_matches)
panels = active_panels + archive_panels + parked_panels
active_deep_block = (
    f"<nav class='tabs'>{active_tabs}</nav>"
    if active_deep_matches
    else deep_file_notice("目前沒有 24 小時內賽前檔案", "下一場進入開賽前 24 小時或賽中後，會自動出現在這裡。")
)
archive_deep_block = (
    f"<div class='section-title sub'><h2>賽後回顧</h2><span>完賽場次先收在這裡，避免干擾賽前決策</span></div>{archived_file_cards(completed_deep_matches)}<nav class='tabs archive-tabs'>{archive_tabs}</nav>"
    if completed_deep_matches
    else ""
)
parked_deep_block = parked_file_note(parked_deep_matches)

overview_cards = "".join(
    [
        card("收錄賽程", "8 場", "本頁收錄目前 ESPN 列出的 16 強賽事。"),
        card("最強熱門", "法國", f"Binance 給法國 90 分鐘勝 {pct(out(par_topics, 'Paraguay vs. France', 'FRA', 'Yes')):.1f}%。"),
        card("最不穩盤", "巴西/挪威", "巴西小熱門，但平局與挪威進球機率都不低。"),
        card("24h 檔案", f"{len(active_deep_matches)} 場", "主賽前檔案只放 24 小時內未完賽或賽中場。"),
    ]
)

schedule_rows = "".join(
    f"<tr><td>{safe(m['time'].strftime('%Y-%m-%d %H:%M'))}</td><td>{safe(m['title'])}</td><td>{safe(m['venue'])}</td><td>{safe(m['subtitle'])}</td></tr>"
    for m in all_schedule_matches
)
monitor_rows = monitor_table(all_schedule_matches, monitor_state, generated_at)
live_center = live_center_cards(all_schedule_matches, monitor_state, generated_at)
extra_radar = radar_cards(extra_matches)
market_source_cards = source_status_cards()
market_comparison = market_comparison_rows(all_schedule_matches)
focus_match = next_focus_match(all_schedule_matches, generated_at)
today_matches_for_dashboard = today_window_matches(all_schedule_matches, generated_at)
dashboard = focus_dashboard(focus_match, today_matches_for_dashboard, generated_at)
consensus_cards = consensus_match_cards(all_schedule_matches)
sidebar_matches = sidebar_match_list(all_schedule_matches, generated_at)
settlement_summary, settlement_cards = settlement_overview_cards(matches)
bracket_html = bracket_view(all_schedule_matches)

def hero_match_cards(matches, monitor_state, now):
    cards = []
    for match in matches:
        item = monitor_item(monitor_state, match)
        phase = phase_for_match(match, item, now)
        lead_label, lead_outcome = match["main"][0]
        cards.append(
            "<button class='match-tile' data-tab='{}'>"
            "<span class='tile-phase'>{}</span>"
            "<span class='tile-teams'>{} <b>vs</b> {}</span>"
            "<span class='tile-time'>{}</span>"
            "<span class='tile-signal'>{} · {}</span>"
            "</button>".format(
                safe(match["key"]),
                safe(phase),
                badge(match["teams"][0]),
                badge(match["teams"][1]),
                safe(match["time"].strftime("%m/%d %H:%M 台灣")),
                safe(lead_label),
                safe(f"{pct(lead_outcome):.1f}%"),
            )
        )
    return "".join(cards)


hero_cards = hero_match_cards(matches, monitor_state, generated_at)

doc = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{SITE_NAME}｜淘汰賽盤口與即時戰況</title>
  <style>
    :root {{
      --bg:#f3f5f1; --panel:#ffffff; --ink:#111827; --muted:#6b7280; --line:#d9dfd6;
      --good:#137a53; --bad:#b42318; --blue:#1d4ed8; --amber:#b7791f; --violet:#6d5bd0;
      --night:#0a1220; --grass:#137a53; --gold:#c9972b;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0; font-family:"Segoe UI",Arial,"Microsoft JhengHei",sans-serif; color:var(--ink);
      background:var(--bg); font-variant-numeric:tabular-nums;
    }}
    body::before {{
      content:none;
    }}
    .hero {{
      position:relative; min-height:310px; color:#fff; overflow:hidden;
      background:
        linear-gradient(90deg, rgba(4,10,18,.98) 0%, rgba(7,17,31,.92) 52%, rgba(7,17,31,.54) 100%),
        linear-gradient(180deg, rgba(7,17,31,.20), rgba(7,17,31,.82)),
        url('/assets/worldcup-stadium-hero.png') center/cover no-repeat;
    }}
    .hero::after {{
      content:""; position:absolute; inset:auto 0 0; height:1px;
      background:rgba(255,255,255,.18);
    }}
    .hero-inner {{ position:relative; z-index:1; max-width:1320px; margin:0 auto; padding:30px 22px 24px; }}
    .eyebrow {{ margin:0 0 10px; color:#d8b25b; font-weight:800; font-size:12px; }}
    header h1 {{ margin:0 0 10px; max-width:760px; font-size:42px; line-height:1.06; letter-spacing:0; }}
    header p {{ margin:0; color:#cbd5e1; line-height:1.65; max-width:820px; font-size:14px; }}
    .hero-board {{
      display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1px; margin-top:22px; max-width:820px;
      border:1px solid rgba(255,255,255,.14); background:rgba(255,255,255,.10);
    }}
    .hero-stat {{
      border:0; border-radius:0; padding:11px 13px;
      background:rgba(5,12,22,.66);
    }}
    .hero-stat span {{ display:block; color:#94a3b8; font-size:11px; margin-bottom:4px; }}
    .hero-stat b {{ display:block; font-size:18px; }}
    .hero-matches {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1px; margin-top:14px; max-width:940px; border:1px solid rgba(255,255,255,.13); background:rgba(255,255,255,.10); }}
    .match-tile {{
      min-height:108px; text-align:left; color:#fff; border:0; border-radius:0;
      padding:13px; background:rgba(8,20,34,.78); cursor:pointer; font:inherit;
    }}
    .match-tile:hover {{ background:rgba(13,35,57,.94); }}
    .tile-phase {{ display:inline-block; margin-bottom:10px; padding:3px 6px; border-radius:3px; background:rgba(216,178,91,.14); color:#f7d991; font-size:11px; font-weight:800; }}
    .tile-teams {{ display:flex; align-items:center; gap:9px; margin-bottom:10px; font-size:14px; }}
    .tile-teams b {{ color:#9fb1c7; font-size:12px; }}
    .team-badge {{ display:inline-grid; place-items:center; min-width:44px; height:30px; border-radius:4px; background:var(--team-bg); color:var(--team-fg); font-weight:900; box-shadow:inset 0 0 0 1px rgba(255,255,255,.24); }}
    .tile-time {{ display:block; color:#d8e2ea; font-size:13px; margin-bottom:8px; }}
    .tile-signal {{ display:block; color:#ffffff; font-size:13px; font-weight:800; line-height:1.45; }}
    main {{ max-width:1320px; margin:0 auto; padding:18px 22px 24px; position:relative; }}
    .desk-shell {{
      display:grid; grid-template-columns:282px minmax(0,1fr); gap:14px; align-items:start;
    }}
    .desk-main {{ min-width:0; }}
    .desk-sidebar {{
      position:sticky; top:58px; border:1px solid #cfdcd6; border-radius:5px; background:#fff; overflow:hidden;
      box-shadow:none;
    }}
    .sidebar-head {{ padding:13px 14px; background:#0f1f33; color:#fff; border-bottom:1px solid #102842; }}
    .sidebar-head h2 {{ margin:6px 0 4px; font-size:18px; }}
    .sidebar-head p {{ margin:0; color:#b9c7d6; font-size:12px; line-height:1.45; }}
    .side-list {{ display:flex; flex-direction:column; }}
    .side-match {{
      width:100%; display:grid; grid-template-columns:58px 1fr; gap:2px 10px; text-align:left; padding:11px 12px;
      border:0; border-bottom:1px solid #e2e8df; border-radius:0; background:#fff; color:#142033; font:inherit;
    }}
    .side-match:last-child {{ border-bottom:0; }}
    .side-match.is-clickable {{ cursor:pointer; }}
    .side-match.is-clickable:hover {{ background:#f7f9f5; }}
    .side-time {{ grid-row:1 / span 3; color:#137a53; font-size:12px; font-weight:900; line-height:1.35; }}
    .side-match b {{ font-size:13px; line-height:1.35; }}
    .side-match em {{ color:#647084; font-style:normal; font-size:12px; }}
    .side-match small {{ color:#2f4f45; font-size:11px; line-height:1.35; font-weight:700; }}
    .grid {{ display:grid; gap:12px; }}
    .grid.four {{ grid-template-columns:repeat(4,minmax(0,1fr)); }}
    .grid.two {{ grid-template-columns:1fr 1fr; margin-top:14px; }}
    .card,.chart-card,.table-card,.callout {{
      background:#fff; border:1px solid var(--line); border-radius:5px; padding:14px;
      box-shadow:none;
    }}
    .card {{ border-top:2px solid var(--grass); }}
    .card:nth-child(2) {{ border-top-color:var(--gold); }}
    .card:nth-child(3) {{ border-top-color:var(--blue); }}
    .card:nth-child(4) {{ border-top-color:var(--bad); }}
    .card h3,.chart-card h3,.table-card h3,.callout h3 {{ margin:0 0 10px; font-size:16px; }}
    .metric {{ font-size:24px; font-weight:900; margin-bottom:5px; color:#0d253f; }}
    p {{ line-height:1.65; }}
    .card p,.table-card p {{ margin:0; color:var(--muted); font-size:13px; }}
    .insight-grid {{ margin-top:14px; }}
    .insight-card {{
      background:#fff; border:1px solid var(--line); border-radius:5px; padding:13px;
      box-shadow:none;
    }}
    .insight-card h3 {{ margin:0 0 8px; color:#0f6b45; font-size:13px; }}
    .insight-card p {{ margin:0; line-height:1.55; font-size:13px; color:#172033; }}
    .monitor-card {{ overflow-x:auto; }}
    .odds-note {{ margin-top:10px !important; color:#475569 !important; }}
    .stake-calc label {{ display:flex; align-items:center; gap:10px; margin:0 0 12px; font-weight:800; color:#334155; }}
    .calc-input {{ width:110px; padding:8px 10px; border:1px solid var(--line); border-radius:8px; font:inherit; background:#fff; }}
    .settlement-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }}
    .settlement-card,.settlement-detail {{
      background:#fff; border:1px solid var(--line); border-radius:5px; padding:14px; box-shadow:none;
    }}
    .settlement-card {{
      display:grid; grid-template-columns:1fr auto; gap:10px; align-items:start; border-top:2px solid #0f6b45;
    }}
    .settlement-card h3 {{ margin:6px 0 0; font-size:18px; }}
    .settlement-card strong {{ font-size:24px; white-space:nowrap; }}
    .settlement-card p {{ grid-column:1 / -1; margin:0; color:#4b5563; font-size:13px; line-height:1.55; }}
    .settlement-jump {{
      grid-column:1 / -1; justify-self:start; border:1px solid #cbd8d2; background:#fff; color:#1f4f42;
      border-radius:4px; padding:7px 10px; font:inherit; font-size:12px; font-weight:900; cursor:pointer;
    }}
    .settlement-jump:hover {{ background:#f7f9f5; }}
    .settlement-detail {{ margin:14px 0; padding:0; overflow:hidden; }}
    .settlement-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; padding:14px; background:#f7f9f5; border-bottom:1px solid #e2e8df; }}
    .settlement-head h3 {{ margin:6px 0 4px; font-size:18px; color:#102a3f; }}
    .settlement-head p {{ margin:0; color:#647084; font-size:12px; }}
    .settlement-head strong {{ font-size:24px; white-space:nowrap; }}
    .settlement-note {{ margin:0 !important; padding:11px 14px; color:#334155 !important; border-bottom:1px solid #e2e8df; background:#fff; }}
    .settlement-table-wrap {{ overflow-x:auto; }}
    .settlement-table-wrap table {{ min-width:860px; }}
    .status-chip {{ display:inline-flex; align-items:center; min-height:22px; padding:3px 7px; border-radius:3px; font-size:12px; font-weight:900; background:#e2e8f0; color:#334155; }}
    .status-chip.good {{ background:#dcfce7; color:#166534; }}
    .status-chip.bad {{ background:#fee2e2; color:#991b1b; }}
    .status-chip.soft,.status-chip.warn {{ background:#fef3c7; color:#92400e; }}
    .warn {{ color:#92400e; font-weight:800; }}
    .archive-card-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin:10px 0 10px; }}
    .archive-card {{
      min-height:88px; text-align:left; border:1px solid #d7e1dc; border-radius:5px; background:#fff;
      padding:12px; font:inherit; color:#132033; cursor:pointer;
    }}
    .archive-card:hover {{ border-color:#8aa39a; background:#fbfdfc; }}
    .archive-card span {{ display:block; color:#647084; font-size:11px; font-weight:900; letter-spacing:0; margin-bottom:6px; }}
    .archive-card b {{ display:block; font-size:16px; margin-bottom:6px; }}
    .archive-card em {{ display:block; color:#0f6b45; font-style:normal; font-size:13px; font-weight:900; }}
    .deep-notice {{ margin:10px 0 14px; }}
    .archive-tabs {{ margin-top:8px; }}
    .app-tabs {{
      position:sticky; top:0; z-index:8; display:flex; gap:0; padding:10px 0; margin:0 0 14px;
      background:rgba(243,245,241,.96); backdrop-filter:blur(8px); border-bottom:1px solid var(--line);
    }}
    .app-tab {{
      border:1px solid #cbd8d2; border-right:0; background:#fff; color:#243447; border-radius:0; padding:9px 14px;
      font-weight:900; cursor:pointer; white-space:nowrap;
    }}
    .app-tab:first-child {{ border-radius:5px 0 0 5px; }}
    .app-tab:last-child {{ border-right:1px solid #cbd8d2; border-radius:0 5px 5px 0; }}
    .app-tab:hover {{ border-color:#8aa39a; }}
    .app-tab.active {{ background:#111827; color:#fff; border-color:#111827; box-shadow:none; }}
    .home-panel {{ display:none; }}
    .home-panel.active {{ display:block; }}
    .tabs {{
      display:flex; gap:8px; padding:10px 0; margin:0 0 14px;
      background:transparent; border-bottom:1px solid var(--line);
    }}
    .tab {{ border:1px solid var(--line); background:#fff; color:#334155; border-radius:5px; padding:9px 13px; font-weight:900; cursor:pointer; }}
    .tab:hover {{ border-color:#8aa39a; }}
    .tab.active {{ background:#111827; color:#fff; border-color:#111827; box-shadow:none; }}
    .match-panel {{ display:none; padding-top:18px; }}
    .match-panel.active {{ display:block; }}
    .match-head {{
      display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom:12px;
      padding:15px; border-radius:5px; color:#fff;
      background:#0f1f33;
      box-shadow:none;
    }}
    .match-head h2 {{ margin:0 0 6px; font-size:26px; }}
    .match-head p {{ margin:0; color:var(--muted); }}
    .match-head p {{ color:#cfe0dd; }}
    .tag,.pill {{ display:inline-block; padding:4px 8px; border-radius:3px; background:#e6f2ef; color:#1f4f42; font-size:12px; font-weight:900; white-space:nowrap; }}
    .match-head .tag {{ background:rgba(255,255,255,.14); color:#fff; border:1px solid rgba(255,255,255,.18); }}
    .callout {{ border-left:4px solid var(--good); background:#fff; }}
    .callout p {{ margin:0; color:#334155; }}
    .bar-row {{ display:grid; grid-template-columns:142px 1fr 132px; gap:10px; align-items:center; margin:10px 0; min-height:26px; }}
    .bar-label {{ font-size:13px; color:#27364a; font-weight:700; }}
    .bar-track {{ height:10px; background:#e7efe9; border-radius:2px; overflow:hidden; box-shadow:none; }}
    .bar-fill {{ height:100%; border-radius:0; }}
    .bar-note {{ font-size:12px; color:#475569; text-align:right; white-space:nowrap; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th,td {{ padding:10px 9px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ color:#315244; background:#f2f7f5; font-weight:900; }}
    tr:last-child td {{ border-bottom:0; }}
    tbody tr:hover td {{ background:#fbfdfc; }}
    a {{ color:#1d4ed8; text-decoration:none; font-weight:800; }}
    a:hover {{ text-decoration:underline; }}
    .good {{ color:var(--good); font-weight:800; }}
    .bad {{ color:var(--bad); font-weight:800; }}
    .section-title {{ display:flex; justify-content:space-between; gap:12px; align-items:end; margin:24px 0 10px; }}
    .section-title h2 {{ margin:0; font-size:21px; color:#102a3f; }}
    .section-title span {{ color:var(--muted); font-size:13px; }}
    .section-title.sub {{ margin-top:18px; }}
    .data-room {{
      margin-top:10px; padding:14px; border:1px solid #cddcd4; border-radius:5px;
      background:#fff;
      box-shadow:none;
    }}
    .lineup-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
    .lineup-board {{
      border:1px solid #d7e1dc; border-radius:5px; overflow:hidden; background:#fff;
    }}
    .lineup-top {{
      display:flex; align-items:center; gap:12px; padding:13px 14px;
      background:#0f1f33; color:#fff;
    }}
    .lineup-top h3 {{ margin:0 0 4px; font-size:18px; }}
    .lineup-top p {{ margin:0; color:#cfe0dd; font-size:12px; }}
    .line-row {{ display:grid; grid-template-columns:54px 1fr; gap:10px; padding:10px 14px; border-bottom:1px solid #edf2ef; }}
    .line-row span {{ display:inline-flex; align-items:center; justify-content:center; height:26px; border-radius:3px; background:#e6f2ef; color:#1f4f42; font-weight:900; font-size:12px; }}
    .line-row p {{ margin:0; color:#1e2d3f; font-size:13px; line-height:1.55; }}
    .lineup-notes {{ margin:0; padding:10px 18px 12px 30px; color:#5b6878; font-size:12px; line-height:1.55; }}
    .history-room {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:14px; }}
    .history-panel {{
      border:1px solid #d7e1dc; border-radius:5px; background:#fff; padding:14px;
    }}
    .history-panel h3 {{ margin:0 0 10px; font-size:16px; }}
    .fact-line {{ padding:10px 0; border-bottom:1px solid #edf2ef; }}
    .fact-line:last-child {{ border-bottom:0; }}
    .fact-line b {{ display:block; color:#0f6b45; font-size:13px; margin-bottom:4px; }}
    .fact-line p {{ margin:0; color:#334155; font-size:13px; line-height:1.55; }}
    .key-table .team-badge {{ min-width:42px; height:30px; }}
    .source-note {{ margin:12px 0 0; color:#647084; font-size:12px; line-height:1.7; }}
    .source-note a {{ margin-right:10px; white-space:nowrap; }}
    .radar-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
    .radar-card {{
      background:#fff; border:1px solid var(--line); border-radius:5px;
      padding:14px; box-shadow:none;
    }}
    .radar-head {{ display:flex; justify-content:space-between; gap:14px; align-items:flex-start; }}
    .radar-head h3 {{ margin:8px 0 5px; font-size:20px; color:#102a3f; }}
    .radar-head p,.radar-subtitle {{ margin:0; color:#647084; font-size:13px; line-height:1.55; }}
    .radar-teams {{ display:flex; align-items:center; gap:7px; flex:0 0 auto; }}
    .radar-teams b {{ color:#94a3b8; font-size:12px; }}
    .radar-main {{ margin-top:12px; padding-top:10px; border-top:1px solid #edf2ef; }}
    .market-chip-row,.exact-strip {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }}
    .market-chip {{
      display:inline-flex; flex-direction:column; gap:2px; padding:7px 9px; border-radius:4px;
      background:#eef6f2; color:#1f4f42; border:1px solid #cfe3da;
    }}
    .market-chip b {{ font-size:12px; }}
    .market-chip em {{ font-style:normal; font-size:12px; color:#456358; }}
    .tiny-chip {{
      display:inline-flex; align-items:center; min-height:26px; padding:4px 8px; border-radius:4px;
      background:#f3f6fa; color:#334155; font-size:12px; font-weight:800;
    }}
    .radar-meta {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }}
    .radar-meta span {{
      display:inline-block; padding:4px 8px; border-radius:4px; background:#fff7e8; color:#7a4a0b; font-size:12px; font-weight:800;
    }}
    .muted-note {{ margin:0; color:#647084; font-size:13px; }}
    .soft {{ color:#647084; font-size:12px; font-weight:700; }}
    .source-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-bottom:14px; }}
    .source-card {{
      background:#fff; border:1px solid var(--line); border-radius:5px;
      padding:13px; box-shadow:none;
    }}
    .source-top {{ display:flex; justify-content:space-between; gap:10px; align-items:start; margin-bottom:8px; }}
    .source-top h3 {{ margin:0; font-size:15px; }}
    .source-top span {{ flex:0 0 auto; padding:3px 7px; border-radius:3px; background:#e6f2ef; color:#1f4f42; font-size:11px; font-weight:900; }}
    .source-card b {{ display:block; color:#0f6b45; font-size:12px; margin-bottom:7px; }}
    .source-card p {{ margin:0; color:#526173; font-size:12px; line-height:1.55; }}
    .market-compare-card {{ overflow-x:auto; }}
    .market-compare-card table {{ min-width:1120px; }}
    .command-center {{
      display:grid; grid-template-columns:270px minmax(0,1fr) 310px; gap:12px; align-items:stretch;
      margin-bottom:16px;
    }}
    .today-rail,.focus-card,.consensus-card {{
      border:1px solid #cfdcd6; border-radius:5px; background:#fff; box-shadow:none;
    }}
    .today-rail {{ padding:0; display:flex; flex-direction:column; gap:0; overflow:hidden; }}
    .today-rail .panel-label {{ padding:10px 12px; border-bottom:1px solid #e2e8df; background:#f7f9f5; }}
    .panel-label {{ color:#6b7280; text-transform:uppercase; letter-spacing:0; font-size:11px; font-weight:900; }}
    .today-match {{
      width:100%; text-align:left; display:grid; grid-template-columns:44px 1fr; gap:2px 10px; padding:11px 12px;
      border:0; border-bottom:1px solid #e2e8df; border-radius:0;
      background:#fff; color:#132033; font:inherit; cursor:pointer;
    }}
    .today-match:hover {{ background:#f7f9f5; }}
    .today-match span {{ color:#137a53; font-size:12px; font-weight:900; grid-row:1 / span 2; }}
    .today-match b {{ font-size:14px; }}
    .today-match em {{ color:#647084; font-style:normal; font-size:12px; }}
    .focus-card {{
      padding:0; background:#fff; border-top:0;
    }}
    .focus-top {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; padding:16px; border-bottom:1px solid #e2e8df; }}
    .focus-top h2 {{ margin:6px 0 6px; font-size:28px; color:#0b2033; }}
    .focus-top p {{ margin:0; color:#647084; font-size:13px; }}
    .score-box {{
      min-width:150px; padding:12px; border-radius:4px; background:#07111f; color:#fff; text-align:right;
      box-shadow:inset 0 0 0 1px rgba(255,255,255,.08);
    }}
    .score-box span,.score-box em {{ display:block; color:#9fb1c7; font-size:12px; font-style:normal; }}
    .score-box strong {{ display:block; margin:6px 0; font-size:23px; }}
    .focus-verdict {{
      margin:0; padding:14px 16px; border-radius:0; background:#f7f9f5; border:0; border-bottom:1px solid #e2e8df;
    }}
    .focus-verdict b {{ display:block; margin:8px 0 4px; font-size:16px; color:#0c3426; }}
    .focus-verdict p {{ margin:0; color:#465769; font-size:13px; }}
    .tone {{
      display:inline-flex; align-items:center; min-height:22px; padding:3px 7px; border-radius:3px;
      font-size:12px; font-weight:900; background:#e8eef6; color:#334155;
    }}
    .tone.good {{ background:#dcfce7; color:#166534; }}
    .tone.hot {{ background:#fee2e2; color:#991b1b; }}
    .tone.warn {{ background:#fef3c7; color:#92400e; }}
    .tone.neutral {{ background:#e2e8f0; color:#334155; }}
    .market-tile-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0; border-top:0; }}
    .market-tile {{
      min-height:100px; padding:12px; border:0; border-right:1px solid #e2e8df; border-bottom:1px solid #e2e8df; border-radius:0; background:#fff;
    }}
    .market-tile:nth-child(even) {{ border-right:0; }}
    .market-tile span {{ display:block; color:#0f6b45; font-size:12px; font-weight:900; margin-bottom:6px; }}
    .market-tile b {{ display:block; color:#142033; font-size:13px; line-height:1.45; }}
    .market-tile em {{ display:block; margin-top:6px; color:#647084; font-size:11px; font-style:normal; }}
    .consensus-card {{ padding:15px; background:#0b1827; color:#fff; border-color:#16304b; }}
    .consensus-card h3 {{ margin:7px 0 13px; font-size:21px; }}
    .consensus-card .panel-label {{ color:#f0c66c; }}
    .consensus-stack {{ display:grid; gap:10px; }}
    .consensus-stack div {{ padding:11px 0; border-top:1px solid rgba(255,255,255,.12); }}
    .consensus-stack span {{ display:block; color:#9fb1c7; font-size:12px; font-weight:900; margin-bottom:5px; }}
    .consensus-stack b {{ display:block; color:#fff; font-size:13px; line-height:1.5; }}
    .consensus-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin-top:14px; }}
    .consensus-match {{
      background:#fff; border:1px solid var(--line); border-radius:5px; padding:13px; box-shadow:none;
    }}
    .consensus-match h3 {{ margin:8px 0 8px; font-size:17px; }}
    .consensus-match p {{ margin:0 0 8px; color:#182536; font-size:13px; font-weight:800; }}
    .consensus-match small {{ color:#647084; line-height:1.5; }}
    .bracket-summary {{
      display:grid; grid-template-columns:180px 1fr; gap:12px; align-items:center; margin-bottom:12px;
      border:1px solid #16304b; border-radius:5px; background:#0b1827; padding:13px 15px;
      box-shadow:inset 0 1px 0 rgba(255,255,255,.08);
    }}
    .bracket-summary span {{ display:block; color:#9fb1c7; font-size:12px; font-weight:900; margin-bottom:4px; }}
    .bracket-summary b {{ display:block; font-size:25px; color:#f0c66c; }}
    .bracket-summary p {{ margin:0; color:#f8fafc; font-size:14px; font-weight:850; }}
    .bracket-scroll {{
      overflow-x:auto; padding:14px; border:1px solid #17324d; border-radius:5px;
      background:
        linear-gradient(90deg, rgba(255,255,255,.045) 1px, transparent 1px) 0 0/46px 46px,
        linear-gradient(180deg, rgba(255,255,255,.035) 1px, transparent 1px) 0 0/46px 46px,
        linear-gradient(180deg,#0b1827,#102235);
    }}
    .bracket-board {{
      min-width:1220px; display:grid; grid-template-columns:2.2fr 1.55fr 1.25fr 1.05fr .85fr; gap:12px; align-items:stretch;
    }}
    .bracket-round {{
      display:flex; flex-direction:column; gap:10px; padding:12px; border:1px solid rgba(255,255,255,.16); border-radius:5px;
      background:rgba(255,255,255,.065); box-shadow:inset 0 1px 0 rgba(255,255,255,.08);
    }}
    .bracket-round h3 {{
      display:flex; align-items:center; gap:10px; margin:0 0 2px; color:#f8fafc; font-size:15px; letter-spacing:0;
    }}
    .bracket-round h3::after {{ content:""; height:1px; flex:1; background:rgba(240,198,108,.45); }}
    .bracket-round.r16 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); align-content:start; }}
    .bracket-round.r16 h3 {{ grid-column:1 / -1; }}
    .bracket-round.compact {{ justify-content:center; }}
    .champion-round {{ justify-content:center; }}
    .bracket-match,.bracket-slot,.bracket-champion {{
      position:relative; border:1px solid rgba(17,39,60,.14); border-radius:5px; background:#fff; padding:10px; min-height:118px;
      box-shadow:0 8px 18px rgba(1,10,20,.18);
    }}
    .bracket-match::before,.bracket-slot::before,.bracket-champion::before {{
      content:""; position:absolute; left:0; top:0; right:0; height:3px; background:#d8b45f; border-radius:5px 5px 0 0;
    }}
    .bracket-match[data-tab] {{ cursor:pointer; transition:transform .16s ease, border-color .16s ease; }}
    .bracket-match[data-tab]:hover {{ transform:translateY(-1px); border-color:#8aa39a; background:#fbfdfc; }}
    .bracket-match.is-complete {{ border-color:#b7d7c7; box-shadow:inset 3px 0 0 #137a53, 0 8px 18px rgba(1,10,20,.18); }}
    .bracket-match-head {{
      display:flex; justify-content:space-between; gap:8px; align-items:center; margin-bottom:7px; color:#647084; font-size:12px;
    }}
    .bracket-match-head b {{ color:#0f6b45; }}
    .bracket-match p {{ margin:7px 0 0; color:#647084; font-size:12px; font-weight:800; }}
    .bracket-slot-title {{ margin-bottom:8px; color:#647084; text-transform:uppercase; letter-spacing:0; font-size:11px; font-weight:900; }}
    .bracket-team {{
      display:grid; grid-template-columns:30px minmax(0,1fr) 28px 44px; gap:8px; align-items:center;
      min-height:42px; padding:6px 0; border-top:1px solid #edf2ef;
    }}
    .bracket-team:first-of-type {{ border-top:0; }}
    .bracket-team .flag {{ font-size:22px; line-height:1; }}
    .team-copy b {{ display:block; color:#122033; font-size:13px; }}
    .team-copy em {{ display:block; color:#647084; font-style:normal; font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .bracket-team strong {{ text-align:right; font-size:16px; color:#122033; }}
    .bracket-team small {{ justify-self:end; min-width:38px; text-align:center; padding:3px 5px; border-radius:3px; color:#647084; background:#eef2f6; font-size:11px; font-weight:900; }}
    .bracket-team.is-winner {{ background:#effaf1; margin:0 -6px; padding-left:6px; padding-right:6px; border-radius:4px; }}
    .bracket-team.is-winner b,.bracket-team.is-winner strong {{ color:#137a53; }}
    .bracket-team.is-winner small {{ background:#dcfce7; color:#166534; }}
    .bracket-team.is-eliminated {{ opacity:.56; }}
    .bracket-team.placeholder {{ color:#94a3b8; }}
    .bracket-team.placeholder .flag {{ color:#cbd5e1; }}
    .bracket-slot.is-ready {{ box-shadow:inset 3px 0 0 #c9972b, 0 8px 18px rgba(1,10,20,.18); }}
    .bracket-slot.is-half {{ box-shadow:inset 3px 0 0 #94a3b8, 0 8px 18px rgba(1,10,20,.18); }}
    .bracket-champion {{ text-align:center; min-height:190px; display:flex; flex-direction:column; justify-content:center; }}
    .champion-cup {{ font-size:38px; margin:4px 0 8px; }}
    .bracket-champion b {{ font-size:18px; color:#0b2033; }}
    .bracket-champion p {{ margin:8px 0 0; color:#647084; font-size:12px; line-height:1.5; }}
    .live-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
    .live-card {{
      background:#fff; border:1px solid var(--line); border-radius:5px;
      padding:13px; box-shadow:none;
    }}
    .live-card.is-live {{ border-color:#c9972b; box-shadow:none; }}
    .live-card-head {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }}
    .live-card-head h3 {{ margin:8px 0 4px; font-size:18px; color:#102a3f; }}
    .live-card-head p {{ margin:0; color:#647084; font-size:12px; }}
    .live-card-head strong {{ font-size:22px; color:#07111f; white-space:nowrap; }}
    .live-meta-line {{ margin-top:10px; padding:7px 9px; border-radius:4px; background:#f3f6fa; color:#334155; font-size:12px; font-weight:800; }}
    .mini-events {{ margin-top:10px; }}
    .live-detail-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:10px; }}
    .event-row {{ display:grid; grid-template-columns:48px 34px 1fr; gap:9px; align-items:start; padding:9px 0; border-bottom:1px solid #edf2ef; }}
    .event-row:last-child {{ border-bottom:0; }}
    .event-time {{ color:#647084; font-size:12px; font-weight:900; padding-top:4px; }}
    .event-icon {{
      display:inline-grid; place-items:center; width:30px; height:26px; border-radius:4px;
      background:#e6f2ef; color:#1f4f42; font-size:11px; font-weight:900;
    }}
    .event-icon.goal {{ background:#dcfce7; color:#166534; }}
    .event-icon.card-yellow {{ background:#fef3c7; color:#92400e; }}
    .event-icon.card-red {{ background:#fee2e2; color:#991b1b; }}
    .event-row b {{ display:block; color:#172033; font-size:13px; margin-bottom:2px; }}
    .event-row p {{ margin:0; color:#647084; font-size:12px; line-height:1.45; }}
    footer {{ max-width:1200px; margin:0 auto; padding:16px 22px 28px; color:#647084; font-size:12px; }}
    @media (max-width: 900px) {{
      .hero {{ min-height:auto; }}
      .hero-inner {{ padding:30px 14px 24px; }}
      header h1 {{ font-size:33px; }}
      .hero-board {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
      .hero-stat {{ padding:10px 11px; }}
      .hero-stat b {{ font-size:18px; }}
      .hero-matches {{ display:flex; overflow-x:auto; padding-bottom:4px; scroll-snap-type:x mandatory; }}
      .match-tile {{ flex:0 0 280px; min-height:124px; scroll-snap-align:start; }}
      main {{ padding:14px; }}
      .grid.four,.grid.two,.lineup-grid,.history-room,.radar-grid,.live-grid,.live-detail-grid,.source-grid,.command-center,.market-tile-grid,.consensus-grid,.settlement-grid,.desk-shell,.bracket-summary,.archive-card-grid {{ grid-template-columns:1fr; }}
      .desk-sidebar {{ position:static; }}
      .focus-top {{ flex-direction:column; }}
      .score-box {{ width:100%; text-align:left; }}
      .app-tabs,.tabs {{ overflow-x:auto; }}
      .app-tab,.tab {{ flex:0 0 auto; }}
      .match-head {{ flex-direction:column; }}
      .radar-head {{ flex-direction:column; }}
      .bar-row {{ grid-template-columns:110px 1fr; }}
      .bar-note {{ grid-column:2; text-align:left; }}
      .line-row {{ grid-template-columns:46px 1fr; padding:9px 10px; }}
      .data-room {{ padding:12px; }}
      table {{ font-size:12px; }}
      th,td {{ padding:8px 6px; }}
    }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="hero-inner">
      <p class="eyebrow">FIFA WORLD CUP 2026 · {SITE_TAGLINE.upper()}</p>
      <h1>{SITE_NAME}</h1>
      <p>賽前盤口、即時戰況、淘汰賽路徑與賽後結算 · Binance 為主，台灣運彩 / ESPN-DK 作參照 · 更新 {generated_at.strftime('%Y-%m-%d %H:%M')} 台灣時間</p>
      <div class="hero-board">
        <div class="hero-stat"><span>收錄賽事</span><b>8 場</b></div>
        <div class="hero-stat"><span>賽前盤口</span><b>30 分</b></div>
        <div class="hero-stat"><span>賽中戰況</span><b>5 分</b></div>
        <div class="hero-stat"><span>24h 檔案</span><b>{len(active_deep_matches)} 場</b></div>
      </div>
    </div>
  </header>
  <main>
    <nav class="app-tabs" aria-label="頁面分區">
      <button class="app-tab active" data-section="matches">總覽</button>
      <button class="app-tab" data-section="bracket">淘汰賽圖</button>
      <button class="app-tab" data-section="markets">盤口比較</button>
      <button class="app-tab" data-section="live">即時戰況</button>
      <button class="app-tab" data-section="settlement">賽果結算</button>
      <button class="app-tab" data-section="research">賽前檔案</button>
    </nav>

    <div class="desk-shell">
      <aside class="desk-sidebar" aria-label="16 強賽事清單">
        <div class="sidebar-head">
          <span class="panel-label">Round of 16</span>
          <h2>16 強對戰</h2>
          <p>固定賽程索引；右側依總覽、盤口、戰況與賽前檔案切換。</p>
        </div>
        <div class="side-list">{sidebar_matches}</div>
      </aside>

      <div class="desk-main">
        <section id="section-matches" class="home-panel active">
          <div class="section-title"><h2>總覽</h2><span>先看下一場，再看後續賽事</span></div>
          {dashboard}
          <div class="grid four">{overview_cards}</div>
          <div class="section-title"><h2>待開賽程</h2><span>遠期場先收一次；進入開賽前 24 小時才改為 30 分鐘更新</span></div>
          <div class="radar-grid">{extra_radar}</div>
        </section>

        <section id="section-bracket" class="home-panel">
          <div class="section-title"><h2>淘汰賽圖</h2><span>完賽後自動帶入晉級隊；未賽保留待定席位</span></div>
          {bracket_html}
          <p class="source-note">淘汰賽圖使用 ESPN scoreboard 寫入的比分、完賽狀態與 winner 欄位；若比賽進入延長賽或 PK，仍以官方與 Binance 結算規則確認最終晉級。</p>
        </section>

        <section id="section-markets" class="home-panel">
          <div class="section-title"><h2>盤口比較</h2><span>Binance 是主要執行盤，其他來源用來校對方向與價格品質</span></div>
          <div class="consensus-grid">{consensus_cards}</div>
          <div class="section-title sub"><h2>資料來源</h2><span>公開來源、自動化狀態與資料限制</span></div>
          <div class="source-grid">{market_source_cards}</div>
          <div class="section-title sub"><h2>全場盤口表</h2><span>所有收錄賽事的主盤、延伸盤與參考盤</span></div>
          <div class="table-card market-compare-card">
            <table>
              <thead><tr><th>比賽</th><th>Binance 90 分鐘主訊號</th><th>Binance 延伸盤</th><th>ESPN / DK 參考盤</th><th>台灣運彩公開盤</th></tr></thead>
              <tbody>{market_comparison}</tbody>
            </table>
            <p class="source-note">台灣運彩欄位使用官方公開 JSON 的返還倍率；Binance 欄位是交易型價格/機率，兩者抽水與結算規則不同，適合比方向，不宜直接當同一種賠率相減。</p>
          </div>
        </section>

        <section id="section-live" class="home-panel">
          <div class="section-title"><h2>即時戰況</h2><span>比分、進球、紅黃牌、犯規、射門、角球與 ESPN 即時狀態</span></div>
          <div class="live-grid">{live_center}</div>
          <div class="section-title"><h2>比賽時程</h2><span>台灣時間</span></div>
          <div class="table-card monitor-card">
            <table><thead><tr><th>時間</th><th>比賽</th><th>場地</th><th>主盤方向</th></tr></thead><tbody>{schedule_rows}</tbody></table>
          </div>
          <div class="section-title"><h2>更新規則</h2><span>賽前每 30 分鐘，賽中每 5 分鐘；完賽後停止盤口更新</span></div>
          <div class="table-card monitor-card">
            <table><thead><tr><th>比賽</th><th>階段</th><th>比分</th><th>ESPN 狀態</th><th>盤口更新</th><th>比分檢查</th><th>規則</th><th>賽後摘要</th></tr></thead><tbody>{monitor_rows}</tbody></table>
          </div>
        </section>

        <section id="section-settlement" class="home-panel">
          <div class="section-title"><h2>賽果結算</h2><span>用鎖定的 100U 建議組合對照完賽結果</span></div>
          <div class="callout">
            <h3>結算摘要</h3>
            <p>{safe(settlement_summary)} 90 分鐘勝負、讓球、晉級盤若涉及延長賽或 PK，仍以 Binance 實際結算為準。</p>
          </div>
          <div class="settlement-grid">{settlement_cards}</div>
        </section>

        <section id="section-research" class="home-panel">
          <div class="section-title"><h2>賽前檔案</h2><span>只顯示接下來 24 小時內未完賽或賽中場</span></div>
          {active_deep_block}
          {active_panels}
          {parked_deep_block}
          {parked_panels}
          {archive_deep_block}
          {archive_panels}
        </section>
      </div>
    </div>
  </main>
  <footer>
    {SITE_NAME} 是賽事、盤口與公開資訊整理工具，不保證獲利。Binance Prediction 價格會快速變動，下注前請用你畫面上的即時價格重算返還。
  </footer>
  <script>
    const appTabs = document.querySelectorAll('.app-tab');
    const homePanels = document.querySelectorAll('.home-panel');
    const tabButtons = document.querySelectorAll('.tab');
    const triggers = document.querySelectorAll('.tab, .match-tile, .today-match[data-tab], .side-match[data-tab], .settlement-jump[data-tab], .bracket-match[data-tab]');
    const panels = document.querySelectorAll('.match-panel');
    function activateSection(sectionId, shouldScroll) {{
      appTabs.forEach((b) => b.classList.toggle('active', b.dataset.section === sectionId));
      homePanels.forEach((p) => p.classList.toggle('active', p.id === 'section-' + sectionId));
      if (shouldScroll) {{
        document.getElementById('section-' + sectionId)?.scrollIntoView({{ behavior:'smooth', block:'start' }});
      }}
    }}
    function activateTab(tabId, shouldScroll) {{
      const activePanel = document.getElementById(tabId);
      if (!activePanel) return;
      activateSection('research', false);
      tabButtons.forEach((b) => b.classList.remove('active'));
      panels.forEach((p) => p.classList.remove('active'));
      const activeButton = document.querySelector(`.tab[data-tab="${{tabId}}"]`);
      if (activeButton) activeButton.classList.add('active');
      activePanel.classList.add('active');
      if (shouldScroll) {{
        document.getElementById('section-research')?.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }}
    }}
    appTabs.forEach((button) => {{
      button.addEventListener('click', () => activateSection(button.dataset.section, false));
    }});
    triggers.forEach((button) => {{
      button.addEventListener('click', () => {{
        const shouldScroll = button.classList.contains('match-tile') || button.classList.contains('today-match') || button.classList.contains('side-match') || button.classList.contains('settlement-jump') || button.classList.contains('bracket-match');
        activateTab(button.dataset.tab, shouldScroll);
      }});
    }});
    function updateCalculators() {{
      document.querySelectorAll('.stake-calc').forEach((calc) => {{
        const input = calc.querySelector('.calc-input');
        const total = Math.max(0, Number(input.value || 0));
        const scale = total / 100;
        calc.querySelectorAll('tbody tr').forEach((row) => {{
          const base = Number(row.dataset.base);
          const price = Number(row.dataset.price);
          const stake = base * scale;
          const returned = price > 0 ? stake / price : 0;
          const net = returned - stake;
          row.querySelector('.calc-stake').textContent = `${{stake.toFixed(2)}}U`;
          row.querySelector('.calc-return').textContent = `${{returned.toFixed(2)}}U`;
          const profitCell = row.querySelector('.calc-profit');
          profitCell.textContent = `${{net >= 0 ? '+' : ''}}${{net.toFixed(2)}}U`;
          profitCell.classList.toggle('good', net >= 0);
          profitCell.classList.toggle('bad', net < 0);
        }});
      }});
    }}
    document.querySelectorAll('.calc-input').forEach((input) => input.addEventListener('input', updateCalculators));
    updateCalculators();
  </script>
</body>
</html>
"""

OUT.mkdir(exist_ok=True)
PUBLIC.mkdir(parents=True, exist_ok=True)
out_path = OUT / "worldcup-r16-tabs-analysis.html"
out_path.write_text(doc, encoding="utf-8")
(PUBLIC / "worldcup-r16-tabs-analysis.html").write_text(doc, encoding="utf-8")
(PUBLIC / "index.html").write_text(doc, encoding="utf-8")
snapshot_copy = PUBLIC / "worldcup-r16-tabs-snapshot.csv"
snapshot_copy.write_text(snapshot_path.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
print(out_path)
print(PUBLIC / "index.html")
print(snapshot_path)
