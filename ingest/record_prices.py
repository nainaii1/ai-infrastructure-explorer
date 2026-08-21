"""Append today's closes to store/price_history.csv, and read it back.

    python3 ingest/record_prices.py            # append today's snapshot
    python3 ingest/record_prices.py --seed     # + back-computed 1W/1M/1Y anchors
    python3 ingest/record_prices.py --status   # what the record holds
    python3 ingest/record_prices.py --after SIVE 2026-08-13 --days 30

`fetch_prices.py` calls `append_snapshot()` on every run, so the record fills
itself twice a day with no extra routine for the operator. This module is only
the file handling; `price_history.py` is the format and the arithmetic and
stays pure.

The file is CSV and append-only on purpose: adding a day must not mean
rewriting the history, and it deliberately does NOT ride in `data.js` — it is
an analysis substrate that would bloat every page load for no benefit.
"""

import sys
import json
import pathlib
import argparse

import price_history as ph
from store_io import load_json_optional as _load_opt

ING = pathlib.Path(__file__).resolve().parent
STORE = ING / "store"
HISTORY_PATH = STORE / "price_history.csv"


def _read_lines():
    if not HISTORY_PATH.exists():
        return []
    return HISTORY_PATH.read_text(encoding="utf-8").splitlines()


def load_rows():
    """Every stored row, deduped. Cheap enough at this size to read whole."""
    return ph.dedupe(ph.parse_csv_lines(_read_lines()))


def _append(rows):
    """Append rows, skipping any (ticker, date) the file already has.

    Reading before writing keeps the file idempotent: running the price fetch
    twice in one day adds nothing the second time, so the launchd schedule and
    a manual refresh cannot double-count.
    """
    if not rows:
        return 0
    # Track what each stored day already IS, not merely that it exists. A real
    # close must still be recordable for a day currently held by a derived
    # anchor — skipping on the key alone would let a rough approximation block
    # the observed price forever. load_rows() then prefers the observed one.
    existing = {(r["ticker"], r["date"]): r["source"] for r in load_rows()}

    def wanted(r):
        had = existing.get((r["ticker"], r["date"]))
        if had is None:
            return True
        return had == ph.SOURCE_DERIVED and r["source"] == ph.SOURCE_OBSERVED

    fresh = [r for r in ph.dedupe(rows) if wanted(r)]
    if not fresh:
        return 0
    new_file = not HISTORY_PATH.exists()
    with HISTORY_PATH.open("a", encoding="utf-8") as fh:
        if new_file:
            fh.write(",".join(ph.HEADER) + "\n")
        for line in ph.to_csv_lines(fresh):
            fh.write(line + "\n")
    return len(fresh)


def append_snapshot(prices=None, asof=None, seed=False):
    """Record today's closes. Called by fetch_prices.py after every fetch.

    Deliberately swallows nothing: if this raises, the caller's price fetch has
    already saved prices.json and regenerated data.js, so the loss is one day
    of history, not the day's prices. fetch_prices guards the call for that
    reason.
    """
    prices = prices if prices is not None else (_load_opt("prices.json", {}) or {})
    if not asof:
        asof = max((s.get("asOf") or "") for s in prices.values()
                   if isinstance(s, dict)) or ""
    rows = ph.rows_from_snapshot(prices, asof)
    if seed:
        rows = ph.derive_anchors(prices, asof) + rows
    return _append(rows)


def status():
    rows = load_rows()
    cov = ph.coverage(rows)
    size = HISTORY_PATH.stat().st_size if HISTORY_PATH.exists() else 0
    cov["fileKB"] = round(size / 1024, 1)
    cov["path"] = str(HISTORY_PATH.relative_to(ING.parent))
    print(json.dumps(cov, indent=2))


def after(ticker, date, days):
    """What happened to one name in the N days after a date."""
    got = ph.forward_return(load_rows(), ticker, date, days)
    if not got:
        sys.exit("no record covering %s around %s — the history does not go "
                 "back that far yet" % (str(ticker).upper(), date))
    print(json.dumps(got, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Daily price record")
    ap.add_argument("--seed", action="store_true",
                    help="also back-compute 1W/1M/1Y anchors from the sheet's "
                         "percentage changes (dates are approximate)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--after", nargs=2, metavar=("TICKER", "DATE"))
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()

    if args.status:
        return status()
    if args.after:
        return after(args.after[0], args.after[1], args.days)
    added = append_snapshot(seed=args.seed)
    print(json.dumps({"appended": added}))


if __name__ == "__main__":
    main()
