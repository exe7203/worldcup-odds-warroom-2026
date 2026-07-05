import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error


def request(url, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=20) as response:
            print(f"{url} -> HTTP {response.status}")
            print(response.read().decode("utf-8")[:1000])
    except urllib.error.HTTPError as exc:
        print(f"{url} -> HTTP {exc.code}")
        print(exc.read().decode("utf-8", errors="replace")[:1000])
    except Exception as exc:
        print(f"{url} -> ERROR {type(exc).__name__}: {exc}")


def signed_url(path, params):
    api_secret = os.environ.get("BINANCE_API_SECRET", "")
    payload = dict(params)
    payload["timestamp"] = int(time.time() * 1000)
    query = urllib.parse.urlencode(payload)
    signature = hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    return f"https://api.binance.com{path}?{query}&signature={signature}"


api_key = os.environ.get("BINANCE_API_KEY", "")

request("https://api.binance.com/api/v3/time")
request(
    signed_url("/sapi/v1/w3w/wallet/prediction/market/search", {"query": "Australia Egypt", "topK": 5}),
    {"X-MBX-APIKEY": api_key},
)
