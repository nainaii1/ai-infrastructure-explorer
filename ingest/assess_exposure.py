"""Record AI-exposure judgements into store/exposure.json (PROJECT.md Step 3).

    # what still needs a call, hardest-hitting names first
    python3 ingest/assess_exposure.py --todo

    # record one
    python3 ingest/assess_exposure.py --set NVDA --exposure 88 \
        --confidence high \
        --basis "Data Center segment is the overwhelming majority of revenue" \
        --source "NVDA FY2026 10-K segment note"

    # what is on file
    python3 ingest/assess_exposure.py --status
    python3 ingest/assess_exposure.py --show NVDA

    # remove one (a judgement you no longer stand behind)
    python3 ingest/assess_exposure.py --clear NVDA

This writes the ONE field in the system that is not fetched or computed, so it
refuses anything it cannot attribute: no basis, no write. See exposure.py.

`exposure.py` stays pure; this module does the I/O.
"""

import sys
import json
import argparse

import generate_data_js as gen
import exposure as exp
from store_io import (
    load_json as _load,
    load_json_optional as _load_opt,
    save_json as _save_json,
    now_iso as _now_iso,
)

STORE_FILE = "exposure.json"


def _save(data):
    _save_json(STORE_FILE, data, trailing_newline=True)


def _read():
    data = _load_opt(STORE_FILE, {}) or {}
    return dict(data.get("companies") or {})


def _write(companies):
    _save({
        "meta": {
            "schemaVersion": 1,
            "updatedAt": _now_iso(),
            "source": "operator judgement",
            "disclaimer": ("Not filed data and not derivable from filings. "
                           "Each figure carries its own basis and confidence."),
            "assessed": len(companies),
        },
        "companies": companies,
    })
    gen.write_data_js()


def _core_watch():
    """Core+Watch symbols, tiered exactly as the app tiers them."""
    import scorer
    tickers = _load("tickers.json")
    theses = _load("theses.json")
    base = _load("base.json") or {}
    canon = scorer.canonicalize_theses(
        theses, base.get("tickerAliases"), base.get("themeTags"))
    priorities = scorer.compute_priorities(canon)
    symbols = [t["ticker"] for t in tickers if t.get("ticker")]
    tiers = scorer.assign_tiers(symbols, priorities)
    picked = [s for s in symbols if tiers.get(s) in ("core", "watch")]
    if not picked:
        sys.exit("refusing to run: the tier table matched no Core/Watch names.")
    return picked


def set_one(args):
    companies = _read()
    try:
        record = exp.validate_assessment({
            "ticker": args.set,
            "aiExposure": args.exposure,
            "confidence": args.confidence,
            "basis": args.basis,
            "sources": args.source or [],
            "contentPerRack": args.content_per_rack,
            "revenueInflection": args.revenue_inflection,
            "assessedAt": _now_iso()[:10],
            "assessedBy": args.by,
        })
    except exp.AssessmentError as err:
        sys.exit("refused: %s" % err)

    companies[record["ticker"]] = record
    _write(companies)
    print(json.dumps(record, indent=2))


def clear_one(sym):
    companies = _read()
    sym = str(sym).upper()
    if sym not in companies:
        sys.exit("%s has no assessment on file" % sym)
    companies.pop(sym)
    _write(companies)
    print(json.dumps({"cleared": sym, "remaining": len(companies)}))


def show(sym):
    companies = _read()
    rec = companies.get(str(sym).upper())
    if not rec:
        sys.exit("%s: not assessed yet" % str(sym).upper())
    print(json.dumps(rec, indent=2))


def status():
    companies = _read()
    cov = exp.coverage(companies, _core_watch())
    funds = (_load_opt("fundamentals.json", {}) or {}).get("companies") or {}
    # How many can produce the derived figure — both halves present.
    derivable = [s for s in cov["assessed"]
                 if exp.ai_revenue(companies.get(s), funds.get(s))]
    by_conf = {}
    for s in cov["assessed"]:
        level = companies[s].get("confidence")
        by_conf[level] = by_conf.get(level, 0) + 1
    print(json.dumps({
        "assessed": len(cov["assessed"]),
        "coreWatch": cov["total"],
        "unassessed": len(cov["unassessed"]),
        "byConfidence": by_conf,
        "aiRevenueDerivable": len(derivable),
    }, indent=2))


def todo():
    """The worklist: unassessed Core/Watch names, biggest revenue first.

    Ordered by filed revenue rather than alphabetically because that is the
    order in which a judgement changes the picture — an unassessed $200B name
    matters more than an unassessed $100M one. Names with no filed revenue
    come last, not first, for the same reason.
    """
    companies = _read()
    cov = exp.coverage(companies, _core_watch())
    funds = (_load_opt("fundamentals.json", {}) or {}).get("companies") or {}
    tickers = {t["ticker"]: t for t in _load("tickers.json")}

    def revenue_of(sym):
        rec = funds.get(sym) or {}
        latest = rec.get("latest") or {}
        return latest.get("revenue") or 0

    rows = sorted(cov["unassessed"], key=revenue_of, reverse=True)
    print("%d of %d Core/Watch names still need a call\n"
          % (len(rows), cov["total"]))
    for sym in rows:
        rec = funds.get(sym) or {}
        latest = rec.get("latest") or {}
        rev = latest.get("revenue")
        shown = ("%s %.1fB" % (rec.get("currency", ""), rev / 1e9)
                 if rev else "no filed revenue")
        print("  %-10s %-18s %s" % (sym, shown,
                                    (tickers.get(sym, {}).get("company") or "")[:40]))
    if rows:
        print("\nRecord one with:\n  python3 ingest/assess_exposure.py --set %s "
              "--exposure <0-100> --confidence high|medium|low \\\n"
              "      --basis \"why\" --source \"where it came from\"" % rows[0])


def main():
    ap = argparse.ArgumentParser(description="Record AI-exposure judgements")
    ap.add_argument("--set", metavar="TICKER")
    ap.add_argument("--exposure", help="percent of revenue tied to AI, 0-100")
    ap.add_argument("--confidence", choices=list(exp.CONFIDENCE_LEVELS))
    ap.add_argument("--basis", help="why — required, and it must say something")
    ap.add_argument("--source", action="append", help="repeatable")
    ap.add_argument("--content-per-rack")
    ap.add_argument("--revenue-inflection",
                    help="the quarter the AI revenue actually lands")
    ap.add_argument("--by", default="operator")
    ap.add_argument("--clear", metavar="TICKER")
    ap.add_argument("--show", metavar="TICKER")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--todo", action="store_true")
    args = ap.parse_args()

    if args.status:
        return status()
    if args.todo:
        return todo()
    if args.show:
        return show(args.show)
    if args.clear:
        return clear_one(args.clear)
    if args.set:
        return set_one(args)
    ap.print_help()


if __name__ == "__main__":
    main()
