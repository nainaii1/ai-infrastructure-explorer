"""Revenue history from SEC XBRL company facts. Pure — no network, no file I/O.

Step 2 of PROJECT.md: the first numbers in this system that describe the
COMPANIES rather than one analyst's posting behaviour.

`fetch_fundamentals.py` does the HTTP and the writing; this module only turns a
`companyfacts` payload into the record we store, so it can be tested against a
saved fixture with no key, no network and no rate limit.

Three things the SEC data does NOT do that this module has to handle:

1. **There is no single revenue tag.** NVDA files under `Revenues` today but
   `RevenueFromContractWithCustomerExcludingAssessedTax` through FY2022; the
   old tag still exists in the payload and still looks plausible. A fixed
   priority order therefore returns a series that silently stops four years
   ago. `pick_series` scores the candidates by how RECENT their data is and
   takes the winner whole, so every value in a series comes from one concept.

2. **`fy` on a row is the filing's fiscal year, not the period's.** NVDA's
   FY2021 revenue appears with `"fy": 2022` because a later 10-K restated it.
   Periods are derived from `start`/`end` only; `fy` is never read.

3. **A company can report in more than one currency.** TSM files the same
   `Revenue` concept in TWD and USD. USD wins when present, so the watchlist
   is not silently comparing a TWD figure with a USD one.
"""

# Which concepts can carry top-line revenue, per taxonomy. Order is NOT
# priority — see pick_series. This is an allowlist, not a substring match:
# the payload lists concepts alphabetically, so a "contains Revenue" search
# hits BusinessAcquisitionProFormaRevenue and InterestRevenueForFinancial...
# long before the real one.
REVENUE_TAGS = {
    "us-gaap": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
    ],
    "ifrs-full": [
        "Revenue",
        "RevenueFromContractsWithCustomers",
    ],
}

ANNUAL_FORMS = ("10-K", "20-F", "40-F")
# A "year" in filings runs 350-380 days: 52/53-week retail calendars and
# transition periods both land inside this band, quarters and half-years do not.
ANNUAL_MIN_DAYS = 350
ANNUAL_MAX_DAYS = 380
MAX_YEARS = 6                 # what we keep; enough for a 3y CAGR plus context
PREFERRED_UNITS = ("USD",)    # comparability beats faithfulness to the filing


# Words that carry no identifying signal when comparing a tracked company name
# against the name on the filing. Stripped before matching so "Micron
# Technology, Inc." and "MICRON TECHNOLOGY INC" agree.
_NAME_NOISE = {
    "incorporated", "inc", "corp", "corporation", "co", "company", "ltd",
    "limited", "plc", "holdings", "holding", "group", "technologies",
    "technology", "the", "sa", "nv", "ag", "se", "adr", "ads", "class",
    "semiconductor", "semiconductors", "international", "industries",
}


def _name_tokens(name):
    import re
    cleaned = re.sub(r"[^a-z0-9 ]", " ", str(name or "").lower())
    return {w for w in cleaned.split() if w and w not in _NAME_NOISE}


def names_match(tracked, entity, ticker=None):
    """Is the company on the filing plausibly the one we track?

    A ticker symbol is not a stable key across venues. EDGAR lists CCXI as
    Churchill Capital Corp XI, while this desk tracks CCXI as Agility Robotics
    — two different companies behind one symbol. Storing revenue on a symbol
    match alone would eventually attach a SPAC's figures to a robotics name,
    which is worse than showing nothing.

    Deliberately loose: one shared identifying word is enough, because legal
    names carry suffixes nobody uses. It is a guard against binding the WRONG
    company, not a test of exact equality.

    Passing `ticker` accepts a second kind of evidence — the filing naming
    itself after the symbol. Iris Energy renamed to "IREN Limited", which
    shares no word with the name this desk stored, but a filing called IREN
    under the symbol IREN is not a collision. Both CCXI candidates fail both
    tests, which is the case this exists for.

    An empty name on either side returns False: unknown is not a match.
    """
    a, b = _name_tokens(tracked), _name_tokens(entity)
    if not a or not b:
        return False
    if a & b:
        return True
    sym = str(ticker or "").strip().lower()
    return bool(sym) and sym in b


def _days_between(start, end):
    """Whole days between two ISO dates, or None if either is unusable."""
    import datetime
    try:
        a = datetime.date.fromisoformat(str(start)[:10])
        b = datetime.date.fromisoformat(str(end)[:10])
    except (TypeError, ValueError):
        return None
    return (b - a).days


def is_annual_row(row):
    """A full-year figure from an annual report, not a quarter or a segment."""
    if not isinstance(row, dict):
        return False
    if row.get("form") not in ANNUAL_FORMS:
        return False
    span = _days_between(row.get("start"), row.get("end"))
    return span is not None and ANNUAL_MIN_DAYS <= span <= ANNUAL_MAX_DAYS


