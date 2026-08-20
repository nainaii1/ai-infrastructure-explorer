"""Fetch prices from the operator's Google Sheet (GOOGLEFINANCE) and bake
them into data.js.

Why a sheet: Yahoo's key-free endpoints rate-limit (HTTP 429) so aggressively
that most runs failed. GOOGLEFINANCE formulas in a Google Sheet keep price,
market cap, currency, and 1W/1M/1Y change continuously fresh on Google's
side; this script just downloads the sheet's public CSV export (one request,
no key, no rate limits), writes store/prices.json, and regenerates ../data.js.
The watchlist then reads the baked-in fields offline.

Run it any time: `python3 ingest/fetch_prices.py`, the Watchlist "Fetch
prices" button via serve.py, or the launchd agent (see docs/GUIDE.md).
Tickers missing from the sheet are reported, never guessed.
"""

import os
import csv
import io
import json
import pathlib
import urllib.request
from datetime import datetime, timezone

import generate_data_js as gen
from dotenv_util import _load_dotenv
from store_io import load_json as _load, save_json, ssl_context as _ssl_context

ING = pathlib.Path(__file__).resolve().parent
STORE = ING / "store"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

SHEET_ID = "1Zeqqq01H1KiSvJnNArm0kr2rcn-F3FV8uxYjjX8mihA"
DEFAULT_SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/{}/export?format=csv".format(SHEET_ID)
)

# Sheet column -> prices.json field. Chg columns are optional (they exist
# once the operator adds the GOOGLEFINANCE history formulas to the sheet).
CHG_COLUMNS = {"Chg1W": "chg7d", "Chg1M": "chg1m", "Chg1Y": "chg1y"}

# Optional USD-normalised returns, same deal as MarketCapUSD. A local-currency
# percentage change is NOT the same quantity as a USD one for a USD/MYR-based
# operator: SIVE prices in SEK, so its 1M move blends the stock with the krona.
# Until these columns exist the app must label such names as local-currency
# rather than pool them into a cross-market comparison. See docs/GUIDE.
CHG_USD_COLUMNS = {"Chg1WUSD": "chg7dUSD", "Chg1MUSD": "chg1mUSD",
                   "Chg1YUSD": "chg1yUSD"}

# Benchmark for the calls ledger (performance.html). Read from its own sheet
# row and stored in prices.json under its symbol, exactly like a ticker.
BENCHMARK_SYMBOLS = ("SMH",)

# Optional fields that should carry forward from the prior snapshot when the
# sheet doesn't supply them this round, same as currency already does below.
# GOOGLEFINANCE history formulas across a large sheet intermittently return
# blank while Google recalculates (a bulk edit is exactly what triggers this) —
# without carrying forward, one flaky fetch wipes every optional field for
# every ticker the sheet went quiet on, discarding real history for no reason.
_CARRY_FORWARD_FIELDS = ("chg7d", "chg1m", "chg1y", "marketCapUSD",
                         "chg7dUSD", "chg1mUSD", "chg1yUSD")


SSL_CTX = _ssl_context()


def _save(name, data):
    save_json(name, data)


def _num(raw):
    """Parse a sheet cell like "$1,842,000.00" / "12.5" / "#N/A" / "" into a
    float, or None when the cell holds no usable number."""
    if raw is None:
        return None
    s = str(raw).strip().replace("$", "").replace(",", "").replace("%", "")
    if not s or s.upper() in ("#N/A", "N/A", "#ERROR!", "#REF!", "-", "—"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_sheet_rows(csv_text):
    """{ticker: {price, marketCap, currency?, chg7d?, chg1m?, chg1y?}} from
    the sheet's CSV export. Pure — no I/O. Rows without a parseable price are
    skipped (the caller keeps the previous snapshot for those). Duplicate
    ticker rows: last one wins."""
    out = {}
    for row in csv.DictReader(io.StringIO(csv_text)):
        ticker = (row.get("Ticker") or "").strip()
        if not ticker:
            continue
        price = _num(row.get("Price"))
        if price is None:
            continue
        snap = {"price": price, "marketCap": _num(row.get("MarketCap"))}
        # Optional: a USD-normalised market cap so the watchlist can rank
        # across markets. Without it a KRW cap and a USD cap sit in the same
        # column and any sort is arithmetically meaningless. The sheet does
        # the conversion (GOOGLEFINANCE keeps the rate fresh); see docs/GUIDE.
        mcap_usd = _num(row.get("MarketCapUSD"))
        if mcap_usd is not None:
            snap["marketCapUSD"] = mcap_usd
        # Only stamp currency when the sheet actually has the column filled —
        # defaulting to USD would mislabel KRW/SEK names until the operator
        # adds the Currency formula column. run() keeps the prior currency.
        currency = (row.get("Currency") or "").strip()
        if currency:
            snap["currency"] = currency
        for col, field in CHG_COLUMNS.items():
            val = _num(row.get(col))
            if val is not None:
                snap[field] = round(val, 2)
        for col, field in CHG_USD_COLUMNS.items():
            val = _num(row.get(col))
            if val is not None:
                snap[field] = round(val, 2)
        out[ticker] = snap
    return out


def _merge_snapshot(prev, snap):
    """Combine this fetch's row (`snap`) with the previous stored snapshot
    (`prev`) for one ticker. Pure — no I/O. `snap` already has price and
    marketCap (required upstream in `_parse_sheet_rows`); this only decides
    what happens to the OPTIONAL fields the sheet may have gone quiet on."""
    merged = dict(snap)
    if "currency" not in merged and prev.get("currency"):
        merged["currency"] = prev["currency"]
    for field in _CARRY_FORWARD_FIELDS:
        if field not in merged and prev.get(field) is not None:
            merged[field] = prev[field]
    return merged


def _cache_busted(url):
    """Append a unique query param so Google's CDN can't serve a stale cached
    copy of the CSV export. Without this, edits to the sheet (a new row, a
    fixed formula) may not appear for several minutes on a plain fetch."""
    sep = "&" if "?" in url else "?"
    return "{}{}_cb={}".format(url, sep, int(datetime.now(timezone.utc).timestamp()))


def _fetch_csv(url):
    req = urllib.request.Request(_cache_busted(url),
                                 headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
        return resp.read().decode("utf-8")


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
    url = os.environ.get("PRICES_SHEET_URL") or DEFAULT_SHEET_CSV_URL

    tickers = _load("tickers.json")
    wanted = [t["ticker"] for t in tickers]
    for bench in BENCHMARK_SYMBOLS:
        if bench not in wanted:
            wanted.append(bench)

    rows = _parse_sheet_rows(_fetch_csv(url))

    prices = _load_prices()  # keep prior snapshot; only overwrite what the sheet has
    asof = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated, not_in_sheet = 0, []
    for sym in wanted:
        snap = rows.get(sym)
        if snap is None:
            not_in_sheet.append(sym)
            continue
        snap = _merge_snapshot(prices.get(sym) or {}, snap)
        snap["asOf"] = asof
        prices[sym] = snap
        updated += 1

    _save("prices.json", prices)
    gen.write_data_js()
    summary = {"updated": updated, "failed": not_in_sheet, "asOf": asof,
               "notInSheet": not_in_sheet}
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    run()
