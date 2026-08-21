"""Fetch revenue history from SEC EDGAR into store/fundamentals.json.

    python3 ingest/fetch_fundamentals.py            # Core + Watch names
    python3 ingest/fetch_fundamentals.py --all      # every tracked ticker
    python3 ingest/fetch_fundamentals.py --ticker NVDA
    python3 ingest/fetch_fundamentals.py --status   # coverage, no network

Free, no API key, no daily limit. SEC asks callers to identify themselves in
the User-Agent; set SEC_USER_AGENT in ingest/.env to add a contact address if
you want to. The default identifies the tool without publishing an email.

This module does the HTTP and the writing; fundamentals.py stays pure
(invariant 6) so the parsing is testable against a saved fixture.

Two SEC-specific manners this respects:
  - www.sec.gov (the ticker->CIK map) rate-limits harder than data.sec.gov, so
    the map is cached on disk and refetched only when older than CIK_MAX_AGE.
  - requests are spaced to stay well under the published 10/sec ceiling.
"""

import os
import sys
import json
import time
import gzip
import argparse
import pathlib
import urllib.error
import urllib.request

import generate_data_js as gen
import fundamentals as fund
from dotenv_util import _load_dotenv
from store_io import (
    load_json as _load,
    load_json_optional as _load_opt,
    save_json as _save_json,
    now_iso as _now_iso,
    ssl_context,
)

ING = pathlib.Path(__file__).resolve().parent
STORE = ING / "store"
CIK_MAP_PATH = STORE / ".cik_map.json"

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json"

DEFAULT_UA = "AI-Infrastructure-Explorer/1.0 (personal research tool)"
# SEC publishes a 10/sec ceiling. 4/sec leaves headroom and still walks the
# whole Core+Watch list in well under a minute.
REQUEST_INTERVAL = 0.25
CIK_MAX_AGE_DAYS = 30
TIMEOUT = 30

_SSL = ssl_context()


def _ua():
    return os.environ.get("SEC_USER_AGENT") or DEFAULT_UA


def _get_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": _ua(),
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return json.loads(raw)


def _save(name, data):
    _save_json(name, data, trailing_newline=True)


def _aliases():
    """base.json tickerAliases, reversed: canonical -> [alternate symbols].

    An alternate US listing is worth trying when the canonical symbol is a
    foreign line EDGAR has never heard of.
    """
    base = _load("base.json") or {}
    out = {}
    for alt, canon in (base.get("tickerAliases") or {}).items():
        out.setdefault(str(canon).upper(), []).append(str(alt).upper())
    return out


def cik_map(force=False):
    """symbol -> CIK, cached on disk.

    www.sec.gov rate-limits harder than data.sec.gov and this file is ~800KB,
    so it is fetched at most monthly rather than once per run.
    """
    cached = _load_opt(".cik_map.json", None)
    if cached and not force:
        age = None
        try:
            import datetime
            stamped = datetime.datetime.fromisoformat(
                str(cached.get("fetchedAt", "")).replace("Z", "+00:00"))
            age = (datetime.datetime.now(datetime.timezone.utc) - stamped).days
        except (ValueError, TypeError):
            age = None
        if age is not None and age < CIK_MAX_AGE_DAYS:
            return cached.get("map") or {}

    payload = _get_json(TICKER_MAP_URL)
    mapping = {}
    for row in (payload or {}).values():
        sym = str(row.get("ticker") or "").upper()
        cik = row.get("cik_str")
        if sym and isinstance(cik, int):
            mapping[sym] = cik
    _save(".cik_map.json", {"fetchedAt": _now_iso(), "count": len(mapping),
                            "map": mapping})
    return mapping


def _core_watch_symbols(tickers, theses):
    """The names worth spending requests on, tiered exactly as the app tiers.

    Same trap `extract_views._core_symbols` hit: `tier` is not stored in
    tickers.json, and canonicalizing without base.json's maps produces a
    different tier table than generate_data_js does.
    """
    import scorer
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


def _resolve(symbol, mapping, alias_index):
    """(sec_symbol, cik) for a tracked ticker, or (None, None).

    Tries the tracked symbol, then any alternate symbol base.json maps onto it
    — a foreign primary line often has a US listing EDGAR does know.
    """
    sym = str(symbol).upper()
    for candidate in [sym] + alias_index.get(sym, []):
        if candidate in mapping:
            return candidate, mapping[candidate]
    return None, None


