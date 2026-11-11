#!/usr/bin/env python3
"""The desk's brain: turns levels, prices and the operator's own sizing rules
into one decision per name. Called by desk/build.py; nothing here fetches.

    tide        is the market helping or hurting (SMH against its averages, and
                how many of the operator's names sit above their own 50-day)
    freeze      a daily close below a name's break line stops all buying on it
                until it closes back above, or a later memo re-argues the case
    capital     liquid money minus the reserve = deployable, split into three
                pots (fund, shots, quick trades); what each pot has left
    rows        per name: state, room to add in RM and shares, position maths
    notices     what Telegram should be told once (freeze, thaw, triggers)
    voices      hedge chatter and roster health from the post store

Rules come from desk/store/book.json (private). Amounts are the operator's own
arithmetic on his own settings: research support, not advice.
"""
import glob
import re
from datetime import date, datetime, timedelta, timezone

from alerts import money as fmt_money, zone_of
from common import POSTS_DIR, load_json
from support import swing

POT_OF = {"fund": "fund", "core": "fund", "shot": "shots"}
STATE_TEXT = {
    "frozen": "Frozen", "exit2": "Exit step 2", "exit1": "Exit step 1", "trigger": "Trigger hit", "add": "Add zone",
    "buy": "Buy zone", "wait": "Wait", "above": "No adding", "trim": "Trim zone", "watch": "Watch", "noprice": "No price",
}


# ---------------------------------------------------------------- tide

def _sma(c, n, i):
    return sum(c[i - n + 1:i + 1]) / n if i >= n - 1 else None


def tide_at(c, i):
    """SMH-only tide on day i of a close series: 'in', 'out', 'turning' or None."""
    if i < 210:
        return None
    m50, m50p, m200 = _sma(c, 50, i), _sma(c, 50, i - 10), _sma(c, 200, i)
    if c[i] > m200 and c[i] > m50 and m50 > m50p:
        return "in"
    if c[i] < m50 and m50 < m50p:
        return "out"
    return "turning"


def tide(data, tickers, bench="SMH"):
    bars = data.get(bench) or []
    c = [b[3] for b in bars]
    i = len(c) - 1
    base = tide_at(c, i)
    if base is None:
        return {"state": "unknown", "text": "Not enough {} history to judge the tide.".format(bench)}
    m50, m200 = _sma(c, 50, i), _sma(c, 200, i)
    counted, above = [], []
    for t in tickers:
        cc = [b[3] for b in data.get(t) or []]
        if len(cc) >= 50:
            counted.append(t)
            if cc[-1] > sum(cc[-50:]) / 50:
                above.append(t)
    share = len(above) / len(counted) if counted else None
    state = "turning" if base == "in" and share is not None and share < 0.5 else base
    text = "{} {:,.2f} is {:+.1f}% against its {} 50-day ({:,.2f}) and {:+.1f}% against its 200-day ({:,.2f}); {} of {} names sit above their own 50-day.".format(
        bench, c[i], (c[i] / m50 - 1) * 100, "rising" if m50 > _sma(c, 50, i - 10) else "falling", m50,
        (c[i] / m200 - 1) * 100, m200, len(above), len(counted))
    rule = {"in": "Tide in: the plan's steps run as written.",
            "turning": "Tide turning: steps run as written; no chasing.",
            "out": "Tide out: first step only on any name until it turns."}[state]
    return {"state": state, "bench": bench, "price": c[i], "asOf": bars[i][0].isoformat(), "ma50": round(m50, 2), "ma200": round(m200, 2),
            "above50": len(above), "counted": len(counted), "text": text, "rule": rule}


# ---------------------------------------------------------------- freeze + close-basis triggers

def last_close(data, t):
    bars = data.get(t) or []
    return (bars[-1][0].isoformat(), bars[-1][3]) if bars else (None, None)


