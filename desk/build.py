#!/usr/bin/env python3
"""Validate the memos, keep the scorecard honest, and write desk.js for the page.

    python3 desk/build.py

1. Validates every desk/memos/*.json (shape, stances, sources). Exit 1 on error.
2. Scorecard (desk/store/calls.json), derived from the LATEST memo only:
   - a ticker marked "accumulate" with no open call opens one, priced from
     that memo's own price snapshot (desk/store/prices/<memo date>.json);
   - an open call whose ticker is no longer "accumulate" is closed at the
     latest snapshot price.
   Idempotent: running it twice changes nothing. Calls are never edited or
   deleted by hand, so the record of hits and misses cannot be rewritten.
3. Marks every call against the latest snapshot and the SMH benchmark.
4. Writes ../desk.js (window.DESK = {...}) so index.html works from file://.
"""
import glob
import json
import re
import sys
from pathlib import Path

from common import DESK, PRICES_DIR, ROOT, STATE_FILE, load_json, now_iso, save_json

MEMOS = DESK / "memos"
CALLS = DESK / "store" / "calls.json"
BENCH = "SMH"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ACTIONS = {"accumulate", "watch", "trim", "avoid"}
STANCES = {"bull", "bear", "mixed"}
CONF = {"low", "medium", "high"}


def validate(m, name):
    e = []
    need = ("date", "window", "headline", "picture", "accumulate", "board", "market", "pushback", "flags")
    for k in need:
        if k not in m:
            e.append("{}: missing {}".format(name, k))
    if e:
        return e
    if not ISO.match(m["date"]):
        e.append("{}: date not ISO".format(name))
    for k in ("now", "next"):
        if not m["picture"].get(k):
            e.append("{}: picture.{} empty".format(name, k))
    for a in m["accumulate"]:
        t = a.get("ticker", "?")
        if a.get("action") not in ACTIONS:
            e.append("{}: {} action {!r} not in {}".format(name, t, a.get("action"), sorted(ACTIONS)))
        if a.get("confidence") not in CONF:
            e.append("{}: {} confidence {!r}".format(name, t, a.get("confidence")))
        for k in ("name", "thesis", "whyCheap", "catalyst", "zone", "invalidation"):
            if not a.get(k):
                e.append("{}: {} missing {}".format(name, t, k))
        v = a.get("valuation") or {}
        if not v.get("text") or not str(v.get("source", "")).startswith("http"):
            e.append("{}: {} valuation needs text and a source URL".format(name, t))
        if not a.get("sources"):
            e.append("{}: {} has no sources".format(name, t))
    for b in m["board"]:
        for v in b.get("views", []):
            if v.get("stance") not in STANCES:
                e.append("{}: board {} @{} stance {!r}".format(name, b.get("ticker"), v.get("handle"), v.get("stance")))
            if not str(v.get("url", "")).startswith("http"):
                e.append("{}: board {} @{} needs the post URL".format(name, b.get("ticker"), v.get("handle")))
    for mv in m["market"].get("movers", []):
        if mv.get("why") and not str(mv.get("source", "")).startswith("http"):
            e.append("{}: mover {} explains why without a source".format(name, mv.get("ticker")))
    return e


def snap(day):
    """Price snapshot for a date, or the latest one on or before it."""
    files = sorted(p for p in glob.glob(str(PRICES_DIR / "*.json")) if Path(p).stem <= day)
    return load_json(files[-1], {}) if files else {}


def px(s, t):
    return ((s.get("prices") or {}).get(t) or {}).get("price")


def update_calls(latest, calls):
    """Open/close calls from the latest memo. Returns list of changes."""
    changes = []
    s_memo = snap(latest["date"])
    s_now = snap("9999-12-31")
    want = {a["ticker"] for a in latest["accumulate"] if a["action"] == "accumulate"}
    open_by = {c["ticker"]: c for c in calls if not c.get("closed")}
    for a in latest["accumulate"]:
        t = a["ticker"]
        if a["action"] == "accumulate" and t not in open_by:
            c = {"ticker": t, "name": a["name"], "opened": latest["date"],
                 "refPrice": px(s_memo, t),
                 "currency": ((s_memo.get("prices") or {}).get(t) or {}).get("currency"),
                 "benchRef": px(s_memo, BENCH), "zone": a["zone"],
                 "invalidation": a["invalidation"], "closed": None}
            calls.append(c)
            changes.append("opened {} at {}".format(t, c["refPrice"]))
    for t, c in open_by.items():
        if t not in want:
            c["closed"] = {"date": latest["date"], "price": px(s_now, t),
                           "benchPrice": px(s_now, BENCH)}
            changes.append("closed {}".format(t))
    return changes


def mark(calls):
    s = snap("9999-12-31")
    out = []
    for c in calls:
        end = c["closed"]["price"] if c.get("closed") else px(s, c["ticker"])
        bend = c["closed"]["benchPrice"] if c.get("closed") else px(s, BENCH)
        r = dict(c)
        r["lastPrice"] = end
        r["ret"] = round((end / c["refPrice"] - 1) * 100, 1) if end and c.get("refPrice") else None
        r["benchRet"] = round((bend / c["benchRef"] - 1) * 100, 1) if bend and c.get("benchRef") else None
        out.append(r)
    return out, s.get("asOf")


def main():
    errors = []
    memos = []
    for f in sorted(glob.glob(str(MEMOS / "*.json"))):
        try:
            m = json.loads(Path(f).read_text(encoding="utf-8"))
        except json.JSONDecodeError as ex:
            errors.append("{}: not valid JSON: {}".format(Path(f).name, ex))
            continue
        errors += validate(m, Path(f).name)
        memos.append(m)
    if errors:
        print("ERRORS:\n  " + "\n  ".join(errors))
        return 1
    memos.sort(key=lambda m: m["date"], reverse=True)

    calls = load_json(CALLS, [])
    changes = update_calls(memos[0], calls) if memos else []
    save_json(CALLS, calls)
    marked, priced_at = mark(calls)

    state = load_json(STATE_FILE, {})
    roster = load_json(DESK / "analysts.json", {"analysts": []})["analysts"]
    desk = {"built": now_iso(), "pricesAsOf": priced_at, "collectorLastRun": state.get("lastRun"),
            "analysts": roster, "memos": memos, "calls": marked, "bench": BENCH}
    (ROOT / "desk.js").write_text(
        "// Generated by desk/build.py from desk/memos and desk/store. Do not edit by hand.\n"
        "window.DESK = " + json.dumps(desk, indent=1, ensure_ascii=False) + ";\n", encoding="utf-8")

    print("{} memo(s), {} call(s) ({} open)".format(
        len(memos), len(calls), sum(1 for c in calls if not c.get("closed"))))
    for ch in changes:
        print("scorecard:", ch)
    unpriced = [c["ticker"] for c in calls if not c.get("closed") and c.get("refPrice") is None]
    if unpriced:
        print("WARNING: open calls with no price in the sheet (add them to the Google Sheet):", ", ".join(unpriced))
    print("wrote desk.js")
    return 0


if __name__ == "__main__":
    sys.exit(main())
