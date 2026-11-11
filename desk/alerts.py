#!/usr/bin/env python3
"""Price alerts on the memo's zones. Called by the collector every run (every
6 hours); safe to run by hand.

Each name on the accumulate list carries numeric levels (desk/store/levels.json,
written by build.py from the latest memo and any event update since):

    add    price <= addBelow      the memo's "add on a drop" level
    buy    price <= buyBelow      inside the accumulate zone
    hold   up to stopAbove        above the zone but not stretched
    above  price >  stopAbove     stop adding
    trim   price >  trimAbove     the memo's take-some-profit level (optional)

An alert goes to Telegram only when a name moves from one zone to another, and
only once it is past the line it crossed by the larger of 1.5% or a quarter of
that stock's typical daily range (so a price sitting on a line, or a wild stock
wobbling across it, does not alert every run).

Since 11 Nov 2026:
  * A name frozen by a daily close below its break line (desk/store/frozen.json,
    written by build.py) sends no buy or add alerts until it thaws.
  * desk/store/notices.json (also written by build.py) carries once-only lines:
    freeze and thaw, buy-above triggers, exit steps and quick-trade setups.
The first check after new levels records the starting zone silently (the memo
already said where it stood). Every alert is logged to desk/store/alerts.json
and shows on the Desk page.

    python3 desk/alerts.py            check now
    python3 desk/alerts.py --dry-run  show zones, send nothing, save nothing
"""
import sys

from common import STATE_FILE, STORE, Telegram, load_env, load_json, now_iso, save_json

LEVELS = STORE / "levels.json"
ALERT_LOG = STORE / "alerts.json"
FROZEN = STORE / "frozen.json"
NOTICES = STORE / "notices.json"
BUFFER = 0.015
NOTICE_DAYS = 4          # a notice older than this is never sent (no flood after a quiet spell)
ORDER = ["add", "buy", "hold", "above", "trim"]
SYMBOL = {"USD": "$", "KRW": "₩", "EUR": "€", "GBP": "£", "SEK": "SEK ", "JPY": "¥", "TWD": "NT$"}


def money(v, ccy):
    s = SYMBOL.get(ccy, (ccy or "") + " ")
    return "{}{:,.2f}".format(s, v) if v < 1000 else "{}{:,.0f}".format(s, v)


def zone_of(price, lv):
    top = lv.get("stopAbove") or lv["buyBelow"]
    if lv.get("addBelow") is not None and price <= lv["addBelow"]:
        return "add"
    if price <= lv["buyBelow"]:
        return "buy"
    if price <= top:
        return "hold"
    if lv.get("trimAbove") is not None and price > lv["trimAbove"]:
        return "trim"
    return "above"


def settled_zone(price, lv, prev):
    """The zone to report, given the zone last recorded. Leaving `prev` needs the
    price to clear the line it crossed by BUFFER; otherwise it stays in `prev`."""
    raw = zone_of(price, lv)
    if prev not in ORDER or raw == prev:
        return raw
    top = lv.get("stopAbove") or lv["buyBelow"]
    bounds = [lv["addBelow"] if lv.get("addBelow") is not None else float("-inf"), lv["buyBelow"], top,
              lv["trimAbove"] if lv.get("trimAbove") is not None else float("inf")]
    i = ORDER.index(prev)
    buf = max(BUFFER, 0.25 * (lv.get("swing") or 0))      # a quarter of a typical day's range
    if ORDER.index(raw) > i:                        # moving up, out of prev
        return raw if price > bounds[i] * (1 + buf) else prev
    return raw if price < bounds[i - 1] * (1 - buf) else prev    # moving down


def message(lv, zone, price):
    n, c, act = lv["name"], lv["currency"], lv.get("action")
    p = money(price, c)
    if act not in ("accumulate", "holding", "plan"):
        if zone in ("add", "buy"):
            return "{} is at {}, at or below the memo's revisit level of {}. It is a watch name, not a call: the next memo decides.".format(
                n, p, money(lv["buyBelow"], c))
        return "{} is at {}, back above the memo's revisit level of {}.".format(n, p, money(lv["buyBelow"], c))
    if zone == "add":
        return "{} is at {}: in the ADD zone (at or below {}). The memo's plan was to add here, if the thesis still holds.".format(
            n, p, money(lv["addBelow"], c))
    if zone == "buy":
        return "{} is at {}: inside the accumulate zone (at or below {}).".format(n, p, money(lv["buyBelow"], c))
    if zone == "hold":
        return "{} is at {}: above the accumulate zone, below the stop-adding level of {}. Hold; no new buying.".format(
            n, p, money(lv["stopAbove"], c))
    if zone == "trim":
        return "{} is at {}: above the memo's trim level of {}. The plan was to take some profit here, if you hold it.".format(
            n, p, money(lv["trimAbove"], c))
    return "{} is at {}: above the stop-adding level of {}. The memo says stop adding here.".format(
        n, p, money(lv.get("stopAbove") or lv["buyBelow"], c))


