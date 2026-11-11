#!/usr/bin/env python3
"""The trade brain: which quick-trade setups have actually paid on these names
with entries the operator can really get, which orders could rest tonight, and
an honest paper record of every fill.

Built on the same daily bars as desk/ta.py (the sheet's price_history tab, via
support.load()). No look-ahead: a floor exists only once its swing low is
confirmed, and a signal on day i sees bars up to day i only.

The operator is asleep during US hours, so execution is part of the test:

    resting orders (placed in advance, filled at the line)
      floor        a LIMIT buy resting at a confirmed swing-low floor; fills
                   when the price comes down to it
      breakstop    a STOP buy resting at the 40-day high while the name is in an
                   uptrend; fills when the price pokes above it
    next-open orders (seen after the close, bought at the next session's open)
      breakout     a CLOSE above the 40-day high in an uptrend
      washout      three falling closes worth more than two typical daily
                   ranges, then the first up close
      pullback     a dip to a rising 50-day in an uptrend, closing back above it
      reclaim      the first close above the 50-day after ten closes below

One trade: stop one typical daily range (20-session ATR) below the entry,
target two ranges above (reward 2 for risk 1), out at the close of session 15
if neither is hit. Results are in R: 1R = the amount risked. On the day a
resting order fills, a low at or under the stop counts as stopped and a
same-day target does not count (the cautious reading of a daily bar).

Every setup is judged against "any day": a trade opened every fifth session at
the open. These names mostly rose, so buying on any day made money too. A setup
is TRADABLE only if it has MIN_TRADES trades and beats the baseline both over
the whole record and in today's tide.

    python3 desk/setups.py         print the lab, the order sheet and the paper record
"""
import sys
from datetime import date, datetime, timedelta

import support
import ta
from common import STORE, load_json, save_json
from plan import tide_at

OUT = STORE / "setups.json"
JOURNAL = STORE / "trades.json"
STOP_ATR, TARGET_ATR, MAX_DAYS = 1.0, 2.0, 15
MIN_TRADES = 30
REACH = 2.5                                   # a resting order is listed when its line is within this many daily ranges
SIDE, MERGE, TOUCH, COOLDOWN = ta.SIDE, ta.MERGE, ta.TOUCH, ta.COOLDOWN
LEVERAGED = {"SOXL", "KORU", "SOXS"}          # kept out of the lab: they distort the pool
ORDER = ["floor", "breakstop", "breakout", "washout", "pullback", "reclaim", "anyday"]
LABELS = {"floor": "Limit order at a support floor", "breakstop": "Stop order at the 40-day high", "breakout": "Close above the 40-day high",
          "washout": "Washout reversal", "pullback": "Pullback to a rising 50-day", "reclaim": "Reclaim of the 50-day",
          "anyday": "Any day (baseline)"}
HOW = {"floor": "resting limit order", "breakstop": "resting stop order", "breakout": "next open", "washout": "next open",
       "pullback": "next open", "reclaim": "next open", "anyday": "at the open"}
WHAT = {"floor": "A buy order waits at a swing-low floor the stock has already formed, and fills when the price comes down to it.",
        "breakstop": "A buy order waits at the highest high of the last 40 sessions while the stock is in an uptrend, and fills on the first poke above.",
        "breakout": "The stock closes above its 40-day high in an uptrend; bought at the next open.",
        "washout": "Three down closes in a row worth more than two typical daily ranges, then the first up close; bought at the next open.",
        "pullback": "A dip to a rising 50-day in an uptrend that closes back above it; bought at the next open.",
        "reclaim": "First close back above the 50-day after ten closes below it; bought at the next open.",
        "anyday": "A trade opened every fifth session at the open, whatever the chart says. Every setup is judged against this."}


def atr(bars, i, n=20):
    if i < n:
        return None
    return sum(max(bars[j][1] - bars[j][2], abs(bars[j][1] - bars[j - 1][3]), abs(bars[j][2] - bars[j - 1][3]))
               for j in range(i - n + 1, i + 1)) / n


