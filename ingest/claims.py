"""The claims ledger — dated, testable predictions and how they turned out.

This is the system's memory. The desk follows one analyst and now also writes
its own research findings; without a record of what each source PREDICTED and
whether it happened, "who is worth listening to" stays a matter of impression.

PURE, like seats.py and pre_review.py: no network, no file I/O, no API client.
Extraction and judging take an injected `call_fn(system, user) -> dict` so a
Claude Code session can drive them without an API key.

Four rules this module exists to enforce (Phase 3 plan, C1-C4):

C1  A claim moves no number. Nothing here feeds compute_priorities or
    assign_tiers. Hit-rate weighting is Phase 4 and is gated on real judged
    outcomes, so until then the ledger observes and does not vote.
C2  "unfalsifiable" is a first-class outcome, not a failure to classify. A
    source whose predictions cannot be tested is telling the operator
    something, and score_claims returns the unfalsifiable share from the same
    call as the hit rate so no surface can show one without the other.
C3  A judgement to "correct" or "wrong" needs a citable primary source. The
    desk judges its own predictions here, which is exactly when an invented
    citation is most tempting and least likely to be checked.
C4  Time moves one way. A claim cannot be judged before its judgeBy date, and
    a claim already judged is never silently re-decided — both raise, because
    a quietly flipped verdict destroys the only record of what was believed.

SECURITY: the text claims are extracted from is forwarded third-party
social-media content, untrusted. build_extract_prompt wraps it in the same
injection firewall as seats.build_seat_prompt, and validate_claim takes the
source and the ticker from the CALLER, never from the model — a claim filed
against the wrong source corrupts the exact measurement this file produces.
"""

import hashlib
from datetime import datetime

import seats

# Who a claim can be attributed to. "desk" is Claude's own verdict language;
# the three seats file under their own names so a seat that is reliably wrong
# can be told apart from one that is not.
VALID_SOURCES = ("analyst", "desk", "semi-expert", "fundamental", "pm")

# open -> the date has not arrived. correct/wrong -> judged against a cited
# source. unfalsifiable -> nothing could ever settle it. See C2.
VALID_STATUS = ("open", "correct", "wrong", "unfalsifiable")

MAX_CLAIM_WORDS = 40


def _as_date(value):
    """A real YYYY-MM-DD date, or "" if the value is not one.

    seats.day() takes the date portion of mixed store formats, but it does no
    validation — "soon"[:10] is "soon", a non-empty string that would sail
    through a truthiness check. A prediction date that cannot be parsed must
    read as absent, not as a date that happens to sort oddly.
    """
    text = seats.day(value)
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return ""
    return text


def validate_claim(raw, source, ticker, allowed_tickers, made_at):
    """Turn one model-proposed claim into a store record, or None to drop it.

    `source`, `ticker` and `made_at` are pinned from the CALLER. The model is
    never trusted for them: it is reading untrusted forwarded posts, and a
    claim that lands under the wrong source or the wrong name corrupts the
    measurement rather than merely being wrong.

    Returns None only when there is nothing to record at all — a non-dict, an
    empty claim, or a ticker outside the universe. A claim that cannot be
    TESTED is still recorded, with status "unfalsifiable" (C2): "we're close to
    the bottom" is a real thing a source says, and counting it is the point.

    Raises on a bad `source` or `made_at`, because those are the caller's own
    arguments. Same reasoning as select_coverage's `since`: there is no inert
    reading of "no source" or "no date made", so the caller gets told.
    """
    if source not in VALID_SOURCES:
        raise ValueError(
            "validate_claim: unknown source {!r}, expected one of {}".format(
                source, ", ".join(VALID_SOURCES)))
    made = _as_date(made_at)
    if not made:
        raise ValueError(
            "validate_claim: `made_at` must be a YYYY-MM-DD date or ISO "
            "timestamp string, got {!r}".format(made_at))

    if not isinstance(raw, dict):
        return None
    text = seats.coerce_str(raw.get("claim"))
    if not text:
        return None
    if ticker is not None and ticker not in allowed_tickers:
        return None

    words = text.split()
    if len(words) > MAX_CLAIM_WORDS:
        text = " ".join(words[:MAX_CLAIM_WORDS])

    # Falsifiability. A claim needs BOTH something that would settle it and a
    # date by which it settles. A judgeBy on or before madeAt is not a
    # prediction, so it is treated the same as having none.
    testable_by = seats.coerce_str(raw.get("testableBy"))
    judge_by = _as_date(raw.get("judgeBy"))
    if judge_by and judge_by <= made:
        judge_by = ""
    falsifiable = bool(testable_by and judge_by)

    return {
        "id": claim_id(source, ticker, text, made),
        "source": source,
        "ticker": ticker,
        "claim": text,
        "testableBy": testable_by,
        "madeAt": made,
        "judgeBy": judge_by or None,
        "thesisId": seats.coerce_str(raw.get("thesisId")) or None,
        # The model never supplies these three. A model that could hand back
        # status "correct" would be marking its own homework.
        "status": "open" if falsifiable else "unfalsifiable",
        "judgedAt": None,
        "evidence": None,
    }


def claim_id(source, ticker, text, made_at):
    """Stable id derived from content, so re-extraction is idempotent.

    The spec wrote these as a per-day counter (cl_AAOI_2026-07-22_01), but a
    counter is positional: re-running extraction over the same posts renumbers
    everything and every claim merges as new. This ledger is meant to be
    re-runnable, so the id has to come from the claim itself.
    """
    key = "|".join([source, ticker or "-", text, made_at])
    return "cl_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
