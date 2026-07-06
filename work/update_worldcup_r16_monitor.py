import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
STATE_PATH = WORK / "worldcup-r16-monitor-state.json"
TPE = timezone(timedelta(hours=8))
TAIWAN_SPORTS_LOTTERY_PAGE = "https://www.sportslottery.com.tw/sportsbook/world-cup"
TAIWAN_SPORTS_LOTTERY_DATA_URL = "https://blob3rd.sportslottery.com.tw/apidata/Pre/WC-Games.en.json"


MATCHES = [
    {
        "key": "can-mar",
        "title": "加拿大 vs 摩洛哥",
        "query": "Canada Morocco",
        "contains": ["Canada", "Morocco"],
        "output": "outputs/binance-canada-morocco-topics.json",
        "espn_id": "760502",
        "espn_dates": ["20260704"],
        "kickoff": "2026-07-05T01:00:00+08:00",
        "monitorMode": "active",
    },
    {
        "key": "par-fra",
        "title": "巴拉圭 vs 法國",
        "query": "Paraguay France",
        "contains": ["Paraguay", "France"],
        "output": "outputs/binance-paraguay-france-topics.json",
        "espn_id": "760503",
        "espn_dates": ["20260704"],
        "kickoff": "2026-07-05T05:00:00+08:00",
        "monitorMode": "active",
    },
    {
        "key": "bra-nor",
        "title": "巴西 vs 挪威",
        "query": "Brazil Norway",
        "contains": ["Brazil", "Norway"],
        "output": "outputs/binance-brazil-norway-topics.json",
        "espn_id": "760504",
        "espn_dates": ["20260705"],
        "kickoff": "2026-07-06T04:00:00+08:00",
        "monitorMode": "active",
    },
    {
        "key": "mex-eng",
        "title": "墨西哥 vs 英格蘭",
        "query": "Mexico England",
        "contains": ["Mexico", "England"],
        "output": "outputs/binance-mexico-england-topics.json",
        "espn_id": "760505",
        "espn_dates": ["20260705"],
        "kickoff": "2026-07-06T08:00:00+08:00",
        "monitorMode": "staged",
    },
    {
        "key": "por-esp",
        "title": "葡萄牙 vs 西班牙",
        "query": "Portugal Spain",
        "contains": ["Portugal", "Spain"],
        "output": "outputs/binance-portugal-spain-topics.json",
        "espn_id": "760506",
        "espn_dates": ["20260706"],
        "kickoff": "2026-07-07T03:00:00+08:00",
        "monitorMode": "staged",
    },
    {
        "key": "usa-bel",
        "title": "美國 vs 比利時",
        "query": "United States Belgium",
        "contains": ["United States", "Belgium"],
        "output": "outputs/binance-usa-belgium-topics.json",
        "espn_id": "760507",
        "espn_dates": ["20260706"],
        "kickoff": "2026-07-07T08:00:00+08:00",
        "monitorMode": "staged",
    },
    {
        "key": "arg-egy",
        "title": "阿根廷 vs 埃及",
        "query": "Argentina Egypt",
        "contains": ["Argentina", "Egypt"],
        "output": "outputs/binance-argentina-egypt-topics.json",
        "espn_id": "760509",
        "espn_dates": ["20260707"],
        "kickoff": "2026-07-08T00:00:00+08:00",
        "monitorMode": "staged",
    },
    {
        "key": "sui-col",
        "title": "瑞士 vs 哥倫比亞",
        "query": "Switzerland Colombia",
        "contains": ["Switzerland", "Colombia"],
        "output": "outputs/binance-switzerland-colombia-topics.json",
        "espn_id": "760508",
        "espn_dates": ["20260707"],
        "kickoff": "2026-07-08T04:00:00+08:00",
        "monitorMode": "staged",
    },
]


def now_tpe():
    return datetime.now(TPE)


def iso(dt):
    return dt.astimezone(TPE).replace(microsecond=0).isoformat()