def outcome(bars, i, entry, a, resting):
    """Result in R of a trade entered on day i at `entry` with range `a`."""
    risk = STOP_ATR * a
    stop, target = entry - risk, entry + TARGET_ATR * a
    first = i if resting else i + 1                       # a next-open trade is entered at bars[i+1]'s open
    if first >= len(bars):
        return None
    last = min(first + MAX_DAYS - 1, len(bars) - 1)
    for j in range(first, last + 1):
        _, hi, lo, close, op = bars[j]
        same = j == first
        if not same and op <= stop:                       # gapped through the stop: out at the open
            return {"r": (op - entry) / risk, "exit": bars[j][0].isoformat(), "how": "stop", "done": True}
        if lo <= stop:
            return {"r": -1.0, "exit": bars[j][0].isoformat(), "how": "stop", "done": True}
        if hi >= target and not (same and resting):       # a same-day target on a resting fill is not counted
            return {"r": TARGET_ATR / STOP_ATR, "exit": bars[j][0].isoformat(), "how": "target", "done": True}
    done = last == first + MAX_DAYS - 1
    return {"r": (bars[last][3] - entry) / risk, "exit": bars[last][0].isoformat(), "how": "time" if done else "open", "done": done}


def floors(bars):
    """(fills, bands) from desk/ta.py's forward walk. A fill is a limit order
    resting at a floor's level on a day the low actually reached it; when two
    floors are reached on one day the higher order fills."""
    bands = ta.floor_walk(bars)
    by_day = {}
    for b in bands:
        for i, level in b["touches"]:
            if bars[i][2] <= level and level > by_day.get(i, (0, 0))[0]:
                by_day[i] = (level, len(b["formed"]))
    fills = [(i, min(bars[i][4], lv), n) for i, (lv, n) in sorted(by_day.items())]
    return fills, bands


def events(bars):
    """Every past trade on one name: [(setup, day index, entry price, resting?)]."""
    c = [b[3] for b in bars]
    m50, m200 = ta.moving(c, "sma", 50), ta.moving(c, "sma", 200)
    out = [("floor", i, entry, True) for i, entry, _ in floors(bars)[0] if i >= 221]
    for i in range(221, len(bars)):
        nxt = bars[i + 1][4] if i + 1 < len(bars) else None
        up_prev = m200[i - 1] is not None and c[i - 1] > m200[i - 1] and m50[i - 1] > m50[i - 11]
        hh = max(b[1] for b in bars[i - 40:i])
        if up_prev and c[i - 1] <= hh and bars[i][1] > hh:
            out.append(("breakstop", i, max(bars[i][4], hh), True))
        up = m200[i] is not None and c[i] > m200[i] and m50[i] > m50[i - 10]
        a = atr(bars, i - 1)
        if up and c[i] > hh and c[i - 1] <= max(b[1] for b in bars[i - 41:i - 1]):
            out.append(("breakout", i, nxt, False))
        if c[i] > c[i - 1] and c[i - 1] < c[i - 2] < c[i - 3] < c[i - 4] and (c[i - 4] - c[i - 1]) > 2 * a:
            out.append(("washout", i, nxt, False))
        if up and bars[i][2] <= m50[i] * 1.01 and c[i] > m50[i] and c[i - 1] > m50[i - 1] * 1.01:
            out.append(("pullback", i, nxt, False))
        if c[i] > m50[i] and all(c[j] < m50[j] for j in range(i - 10, i)):
            out.append(("reclaim", i, nxt, False))
        if i % 5 == 0:
            out.append(("anyday", i, bars[i][4], True))
    return out


def _stat(rs, base=None):
    if not rs:
        return {"n": 0}
    s = {"n": len(rs), "winRate": round(100 * sum(1 for r in rs if r >= TARGET_ATR / STOP_ATR - 1e-9) / len(rs)),
         "avgR": round(sum(rs) / len(rs), 2)}
    if base and base.get("n"):
        s["edge"] = round(s["avgR"] - base["avgR"], 2)
    return s


