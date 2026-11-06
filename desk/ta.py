#!/usr/bin/env python3
"""Tested support levels: which lines has each stock actually bounced from?

The weekly memo used to set one buy line 3% above the nearest swing low. This
script asks the question a quant desk would ask first: when the price came
down to a given line in the past, how often did that line hold, and what
happened next? It tests every candidate on the same daily bars the desk
already uses (the Google Sheet's price_history tab, about four years since
6 Nov 2026, via support.load()), with
no look-ahead: each day only sees the bars up to that day.

Candidate lines
    SMA 20 / 50 / 100 / 200   simple moving averages of the close
    EMA 21 / 50               exponential moving averages of the close
    Floor                     a daily swing low (lowest low 5 sessions either
                              side), confirmed 5 sessions later, merged with
                              swing lows within 3%

A touch
    The day's low comes within TOUCH (1%) of the line, the previous close sat
    more than TOUCH above it, and the line was not touched in the previous
    COOLDOWN (5) sessions.

The outcome of a touch, over the next HOLD_DAYS (5) sessions
    held   no close more than BREAK (2%) below the line
    broke  a close more than 2% below it
    plus the close-to-close return over FWD (10) sessions from the touch day,
    the deepest low below the line in the next 5 sessions (adverse move), and
    the best high in the next 10 sessions (bounce).

Scoring
    Small samples lie, so each name's hold rate is pulled towards the hold rate
    of the same kind of line across every name in the tab (a beta prior worth
    PRIOR touches): shrunk = (held + PRIOR * pooled) / (touches + PRIOR). The
    10-session return after a touch is compared with the name's own average
    10-session return over the year (its drift), so "edge" is what the touch
    added beyond the trend. Each record is also given for the last year alone,
    so a line whose behaviour has changed shows it.

Output
    desk/store/ta.json, which build.py puts into desk.js for the page:
    per name, the tested lines below and above the price, each with its record
    and every touch (date, held or broke, 10-session return); and the pooled
    record per kind of line.

    python3 desk/ta.py            all names, writes desk/store/ta.json
    python3 desk/ta.py TSM MU     print just these, write nothing
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import support

STORE = Path(__file__).resolve().parent / "store"
OUT = STORE / "ta.json"

TOUCH = 0.01
BREAK = 0.02
HOLD_DAYS = 5
FWD = 10
COOLDOWN = 5
PRIOR = 6
SIDE = support.SIDE
MERGE = support.MERGE
MA_KEEP = 190            # days of moving-average values sent to the page (matches the chart history)
SHOW_WITHIN = 0.30       # lines more than 30% away are not shown

KINDS = [("sma", 20), ("sma", 50), ("sma", 100), ("sma", 200), ("ema", 21), ("ema", 50)]


def label(kind, n=None):
    return "Floor" if kind == "floor" else "{}{} {}d".format(kind.upper(), "", n)


def moving(closes, kind, n):
    """Series aligned to closes; None until there are n closes."""
    out = [None] * len(closes)
    if kind == "sma":
        s = 0.0
        for i, c in enumerate(closes):
            s += c
            if i >= n:
                s -= closes[i - n]
            if i >= n - 1:
                out[i] = s / n
    else:
        k = 2 / (n + 1)
        e = None
        for i, c in enumerate(closes):
            if i == n - 1:
                e = sum(closes[:n]) / n
            elif i >= n:
                e = c * k + e * (1 - k)
            out[i] = e
    return out


def outcome(bars, i, level):
    """Held or broke, 10-session return, adverse move and bounce for a touch on day i."""
    nxt = bars[i + 1:i + 1 + HOLD_DAYS]
    if len(nxt) < HOLD_DAYS:
        return None                                   # too recent to judge
    held = all(b[3] >= level * (1 - BREAK) for b in nxt)
    fwd = bars[i + FWD][3] / bars[i][3] - 1 if i + FWD < len(bars) else None
    mae = min(b[2] for b in bars[i:i + 1 + HOLD_DAYS]) / level - 1
    up = bars[i + 1:i + 1 + FWD]
    bounce = max(b[1] for b in up) / level - 1 if up else None
    return {"d": bars[i][0].isoformat(), "held": held, "fwd": None if fwd is None else round(fwd * 100, 1),
            "mae": round(mae * 100, 1), "bounce": None if bounce is None else round(bounce * 100, 1)}


def touches_dynamic(bars, series, dr):
    out, last = [], -99
    for i in range(1, len(bars)):
        lv, pv = series[i], series[i - 1]
        if lv is None or pv is None:
            continue
        if bars[i][2] <= lv * (1 + TOUCH) and bars[i - 1][3] > pv * (1 + TOUCH) and i - last > COOLDOWN:
            last = i
            o = outcome(bars, i, lv)
            if o:
                o["lv"] = round(lv, 2)
                o["up"] = i >= 10 and series[i - 10] is not None and lv > series[i - 10]   # line rising over 10 sessions
                o["ex"] = None if o["fwd"] is None else round(o["fwd"] - dr, 1)
                out.append(o)
    return out


def floor_bands(bars):
    """Every confirmed swing-low band in the history: [{'lo','hi','formed':[(i,date)]}]."""
    piv = []
    for i in range(SIDE, len(bars) - SIDE):
        w = bars[i - SIDE:i + SIDE + 1]
        if bars[i][2] == min(b[2] for b in w):
            piv.append((bars[i][2], i))
    bands = []
    for low, i in sorted(piv):
        for b in bands:
            if abs(low / b["lo"] - 1) < MERGE or abs(low / b["hi"] - 1) < MERGE:
                b["lo"], b["hi"] = min(b["lo"], low), max(b["hi"], low)
                b["formed"].append(i)
                break
        else:
            bands.append({"lo": low, "hi": low, "formed": [i]})
    return bands


def touches_floor(bars, band, dr):
    """Touches of a floor band after it was first confirmed (formed + SIDE sessions)."""
    start = min(band["formed"]) + SIDE
    top, out, last = band["hi"], [], -99
    for i in range(max(start, 1), len(bars)):
        if bars[i][2] <= top * (1 + TOUCH) and bars[i - 1][3] > top * (1 + TOUCH) and i - last > COOLDOWN:
            last = i
            o = outcome(bars, i, top)
            if o:
                o["lv"] = round(top, 2)
                o["up"] = None
                o["ex"] = None if o["fwd"] is None else round(o["fwd"] - dr, 1)
                out.append(o)
    return out


def drift(bars):
    r = [bars[i + FWD][3] / bars[i][3] - 1 for i in range(len(bars) - FWD)]
    return sum(r) / len(r) * 100 if r else 0.0


def summary(t):
    n, h = len(t), sum(1 for x in t if x["held"])
    f = [x["fwd"] for x in t if x["fwd"] is not None]
    e = [x["ex"] for x in t if x.get("ex") is not None]
    return {"n": n, "held": h, "rate": round(h / n * 100) if n else None,
            "fwd": round(sum(f) / len(f), 1) if f else None,
            "edge": round(sum(e) / len(e), 1) if e else None,
            "mae": round(sum(x["mae"] for x in t) / n, 1) if n else None}


RECENT = 252            # sessions in "the last year" column


def analyse(data):
    names, pooled_raw, cut = {}, {}, {}
    for key, bars in data.items():
        if len(bars) < 60:
            continue
        closes = [b[3] for b in bars]
        px, dr = closes[-1], drift(bars)
        cut[key] = bars[-RECENT][0].isoformat() if len(bars) > RECENT else bars[0][0].isoformat()
        lines = []
        for kind, n in KINDS:
            s = moving(closes, kind, n)
            if s[-1] is None:
                continue
            t = touches_dynamic(bars, s, dr)
            for x in t:
                x["recent"] = x["d"] >= cut[key]
            pooled_raw.setdefault(label(kind, n), []).extend(t)
            lines.append({"kind": kind, "n": n, "label": label(kind, n), "value": round(s[-1], 2), "touches": t,
                          "series": [[bars[i][0].isoformat(), round(v, 2)] for i, v in enumerate(s) if v is not None][-MA_KEEP:]})
        for b in floor_bands(bars):
            t = touches_floor(bars, b, dr)
            for x in t:
                x["recent"] = x["d"] >= cut[key]
            formed = sorted(bars[i][0].isoformat() for i in b["formed"])
            pooled_raw.setdefault("Floor", []).extend(t)
            lines.append({"kind": "floor", "label": "Floor", "value": round(b["hi"], 2), "low": round(b["lo"], 2),
                          "formed": formed, "touches": t})
        names[key] = {"price": px, "asOf": bars[-1][0].isoformat(), "from": bars[0][0].isoformat(), "drift": round(dr, 1), "lines": lines, "bars": len(bars)}

    pooled = {}
    for k, v in pooled_raw.items():
        pooled[k] = summary(v)
        pooled[k]["recent"] = summary([x for x in v if x["recent"]])
        if k != "Floor":
            pooled[k]["rising"] = summary([x for x in v if x.get("up")])
            pooled[k]["falling"] = summary([x for x in v if x.get("up") is False])
    for key, nm in names.items():
        out_below, out_above = [], []
        for ln in nm["lines"]:
            s = summary(ln["touches"])
            p = (pooled.get(ln["label"]) or {}).get("rate") or 50
            shrunk = (s["held"] + PRIOR * p / 100) / (s["n"] + PRIOR) * 100
            dist = ln["value"] / nm["price"] - 1
            if abs(dist) > SHOW_WITHIN:
                continue
            row = {k: v for k, v in ln.items() if k != "touches"}
            row.update(s, recent=summary([x for x in ln["touches"] if x["recent"]]), shrunk=round(shrunk), dist=round(dist * 100, 1),
                       edge=None if s["fwd"] is None else round(s["fwd"] - nm["drift"], 1),
                       last=ln["touches"][-1]["d"] if ln["touches"] else None,
                       hist=ln["touches"][-8:])
            (out_below if dist <= 0.003 else out_above).append(row)
        # A floor only counts as support with a record; a moving average always shows so its slope is visible.
        out_below.sort(key=lambda r: (-r["shrunk"], -r["dist"]))
        out_above.sort(key=lambda r: r["dist"])
        nm["support"], nm["resistance"] = out_below, out_above
        nm["best"] = next((r["label"] + (" " + str(r["value"]) if r["kind"] == "floor" else "") for r in out_below if r["n"] >= 2), None)
        del nm["lines"]
    return {"built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "rules": {"touch": TOUCH, "break": BREAK, "holdDays": HOLD_DAYS, "fwd": FWD, "prior": PRIOR},
            "pooled": pooled, "names": names}


def show(res, keys):
    print("Pooled record by kind of line (every name in the tab):")
    for k, s in sorted(res["pooled"].items(), key=lambda x: -(x[1]["rate"] or 0)):
        print("  {:8s} last yr {:>4}%/{:<3d} | {:3d} touches  held {:3}%  10d after {:+.1f}%  vs drift {:+.1f}%  adverse {:+.1f}%{}".format(
            k, s["recent"]["rate"], s["recent"]["n"], s["n"], s["rate"] if s["rate"] is not None else 0, s["fwd"] or 0, s["edge"] or 0, s["mae"] or 0,
            "  | rising line: held {}% of {}, falling: {}% of {}".format(s["rising"]["rate"], s["rising"]["n"], s["falling"]["rate"], s["falling"]["n"]) if "rising" in s else ""))
    for key in keys:
        nm = res["names"].get(key)
        if not nm:
            print("\n{}: no history".format(key))
            continue
        print("\n{}  {:,.2f} on {}  ({} sessions, drift {:+.1f}% per 10d)  best tested support: {}".format(
            key, nm["price"], nm["asOf"], nm["bars"], nm["drift"], nm["best"] or "none with 2+ touches"))
        for r in nm["support"][:6]:
            print("   support {:8s} {:>12,.2f} ({:+.1f}%)  held {}/{}  score {}%  10d {}  last {}".format(
                r["label"], r["value"], r["dist"], r["held"], r["n"], r["shrunk"],
                "{:+.1f}%".format(r["fwd"]) if r["fwd"] is not None else "n/a", r["last"] or "never touched"))
        for r in nm["resistance"][:3]:
            print("   above   {:8s} {:>12,.2f} ({:+.1f}%)".format(r["label"], r["value"], r["dist"]))


def main():
    res = analyse(support.load())
    keys = sys.argv[1:]
    if keys:
        show(res, keys)
        return 0
    OUT.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    show(res, sorted(res["names"]))
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
