#!/usr/bin/env python3
"""Validate the memos, keep the records honest, and write desk.js for the page.

    python3 desk/build.py

1. Validates every desk/memos/*.json and desk/memos/events/*.json. Exit 1 on
   any error.
2. Scorecard (desk/store/calls.json), derived from the LATEST memo only:
   a ticker marked "accumulate" with no open call opens one, priced from that
   memo's own snapshot; an open call no longer "accumulate" is closed at the
   latest snapshot. Calls are never edited by hand.
3. Analyst track record (desk/store/stances.json): every stance on the analyst
   board is logged once, with the price the day it was first seen, and kept
   until the analyst changes it. Marked against SMH.
4. Alert levels (desk/store/levels.json): the numeric zones from the latest
   memo, overridden by any event update since. The collector checks prices
   against these every run.
5. "What changed": latest memo against the one before, plus event updates.
6. Writes ../desk.js (window.DESK = {...}) so index.html works from file://.
All steps are idempotent: running build twice changes nothing.
"""
import glob
import json
import re
import sys
from pathlib import Path

from common import DESK, PRICES_DIR, ROOT, STATE_FILE, STORE, load_json, now_iso, save_json

MEMOS = DESK / "memos"
EVENTS = MEMOS / "events"
CALLS = STORE / "calls.json"
STANCE_LOG = STORE / "stances.json"
LEVELS = STORE / "levels.json"
ALERT_LOG = STORE / "alerts.json"
BENCH = "SMH"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ACTIONS = {"accumulate", "watch", "trim", "avoid"}
STANCES = {"bull", "bear", "mixed"}
CONF = {"low", "medium", "high"}
VERDICTS = {"confirms", "mixed", "breaks"}


# ---------------------------------------------------------------- validation

def _url(x):
    return str(x or "").startswith("http")


def validate_levels(lv, where):
    e = []
    if not isinstance(lv, dict):
        return ["{}: levels must be an object".format(where)]
    if not lv.get("currency"):
        e.append("{}: levels.currency missing".format(where))
    nums = {k: lv.get(k) for k in ("buyBelow", "addBelow", "stopAbove")}
    for k, v in nums.items():
        if v is not None and not isinstance(v, (int, float)):
            e.append("{}: levels.{} must be a number".format(where, k))
    if not isinstance(nums["buyBelow"], (int, float)):
        e.append("{}: levels.buyBelow is required".format(where))
    elif isinstance(nums["addBelow"], (int, float)) and nums["addBelow"] > nums["buyBelow"]:
        e.append("{}: addBelow must be at or below buyBelow".format(where))
    elif isinstance(nums["stopAbove"], (int, float)) and nums["stopAbove"] < nums["buyBelow"]:
        e.append("{}: stopAbove must be at or above buyBelow".format(where))
    return e


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
        if not v.get("text") or not _url(v.get("source")):
            e.append("{}: {} valuation needs text and a source URL".format(name, t))
        if not a.get("sources"):
            e.append("{}: {} has no sources".format(name, t))
        if a.get("action") == "accumulate" and "levels" not in a:
            e.append("{}: {} is 'accumulate' but has no numeric levels for alerts".format(name, t))
        if "levels" in a:
            e += validate_levels(a["levels"], "{}: {}".format(name, t))
    for b in m["board"]:
        for v in b.get("views", []):
            if v.get("stance") not in STANCES:
                e.append("{}: board {} @{} stance {!r}".format(name, b.get("ticker"), v.get("handle"), v.get("stance")))
            if not _url(v.get("url")):
                e.append("{}: board {} @{} needs the post URL".format(name, b.get("ticker"), v.get("handle")))
    for mv in m["market"].get("movers", []):
        if mv.get("why") and not _url(mv.get("source")):
            e.append("{}: mover {} explains why without a source".format(name, mv.get("ticker")))
    for c in m["market"].get("calendar", []):
        if not ISO.match(c.get("date", "")) or not _url(c.get("source")):
            e.append("{}: calendar item {!r} needs an ISO date and a source".format(name, c.get("event")))
    return e


