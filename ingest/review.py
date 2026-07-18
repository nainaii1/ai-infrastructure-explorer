"""Triage CLI for the ingest store.

Auto-add only handles clean $CASHTAGS (they land as 'unsorted'). This tool
lets you (1) classify/enrich those unsorted tickers, and (2) approve or reject
the low-confidence candidates queued in pending_tickers.json. Regenerates
data.js after any change.

Usage
  python review.py list
  python review.py classify NVTS --category photonics --company "Navitas" \\
      --market US --exchange NASDAQ --tier Small \\
      --what "GaN/SiC power semis." --why "Powers dense GPU racks."
  python review.py approve XYZ --category fabs --company "Example Corp"
  python review.py reject ZZZZ
"""

import sys
import json
import argparse
import pathlib

import generate_data_js as gen
from store_io import load_json as _load, save_json

ING = pathlib.Path(__file__).resolve().parent
STORE = ING / "store"


def _save(name, data):
    save_json(name, data)


def _apply_fields(ticker, args):
    if args.category:
        ticker["category"] = args.category
    if args.company is not None:
        ticker["company"] = args.company
    if args.market is not None:
        ticker["market"] = args.market
    if args.exchange is not None:
        ticker["exchange"] = args.exchange
    if args.tier is not None:
        ticker["marketCapTier"] = args.tier
    if args.what is not None:
        ticker["whatTheyDo"] = args.what
    if args.why is not None:
        ticker["whyNVDA"] = args.why
    return ticker


def cmd_list(_args):
    pending = _load("pending_tickers.json")
    tickers = _load("tickers.json")
    unsorted = [t["ticker"] for t in tickers if t.get("category") == "unsorted"]
    print("Unsorted tickers (need classify):", unsorted or "none")
    print("Pending candidates (approve/reject):")
    for p in pending:
        print("  {:8} seen {}x  {}".format(p["candidate"], p["count"], p.get("sourceUrl", "")))
    if not pending:
        print("  none")


def cmd_classify(args):
    tickers = _load("tickers.json")
    sym = args.symbol.upper()
    target = next((t for t in tickers if t["ticker"].upper() == sym), None)
    if not target:
        sys.exit("No such ticker in store: " + sym)
    _apply_fields(target, args)
    _save("tickers.json", tickers)
    gen.write_data_js()
    print("Classified", sym, "->", target.get("category"))


def cmd_approve(args):
    tickers = _load("tickers.json")
    pending = _load("pending_tickers.json")
    sym = args.symbol.upper()
    if any(t["ticker"].upper() == sym for t in tickers):
        sys.exit(sym + " already in tickers.json (use classify).")
    tickers.append({
        "ticker": sym,
        "company": args.company or "",
        "category": args.category or "unsorted",
        "market": args.market or "",
        "exchange": args.exchange or "",
        "whatTheyDo": args.what or "",
        "whyNVDA": args.why or "",
        "marketCapTier": args.tier or "",
        "rating": "watch",
        "sourceTweetUrl": "",
        "addedDate": "",
    })
    pending = [p for p in pending if p["candidate"].upper() != sym]
    _save("tickers.json", tickers)
    _save("pending_tickers.json", pending)
    gen.write_data_js()
    print("Approved", sym)


def cmd_reject(args):
    pending = _load("pending_tickers.json")
    sym = args.symbol.upper()
    pending = [p for p in pending if p["candidate"].upper() != sym]
    _save("pending_tickers.json", pending)
    print("Rejected", sym)


def main():
    ap = argparse.ArgumentParser(description="Triage the ingest store.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list").set_defaults(func=cmd_list)

    def add_field_args(p):
        p.add_argument("symbol")
        p.add_argument("--category")
        p.add_argument("--company")
        p.add_argument("--market")
        p.add_argument("--exchange")
        p.add_argument("--tier", choices=["Mega", "Large", "Mid", "Small"])
        p.add_argument("--what", dest="what")
        p.add_argument("--why", dest="why")

    p_classify = sub.add_parser("classify"); add_field_args(p_classify); p_classify.set_defaults(func=cmd_classify)
    p_approve = sub.add_parser("approve"); add_field_args(p_approve); p_approve.set_defaults(func=cmd_approve)
    p_reject = sub.add_parser("reject"); p_reject.add_argument("symbol"); p_reject.set_defaults(func=cmd_reject)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
