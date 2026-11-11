#!/usr/bin/env python3
"""The capital brain's eyes: read the operator's portfolio file (READ-ONLY) and
write a private summary the desk can size from.

    python3 desk/money.py        -> desk/store/money.json, prints the summary

The portfolio file belongs to another project (the portfolio dashboard). This
script never writes to it. It reads positions, cash and stablecoins and works
out the liquid money outside the perp-DEX farm. Sizing rules (reserve, pots,
caps) live in desk/store/book.json and are applied by desk/plan.py.

Everything here is private: desk/store/ is gitignored, and no amount from this
file may appear in a tracked file, a commit message or anything public.

If the portfolio file cannot be read, the last summary is kept and marked
stale, so the page shows old numbers with their date instead of guessing.
"""
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from common import STORE, load_json, now_iso, save_json

BOOK = STORE / "book.json"
MONEY = STORE / "money.json"
DEFAULT_PORTFOLIO = "~/Documents/Claude/port_dashboard_2026/portfolio.json"


def load_book():
    return load_json(BOOK, {})


def _is_broker_cash(p):
    return p.get("kind") == "broker_cash" or (p.get("category") == "Equities" and p.get("asset") in ("USD", "MYR", "SGD", "HKD"))


def summarise(P, book):
    """Portfolio dict -> the summary. No rule is applied here, only counting."""
    meta = P.get("meta", {})
    fx = dict(meta.get("fx_fallback", {}))
    fx["MYR"] = 1.0
    fx_note = "the dashboard file's fallback rates"
    ramps = [o for o in P.get("offramp_transactions", []) if o.get("rate") and o.get("date")]
    if ramps:                     # the operator's own latest realised USD rate beats a stale fallback
        last = max(ramps, key=lambda o: o["date"])
        fx["USD"] = last["rate"]
        fx_note = "USD at the last off-ramp rate ({}); other currencies from the dashboard file's fallback rates".format(last["date"])
    alias = book.get("aliases", {})

    def myr(amount, ccy):
        return amount * fx.get(ccy or "MYR", 1.0)

    broker_cash = stables = farm = gold = 0.0
    positions = {}
    for p in P.get("positions", []):
        cat, units, price, ccy = p.get("category"), p.get("units") or 0, p.get("price") or 0, p.get("currency") or "MYR"
        if cat == "Stables":
            v = myr(units * price, ccy)
            stables += v
            if "perp dex" in (p.get("note") or "").lower():
                farm += v
        elif cat == "Equities" and _is_broker_cash(p):
            broker_cash += myr(units * price, ccy)
        elif cat == "Equities" and p.get("kind") == "commodity":
            gold += myr(units * price, ccy)
        elif cat == "Equities":
            t = alias.get(p["asset"], p["asset"])
            r = positions.setdefault(t, {"asset": p["asset"], "name": p.get("name") or p["asset"], "units": 0.0, "cost": 0.0,
                                         "currency": ccy, "filePrice": price, "brokers": [], "trade": False})
            r["units"] += units
            r["cost"] += units * (p.get("avg_cost") or 0)
            if p.get("broker") and p["broker"] not in r["brokers"]:
                r["brokers"].append(p["broker"])
            if p.get("kind") == "trade" or "#trade" in (p.get("note") or "").lower():
                r["trade"] = True
    for r in positions.values():
        r["avgCost"] = round(r["cost"] / r["units"], 4) if r["units"] else None
        r["cost"] = round(r["cost"], 2)

    cash = float(meta.get("cash_on_hand_myr") or 0)
    nw = (P.get("net_worth_history") or [{}])[-1]
    this_year = [o for o in ramps if o["date"][:4] == str(date.today().year)]
    return {
        "asOf": now_iso(), "stale": False, "fx": fx, "fxNote": fx_note,
        "cashOnHand": round(cash), "brokerCash": round(broker_cash), "stables": round(stables), "farm": round(farm),
        "gold": round(gold), "liquid": round(cash + broker_cash + stables - farm),
        "netWorth": {"total": nw.get("total_myr"), "date": nw.get("date")},
        "offRampedThisYear": round(sum(o.get("myr", 0) for o in this_year)),
        "positions": positions,
    }


def refresh(quiet=True):
    """Read the portfolio, save and return the summary. On any failure keep the
    last summary and mark it stale."""
    book = load_book()
    path = Path(os.path.expanduser(book.get("portfolio") or DEFAULT_PORTFOLIO))
    try:
        P = json.loads(path.read_text(encoding="utf-8"))
        out = summarise(P, book)
        out["portfolioModified"] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception as ex:                      # missing, unreadable or malformed: never guess
        old = load_json(MONEY, None)
        if not quiet:
            print("WARNING: portfolio not read ({}); {}".format(ex, "using the last summary" if old else "no summary yet"))
        if old:
            old["stale"] = True
            old["staleWhy"] = str(ex)
            save_json(MONEY, old)
        return old
    # First run: remember each position's cost so later adds can be counted against the pots.
    if book and "baseline" not in book:
        book["baseline"] = {t: {"cost": r["cost"], "currency": r["currency"]} for t, r in out["positions"].items()}
        book["since"] = date.today().isoformat()
        save_json(BOOK, book)
    save_json(MONEY, out)
    return out


def main():
    m = refresh(quiet=False)
    if not m:
        return 1
    print("as of {}{}".format(m["asOf"], "  (STALE: {})".format(m.get("staleWhy")) if m.get("stale") else ""))
    print("FX: {}".format(m["fxNote"]))
    print("cash on hand RM {:,} | broker cash RM {:,} | stables RM {:,} (farm RM {:,})".format(
        m["cashOnHand"], m["brokerCash"], m["stables"], m["farm"]))
    print("liquid outside the farm: RM {:,}".format(m["liquid"]))
    for t, r in sorted(m["positions"].items()):
        print("  {:10} {:>9g} @ {:>9} {}".format(t, r["units"], r["avgCost"], r["currency"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