def run(symbols=None, all_tickers=False, limit=None):
    _load_dotenv()
    tickers = _load("tickers.json")
    theses = _load("theses.json")

    if symbols:
        targets = [str(s).upper() for s in symbols]
    elif all_tickers:
        targets = [t["ticker"] for t in tickers if t.get("ticker")]
    else:
        targets = _core_watch_symbols(tickers, theses)
    if limit:
        targets = targets[:limit]

    mapping = cik_map()
    alias_index = _aliases()
    names = {t["ticker"]: t.get("company") or "" for t in tickers if t.get("ticker")}
    existing = _load_opt("fundamentals.json", {}) or {}
    companies = dict(existing.get("companies") or {})
    unavailable = dict(existing.get("unavailable") or {})

    stats = {"requested": len(targets), "fetched": 0, "noFiler": 0,
             "noRevenue": 0, "nameMismatch": 0, "failed": 0}
    now = _now_iso()

    for i, sym in enumerate(targets):
        sec_sym, cik = _resolve(sym, mapping, alias_index)
        if cik is None:
            unavailable[sym] = "no SEC filer for this symbol (not US-listed)"
            companies.pop(sym, None)
            stats["noFiler"] += 1
            continue
        if i:
            time.sleep(REQUEST_INTERVAL)
        try:
            payload = _get_json(FACTS_URL % cik)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError,
                OSError) as exc:
            # Leave any previous record in place — a transient failure must not
            # delete good data, and the next run retries.
            print("WARN %s (CIK %s): %s" % (sym, cik, exc), file=sys.stderr)
            stats["failed"] += 1
            continue

        entity = (payload or {}).get("entityName")
        # Identity before data. A symbol match is not proof: EDGAR's CCXI is
        # Churchill Capital Corp XI, this desk's CCXI is Agility Robotics.
        if not fund.names_match(names.get(sym, ""), entity, sym):
            unavailable[sym] = (
                "symbol collision: EDGAR CIK %010d is %r, not %r — not stored"
                % (cik, entity, names.get(sym, "")))
            companies.pop(sym, None)
            stats["nameMismatch"] += 1
            continue

        record = fund.summarize(payload, sym, cik="%010d" % cik, fetched_at=now,
                                tracked_name=names.get(sym, ""))
        if record is None:
            unavailable[sym] = "no annual revenue concept in EDGAR filings"
            companies.pop(sym, None)
            stats["noRevenue"] += 1
            continue
        record["secSymbol"] = sec_sym
        companies[sym] = record
        unavailable.pop(sym, None)
        stats["fetched"] += 1

    _save("fundamentals.json", {
        "meta": {
            "schemaVersion": 1,
            "updatedAt": now,
            "source": "SEC EDGAR XBRL companyfacts (data.sec.gov)",
            "disclaimer": "Figures as filed. Not investment advice.",
            "covered": len(companies),
            "unavailable": len(unavailable),
        },
        "companies": companies,
        "unavailable": unavailable,
    })
    gen.write_data_js()
    print(json.dumps(stats))
    return stats


def status():
    data = _load_opt("fundamentals.json", {}) or {}
    companies = data.get("companies") or {}
    tickers = _load("tickers.json")
    theses = _load("theses.json")
    core_watch = set(_core_watch_symbols(tickers, theses))
    covered = core_watch & set(companies)
    print(json.dumps({
        "updatedAt": (data.get("meta") or {}).get("updatedAt"),
        "companies": len(companies),
        "coreWatch": len(core_watch),
        "coreWatchCovered": len(covered),
        "coreWatchMissing": sorted(core_watch - covered),
        "unavailable": len(data.get("unavailable") or {}),
    }, indent=2))


def main():
    ap = argparse.ArgumentParser(description="SEC EDGAR revenue fundamentals")
    ap.add_argument("--ticker", action="append", help="specific symbol(s)")
    ap.add_argument("--all", action="store_true", help="every tracked ticker")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--refresh-cik", action="store_true",
                    help="force a refetch of the ticker->CIK map")
    args = ap.parse_args()

    if args.status:
        return status()
    if args.refresh_cik:
        _load_dotenv()
        m = cik_map(force=True)
        print(json.dumps({"cikMapEntries": len(m)}))
        return
    return run(symbols=args.ticker, all_tickers=args.all, limit=args.limit)


if __name__ == "__main__":
    main()
