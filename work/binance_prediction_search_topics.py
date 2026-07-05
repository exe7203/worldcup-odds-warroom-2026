import argparse
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
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
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Binance HTTP {exc.code}: {body}") from exc


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
    parser.add_argument("--query", required=True)
    parser.add_argument("--contains", nargs="*", default=[])
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data = signed_get(
        "/sapi/v1/w3w/wallet/prediction/market/search",
        {"query": args.query, "topK": args.top_k},
    )
    topics = topics_from_search(data)
    filtered = []
    needles = [s.lower() for s in args.contains]
    for topic in topics:
        haystack = json.dumps(topic, ensure_ascii=False).lower()
        if all(n in haystack for n in needles):
            filtered.append(topic)

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"topics={len(filtered)}")
    for topic in filtered:
        print(f"\n[{topic.get('marketTopicId')}] {topic.get('title')} volume={topic.get('tradeVolume')} liquidity={topic.get('liquidity')}")
        for market in (topic.get("markets") or [])[:16]:
            outcomes = ", ".join(f"{o.get('name')}={o.get('price')}/{o.get('chance')}" for o in market.get("outcomes", []))
            print(f"  {market.get('title')}: {outcomes}")


if __name__ == "__main__":
    main()