def fiscal_year(end):
    """The calendar year the period ENDS in.

    Matches how the companies label themselves: NVDA's year to 25 Jan 2026 is
    FY2026, TSM's to 31 Dec 2024 is FY2024, and a September filer's to Sep 2025
    is FY2025. Derived from the period, never from the row's `fy`.
    """
    try:
        return int(str(end)[:4])
    except (TypeError, ValueError):
        return None


def _dedupe_latest_filed(rows):
    """One row per period, keeping the most recently FILED value.

    The same year appears in several filings as it is restated; the newest
    filing is the company's current answer.
    """
    best = {}
    for r in rows:
        key = (str(r.get("start"))[:10], str(r.get("end"))[:10])
        prev = best.get(key)
        if prev is None or str(r.get("filed") or "") > str(prev.get("filed") or ""):
            best[key] = r
    return [best[k] for k in sorted(best)]


def series_for(payload, taxonomy, tag, unit):
    """Clean annual rows for one (taxonomy, tag, unit), oldest first."""
    facts = (payload or {}).get("facts") or {}
    concept = (facts.get(taxonomy) or {}).get(tag) or {}
    rows = (concept.get("units") or {}).get(unit) or []
    annual = _dedupe_latest_filed([r for r in rows if is_annual_row(r)])
    out = []
    for r in annual:
        fy = fiscal_year(r.get("end"))
        val = r.get("val")
        if fy is None or not isinstance(val, (int, float)):
            continue
        out.append({"fy": fy, "end": str(r.get("end"))[:10],
                    "revenue": val, "filed": str(r.get("filed") or "")[:10] or None})
    return out


def _candidates(payload):
    """Every (taxonomy, tag, unit) in the payload that could be top-line revenue."""
    facts = (payload or {}).get("facts") or {}
    for taxonomy, tags in REVENUE_TAGS.items():
        concepts = facts.get(taxonomy) or {}
        for tag in tags:
            units = ((concepts.get(tag) or {}).get("units") or {})
            for unit in units:
                yield taxonomy, tag, unit


def pick_series(payload):
    """The best revenue series in the payload, or None.

    Ranked by, in order: a preferred (USD) unit, then the most recent fiscal
    year, then the longest history. Recency outranks the tag's position in
    REVENUE_TAGS on purpose — a company that migrated tags leaves the old one
    in the payload, populated and stale, and a fixed priority order would
    return a series that quietly ends years ago.
    """
    best, best_key = None, None
    for taxonomy, tag, unit in _candidates(payload):
        rows = series_for(payload, taxonomy, tag, unit)
        if not rows:
            continue
        key = (1 if unit in PREFERRED_UNITS else 0, rows[-1]["fy"], len(rows))
        if best_key is None or key > best_key:
            best_key, best = key, (taxonomy, tag, unit, rows)
    return best


def growth(rows):
    """Year-on-year and 3-year CAGR off the cleaned series, as fractions.

    Returns None for a leg there is not enough history for, or where the base
    year is zero or negative — a growth rate off a non-positive base is not a
    number worth showing.
    """
    out = {"yoy": None, "cagr3y": None}
    if len(rows) >= 2:
        prev, last = rows[-2]["revenue"], rows[-1]["revenue"]
        if prev > 0:
            out["yoy"] = (last / prev) - 1.0
    if len(rows) >= 4:
        base, last = rows[-4]["revenue"], rows[-1]["revenue"]
        if base > 0:
            out["cagr3y"] = (last / base) ** (1.0 / 3.0) - 1.0
    return out


def summarize(payload, ticker, cik=None, fetched_at=None, tracked_name=None):
    """The stored record for one company, or None when nothing usable is filed.

    None is a real answer, not a failure: a company can be in EDGAR with no
    annual revenue concept this module recognises, and recording that honestly
    is better than inventing a zero.

    Passing `tracked_name` turns on the wrong-company guard (see names_match).
    Omit it only when the caller has already established identity some other
    way — a symbol match on its own has not.
    """
    entity = (payload or {}).get("entityName")
    if tracked_name is not None and not names_match(tracked_name, entity, ticker):
        return None
    picked = pick_series(payload)
    if not picked:
        return None
    taxonomy, tag, unit, rows = picked
    rows = rows[-MAX_YEARS:]
    return {
        "ticker": str(ticker).upper(),
        "cik": cik,
        "entityName": entity,
        "taxonomy": taxonomy,
        "tag": tag,
        "currency": unit,
        "years": rows,
        "latest": rows[-1],
        "growth": growth(rows),
        "fetchedAt": fetched_at,
    }
