"""Fetch weekly prices from Yahoo Finance (server-side) and bake them into data.js.

Why server-side: the app is offline/file:// and browsers block Yahoo via CORS,
so quotes cannot be fetched from the page. This script (run weekly, by the
Watchlist "Fetch prices" button via serve.py, or `python3 fetch_prices.py`)
writes store/prices.json and regenerates ../data.js. The table then reads the
baked-in price / 7d% / 1M% / market-cap / asOf fields offline.

No API key required. Uses only the standard library.
Per-ticker failures are isolated — one bad symbol never breaks the run.
"""

import os
import ssl
import sys
import json
import time
import pathlib
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar
from datetime import datetime, timezone

import generate_data_js as gen

ING = pathlib.Path(__file__).resolve().parent
STORE = ING / "store"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=3mo&interval=1d"


def _ssl_context():
    """A verifying SSL context backed by a real CA bundle. Some Python builds
    (notably python.org macOS) ship without a configured store, so fall back to
    the system bundle / certifi. Verification stays ON in every case."""
    candidates = [ssl.get_default_verify_paths().cafile, "/etc/ssl/cert.pem"]
    try:
        import certifi
        candidates.append(certifi.where())
    except Exception:
        pass
    for ca in candidates:
        if ca and os.path.exists(ca):
            try:
                return ssl.create_default_context(cafile=ca)
            except Exception:
                continue
    return ssl.create_default_context()


SSL_CTX = _ssl_context()


def _load(name):
    return json.loads((STORE / name).read_text(encoding="utf-8"))


def _save(name, data):
    (STORE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _http_json(url, opener=None, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(retries + 1):
        try:
            if opener is not None:
                resp = opener.open(req, timeout=20)      # opener carries the SSL ctx
            else:
                resp = urllib.request.urlopen(req, timeout=20, context=SSL_CTX)
            with resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries:    # rate limited — back off
                time.sleep(3 * (attempt + 1))
                continue
            raise


def _pct(now, then):
    if now is None or then in (None, 0):
        return None
    return round((now / then - 1.0) * 100.0, 2)


def fetch_chart(symbol):
    """Return {price, currency, chg7d, chg1m} from the (key-free) chart API."""
    data = _http_json(CHART_URL.format(sym=urllib.parse.quote(symbol)))
    result = (data.get("chart", {}).get("result") or [None])[0]
    if not result:
        return None
    meta = result.get("meta", {})
    ts = result.get("timestamp") or []
    closes = (result.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    pairs = [(t, c) for t, c in zip(ts, closes) if c is not None]
    if not pairs:
        return None
    price = meta.get("regularMarketPrice") or pairs[-1][1]
    now_s = pairs[-1][0]

    def close_near(days_ago):
        target = now_s - days_ago * 86400
        best = min(pairs, key=lambda p: abs(p[0] - target))
        return best[1]

    return {
        "price": round(price, 4),
        "currency": meta.get("currency"),
        "chg7d": _pct(price, close_near(7)),
        "chg1m": _pct(price, close_near(30)),
    }


def _crumb_opener():
    """Best-effort cookie+crumb so we can read marketCap from the quote API."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPSHandler(context=SSL_CTX),
    )
    try:
        opener.open(urllib.request.Request("https://fc.yahoo.com", headers={"User-Agent": UA}), timeout=10)
    except Exception:
        pass
    try:
        req = urllib.request.Request("https://query2.finance.yahoo.com/v1/test/getcrumb",
                                     headers={"User-Agent": UA})
        with opener.open(req, timeout=10) as r:
            crumb = r.read().decode("utf-8").strip()
        return opener, crumb
    except Exception:
        return opener, None


def fetch_marketcap(symbol, opener, crumb):
    if not crumb:
        return None
    try:
        url = ("https://query1.finance.yahoo.com/v7/finance/quote?symbols={sym}&crumb={crumb}"
               .format(sym=urllib.parse.quote(symbol), crumb=urllib.parse.quote(crumb)))
        data = _http_json(url, opener=opener)
        rows = data.get("quoteResponse", {}).get("result") or []
        return rows[0].get("marketCap") if rows else None
    except Exception:
        return None


def _load_prices():
    path = STORE / "prices.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
    return {}


def run():
    tickers = _load("tickers.json")
    opener, crumb = _crumb_opener()
    prices = _load_prices()  # keep prior snapshot; only overwrite what succeeds
    ok, failed = 0, []
    asof = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for t in tickers:
        sym = t.get("yahooSymbol") or t["ticker"]
        try:
            chart = fetch_chart(sym)
            if not chart:
                failed.append(t["ticker"])
                continue
            chart["marketCap"] = fetch_marketcap(sym, opener, crumb)
            chart["asOf"] = asof
            prices[t["ticker"]] = chart
            ok += 1
        except Exception as exc:
            failed.append(t["ticker"])
            print("  ! {}: {}".format(sym, exc), file=sys.stderr)
        time.sleep(1.0)  # be polite to Yahoo (avoid 429 rate limiting)

    _save("prices.json", prices)
    gen.write_data_js()
    summary = {"updated": ok, "failed": failed, "asOf": asof}
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    run()