def check(snapshot, state, levels, frozen=None):
    """Return list of alert records; updates state["alertZones"] in place.
    A frozen name still has its zone tracked, but a move into buy or add is silent."""
    frozen = frozen or {}
    zones = state.setdefault("alertZones", {})
    out = []
    for t, lv in levels.items():
        row = (snapshot.get("prices") or {}).get(t) or {}
        price, ccy = row.get("price"), row.get("currency")
        if price is None:
            continue
        if ccy and lv.get("currency") and ccy != lv["currency"]:
            out.append({"ticker": t, "error": "currency mismatch: sheet {} vs levels {}".format(ccy, lv["currency"])})
            continue
        prev = zones.get(t)
        same = bool(prev) and prev.get("source") == lv.get("source")
        z = settled_zone(price, lv, prev["zone"]) if same else zone_of(price, lv)
        zones[t] = {"zone": z, "source": lv.get("source"), "price": price, "at": now_iso()}
        if not same:
            continue                      # new levels: record the starting zone silently
        if prev["zone"] != z and not (t in frozen and z in ("add", "buy")):
            out.append({"ticker": t, "name": lv["name"], "from": prev["zone"], "to": z, "price": price,
                        "currency": lv["currency"], "at": now_iso(), "text": message(lv, z, price)})
    for t in list(zones):
        if t not in levels:
            zones.pop(t)
    return out


def pending_notices(state):
    """Notices from build.py not yet sent, newest rules only. Marks them seen."""
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=NOTICE_DAYS)).isoformat()
    seen = state.setdefault("noticed", [])
    out = []
    for n in load_json(NOTICES, []):
        if n["key"] in seen:
            continue
        seen.append(n["key"])
        if n.get("date", "9999") >= cutoff:
            out.append(n)
    state["noticed"] = seen[-400:]
    return out


def run(tg=None, state=None, save_state=False, dry=False):
    from prices import save_latest, snapshot as fetch
    levels = load_json(LEVELS, {}).get("levels", {})
    if not levels:
        return []
    own_state = state is None
    state = load_json(STATE_FILE, {}) if own_state else state
    snap = {"prices": fetch()} if dry else save_latest()
    frozen = load_json(FROZEN, {})
    if dry:
        for t, lv in levels.items():
            row = snap["prices"].get(t) or {}
            print("{:10} {:>14} -> {}{}".format(t, str(row.get("price")), zone_of(row["price"], lv) if row.get("price") else "no price",
                                              "  FROZEN since {}".format(frozen[t]["since"]) if t in frozen else ""))
        seen = set(state.get("noticed", []))
        for n in load_json(NOTICES, []):
            print("notice{}: {}".format(" (already sent)" if n["key"] in seen else "", n["text"]))
        return []
    alerts = check(snap, state, levels, frozen)
    for n in pending_notices(state):
        alerts.append({"ticker": n.get("ticker"), "name": n.get("ticker"), "from": "notice", "to": n["key"].split("|")[0],
                       "price": None, "currency": None, "at": now_iso(), "text": n["text"]})
    real = [a for a in alerts if "text" in a]
    if real:
        log = load_json(ALERT_LOG, [])
        log.extend(real)
        save_json(ALERT_LOG, log[-500:])
        if tg and state.get("chatId"):
            tg.send(state["chatId"], "DESK PRICE ALERT\n" + "\n\n".join("• " + a["text"] for a in real) +
                    "\n\nResearch support, not advice.")
    for a in alerts:
        print("alert:", a.get("text") or a.get("error"))
    if own_state or save_state:
        save_json(STATE_FILE, state)
    return alerts


if __name__ == "__main__":
    env = load_env()
    tg = Telegram(env["TELEGRAM_BOT_TOKEN"]) if env.get("TELEGRAM_BOT_TOKEN") else None
    run(tg=tg, dry="--dry-run" in sys.argv)
    print("alerts: checked")