def validate_event(ev, name):
    e = []
    for k in ("date", "ticker", "event", "verdict", "headline", "summary", "sources"):
        if not ev.get(k):
            e.append("{}: missing {}".format(name, k))
    if ev.get("date") and not ISO.match(ev["date"]):
        e.append("{}: date not ISO".format(name))
    if ev.get("verdict") and ev["verdict"] not in VERDICTS:
        e.append("{}: verdict {!r} not in {}".format(name, ev["verdict"], sorted(VERDICTS)))
    for n in ev.get("numbers", []):
        if not n.get("text") or not _url(n.get("source")):
            e.append("{}: every number needs text and a source".format(name))
    if not all(_url(u) for u in ev.get("sources", [])):
        e.append("{}: sources must be URLs".format(name))
    if "levels" in ev:
        e += validate_levels(ev["levels"], name)
    return e


# ---------------------------------------------------------------- prices

def snap(day):
    """Price snapshot for a date, or the latest one on or before it."""
    files = sorted(p for p in glob.glob(str(PRICES_DIR / "*.json")) if Path(p).stem <= day)
    return load_json(files[-1], {}) if files else {}


def px(s, t):
    return ((s.get("prices") or {}).get(t) or {}).get("price")


def cur(s, t):
    return ((s.get("prices") or {}).get(t) or {}).get("currency")


def pct(a, b):
    return round((a / b - 1) * 100, 1) if a and b else None


# ---------------------------------------------------------------- scorecard

def update_calls(latest, calls):
    changes = []
    s_memo, s_now = snap(latest["date"]), snap("9999-12-31")
    want = {a["ticker"] for a in latest["accumulate"] if a["action"] == "accumulate"}
    open_by = {c["ticker"]: c for c in calls if not c.get("closed")}
    for a in latest["accumulate"]:
        t = a["ticker"]
        if a["action"] == "accumulate" and t not in open_by:
            c = {"ticker": t, "name": a["name"], "opened": latest["date"],
                 "refPrice": px(s_memo, t), "currency": cur(s_memo, t),
                 "benchRef": px(s_memo, BENCH), "zone": a["zone"],
                 "invalidation": a["invalidation"], "closed": None}
            calls.append(c)
            changes.append("opened {} at {}".format(t, c["refPrice"]))
    for t, c in open_by.items():
        if t not in want:
            c["closed"] = {"date": latest["date"], "price": px(s_now, t), "benchPrice": px(s_now, BENCH)}
            changes.append("closed {}".format(t))
    return changes


def mark(calls, s):
    out = []
    for c in calls:
        end = c["closed"]["price"] if c.get("closed") else px(s, c["ticker"])
        bend = c["closed"]["benchPrice"] if c.get("closed") else px(s, BENCH)
        r = dict(c, lastPrice=end, ret=pct(end, c.get("refPrice")), benchRet=pct(bend, c.get("benchRef")))
        out.append(r)
    return out


# ---------------------------------------------------------------- analyst track record

def update_stances(memos, log):
    """One record per (analyst, ticker, stance) run. Opened the first memo a
    stance appears, priced from that memo's snapshot; closed when a later memo
    shows a different stance. A memo that doesn't mention the pair leaves the
    record open (no news is not a change of mind)."""
    by_key = {}
    for r in log:
        if not r.get("ended"):
            by_key[(r["handle"], r["ticker"])] = r
    for m in sorted(memos, key=lambda x: x["date"]):
        s = snap(m["date"])
        for b in m["board"]:
            for v in b["views"]:
                key = (v["handle"], b["ticker"])
                r = by_key.get(key)
                if r and r["stance"] == v["stance"]:
                    r["lastSeen"] = max(r["lastSeen"], m["date"])
                    continue
                if r:
                    if r["since"] >= m["date"]:
                        continue            # already recorded from this or a later memo
                    r["ended"] = {"date": m["date"], "price": px(s, b["ticker"]), "benchPrice": px(s, BENCH)}
                if any(x for x in log if (x["handle"], x["ticker"]) == key and x["since"] == m["date"]):
                    continue
                r = {"handle": v["handle"], "ticker": b["ticker"], "stance": v["stance"],
                     "since": m["date"], "lastSeen": m["date"], "note": v.get("note"), "url": v["url"],
                     "price": px(s, b["ticker"]), "currency": cur(s, b["ticker"]),
                     "benchPrice": px(s, BENCH), "ended": None}
                log.append(r)
                by_key[key] = r
    return log


