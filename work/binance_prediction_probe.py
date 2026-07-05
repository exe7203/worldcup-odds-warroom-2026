import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
import urllib.request


BASE_URL = "https://api.binance.com"


def signed_get(path, params):
    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        raise SystemExit(
            "Missing BINANCE_API_KEY or BINANCE_API_SECRET environment variables."
        )

    payload = dict(params)
    payload["timestamp"] = int(time.time() * 1000)
    query = urllib.parse.urlencode(payload)
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
        raise SystemExit(f"HTTP {exc.code}: {body}") from exc


def print_market_topic(topic):
    print(f"\n[{topic.get('marketTopicId')}] {topic.get('title')}")
    print(f"vendor={topic.get('vendor')} status={topic.get('status')} volume={topic.get('tradeVolume')} liquidity={topic.get('liquidity')}")
    for market in topic.get("markets") or []:
        print(f"  marketId={market.get('marketId')} title={market.get('title')} trading={market.get('tradingStatus')}")
        for outcome in market.get("outcomes") or []:
            print(
                "    "
                f"{outcome.get('name')}: price={outcome.get('price')} "
                f"chance={outcome.get('chance')} tokenId={outcome.get('tokenId')}"
            )


def search(args):
    data = signed_get(
        "/sapi/v1/w3w/wallet/prediction/market/search",
        {"query": args.query, "topK": args.top_k},
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))


def list_markets(args):
    params = {"limit": args.limit, "offset": args.offset}
    if args.l1_category:
        params["l1Category"] = args.l1_category
    if args.l2_category:
        params["l2Category"] = args.l2_category
    if args.sort_by:
        params["sortBy"] = args.sort_by
    if args.order_by:
        params["orderBy"] = args.order_by

    data = signed_get("/sapi/v1/w3w/wallet/prediction/market/list", params)
    for topic in data.get("marketTopics", []):
        print_market_topic(topic)
    print(f"\ntotal={data.get('total')} hasMore={data.get('hasMore')}")


def detail(args):
    data = signed_get(
        "/sapi/v1/w3w/wallet/prediction/market/detail",
        {"marketTopicId": args.market_topic_id},
    )
    print_market_topic(data)


def order_book(args):
    data = signed_get(
        "/sapi/v1/w3w/wallet/prediction/order-book",
        {
            "vendor": args.vendor,
            "marketId": args.market_id,
            "tokenId": args.token_id,
        },
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Query Binance Web3 Prediction market data using signed API requests."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--top-k", type=int, default=20)
    search_parser.set_defaults(func=search)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--offset", type=int, default=0)
    list_parser.add_argument("--l1-category")
    list_parser.add_argument("--l2-category")
    list_parser.add_argument("--sort-by", default="RECOMMENDED")
    list_parser.add_argument("--order-by", default="DESC")
    list_parser.set_defaults(func=list_markets)

    detail_parser = subparsers.add_parser("detail")
    detail_parser.add_argument("market_topic_id", type=int)
    detail_parser.set_defaults(func=detail)

    book_parser = subparsers.add_parser("order-book")
    book_parser.add_argument("vendor")
    book_parser.add_argument("market_id", type=int)
    book_parser.add_argument("token_id")
    book_parser.set_defaults(func=order_book)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
