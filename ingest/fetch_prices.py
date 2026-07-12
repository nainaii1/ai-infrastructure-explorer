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
from dotenv_util import _load_dotenv

ING = pathlib.Path(__file__).resolve().parent
STORE = ING / "store"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=3mo&interval=1d"
QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote?symbols={syms}&crumb={crumb}"

# FMP's free tier (250 calls/day) covers /stable/profile (price + market cap +
# currency) but NOT historical/price-change endpoints (those return HTTP 402,
# verified 2026-07). So FMP is the primary source for price/marketCap; Yahoo
# stays the (best-effort, no key) source for chg7d/chg1m, which needs history.
FMP_PROFILE_URL = "https://financialmodelingprep.com/stable/profile?symbol={sym}&apikey={key}"
FMP_REQUEST_DELAY_SECONDS = 0.3

# Yahoo rate-limits (HTTP 429) aggressively if a burst of requests looks
# automated. Pacing between per-symbol chart requests + exponential backoff
# on 429 keeps a run of ~80-100 tickers under that threshold.
REQUEST_DELAY_SECONDS = 1.5

# Non-tracked symbols fetched purely as benchmarks for the calls ledger
# (performance.html). Stored in prices.json under their own symbol.
BENCHMARK_SYMBOLS = ("SMH",)
BASE_BACKOFF_SECONDS = 2.0
MAX_BACKOFF_SECONDS = 30.0


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


def _retry_delay(attempt, retry_after=None):
    """Seconds to wait before retrying. Honors a Retry-After header when
    Yahoo sends one; otherwise exponential backoff capped at MAX_BACKOFF_SECONDS."""
    if retry_after is not None:
        try:
            return float(retry_after)
        except (TypeError, ValueError):
            pass  # not a valid header value — fall through to backoff
    return min(BASE_BACKOFF_SECONDS * (2 ** attempt), MAX_BACKOFF_SECONDS)


def _http_json(url, opener=None, retries=5, sleep_fn=time.sleep):
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
                sleep_fn(_retry_delay(attempt, exc.headers.get("Retry-After")))
                continue
            raise


def _pct(now, then):
    if now is None or then in (None, 0):
        return None
    return round((now / then - 1.0) * 100.0, 2)


def fetch_chart(symbol, opener=None, retries=5):
    """Return {price, currency, chg7d, chg1m} from the (key-free) chart API."""
    data = _http_json(CHART_URL.format(sym=urllib.parse.quote(symbol)), opener=opener, retries=retries)
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


def _parse_quote_batch(data):
    """{symbol: marketCap} for every result row that has one. Pure — no I/O."""
    rows = data.get("quoteResponse", {}).get("result") or []
    out = {}
    for row in rows:
        sym = row.get("symbol")
        cap = row.get("marketCap")
        if sym and cap is not None:
            out[sym] = cap
    return out


def _parse_fmp_profile(data):
    """{price, marketCap, currency} from an FMP /stable/profile response, or
    None if it's not a usable single-row list (empty match, or an error dict
    like {"Error Message": ...}). Pure — no I/O."""
    if not isinstance(data, list) or not data:
        return None
    row = data[0]
    return {"price": row.get("price"), "marketCap": row.get("marketCap"), "currency": row.get("currency")}


def fetch_fmp_profile(symbol, api_key, opener=None, sleep_fn=time.sleep):
    """One FMP /stable/profile lookup. Returns None (never raises) on any
    failure — unmatched symbol, premium-gated (402), or transient error —
    so a caller can fall back to Yahoo without special-casing exceptions."""
    url = FMP_PROFILE_URL.format(sym=urllib.parse.quote(symbol), key=urllib.parse.quote(api_key))
    try:
        data = _http_json(url, opener=opener, retries=1, sleep_fn=sleep_fn)
        return _parse_fmp_profile(data)
    except Exception as exc:
        print("  ! FMP profile {}: {}".format(symbol, exc), file=sys.stderr)
        return None


def fetch_marketcaps_batch(symbols, opener, crumb):
    """One request for every symbol's market cap (Yahoo's quote endpoint
    accepts a comma-joined symbol list) instead of one request per ticker —
    cuts request volume roughly in half and is far less likely to 429."""
    if not crumb or not symbols:
        return {}
    try:
        url = QUOTE_URL.format(syms=urllib.parse.quote(",".join(symbols)),
                                crumb=urllib.parse.quote(crumb))
        return _parse_quote_batch(_http_json(url, opener=opener))
    except Exception as exc:
        print("  ! batch market cap fetch failed: {}".format(exc), file=sys.stderr)
        return {}


def _load_prices():
    path = STORE / "prices.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
    return {}


def run():
    _load_dotenv()
    fmp_key = os.environ.get("FMP_API_KEY")

    tickers = _load("tickers.json")
    # Benchmark quote for the calls ledger (performance.html's vs-SMH column).
    # Fetched exactly like a ticker; stored in prices.json under its symbol.
    tracked = {t["ticker"] for t in tickers}
    for bench in BENCHMARK_SYMBOLS:
        if bench not in tracked:
            tickers = tickers + [{"ticker": bench}]

    opener, crumb = _crumb_opener()
    prices = _load_prices()  # keep prior snapshot; only overwrite what succeeds
    ok, failed = 0, []
    asof = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    symbols = [t.get("yahooSymbol") or t["ticker"] for t in tickers]
    # Yahoo's batched quote (marketCap fallback for anything FMP misses).
    marketcaps = fetch_marketcaps_batch(symbols, opener, crumb)  # 1 request, not N

    results = {}
    for t in tickers:
        sym = t.get("yahooSymbol") or t["ticker"]
        row = {}

        # Primary source: FMP /stable/profile — exact price + market cap +
        # currency, reliable (no key-free rate-limit roulette). Best-effort:
        # None for symbols FMP doesn't carry (e.g. some OTC tickers).
        if fmp_key:
            fmp = fetch_fmp_profile(sym, fmp_key)
            if fmp:
                row["price"] = fmp["price"]
                row["marketCap"] = fmp["marketCap"]
                row["currency"] = fmp["currency"]
            time.sleep(FMP_REQUEST_DELAY_SECONDS)

        # Yahoo chart — the only source for chg7d/chg1m (needs history, which
        # FMP's free tier doesn't expose). Also backfills price/marketCap/
        # currency when FMP had nothing for this symbol. Best-effort only:
        # fail fast (1 retry, not 5) so an unreliable Yahoo can't stall the
        # whole run — FMP already carries price/marketCap either way.
        try:
            chart = fetch_chart(sym, opener=opener, retries=1)
            if chart:
                for field in ("price", "currency", "chg7d", "chg1m"):
                    row.setdefault(field, chart.get(field))
                row.setdefault("marketCap", marketcaps.get(sym))
        except Exception as exc:
            print("  ! {}: {}".format(sym, exc), file=sys.stderr)
        time.sleep(REQUEST_DELAY_SECONDS)  # be polite to Yahoo (avoid 429 rate limiting)

        if row.get("price") is not None:
            row["asOf"] = asof
            results[t["ticker"]] = row
            ok += 1
        else:
            failed.append(t["ticker"])

    prices.update(results)
    _save("prices.json", prices)
    gen.write_data_js()
    summary = {"updated": ok, "failed": failed, "asOf": asof}
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    run()