def freeze_state(levels, data, prev):
    """{ticker: {since, close, line, source}}. Frozen on a daily close below the
    break line. Thaws on a close back above the frozen line by half a typical
    day's range, or when later levels carry a `reargued` note."""
    out = {}
    for t, lv in levels.items():
        d, close = last_close(data, t)
        was = (prev or {}).get(t)
        if close is None:
            if was:
                out[t] = was                      # no fresh close: keep the state, never guess
            continue
        sw = swing(data[t]) or 0.04
        if was:
            reclaimed = close > was["line"] * (1 + sw / 2)
            reargued = bool(lv.get("reargued")) and lv.get("source") != was.get("source")
            if not (reclaimed or reargued):
                out[t] = was
            continue
        line = lv.get("breakBelow")
        if line is not None and close < line:
            out[t] = {"since": d, "close": close, "line": line, "source": lv.get("source")}
    return out


def close_triggers(levels, data):
    """Lines judged on the daily close only: a buy-above trigger and the
    operator's optional two exit steps. {ticker: [{kind, line, close, date}]}"""
    out = {}
    for t, lv in levels.items():
        d, close = last_close(data, t)
        if close is None:
            continue
        hits = []
        if lv.get("buyAbove") is not None and close > lv["buyAbove"]:
            hits.append({"kind": "trigger", "line": lv["buyAbove"], "close": close, "date": d})
        if lv.get("exit2") is not None and close < lv["exit2"]:
            hits.append({"kind": "exit2", "line": lv["exit2"], "close": close, "date": d})
        elif lv.get("exit1") is not None and close < lv["exit1"]:
            hits.append({"kind": "exit1", "line": lv["exit1"], "close": close, "date": d})
        if hits:
            out[t] = hits
    return out


# ---------------------------------------------------------------- capital

def sleeve_map(book, memo):
    """ticker -> sleeve. The memo row's own `sleeve` wins over book.json's lists."""
    out = {t: s for s, ts in (book.get("sleeves") or {}).items() for t in ts}
    for a in (memo or {}).get("accumulate", []):
        if a.get("sleeve"):
            out[a["ticker"]] = a["sleeve"]
    return out


def capital(money, book, sleeves):
    """Deployable money and the three pots. Money already added since the
    baseline counts as used, so buying from a pot moves it from free to used
    instead of shrinking every pot."""
    if not money or not book or "split" not in book:
        return None
    fx = money["fx"]
    spend = book["monthlySpendMYR"]
    reserve = book["reserveMonths"] * spend
    base = book.get("baseline") or {}
    added, used = {}, {"fund": 0, "shots": 0, "trades": 0}
    for t, r in money["positions"].items():
        grew = (r["cost"] - (base.get(t) or {}).get("cost", 0)) * fx.get(r["currency"], 1.0)
        if grew > 1:
            added[t] = round(grew)
            pot = "trades" if r.get("trade") else POT_OF.get(sleeves.get(t))
            if pot:
                used[pot] += round(grew)
    deployable = max(0, money["liquid"] - reserve)
    total = deployable + sum(used.values())
    pots = {}
    for k, share in book["split"].items():
        budget = round(total * share / 100)
        pots[k] = {"share": share, "budget": budget, "used": used.get(k, 0), "free": max(0, min(budget - used.get(k, 0), deployable))}
    return {"asOf": money["asOf"], "stale": bool(money.get("stale")), "fxNote": money.get("fxNote"), "liquid": money["liquid"],
            "cashOnHand": money["cashOnHand"], "brokerCash": money["brokerCash"], "stablesFree": money["stables"] - money["farm"],
            "farm": money["farm"], "reserve": reserve, "reserveMonths": book["reserveMonths"], "spend": spend,
            "deployable": deployable, "runwayMonths": round(money["liquid"] / spend, 1) if spend else None,
            "pots": pots, "added": added, "since": book.get("since"), "riskPerTrade": book.get("riskPerTradeMYR"),
            "netWorth": money.get("netWorth")}


# ---------------------------------------------------------------- one row per name