def lab(data, tide_state):
    smh = data.get("SMH") or []
    sc = [b[3] for b in smh]
    sidx = {b[0]: i for i, b in enumerate(smh)}
    res, pool = {}, []
    for key, bars in data.items():
        if key in LEVERAGED or len(bars) < 300:
            continue
        pool.append(key)
        c = [b[3] for b in bars]
        m200 = ta.moving(c, "sma", 200)
        for setup, i, entry, resting in events(bars):
            if entry is None:
                continue
            o = outcome(bars, i, entry, atr(bars, i - 1 if resting else i), resting)
            if not o or not o["done"]:
                continue
            td = tide_at(sc, sidx[bars[i][0]]) if bars[i][0] in sidx else None
            own = "below200" if m200[i - 1] is not None and c[i - 1] < m200[i - 1] else "above200"
            for k in ("all", td, own):
                if k:
                    res.setdefault((setup, k), []).append(o["r"])
    rows = []
    for setup in ORDER:
        row = {"setup": setup, "label": LABELS[setup], "how": HOW[setup], "what": WHAT[setup]}
        for k in ("all", "in", "turning", "out", "above200", "below200"):
            row[k] = _stat(res.get((setup, k), []), _stat(res.get(("anyday", k), [])) if setup != "anyday" else None)
        a, now = row["all"], row.get(tide_state) or {}
        beats_now = now.get("edge", 0) > 0 if now.get("n", 0) >= MIN_TRADES else True
        row["tradable"] = setup != "anyday" and a["n"] >= MIN_TRADES and a.get("edge", 0) > 0 and beats_now
        row["thin"] = row["tradable"] and a.get("edge", 0) < 0.15
        rows.append(row)
    return {"rows": rows, "pool": sorted(pool), "tide": tide_state,
            "rules": {"stop": STOP_ATR, "target": TARGET_ATR, "maxDays": MAX_DAYS, "minTrades": MIN_TRADES}}


