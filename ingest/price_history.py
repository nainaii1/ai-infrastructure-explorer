"""An append-only daily price record. Pure — no network, no file I/O.

The gap this closes: `prices.json` holds ONE row per ticker and is overwritten
twice a day. So the desk has 1,200+ dated arguments from the analyst and no way
to score a single one of them — "what happened after he argued SIVE in August"
is unanswerable, permanently, for every day that passes without a record.

Why store rather than query an API on demand:
  - Every free keyless source this project has tried has failed. Yahoo and FMP
    were retired 2026-07-16 for chronic 429s; Stooq returns a bot-challenge
    page instead of CSV (checked 21 Aug 2026). Prices now come from the
    operator's own Google Sheet, which serves a snapshot, not a history.
  - The data already flows through `fetch_prices.py` twice a day. Keeping it
    costs one appended line per ticker — about 1 MB a year, against a data.js
    that is already 1.4 MB. Throwing it away is the expensive option.
  - A local record cannot be rate-limited, retired, or repriced by a vendor.

Storage is CSV, not JSON: appending a day must not mean parsing and rewriting
the whole file, and this never rides in `data.js` — it is an analysis
substrate, not app data.

`fetch_prices.py` does the writing; this module is the format and the
arithmetic, so the read side is testable with no disk.
"""

HEADER = ["date", "ticker", "close", "currency", "source"]

# How a row got here. "sheet" is an observed close from the operator's
# GOOGLEFINANCE sheet. "derived" is back-computed from a percentage change
# (see derive_anchors) — real arithmetic on real data, but the DATE is
# approximate, so the two must never be silently mixed in an analysis.
SOURCE_OBSERVED = "sheet"
SOURCE_DERIVED = "derived"