def _next_date(a, calendar, today):
    cands = []
    for ms in a.get("milestones") or []:
        if ms.get("by") and ms["by"] >= today and ms.get("status", "pending") == "pending":
            cands.append((ms["by"], "Milestone: " + ms["what"]))
    ts = a.get("test") or {}
    if ts.get("by") and ts["by"] >= today:
        cands.append((ts["by"], "Test: " + ts["metric"]))
    for c in calendar:
        if c.get("ticker") == a.get("ticker") and c["date"] >= today:
            cands.append((c["date"], c["event"]))
    return dict(zip(("date", "text"), min(cands))) if cands else None


def rows(levels, quotes, data, frozen, triggers, tide_now, cap, money, book, memo, sleeves):
    today = date.today().isoformat()
    memo_rows = {a["ticker"]: a for a in (memo or {}).get("accumulate", [])}
    calendar = ((memo or {}).get("market") or {}).get("calendar", [])
    fx = (money or {}).get("fx", {})
    nw = ((money or {}).get("netWorth") or {}).get("total")
    out = []
    for t, lv in levels.items():
        a = memo_rows.get(t, {"ticker": t})
        price = (quotes.get(t) or {}).get("price")
        price_from = "sheet"
        if price is None and data.get(t):                # no row on the sheet's main tab: fall back to the last daily close
            price, price_from = data[t][-1][3], "last close {}".format(data[t][-1][0].isoformat())
        ccy = lv.get("currency")
        sleeve = sleeves.get(t) or ("core" if lv.get("action") in ("accumulate", "watch") else None)
        pot = POT_OF.get(sleeve)
        sw = swing(data[t]) if data.get(t) else None
        hits = {h["kind"]: h for h in triggers.get(t, [])}
        fz = frozen.get(t)
        watch = lv.get("action") == "watch"
        if price is None:
            state = "noprice"
        elif fz:
            state = "frozen"
        elif "exit2" in hits or "exit1" in hits:
            state = "exit2" if "exit2" in hits else "exit1"
        elif "trigger" in hits:
            state = "trigger"
        elif watch:
            state = "watch"
        else:
            state = {"add": "add", "buy": "buy", "hold": "wait", "above": "above", "trim": "trim"}[zone_of(price, lv)]

        # Room to add: steps of the name's cap, limited by the pot, the tide and the state.
        room = None
        if cap and pot and price is not None and not watch:
            p = cap["pots"][pot]
            etf = sleeve == "fund"
            steps = (book.get("fundTranches") or 4) if etf else 3
            name_cap = p["budget"] * (1.0 if etf else book.get("maxNameShare", 0.25))
            step = name_cap / steps
            proven = any(ms.get("status") == "hit" for ms in a.get("milestones") or [])
            allowed = {"add": 2, "buy": 1, "trigger": 1}.get(state, 0)
            if proven and state in ("add", "buy", "wait", "trigger"):
                allowed += 1                      # the last step is bought on proof, not on a lower price
            if tide_now.get("state") == "out":
                allowed = min(allowed, 1)
            done = cap["added"].get(t, 0)
            now = max(0, min(p["free"], allowed * step - done))
            unit_myr = price * fx.get(ccy, 1.0)
            room = {"pot": pot, "cap": round(name_cap), "step": round(step), "steps": steps, "allowed": allowed, "added": done,
                    "now": round(now), "units": int(now // unit_myr) if unit_myr else 0, "unitMYR": round(unit_myr, 2)}
            if lv.get("breakBelow") and lv.get("buyBelow"):
                room["ifBreaks"] = round(step * (lv["breakBelow"] / lv["buyBelow"] - 1))

        pos = None
        held = (money or {}).get("positions", {}).get(t)
        if held and price is not None and held.get("units"):
            value = held["units"] * price * fx.get(held["currency"], 1.0)
            pos = {"units": held["units"], "avgCost": held["avgCost"], "currency": held["currency"], "value": round(value),
                   "pl": round((price / held["avgCost"] - 1) * 100, 1) if held["avgCost"] else None,
                   "toCost": round((held["avgCost"] / price - 1) * 100, 1) if held["avgCost"] else None,
                   "ofNetWorth": round(value / nw * 100, 1) if nw else None}
            mult = (a.get("upside") or {}).get("multiple")
            if mult:
                pos["atUpside"] = round(value * mult)
                pos["addsToNetWorth"] = round(value * (mult - 1) / nw * 100, 1) if nw else None

        out.append({
            "ticker": t, "name": lv.get("name") or t, "action": lv.get("action"), "sleeve": sleeve, "pot": pot,
            "state": state, "stateText": STATE_TEXT[state], "price": price, "priceFrom": price_from, "currency": ccy,
            "distBuy": round((price / lv["buyBelow"] - 1) * 100, 1) if price and lv.get("buyBelow") else None,
            "swing": round(sw * 100, 1) if sw else None, "frozen": fz, "hits": list(hits.values()),
            "levels": {k: lv.get(k) for k in ("buyBelow", "addBelow", "stopAbove", "trimAbove", "breakBelow", "buyAbove", "exit1", "exit2", "buyBack")
                       if lv.get(k) is not None},
            "note": lv.get("note"), "source": lv.get("source"), "room": room, "pos": pos,
            "next": _next_date(a, calendar, today),
            "conviction": a.get("confidence"),
        })
    order = ["exit2", "exit1", "frozen", "trigger", "add", "buy", "wait", "above", "trim", "watch", "noprice"]
    out.sort(key=lambda r: (order.index(r["state"]), r["distBuy"] if r["distBuy"] is not None else 1e9))
    return out


def book_flags(plan_rows, others=()):
    """Plain observations about the book as a whole (no advice)."""
    flags = []
    shots = [dict(r["pos"], name=r["name"], conviction=r["conviction"]) for r in plan_rows if r["sleeve"] == "shot" and r["pos"]]
    shots += [dict(o, conviction=None) for o in others if o.get("sleeve") == "shot"]
    priced = [x for x in shots if x.get("pl") is not None and x["pl"] > -100]
    if priced:
        total = sum(x["value"] for x in priced)
        cost = sum(x["value"] / (1 + x["pl"] / 100) for x in priced)
        flags.append("Your {} shots are worth RM {:,.0f} against RM {:,.0f} paid ({:+.0f}%).".format(len(priced), total, cost, (total / cost - 1) * 100))
        big = max(priced, key=lambda x: x["value"])
        if big.get("conviction") == "low" and any(x.get("conviction") in ("medium", "high") for x in priced):
            flags.append("{} is the largest shot and carries the lowest confidence on the list.".format(big["name"].split(" (")[0]))
    return flags


# ---------------------------------------------------------------- telegram: notices + the decision sheet

def notices(plan_rows, prev_frozen, frozen, signals):
    """One line per thing Telegram should hear once. `key` makes it once-only."""
    out = []
    for r in plan_rows:
        t, name, c = r["ticker"], r["name"], r["currency"]
        fz = r["frozen"]
        if fz:
            out.append({"key": "frozen|{}|{}".format(t, fz["since"]), "date": fz["since"], "ticker": t,
                        "text": "{} closed at {} on {}, below its break line of {}. Buying on it is FROZEN until it closes back above, or the next memo re-argues the case.".format(
                            name, fmt_money(fz["close"], c), fz["since"], fmt_money(fz["line"], c))})
        for h in r["hits"]:
            if h["kind"] == "trigger":
                txt = "{} closed at {} on {}, above the trigger of {}. This is the plan's buy-on-strength step{}.".format(
                    name, fmt_money(h["close"], c), h["date"], fmt_money(h["line"], c),
                    ": room RM {:,} ({} shares)".format(r["room"]["now"], r["room"]["units"]) if r["room"] and r["room"]["now"] else "")
            else:
                txt = "{} closed at {} on {}, below your exit step {} line of {}. Your rule: {}.".format(
                    name, fmt_money(h["close"], c), h["date"], h["kind"][-1], fmt_money(h["line"], c),
                    "sell half" if h["kind"] == "exit1" else "sell the rest")
            out.append({"key": "{}|{}|{}|{}".format(h["kind"], t, h["line"], h["date"]), "date": h["date"], "ticker": t, "text": txt})
    for t, was in (prev_frozen or {}).items():
        if t not in frozen:
            out.append({"key": "thaw|{}|{}".format(t, was["since"]), "date": date.today().isoformat(), "ticker": t,
                        "text": "{} is no longer frozen: it closed back above {} (or the memo re-argued it). Its buy lines are live again.".format(t, was["line"])})
    for s in signals or []:
        if s.get("tradable") and not s.get("blocked"):
            out.append({"key": "trade|{}|{}|{}".format(s["setup"], s["ticker"], s["date"]), "date": s["date"], "ticker": s["ticker"],
                        "text": "QUICK TRADE SETUP: {} on {} ({}). Reference entry {}, stop {}, target {} ({}:1). Record: {}% wins, {:+.2f}R average over {} past trades. Size for RM {:,} at risk: {} shares (about RM {:,}). Check the open: skip it if it opens past the stop or the target.".format(
                            s["label"], s["name"], s["date"], fmt_money(s["entry"], s["currency"]), fmt_money(s["stop"], s["currency"]),
                            fmt_money(s["target"], s["currency"]), s["rr"], s["winRate"], s["avgR"], s["n"], s["risk"], s["shares"], s["sizeMYR"])})
    return out


def decision_text(plan_rows, tide_now, cap, signals, flags):
    """The decision sheet as plain text, for Telegram (weekly summary, daily digest)."""
    L = ["TODAY · {}".format(datetime.now(timezone(timedelta(hours=8))).strftime("%d %b %Y, %H:%M MYT"))]
    L.append("TIDE {}: {}".format(tide_now.get("state", "?").upper(), tide_now.get("rule", "")))
    if cap:
        p = cap["pots"]
        L.append("MONEY: deployable RM {:,} after a {}-month reserve (runway {} months){}".format(
            cap["deployable"], cap["reserveMonths"], cap["runwayMonths"], " [old figures]" if cap["stale"] else ""))
        L.append("POTS free: fund RM {:,} · shots RM {:,} · quick trades RM {:,}".format(p["fund"]["free"], p["shots"]["free"], p["trades"]["free"]))
    for title, pick in (("NEEDS YOU", lambda r: r["state"] in ("exit2", "exit1", "frozen", "trigger", "add", "buy")),
                        ("WAITING", lambda r: r["state"] in ("wait", "above", "trim", "watch"))):
        sel = [r for r in plan_rows if pick(r)]
        if not sel:
            continue
        L.append("")
        L.append(title)
        for r in sel:
            line = "• {} {}: {}".format(r["name"].split(" (")[0], fmt_money(r["price"], r["currency"]), r["stateText"])
            if r["state"] in ("wait", "above") and r["distBuy"] is not None:
                line += ", {:+.1f}% above its buy line {}".format(r["distBuy"], fmt_money(r["levels"]["buyBelow"], r["currency"]))
            if r["room"] and r["room"]["now"]:
                line += " · room RM {:,} ({} sh)".format(r["room"]["now"], r["room"]["units"])
            if r["next"]:
                line += " · next {}".format(r["next"]["date"])
            L.append(line)
    live = [s for s in signals or [] if s.get("tradable")]
    if live:
        L.append("")
        L.append("QUICK TRADES (paper until the record earns trust)")
        for s in live:
            L.append("• {} {}: entry about {}, stop {}, target {}{}".format(
                s["name"], s["label"], fmt_money(s["entry"], s["currency"]), fmt_money(s["stop"], s["currency"]),
                fmt_money(s["target"], s["currency"]), " (blocked: {})".format(s["blocked"]) if s.get("blocked") else ""))
    for f in flags:
        L.append("")
        L.append("NOTE: " + f)
    L.append("")
    L.append("Research support, not advice.")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- voices: chatter + roster health

HEDGE = re.compile(r"\bhedg|\bshort(ed|ing|s)?\b|\bputs?\b|rais(e|ed|ing) cash|de-?gross|de-?risk|\bSOXS\b|\bSQQQ\b", re.I)
CASHTAG = re.compile(r"\$([A-Za-z]{1,6}|\d{4,6})\b")


def _posts(since):
    out = []
    for f in sorted(glob.glob(str(POSTS_DIR / "posts-*.json"))):
        for p in load_json(f, []):
            if (p.get("postedAt") or p["collectedAt"]) >= since:
                out.append(p)
    return out


def chatter(roster, weeks=8):
    """Share of the roster's own posts each week that talk about hedges, shorts
    or raising cash. A rising line means the voices are getting defensive."""
    handles = {a["handle"].lower() for a in roster}
    start = (date.today() - timedelta(days=7 * weeks)).isoformat()
    by = {}
    for p in _posts(start):
        if p.get("repostedBy") or (p.get("author") or "").lower() not in handles:
            continue
        d = datetime.strptime((p.get("postedAt") or p["collectedAt"])[:10], "%Y-%m-%d").date()
        wk = (d - timedelta(days=d.weekday())).isoformat()
        b = by.setdefault(wk, [0, 0])
        b[0] += 1
        b[1] += bool(HEDGE.search(p.get("text") or ""))
    return [{"week": wk, "posts": n, "hedge": h, "share": round(100 * h / n, 1) if n else 0} for wk, (n, h) in sorted(by.items())]


def roster_health(roster, track, mine, days=31):
    """Per seat over the last month: volume, depth, posts on the operator's
    names, hedge talk and the scored record; plus the outside accounts the
    roster cites most. It suggests, the operator decides."""
    since = (date.today() - timedelta(days=days)).isoformat()
    posts = _posts(since)
    names = {a["handle"].lower(): a["handle"] for a in roster}
    mine = {m.split(".")[0].upper() for m in mine}
    tr = {a["handle"]: a for a in track or []}
    seats, cited = [], {}
    for low, h in names.items():
        own = [p for p in posts if (p.get("author") or "").lower() == low and not p.get("repostedBy") and not p.get("paid")]
        solo = [p for p in own if not p.get("replyTo")]
        lens = sorted(len(p.get("text") or "") for p in solo) or [0]
        on_mine = sum(1 for p in solo if {x.upper() for x in CASHTAG.findall(p.get("text") or "")} & mine)
        t = tr.get(h, {})
        seats.append({"handle": h, "posts": len(solo), "replies": len(own) - len(solo), "medianLen": lens[len(lens) // 2],
                      "longShare": round(100 * sum(1 for x in lens if x >= 600) / max(1, len(solo))),
                      "onYourNames": on_mine, "hedgeTalk": sum(1 for p in solo if HEDGE.search(p.get("text") or "")),
                      "scored": t.get("scored"), "avgEdge": t.get("avgEdge"), "hitRate": t.get("hitRate")})
    for p in posts:
        src = None
        if p.get("repostedBy") and (p.get("author") or "").lower() not in names:
            src, by = p.get("author"), (p.get("repostedBy") or "").lower()
        elif (p.get("quote") or {}).get("author") and p["quote"]["author"].lower() not in names:
            src, by = p["quote"]["author"], (p.get("author") or "").lower()
        if src and by in names:
            c = cited.setdefault(src, {"n": 0, "by": set()})
            c["n"] += 1
            c["by"].add(names[by])
    top = sorted(cited.items(), key=lambda x: (-len(x[1]["by"]), -x[1]["n"]))[:10]
    return {"since": since, "seats": sorted(seats, key=lambda s: -s["onYourNames"]),
            "cited": [{"handle": k, "times": v["n"], "bySeats": len(v["by"])} for k, v in top]}