def _size(level, a, ccy, fx, risk, free):
    """Shares so that a stop-out costs `risk` RM, capped by what the pot has free."""
    if not (risk and ccy and fx.get(ccy)):
        return {}
    per_share = STOP_ATR * a * fx[ccy]
    shares = int(risk // per_share)
    if free is not None and shares * level * fx[ccy] > free:
        shares = int(free // (level * fx[ccy]))
    return {"risk": risk, "shares": shares, "sizeMYR": round(shares * level * fx[ccy]), "lossAtStop": round(shares * per_share)}


def _plus(iso, days):
    return (datetime.strptime(iso, "%Y-%m-%d").date() + timedelta(days=days)).isoformat()


def order_sheet(data, lab_rows, quotes, money, cap, names, calendar, frozen):
    """What could be acted on now: limit orders that could rest at the nearest
    confirmed floors, and next-open signals from the latest bar."""
    by = {r["setup"]: r for r in lab_rows}
    fx = (money or {}).get("fx", {})
    risk = (cap or {}).get("riskPerTrade")
    free = ((cap or {}).get("pots") or {}).get("trades", {}).get("free")
    today = date.today().isoformat()
    out = []
    for key, bars in data.items():
        if key in LEVERAGED or len(bars) < 300:
            continue
        i = len(bars) - 1
        a, close, ccy = atr(bars, i), bars[i][3], (quotes.get(key) or {}).get("currency")
        soon = [c for c in calendar if c.get("ticker") == key and today <= c["date"] <= _plus(today, 4)]
        base = {"ticker": key, "name": names.get(key, key), "date": bars[i][0].isoformat(), "currency": ccy,
                "rr": int(TARGET_ATR / STOP_ATR), "atrPct": round(a / close * 100, 1), "close": close}
        if soon:
            base["blocked"] = "results on {}".format(soon[0]["date"])
        elif key in (frozen or {}):
            base["blocked"] = "frozen below its break line"

        def add(setup, level, extra):
            rec = by[setup]["all"]
            s = dict(base, setup=setup, label=LABELS[setup], how=HOW[setup], entry=round(level, 2), stop=round(level - STOP_ATR * a, 2),
                     target=round(level + TARGET_ATR * a, 2), tradable=by[setup]["tradable"], thin=by[setup].get("thin"),
                     n=rec["n"], winRate=rec.get("winRate"), avgR=rec.get("avgR"), edge=rec.get("edge"))
            s.update(_size(level, a, ccy, fx, risk, free))
            s.update(extra)
            out.append(s)

        _, bands = floors(bars)
        live = [b for b in bands if close > b["hi"] * (1 + TOUCH) and (i + 1) - b["last"] > COOLDOWN and (close - b["hi"]) <= REACH * a]
        for b in sorted(live, key=lambda x: -x["hi"])[:1]:
            add("floor", b["hi"], {"kind": "resting", "away": round((b["hi"] / close - 1) * 100, 1),
                                  "formed": [bars[k][0].isoformat() for k in b["formed"][-3:]], "lows": len(b["formed"])})
        for setup, j, entry, resting in events(bars[-260:]):
            if j == len(bars[-260:]) - 1 and not resting and setup != "anyday":
                add(setup, close, {"kind": "next-open"})
    out.sort(key=lambda s: (not s["tradable"], bool(s.get("blocked")), abs(s.get("away", 0))))
    return out


def journal(data, lab_rows):
    """The paper record: every fill of a logged setup since the journal began,
    closed by its own rules from the daily bars. Never edited by hand."""
    j = load_json(JOURNAL, None)
    if not isinstance(j, dict):
        j = {"since": date.today().isoformat(), "trades": []}
    tradable = {r["setup"]: r["tradable"] for r in lab_rows}
    known = {t["id"]: t for t in j["trades"]}
    for key, bars in data.items():
        if key in LEVERAGED or len(bars) < 300:
            continue
        for setup, i, entry, resting in events(bars):
            d = bars[i][0].isoformat()
            if setup == "anyday" or entry is None or d < j["since"]:
                continue
            tid = "{}|{}|{}".format(setup, key, d)
            t = known.get(tid)
            if t is None:
                t = {"id": tid, "setup": setup, "label": LABELS[setup], "ticker": key, "date": d, "entry": round(entry, 2),
                     "tradable": tradable.get(setup, False), "status": "open", "r": None}
                j["trades"].append(t)
                known[tid] = t
            if t["status"] != "closed":
                o = outcome(bars, i, entry, atr(bars, i - 1 if resting else i), resting)
                if o:
                    t.update(r=round(o["r"], 2), exit=o["exit"], how=o["how"], status="closed" if o["done"] else "open")
    save_json(JOURNAL, j)
    rs = [t["r"] for t in j["trades"] if t["status"] == "closed" and t["tradable"]]
    return {"since": j["since"], "trades": sorted(j["trades"], key=lambda t: t["date"], reverse=True)[:40],
            "closed": len(rs), "wins": sum(1 for r in rs if r > 0), "totalR": round(sum(rs), 2) if rs else 0,
            "open": sum(1 for t in j["trades"] if t["status"] != "closed")}


# ---------------------------------------------------------------- fund lab

def fund_lab(data, tickers=("SMH", "QQQ")):
    """Three ways of stepping into an ETF with one unit of cash a month, on the
    same history: monthly whatever happens; only after a washout reversal (cash
    waits); only while the fund is above its 200-day (cash waits below it)."""
    out = []
    for t in tickers:
        bars = data.get(t) or []
        if len(bars) < 300:
            continue
        c = [b[3] for b in bars]
        m200 = ta.moving(c, "sma", 200)
        wash = {i for s, i, _, _ in events(bars) if s == "washout"}
        start, res = 221, {}
        for mode in ("monthly", "washout", "above200"):
            cash = shares = paid = 0.0
            month, peak, worst = None, 0.0, 0.0
            for i in range(start, len(bars) - 1):
                m = bars[i][0].strftime("%Y-%m")
                if m != month:
                    month = m
                    cash += 1.0
                go = mode == "monthly" or (mode == "washout" and i in wash) or (mode == "above200" and c[i] > m200[i])
                if go and cash > 0:
                    shares += cash / bars[i + 1][4]          # bought at the next open
                    paid += cash
                    cash = 0.0
                put = paid + cash
                if put:
                    value = (shares * c[i] + cash) / put
                    peak = max(peak, value)
                    worst = min(worst, value / peak - 1)
            put = paid + cash
            res[mode] = {"ret": round((shares * c[-1] + cash) / put * 100 - 100, 1) if put else None,
                         "invested": round(100 * paid / put) if put else 0, "worst": round(worst * 100, 1)}
        out.append({"ticker": t, "from": bars[start][0].isoformat(), "to": bars[-1][0].isoformat(), "modes": res})
    return out


def build(data, quotes, money, cap, names, calendar, tide_state, frozen):
    L = lab(data, tide_state)
    out = {"lab": L, "orders": order_sheet(data, L["rows"], quotes, money, cap, names, calendar, frozen),
           "record": journal(data, L["rows"]), "fund": fund_lab(data)}
    save_json(OUT, out)
    return out


def main():
    data = support.load()
    smh = [b[3] for b in data.get("SMH") or []]
    state = tide_at(smh, len(smh) - 1) or "turning"
    quotes = load_json(STORE / "prices_latest.json", {}).get("prices", {})
    res = build(data, quotes, load_json(STORE / "money.json", None), None, {}, [], state, {})
    print("Setup lab: {} names, stop {} ATR, target {} ATR, {} sessions max. Tide today: {}".format(
        len(res["lab"]["pool"]), STOP_ATR, TARGET_ATR, MAX_DAYS, state))
    print("  {:32} {:20} {:>6} {:>5} {:>7} {:>6}   avg R by tide in / turning / out · name above / below its 200-day".format(
        "setup", "entry", "trades", "win%", "avg R", "edge"))
    for r in res["lab"]["rows"]:
        a = r["all"]
        cell = lambda k: "{:+.2f} ({})".format(r[k]["avgR"], r[k]["n"]) if r[k].get("n") else "n/a"
        print("  {:32} {:20} {:>6} {:>4}% {:>+7.2f} {:>6}   {} / {} / {} · {} / {}{}".format(
            r["label"], r["how"], a["n"], a.get("winRate", 0), a.get("avgR", 0), "{:+.2f}".format(a["edge"]) if "edge" in a else "",
            cell("in"), cell("turning"), cell("out"), cell("above200"), cell("below200"),
            "   TRADABLE" + (" (thin edge)" if r["thin"] else "") if r["tradable"] else ""))
    print("\nOrder sheet:")
    for s in res["orders"]:
        print("  {:10} {:32} {:9} entry {:>10} stop {:>10} target {:>10} {}{}{}".format(
            s["ticker"], s["label"], s["kind"], s["entry"], s["stop"], s["target"],
            "{:+.1f}% away  ".format(s["away"]) if "away" in s else "", "TRADABLE" if s["tradable"] else "no edge",
            "  BLOCKED: " + s["blocked"] if s.get("blocked") else ""))
    rec = res["record"]
    print("\nPaper record since {}: {} closed ({} wins, {:+.2f}R), {} open".format(rec["since"], rec["closed"], rec["wins"], rec["totalR"], rec["open"]))
    for f in res["fund"]:
        print("\nFund lab {} ({} to {}):".format(f["ticker"], f["from"], f["to"]))
        for k, v in f["modes"].items():
            print("  {:10} return on money set aside {:+.1f}% · {}% invested · worst drop {}%".format(k, v["ret"], v["invested"], v["worst"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