def parse_iso(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(TPE)


def load_state():
    if not STATE_PATH.exists():
        return {"updatedAt": None, "matches": {}}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {"updatedAt": None, "matches": {}}


def save_state(state):
    WORK.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_json(url, retries=2, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_error = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.5 * (attempt + 1))
    raise last_error


TAIWAN_TEAM_ALIASES = {
    "United States": ["United States", "USA"],
    "Switzerland": ["Switzerland", "Swiss"],
}


def taiwan_aliases(name):
    return TAIWAN_TEAM_ALIASES.get(name, [name])


def selection_decimal_odds(selection):
    try:
        numerator = float(selection.get("pu"))
        denominator = float(selection.get("pd"))
    except (TypeError, ValueError):
        return None
    if denominator == 0:
        return None
    return 1 + numerator / denominator


def format_taiwan_selection(selection):
    odds = selection_decimal_odds(selection)
    if odds is None:
        return f"{selection.get('name', '-')}: -"
    return f"{selection.get('name', '-')}: {odds:.2f}x"


def find_taiwan_game(match, games):
    required = match.get("contains") or []
    for game in games:
        text = " ".join(str(game.get(key) or "") for key in ["bn", "hn", "an"]).lower()
        if all(any(alias.lower() in text for alias in taiwan_aliases(name)) for name in required):
            return game
    return None


def taiwan_market(game, predicate):
    for market in game.get("ms") or []:
        if predicate(market):
            return market
    return None


def summarize_taiwan_market(market, limit=5, sort_by_shortest=False):
    if not market:
        return ""
    selections = list(market.get("cs") or [])
    if sort_by_shortest:
        selections = sorted(selections, key=lambda item: selection_decimal_odds(item) or 999)
    return " / ".join(format_taiwan_selection(selection) for selection in selections[:limit])


def summarize_taiwan_game(game, checked_at):
    if not game:
        return None
    market_1x2 = taiwan_market(game, lambda market: str(market.get("ti")) == "1" or market.get("name") == "1x2")
    total_25 = taiwan_market(game, lambda market: "Total 2.5" in str(market.get("name") or ""))
    odd_even = taiwan_market(game, lambda market: "Odd/Even" in str(market.get("name") or ""))
    correct_score = taiwan_market(game, lambda market: "Correct Score" in str(market.get("name") or ""))
    return {
        "source": "Taiwan Sports Lottery",
        "status": "ok",
        "url": TAIWAN_SPORTS_LOTTERY_PAGE,
        "dataUrl": TAIWAN_SPORTS_LOTTERY_DATA_URL,
        "updatedAt": checked_at,
        "eventId": game.get("id"),
        "boardName": game.get("bn"),
        "kickoff": game.get("kt"),
        "marketCount": len(game.get("ms") or []),
        "markets": {
            "1x2": summarize_taiwan_market(market_1x2),
            "total2.5": summarize_taiwan_market(total_25),
            "oddEven": summarize_taiwan_market(odd_even),
            "correctScoreShort": summarize_taiwan_market(correct_score, limit=5, sort_by_shortest=True),
        },
    }


def update_from_taiwan_sports_lottery(state):
    checked_at = iso(now_tpe())
    try:
        games = fetch_json(TAIWAN_SPORTS_LOTTERY_DATA_URL)
    except Exception as exc:
        for match in MATCHES:
            item = state.setdefault("matches", {}).setdefault(match["key"], {})
            if item.get("completed") or item.get("status") == "finished":
                continue
            item["taiwanSportsLottery"] = {
                "source": "Taiwan Sports Lottery",
                "status": "error",
                "url": TAIWAN_SPORTS_LOTTERY_PAGE,
                "dataUrl": TAIWAN_SPORTS_LOTTERY_DATA_URL,
                "updatedAt": checked_at,
                "error": str(exc),
            }
        return state

    for match in MATCHES:
        item = state.setdefault("matches", {}).setdefault(match["key"], {})
        if item.get("completed") or item.get("status") == "finished":
            continue
        game = find_taiwan_game(match, games)
        summary = summarize_taiwan_game(game, checked_at)
        if summary:
            item["taiwanSportsLottery"] = summary
        else:
            item["taiwanSportsLottery"] = {
                "source": "Taiwan Sports Lottery",
                "status": "missing",
                "url": TAIWAN_SPORTS_LOTTERY_PAGE,
                "dataUrl": TAIWAN_SPORTS_LOTTERY_DATA_URL,
                "updatedAt": checked_at,
                "error": "World Cup public JSON did not include this match.",
            }
    return state


def load_espn_events(dates):
    events = {}
    for date in sorted(set(dates)):
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={date}"
        try:
            data = fetch_json(url, retries=3, timeout=20)
        except Exception as exc:  # ESPN occasionally drops live scoreboard requests.
            print(f"WARNING: ESPN scoreboard update failed for {date}: {exc}", file=sys.stderr)
            continue
        for event in data.get("events", []):
            events[event.get("id")] = event
    return events


def fetch_espn_summary(event_id):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={event_id}"
    try:
        return fetch_json(url)
    except Exception as exc:  # ESPN can be briefly unavailable around live updates.
        return {"_error": str(exc)}


def summarize_odds(odds):
    if not odds:
        return {}
    item = next((entry for entry in odds if isinstance(entry, dict)), {})
    if not item:
        return {}
    moneyline = item.get("moneyline") or {}
    spread = item.get("pointSpread") or {}
    total = item.get("total") or {}

    def close(side):
        node = side.get("close") if isinstance(side, dict) else None
        if not node:
            return ""
        line = node.get("line")
        odd = node.get("odds")
        return " ".join(str(x) for x in [line, odd] if x not in (None, ""))

    ml_parts = []
    for label, key in [("主", "home"), ("客", "away"), ("和", "draw")]:
        value = close(moneyline.get(key) or {})
        if value:
            ml_parts.append(f"{label} {value}")

    spread_parts = []
    for label, key in [("主", "home"), ("客", "away")]:
        value = close(spread.get(key) or {})
        if value:
            spread_parts.append(f"{label} {value}")

    total_parts = []
    for label, key in [("大", "over"), ("小", "under")]:
        value = close(total.get(key) or {})
        if value:
            total_parts.append(f"{label} {value}")

    return {
        "moneyline": " / ".join(ml_parts),
        "spread": " / ".join(spread_parts),
        "total": " / ".join(total_parts),
    }


def team_id_map(competition):
    mapping = {}
    for competitor in competition.get("competitors", []):
        team = competitor.get("team") or {}
        if team.get("id") and team.get("abbreviation"):
            mapping[str(team["id"])] = team["abbreviation"]
    return mapping


def competition_team_order(competition):
    ordered = []
    for competitor in competition.get("competitors", []):
        abbr = (competitor.get("team") or {}).get("abbreviation")
        if abbr:
            ordered.append(abbr)
    return ordered


def translate_event_type(detail):
    text = ((detail.get("type") or {}).get("text") or "").lower()
    if detail.get("redCard"):
        return "紅牌"
    if detail.get("yellowCard"):
        return "黃牌"
    if detail.get("ownGoal"):
        return "烏龍球"
    if detail.get("penaltyKick") and detail.get("scoringPlay"):
        return "點球進球"
    if detail.get("scoringPlay"):
        return "進球"
    if "substitution" in text:
        return "換人"
    return (detail.get("type") or {}).get("text") or "事件"


def extract_live_events(competition, limit=14):
    mapping = team_id_map(competition)
    events = []
    for detail in competition.get("details") or []:
        athletes = detail.get("athletesInvolved") or []
        player = athletes[0].get("displayName") if athletes else ""
        team_id = str((detail.get("team") or {}).get("id") or "")
        events.append(
            {
                "time": (detail.get("clock") or {}).get("displayValue") or "",
                "team": mapping.get(team_id, ""),
                "type": translate_event_type(detail),
                "rawType": (detail.get("type") or {}).get("text") or "",
                "player": player,
                "scoringPlay": bool(detail.get("scoringPlay")),
                "yellowCard": bool(detail.get("yellowCard")),
                "redCard": bool(detail.get("redCard")),
                "penaltyKick": bool(detail.get("penaltyKick")),
                "ownGoal": bool(detail.get("ownGoal")),
                "shootout": bool(detail.get("shootout")),
            }
        )
    return events[-limit:]


STAT_LABELS = {
    "totalShots": "射門",
    "shotsOnTarget": "射正",
    "possessionPct": "控球",
    "foulsCommitted": "犯規",
    "yellowCards": "黃牌",
    "redCards": "紅牌",
    "wonCorners": "角球",
    "offsides": "越位",
    "saves": "撲救",
}


def normalize_stat_value(name, value):
    if value in (None, ""):
        return "-"
    if name == "possessionPct" and "%" not in str(value):
        return f"{value}%"
    return str(value)


def extract_live_stats(summary):
    if not summary or summary.get("_error"):
        return {"teams": [], "rows": [], "sourceError": summary.get("_error") if summary else "missing summary"}
    boxscore = summary.get("boxscore") or {}
    teams = []
    values_by_stat = {name: {} for name in STAT_LABELS}
    for team_entry in boxscore.get("teams") or []:
        team = team_entry.get("team") or {}
        abbr = team.get("abbreviation")
        if not abbr:
            continue
        teams.append(abbr)
        for stat in team_entry.get("statistics") or []:
            name = stat.get("name")
            if name in values_by_stat:
                values_by_stat[name][abbr] = normalize_stat_value(name, stat.get("displayValue"))

    rows = []
    for name, label in STAT_LABELS.items():
        if any(value not in (None, "", "-") for value in values_by_stat[name].values()):
            rows.append({"name": name, "label": label, "values": values_by_stat[name]})
    return {"teams": teams, "rows": rows, "sourceError": None}


def card_counts(events, teams):
    counts = {team: {"yellow": 0, "red": 0} for team in teams}
    for event in events:
        team = event.get("team")
        if team not in counts:
            continue
        if event.get("yellowCard"):
            counts[team]["yellow"] += 1
        if event.get("redCard"):
            counts[team]["red"] += 1
    return counts


def event_score(event):
    competition = (event.get("competitions") or [{}])[0]
    teams = {}
    winner = None
    for competitor in competition.get("competitors", []):
        abbr = (competitor.get("team") or {}).get("abbreviation")
        if not abbr:
            continue
        try:
            score = int(competitor.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        teams[abbr] = score
        if competitor.get("winner"):
            winner = abbr
    return teams, winner


def build_result_summary(match, item, teams, winner):
    if not teams:
        return item.get("resultSummary") or ""
    score_display = item.get("scoreDisplay") or "比分未知"
    total_goals = sum(teams.values())
    btts = "Yes" if sum(1 for score in teams.values() if score > 0) >= 2 else "No"
    ou25 = "大 2.5" if total_goals > 2.5 else "小 2.5"
    ou35 = "大 3.5" if total_goals > 3.5 else "小 3.5"
    winner_text = winner or "待確認"
    return (
        f"完賽 {score_display}，勝方/晉級方：{winner_text}。"
        f"總進球 {total_goals}，{ou25}、{ou35}，BTTS {btts}。"
        "90 分鐘勝負與讓球若涉及延長/PK，仍需以 Binance 結算規則核對。"
    )


def update_from_espn(state):
    all_dates = [date for match in MATCHES for date in match["espn_dates"]]
    events = load_espn_events(all_dates)
    checked_at = iso(now_tpe())
    for match in MATCHES:
        item = state.setdefault("matches", {}).setdefault(match["key"], {})
        item.setdefault("title", match["title"])
        item.setdefault("kickoff", match["kickoff"])
        event = events.get(match["espn_id"])
        if not event:
            item["lastScoreCheck"] = checked_at
            item["espnStatus"] = "ESPN 尚未回傳賽事"
            continue

        competition = (event.get("competitions") or [{}])[0]
        status = competition.get("status") or event.get("status") or {}
        status_type = status.get("type") or {}
        teams, winner = event_score(event)
        order = competition_team_order(competition)
        score_display = "-"
        if teams:
            score_display = " ".join(f"{team} {teams[team]}" for team in order)

        should_fetch_summary = status_type.get("state") == "in" or bool(status_type.get("completed"))
        live_events = extract_live_events(competition)
        summary = fetch_espn_summary(match["espn_id"]) if should_fetch_summary else None
        live_stats = extract_live_stats(summary) if should_fetch_summary else {"teams": order, "rows": [], "sourceError": None}

        item["lastScoreCheck"] = checked_at
        item["espnStatus"] = status_type.get("shortDetail") or status_type.get("description") or "未知"
        item["espnState"] = status_type.get("state")
        item["clock"] = status.get("displayClock") if status_type.get("state") == "in" else ""
        item["completed"] = bool(status_type.get("completed"))
        item["scoreDisplay"] = score_display
        item["espnOdds"] = summarize_odds(competition.get("odds") or [])
        item["liveEvents"] = live_events
        item["liveStats"] = live_stats
        item["cardCounts"] = card_counts(live_events, order)
        item["liveDataUpdatedAt"] = checked_at

        if item["completed"]:
            item["status"] = "finished"
            item["winner"] = winner
            item["resultSummary"] = build_result_summary(match, item, teams, winner)
            item["finishedAt"] = item.get("finishedAt") or checked_at
        elif status_type.get("state") == "in":
            item["status"] = "live"
        else:
            item["status"] = "prematch"
    state["updatedAt"] = checked_at
    return state


def minutes_since(value, now):
    dt = parse_iso(value)
    if not dt:
        return None
    return (now - dt).total_seconds() / 60


def due_matches(state):
    due = []
    now = now_tpe()
    for match in MATCHES:
        item = state.get("matches", {}).get(match["key"], {})
        if item.get("completed") or item.get("status") == "finished":
            continue
        kickoff = parse_iso(match["kickoff"])
        is_live = item.get("espnState") == "in" or (kickoff and kickoff <= now <= kickoff + timedelta(hours=4))
        in_prematch_window = match.get("monitorMode") == "active" or (kickoff and now >= kickoff - timedelta(hours=24))
        if is_live:
            last = minutes_since(item.get("lastLiveOddsUpdate"), now)
            if last is None or last >= 5:
                due.append({**match, "phase": "live"})
        elif in_prematch_window:
            last = minutes_since(item.get("lastPrematchOddsUpdate"), now)
            if last is None or last >= 30:
                due.append({**match, "phase": "prematch"})
        elif not item.get("lastPrematchOddsUpdate"):
            due.append({**match, "phase": "initial"})
    return due


def mark_odds(keys):
    state = load_state()
    stamp = iso(now_tpe())
    for key in keys:
        item = state.setdefault("matches", {}).setdefault(key, {})
        phase = item.get("status")
        item["lastOddsUpdate"] = stamp
        if phase == "live":
            item["lastLiveOddsUpdate"] = stamp
        else:
            item["lastPrematchOddsUpdate"] = stamp
    state["updatedAt"] = stamp
    save_state(state)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mark-odds", nargs="*", default=None)
    args = parser.parse_args()

    if args.mark_odds is not None:
        mark_odds(args.mark_odds)
        print(json.dumps({"marked": args.mark_odds}, ensure_ascii=True))
        return

    state = load_state()
    state = update_from_espn(state)
    state = update_from_taiwan_sports_lottery(state)
    save_state(state)
    print(json.dumps({"due": due_matches(state), "state": str(STATE_PATH)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
