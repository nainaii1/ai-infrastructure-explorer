#!/usr/bin/env python3
"""Snapshot prices from the operator's Google Sheet (GOOGLEFINANCE formulas,
public CSV export, no key) into desk/store/prices/YYYY-MM-DD.json.

Run by the memo, not on a timer: prices are context for a dated memo and for
marking the accumulate scorecard, never stored in data.js. A ticker the sheet
does not carry is listed as missing, never guessed.

    python3 desk/prices.py            snapshot today, print a summary
    python3 desk/prices.py --quiet    snapshot only
"""
import csv
import io
import sys
from datetime import date

from common import PRICES_DIR, ROOT, http_get, now_iso, save_json

SHEET_CSV = ("https://docs.google.com/spreadsheets/d/"
             "1Zeqqq01H1KiSvJnNArm0kr2rcn-F3FV8uxYjjX8mihA/export?format=csv")
FIELDS = {"Price": "price", "MarketCap": "marketCap", "Chg1W": "chg1w",
          "Chg1M": "chg1m", "Chg1MUSD": "chg1mUSD", "Chg1Y": "chg1y", "PE": "pe"}


def num(raw):
    s = (raw or "").strip().replace("$", "").replace(",", "").replace("%", "")
    if not s or s.upper() in ("#N/A", "N/A", "#ERROR!", "#REF!", "-", "—", "LOADING..."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def snapshot():
    text = http_get(SHEET_CSV, timeout=30).decode("utf-8")
    rows = {}
    for r in csv.DictReader(io.StringIO(text)):
        t = (r.get("Ticker") or "").strip()
        if not t:
            continue
        rec = {"symbol": r.get("GoogleFinanceSymbol"), "currency": r.get("Currency") or None}
        for col, key in FIELDS.items():
            if col in r:
                rec[key] = num(r[col])
        if rec.get("price") is not None:
            rows[t] = rec
    return rows


def guide_tickers():
    import json
    raw = (ROOT / "data.js").read_text(encoding="utf-8")
    d = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    return [c["ticker"] for c in d["companies"] if c.get("listed", True)]


def main():
    rows = snapshot()
    out = {"asOf": now_iso(), "source": "Google Sheet (GOOGLEFINANCE), public CSV export",
           "prices": rows}
    path = PRICES_DIR / "{}.json".format(date.today().isoformat())
    save_json(path, out)
    if "--quiet" not in sys.argv:
        missing = [t for t in guide_tickers() if t not in rows]
        print("saved {} prices to {}".format(len(rows), path.relative_to(ROOT)))
        print("guide companies with no price in the sheet:", ", ".join(missing) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