def score_analysts(log, roster, s_now):
    """Excess return vs SMH, signed by stance: a bull call earns the stock's
    move minus SMH's, a bear call earns SMH's minus the stock's. Mixed calls
    are listed but not scored. Unpriced tickers are listed, not scored."""
    out = []
    for a in roster:
        h = a["handle"]
        rows, scored = [], []
        for r in [x for x in log if x["handle"] == h]:
            end = r["ended"]["price"] if r.get("ended") else px(s_now, r["ticker"])
            bend = r["ended"]["benchPrice"] if r.get("ended") else px(s_now, BENCH)
            ret, bret = pct(end, r.get("price")), pct(bend, r.get("benchPrice"))
            edge = None
            if ret is not None and bret is not None and r["stance"] != "mixed":
                edge = round(ret - bret if r["stance"] == "bull" else bret - ret, 1)
                scored.append(edge)
            rows.append(dict(r, ret=ret, benchRet=bret, edge=edge))
        rows.sort(key=lambda x: x["since"], reverse=True)
        out.append({"handle": h, "name": a.get("name"), "calls": len(rows), "scored": len(scored),
                    "avgEdge": round(sum(scored) / len(scored), 1) if scored else None,
                    "hitRate": round(100 * sum(1 for x in scored if x > 0) / len(scored)) if scored else None,
                    "rows": rows})
    out.sort(key=lambda x: (x["avgEdge"] is None, -(x["avgEdge"] or 0)))
    return out


# ---------------------------------------------------------------- levels + what changed

def current_levels(latest, events):
    lv = {}
    for a in latest["accumulate"]:
        if a.get("levels"):
            lv[a["ticker"]] = dict(a["levels"], ticker=a["ticker"], name=a["name"], action=a["action"],
                                   source="memo " + latest["date"])
    for ev in sorted(events, key=lambda x: x["date"]):
        if ev["date"] >= latest["date"] and ev.get("levels"):
            base = lv.get(ev["ticker"], {"ticker": ev["ticker"], "name": ev["ticker"], "action": "watch"})
            lv[ev["ticker"]] = dict(base, **ev["levels"], source="event " + ev["date"])
    return {"memo": latest["date"], "built": now_iso(), "levels": lv}


def what_changed(memos, calls, events):
    latest = memos[0]
    prev = memos[1] if len(memos) > 1 else None
    items = []
    opened = [c for c in calls if c["opened"] == latest["date"]]
    closed = [c for c in calls if c.get("closed") and c["closed"]["date"] == latest["date"]]
    for c in opened:
        items.append({"kind": "open", "text": "Opened call: {} at {} {}".format(
            c["ticker"], "{:,.2f}".format(c["refPrice"]).rstrip("0").rstrip("."), c.get("currency") or "") if c.get("refPrice") else
            "Opened call: {} (no price in the sheet)".format(c["ticker"])})
    for c in closed:
        items.append({"kind": "close", "text": "Closed call: {}".format(c["ticker"])})
    if prev:
        pa = {a["ticker"]: a for a in prev["accumulate"]}
        la = {a["ticker"]: a for a in latest["accumulate"]}
        for t, a in la.items():
            if t not in pa:
                items.append({"kind": "new", "text": "New on the list: {} ({})".format(a["name"], a["action"])})
            elif pa[t]["action"] != a["action"]:
                items.append({"kind": "move", "text": "{}: {} → {}".format(a["name"], pa[t]["action"], a["action"])})
            elif (pa[t].get("levels") or {}) != (a.get("levels") or {}):
                items.append({"kind": "move", "text": "{}: zone levels changed".format(a["name"])})
        for t, a in pa.items():
            if t not in la:
                items.append({"kind": "drop", "text": "Dropped from the list: {}".format(a["name"])})
        pv = {(v["handle"], b["ticker"]): v["stance"] for b in prev["board"] for v in b["views"]}
        for b in latest["board"]:
            for v in b["views"]:
                old = pv.get((v["handle"], b["ticker"]))
                if old and old != v["stance"]:
                    items.append({"kind": "flip", "text": "@{} flipped on {}: {} → {}".format(
                        v["handle"], b["ticker"], old, v["stance"])})
    else:
        items.append({"kind": "new", "text": "First memo: the list, the board and the scorecard start here."})
    for ev in sorted(events, key=lambda x: x["date"]):
        if ev["date"] >= latest["date"]:
            items.append({"kind": "event", "text": "{} {}: {} ({})".format(ev["date"], ev["ticker"], ev["headline"], ev["verdict"])})
    return items