def _num(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out and out not in (float("inf"), float("-inf")) else None


def make_row(date, ticker, close, currency=None, source=SOURCE_OBSERVED):
    """One record, or None if it is not worth keeping.

    A missing or non-positive close is dropped rather than stored as 0 — a
    zero price would silently poison every return computed through it.
    """
    price = _num(close)
    sym = str(ticker or "").strip().upper()
    day = str(date or "")[:10]
    if not sym or not day or price is None or price <= 0:
        return None
    return {"date": day, "ticker": sym, "close": price,
            "currency": (currency or "").strip().upper() or "",
            "source": source}


def rows_from_snapshot(prices, asof):
    """Today's observed closes, from the prices.json snapshot. Oldest-first
    ordering is irrelevant here; the file is sorted on read, not on write."""
    day = str(asof or "")[:10]
    out = []
    for sym, snap in (prices or {}).items():
        if not isinstance(snap, dict):
            continue
        row = make_row(day, sym, snap.get("price"), snap.get("currency"))
        if row:
            out.append(row)
    return sorted(out, key=lambda r: r["ticker"])


def derive_anchors(prices, asof):
    """Back-compute where the price was 1W / 1M / 1Y ago from today's close
    and the percentage changes the sheet already supplies.

    close_then = close_now / (1 + chg/100)

    This is arithmetic on data the sheet genuinely provides, not an estimate —
    but the DATE is approximate ("about a month ago"), so every row is stamped
    `derived` and analyses that need exact dates must filter them out. It
    exists so the record is not empty on day one: three rough anchors per name
    beat waiting three months for the first comparison.

    A change of exactly -100% is skipped rather than dividing by zero.
    """
    day = str(asof or "")[:10]
    if len(day) != 10:
        return []
    try:
        import datetime
        today = datetime.date.fromisoformat(day)
    except (ValueError, TypeError):
        return []

    out = []
    for sym, snap in (prices or {}).items():
        if not isinstance(snap, dict):
            continue
        now = _num(snap.get("price"))
        if now is None or now <= 0:
            continue
        for field, days in (("chg7d", 7), ("chg1m", 30), ("chg1y", 365)):
            chg = _num(snap.get(field))
            if chg is None:
                continue
            factor = 1.0 + (chg / 100.0)
            if factor <= 0:
                continue
            then = today - datetime.timedelta(days=days)
            row = make_row(then.isoformat(), sym, now / factor,
                           snap.get("currency"), SOURCE_DERIVED)
            if row:
                out.append(row)
    return sorted(out, key=lambda r: (r["ticker"], r["date"]))


def to_csv_lines(rows):
    """Rows as CSV text lines (no header, no trailing newline)."""
    out = []
    for r in rows:
        out.append("%s,%s,%.6g,%s,%s" % (r["date"], r["ticker"], r["close"],
                                         r["currency"], r["source"]))
    return out


def parse_csv_lines(lines):
    """Parse stored lines back into rows, skipping the header and anything
    malformed. A corrupt line must not take the whole history down with it."""
    out = []
    for line in lines:
        line = str(line).strip()
        if not line or line.startswith("date,"):
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        row = make_row(parts[0], parts[1], parts[2],
                       parts[3] if len(parts) > 3 else "",
                       parts[4] if len(parts) > 4 else SOURCE_OBSERVED)
        if row:
            out.append(row)
    return out


def dedupe(rows):
    """One row per (ticker, date). Later rows win, and an OBSERVED row always
    beats a derived one for the same day regardless of order — a real close
    must never be overwritten by a back-computed approximation."""
    best = {}
    for r in rows:
        key = (r["ticker"], r["date"])
        prev = best.get(key)
        if prev is None:
            best[key] = r
        elif prev["source"] == SOURCE_DERIVED and r["source"] == SOURCE_OBSERVED:
            best[key] = r
        elif prev["source"] == r["source"]:
            best[key] = r
    return [best[k] for k in sorted(best)]


def series(rows, ticker):
    """One ticker's closes, oldest first."""
    sym = str(ticker or "").upper()
    return sorted([r for r in rows if r["ticker"] == sym],
                  key=lambda r: r["date"])


def close_on_or_before(rows, ticker, date, max_gap_days=10):
    """The last close at or before `date`, or None.

    `max_gap_days` stops a lookup silently reaching back months when the
    record simply has no data near the date asked for — a return computed
    across an unknown gap is not a return.
    """
    import datetime
    try:
        want = datetime.date.fromisoformat(str(date)[:10])
    except (ValueError, TypeError):
        return None
    best = None
    for r in series(rows, ticker):
        try:
            got = datetime.date.fromisoformat(r["date"])
        except ValueError:
            continue
        if got <= want and (want - got).days <= max_gap_days:
            best = r
        elif got > want:
            break
    return best


def forward_return(rows, ticker, from_date, days, max_gap_days=10):
    """Percent change from `from_date` to `days` later — the shape the whole
    record exists for: what happened AFTER an argument was made.

    Returns None unless both ends are actually present. A half-measured return
    is worse than no answer.
    """
    import datetime
    start = close_on_or_before(rows, ticker, from_date, max_gap_days)
    if not start:
        return None
    try:
        end_date = (datetime.date.fromisoformat(str(from_date)[:10])
                    + datetime.timedelta(days=days))
    except (ValueError, TypeError):
        return None
    end = close_on_or_before(rows, ticker, end_date.isoformat(), max_gap_days)
    if not end or end["date"] <= start["date"]:
        return None
    if start["close"] <= 0:
        return None
    return {
        "from": start["date"], "to": end["date"],
        "pct": (end["close"] / start["close"] - 1.0) * 100.0,
        "approximate": SOURCE_DERIVED in (start["source"], end["source"]),
    }


def coverage(rows):
    """What the record actually holds, for a status line."""
    if not rows:
        return {"rows": 0, "tickers": 0, "firstDate": None, "lastDate": None,
                "observed": 0, "derived": 0}
    dates = [r["date"] for r in rows]
    return {
        "rows": len(rows),
        "tickers": len({r["ticker"] for r in rows}),
        "firstDate": min(dates),
        "lastDate": max(dates),
        "observed": sum(1 for r in rows if r["source"] == SOURCE_OBSERVED),
        "derived": sum(1 for r in rows if r["source"] == SOURCE_DERIVED),
    }
