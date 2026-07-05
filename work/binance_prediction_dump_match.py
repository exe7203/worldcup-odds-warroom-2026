import argparse
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "https://api.binance.com"
ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"


def signed_get(path, params):
    api_key = os.environ["BINANCE_API_KEY"]
    api_secret = os.environ["BINANCE_API_SECRET"]
    payload = dict(params)
    payload["timestamp"] = int(time.time() * 1000)
    query = urllib.parse.urlencode(payload, quote_via=urllib.parse.quote)
    signature = hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{path}?{query}&signature={signature}"
    req = urllib.request.Request(url, headers={"X-MBX-APIKEY": api_key})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def topics_from_search(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("marketTopics"), list):
            return data["marketTopics"]
        if isinstance(data.get("data"), list):
            return data["data"]
        if isinstance(data.get("data"), dict) and isinstance(data["data"].get("marketTopics"), list):
            return data["data"]["marketTopics"]
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="Australia Egypt")
    parser.add_argument("--top-k", type=int, default=30)
    args = parser.parse_args()

    data = signed_get(
        "/sapi/v1/w3w/wallet/prediction/market/search",
        {"query": args.query, "topK": args.top_k},
    )
    topics = topics_from_search(data)
    match_topics = []
    for topic in topics:
        title = str(topic.get("title") or "")
        if "Australia" in title and "Egypt" in title:
            match_topics.append(topic)

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / "binance-australia-egypt-topics.json"
    out_path.write_text(json.dumps(match_topics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"topics={len(match_topics)}")
    for topic in match_topics:
        print(f"\n[{topic.get('marketTopicId')}] {topic.get('title')} volume={topic.get('tradeVolume')} liquidity={topic.get('liquidity')}")
        markets = topic.get("markets") or []
        for market in markets[:12]:
            yes = next((o for o in market.get("outcomes", []) if o.get("name") == "Yes"), None)
            if yes:
                print(f"  {market.get('title')}: yes_price={yes.get('price')} chance={yes.get('chance')}")
            else:
                outcomes = ", ".join(f"{o.get('name')}={o.get('price')}/{o.get('chance')}" for o in market.get("outcomes", []))
                print(f"  {market.get('title')}: {outcomes}")
        if len(markets) > 12:
            print(f"  ... {len(markets) - 12} more markets")


if __name__ == "__main__":
    main()