# ---------------------------------------------------------------- main

def load_dir(folder, check):
    items, errors = [], []
    for f in sorted(glob.glob(str(folder / "*.json"))):
        try:
            x = json.loads(Path(f).read_text(encoding="utf-8"))
        except json.JSONDecodeError as ex:
            errors.append("{}: not valid JSON: {}".format(Path(f).name, ex))
            continue
        errors += check(x, Path(f).name)
        items.append(x)
    return items, errors


def main():
    memos, e1 = load_dir(MEMOS, validate)
    events, e2 = load_dir(EVENTS, validate_event)
    if e1 or e2:
        print("ERRORS:\n  " + "\n  ".join(e1 + e2))
        return 1
    memos.sort(key=lambda m: m["date"], reverse=True)
    events.sort(key=lambda m: m["date"], reverse=True)
    s_now = snap("9999-12-31")
    roster = load_json(DESK / "analysts.json", {"analysts": []})["analysts"]

    calls = load_json(CALLS, [])
    changes = update_calls(memos[0], calls) if memos else []
    save_json(CALLS, calls)

    log = update_stances(memos, load_json(STANCE_LOG, []))
    save_json(STANCE_LOG, log)
    board_handles = {r["handle"] for r in log}
    track = score_analysts(log, roster + [{"handle": h} for h in sorted(board_handles - {a["handle"] for a in roster})], s_now)

    levels = current_levels(memos[0], events) if memos else {"levels": {}}
    save_json(LEVELS, levels)

    wanted = set(levels["levels"]) | {c["ticker"] for c in calls} | {r["ticker"] for r in log} | {BENCH}
    quotes = {t: {"price": px(s_now, t), "currency": cur(s_now, t)} for t in sorted(wanted) if px(s_now, t) is not None}

    state = load_json(STATE_FILE, {})
    desk = {"quotes": quotes, "built": now_iso(), "pricesAsOf": s_now.get("asOf"), "collectorLastRun": state.get("lastRun"),
            "analysts": roster, "memos": memos, "events": events, "calls": mark(calls, s_now), "bench": BENCH,
            "changes": what_changed(memos, calls, events) if memos else [],
            "track": track, "levels": levels["levels"],
            "alerts": load_json(ALERT_LOG, [])[-20:][::-1]}
    (ROOT / "desk.js").write_text(
        "// Generated by desk/build.py from desk/memos and desk/store. Do not edit by hand.\n"
        "window.DESK = " + json.dumps(desk, indent=1, ensure_ascii=False) + ";\n", encoding="utf-8")

    print("{} memo(s), {} event(s), {} call(s) ({} open), {} stance record(s), {} alert level(s)".format(
        len(memos), len(events), len(calls), sum(1 for c in calls if not c.get("closed")),
        len(log), len(levels["levels"])))
    for ch in changes:
        print("scorecard:", ch)
    unpriced = [c["ticker"] for c in calls if not c.get("closed") and c.get("refPrice") is None]
    if unpriced:
        print("WARNING: open calls with no price in the sheet:", ", ".join(unpriced))
    print("wrote desk.js")
    return 0


if __name__ == "__main__":
    sys.exit(main())
