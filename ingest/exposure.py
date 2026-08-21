"""AI exposure — the operator's judgement, recorded with its reasoning. Pure.

Step 3 of PROJECT.md. Steps 1 and 2 read things: what the analyst argued, what
the company filed. This one records something nobody publishes — how much of a
company is genuinely the AI datacentre buildout rather than its legacy business.

**Verified 21 Aug 2026: this cannot be derived.** SEC `companyfacts` carries no
segment dimension at all — every row is consolidated, so NVDA's Data Center
share is not in the payload `fundamentals.py` reads. There is no free API for
it. It is a judgement, and the only honest thing to do with a judgement is
record who made it, when, on what basis, and how sure they were.

So the integrity rule of this module is one line:

    a number without a stated basis is refused at write time.

`validate_assessment` raises rather than storing a bare percentage. Nothing in
this file invents, defaults or infers a value — an unassessed name stays
unassessed and renders as "not assessed", never as zero. `confidence` is
mandatory and travels with the number everywhere it is displayed, so a rough
guess can never be read as a measurement.

Pure (invariant 6): no network, no file I/O. `assess_exposure.py` does both.
"""

CONFIDENCE_LEVELS = ("high", "medium", "low")
MAX_BASIS_CHARS = 400
MAX_FIELD_CHARS = 120
MAX_SOURCES = 6
MIN_BASIS_WORDS = 4     # "because I said so" is not a basis


class AssessmentError(ValueError):
    """Raised when an assessment is not fit to store. The message is shown to
    the operator verbatim, so it says what to fix, not merely what is wrong."""


def _clean(value, limit=MAX_FIELD_CHARS):
    if value is None:
        return None
    text = " ".join(str(value).split())[:limit].strip()
    return text or None


def normalize_exposure(value):
    """A percentage 0-100, or None.

    Accepts "45", "45%", 0.45 -> rejected (see below), 45.0. A fraction is
    NOT silently multiplied: 0.45 could mean 45% or could mean "half a
    percent", and guessing between them on the operator's behalf is exactly
    the kind of quiet decision this project does not make. It is refused with
    an instruction instead.
    """
    if value is None or value == "":
        return None
    text = str(value).strip().rstrip("%").strip()
    try:
        pct = float(text)
    except (TypeError, ValueError):
        raise AssessmentError(
            "exposure %r is not a number — give a percentage like 88 or 88%%"
            % value)
    if 0 < pct < 1:
        raise AssessmentError(
            "exposure %r looks like a fraction. Write the percentage: 45, not "
            "0.45. (If you really mean under one percent, write 0.)" % value)
    if not (0 <= pct <= 100):
        raise AssessmentError(
            "exposure %s is outside 0-100" % pct)
    return round(pct, 1)


def validate_assessment(raw, ticker=None):
    """Turn a proposed assessment into a storable record, or raise.

    Required: `aiExposure`, `confidence`, and a `basis` that actually says
    something. Optional: `contentPerRack`, `revenueInflection`, `sources`.
    """
    if not isinstance(raw, dict):
        raise AssessmentError("assessment must be an object")

    sym = _clean(ticker or raw.get("ticker"), 20)
    if not sym:
        raise AssessmentError("assessment needs a ticker")
    sym = sym.upper()

    exposure = normalize_exposure(raw.get("aiExposure"))
    if exposure is None:
        raise AssessmentError(
            "%s: aiExposure is required — the percentage of revenue tied to "
            "the AI datacentre buildout" % sym)

    confidence = _clean(raw.get("confidence"), 12)
    confidence = confidence.lower() if confidence else None
    if confidence not in CONFIDENCE_LEVELS:
        raise AssessmentError(
            "%s: confidence must be one of %s — a number without one reads as "
            "a measurement" % (sym, "/".join(CONFIDENCE_LEVELS)))

    basis = _clean(raw.get("basis"), MAX_BASIS_CHARS)
    if not basis or len(basis.split()) < MIN_BASIS_WORDS:
        raise AssessmentError(
            "%s: basis is required and must say WHY (at least %d words). A "
            "percentage with no reasoning is indistinguishable from a guess."
            % (sym, MIN_BASIS_WORDS))

    sources = raw.get("sources") or []
    if isinstance(sources, str):
        sources = [sources]
    if not isinstance(sources, (list, tuple)):
        raise AssessmentError("%s: sources must be a list" % sym)
    sources = [s for s in (_clean(x, 200) for x in sources) if s][:MAX_SOURCES]

    record = {
        "ticker": sym,
        "aiExposure": exposure,
        "confidence": confidence,
        "basis": basis,
        "sources": sources,
        "assessedAt": _clean(raw.get("assessedAt"), 30),
        "assessedBy": _clean(raw.get("assessedBy"), 30) or "operator",
    }
    for key in ("contentPerRack", "revenueInflection"):
        value = _clean(raw.get(key))
        if value:
            record[key] = value
    return record


def ai_revenue(assessment, fundamentals_record):
    """The payoff: filed revenue x judged exposure, in the filing's currency.

    Returns None unless BOTH halves exist. A derived figure whose inputs are
    half-missing is worse than no figure — it looks like data.

    The result is explicitly an estimate: it multiplies an audited number by an
    unaudited one, so every caller must render it next to `confidence`.
    """
    if not assessment or not fundamentals_record:
        return None
    pct = assessment.get("aiExposure")
    latest = (fundamentals_record.get("latest")
              or (fundamentals_record.get("years") or [None])[-1])
    if pct is None or not latest:
        return None
    revenue = latest.get("revenue")
    if not isinstance(revenue, (int, float)):
        return None
    return {
        "value": revenue * (pct / 100.0),
        "currency": fundamentals_record.get("currency"),
        "fy": latest.get("fy"),
        "exposure": pct,
        "confidence": assessment.get("confidence"),
    }


def coverage(assessments, symbols):
    """Which names are assessed and which are not, for the worklist.

    Sorted so the report is stable between runs rather than dict-ordered.
    """
    have = {str(s).upper() for s in (assessments or {})}
    want = [str(s).upper() for s in (symbols or [])]
    missing = sorted({s for s in want if s not in have})
    return {
        "assessed": sorted({s for s in want if s in have}),
        "unassessed": missing,
        "total": len(set(want)),
    }


def confidence_rank(level):
    """low -> 0, high -> 2. For sorting a worklist worst-first."""
    try:
        return CONFIDENCE_LEVELS[::-1].index(str(level).lower())
    except (ValueError, AttributeError):
        return -1
