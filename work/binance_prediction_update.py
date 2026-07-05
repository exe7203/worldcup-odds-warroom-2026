import argparse
import csv
import datetime as dt
import hashlib
import hmac
import html
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "https://api.binance.com"
ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
CSV_PATH = OUTPUTS / "binance-prediction-odds-history.csv"
HTML_PATH = OUTPUTS / "binance-prediction-odds-chart.html"
JSON_PATH = OUTPUTS / "binance-prediction-latest.json"


def signed_get(path, params):
    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        raise RuntimeError(
            "Missing BINANCE_API_KEY or BINANCE_API_SECRET. "
            "Set them in the current shell before running this script."
        )

    payload = dict(params)
    payload["timestamp"] = int(time.time() * 1000)
    query = urllib.parse.urlencode(payload, quote_via=urllib.parse.quote)
    signature = hmac.new(
        api_secret.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    url = f"{BASE_URL}{path}?{query}&signature={signature}"

    request = urllib.request.Request(url, headers={"X-MBX-APIKEY": api_key})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        headers = "\n".join(f"{k}: {v}" for k, v in exc.headers.items())
        raise RuntimeError(f"HTTP {exc.code}\n{headers}\n{body}") from exc


def search_market(query, top_k):
    return signed_get(
        "/sapi/v1/w3w/wallet/prediction/market/search",
        {"query": query, "topK": top_k},
    )


def market_detail(market_topic_id):
    return signed_get(
        "/sapi/v1/w3w/wallet/prediction/market/detail",
        {"marketTopicId": market_topic_id},
    )


def topics_from_search(data):
    if isinstance(data, dict):
        if isinstance(data.get("marketTopics"), list):
            return data["marketTopics"]
        if isinstance(data.get("data"), dict) and isinstance(data["data"].get("marketTopics"), list):
            return data["data"]["marketTopics"]
        if isinstance(data.get("data"), list):
            return data["data"]
    if isinstance(data, list):
        return data
    return []


def choose_topic(topics, query):
    query_terms = [term.lower() for term in query.replace("vs", " ").split() if term.strip()]
    best = None
    best_score = -1
    for topic in topics:
        title = str(topic.get("title") or topic.get("name") or "")
        lowered = title.lower()
        score = sum(1 for term in query_terms if term in lowered)
        if score > best_score:
            best = topic
            best_score = score
    return best


def flatten(topic):
    rows = []
    topic_id = topic.get("marketTopicId") or topic.get("id")
    topic_title = topic.get("title") or topic.get("name") or ""
    vendor = topic.get("vendor") or ""
    status = topic.get("status") or topic.get("tradingStatus") or ""
    for market in topic.get("markets") or []:
        market_id = market.get("marketId") or market.get("id")
        market_title = market.get("title") or market.get("name") or ""
        market_status = market.get("tradingStatus") or market.get("status") or ""
        for outcome in market.get("outcomes") or []:
            rows.append({
                "market_topic_id": topic_id,
                "topic_title": topic_title,
                "vendor": vendor,
                "topic_status": status,
                "market_id": market_id,
                "market_title": market_title,
                "market_status": market_status,
                "outcome_name": outcome.get("name") or outcome.get("title") or "",
                "token_id": outcome.get("tokenId") or "",
                "price": outcome.get("price"),
                "chance": outcome.get("chance"),
            })
    return rows


def normalize_float(value):
    if value is None or value == "":
        return ""
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def append_history(rows):
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    fieldnames = [
        "timestamp",
        "market_topic_id",
        "topic_title",
        "vendor",
        "topic_status",
        "market_id",
        "market_title",
        "market_status",
        "outcome_name",
        "token_id",
        "price",
        "chance",
    ]
    exists = CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        for row in rows:
            serialized = dict(row)
            serialized["timestamp"] = timestamp
            serialized["price"] = normalize_float(serialized["price"])
            serialized["chance"] = normalize_float(serialized["chance"])
            writer.writerow(serialized)


def read_history():
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def render_html(history):
    grouped = {}
    for row in history:
        key = f"{row.get('market_title')} | {row.get('outcome_name')}"
        grouped.setdefault(key, []).append(row)

    payload = json.dumps(grouped, ensure_ascii=False)
    latest_rows = history[-40:]
    table_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(row.get('timestamp', ''))}</td>"
        f"<td>{html.escape(row.get('market_title', ''))}</td>"
        f"<td>{html.escape(row.get('outcome_name', ''))}</td>"
        f"<td>{html.escape(row.get('price', ''))}</td>"
        f"<td>{html.escape(row.get('chance', ''))}</td>"
        "</tr>"
        for row in latest_rows
    )
    content = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Binance Prediction 盤口折線</title>
  <style>
    body {{ margin: 0; font-family: "Microsoft JhengHei", Arial, sans-serif; background: #f6f7fb; color: #172033; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px 18px; }}
    h1 {{ margin: 0 0 8px; font-size: 26px; }}
    p {{ color: #647084; }}
    .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 16px 0; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06); }}
    svg {{ width: 100%; height: 420px; display: block; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid #e2e8f0; padding: 8px; text-align: left; }}
    th {{ background: #f8fafc; }}
    .muted {{ color: #647084; font-size: 13px; }}
  </style>
</head>
<body>
  <main>
    <h1>Binance Prediction 盤口折線</h1>
    <p>資料來自 Binance Prediction API。price/chance 欄位依官方回傳為準；不同市場的 price 含義可能不同。</p>
    <section class="card">
      <h2>Outcome Chance / Price 歷史</h2>
      <svg id="chart"></svg>
      <p class="muted">目前先畫 chance；若 chance 缺值則跳過該點。每次執行更新腳本會追加資料。</p>
    </section>
    <section class="card">
      <h2>最新資料</h2>
      <table>
        <thead><tr><th>時間</th><th>市場</th><th>選項</th><th>price</th><th>chance</th></tr></thead>
        <tbody>{table_rows}</tbody>
      </table>
    </section>
  </main>
  <script>
    const grouped = {payload};
    const svg = document.getElementById("chart");
    const width = 1100, height = 420;
    const margin = {{ top: 24, right: 220, bottom: 42, left: 54 }};
    svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
    const colors = ["#2563eb", "#059669", "#dc2626", "#b45309", "#7c3aed", "#0891b2", "#be123c", "#4d7c0f"];
    const series = Object.entries(grouped).map(([name, rows], index) => ({{
      name,
      color: colors[index % colors.length],
      points: rows.map(row => ({{ t: row.timestamp, v: Number(row.chance) }})).filter(p => Number.isFinite(p.v))
    }})).filter(s => s.points.length);
    const all = series.flatMap(s => s.points);
    const xs = [...new Set(all.map(p => p.t))];
    const minY = 0, maxY = 1;
    function x(t) {{ return margin.left + (xs.length <= 1 ? 0 : xs.indexOf(t) * ((width - margin.left - margin.right) / (xs.length - 1))); }}
    function y(v) {{ return margin.top + (maxY - v) / (maxY - minY) * (height - margin.top - margin.bottom); }}
    function el(tag, attrs, text) {{
      const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
      for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
      if (text) node.textContent = text;
      svg.appendChild(node);
      return node;
    }}
    for (let i = 0; i <= 5; i++) {{
      const val = i / 5;
      const yy = y(val);
      el("line", {{ x1: margin.left, y1: yy, x2: width - margin.right, y2: yy, stroke: "#d7dde8" }});
      el("text", {{ x: margin.left - 8, y: yy + 4, "text-anchor": "end", fill: "#647084", "font-size": 12 }}, val.toFixed(1));
    }}
    el("line", {{ x1: margin.left, y1: height - margin.bottom, x2: width - margin.right, y2: height - margin.bottom, stroke: "#94a3b8" }});
    series.forEach((s, i) => {{
      const d = s.points.map((p, idx) => `${{idx ? "L" : "M"}} ${{x(p.t)}} ${{y(p.v)}}`).join(" ");
      el("path", {{ d, fill: "none", stroke: s.color, "stroke-width": 2.5, "stroke-linecap": "round", "stroke-linejoin": "round" }});
      s.points.forEach(p => el("circle", {{ cx: x(p.t), cy: y(p.v), r: 4, fill: "#fff", stroke: s.color, "stroke-width": 2 }}));
      el("text", {{ x: width - margin.right + 16, y: margin.top + 18 + i * 18, fill: s.color, "font-size": 12 }}, s.name.slice(0, 46));
    }});
    xs.forEach((t, i) => {{
      if (i % Math.max(1, Math.ceil(xs.length / 6)) === 0) {{
        el("text", {{ x: x(t), y: height - 14, "text-anchor": "middle", fill: "#647084", "font-size": 11 }}, t.slice(11, 16));
      }}
    }});
  </script>
</body>
</html>
"""
    HTML_PATH.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="Australia Egypt")
    parser.add_argument("--topic-id", type=int)
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()

    if args.topic_id:
        topic = market_detail(args.topic_id)
    else:
        search_data = search_market(args.query, args.top_k)
        topics = topics_from_search(search_data)
        if not topics:
            raise RuntimeError(f"No Binance prediction markets found for query: {args.query}")
        selected = choose_topic(topics, args.query)
        topic_id = selected.get("marketTopicId") or selected.get("id")
        if topic_id:
            topic = market_detail(topic_id)
        else:
            topic = selected

    rows = flatten(topic)
    if not rows:
        JSON_PATH.write_text(json.dumps(topic, ensure_ascii=False, indent=2), encoding="utf-8")
        raise RuntimeError("Market found, but no outcomes were returned. Raw response saved to latest JSON.")

    JSON_PATH.write_text(json.dumps(topic, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history(rows)
    render_html(read_history())

    print(f"updated_rows={len(rows)}")
    print(f"csv={CSV_PATH}")
    print(f"html={HTML_PATH}")
    for row in rows[:12]:
        print(
            f"{row['market_title']} | {row['outcome_name']} "
            f"price={row['price']} chance={row['chance']}"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
