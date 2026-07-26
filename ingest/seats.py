"""The expert review seats — three reviewers with different mandates.

Mirrors ingest/synthesize.py: every function here is PURE. Prompt building,
validation and orchestration take an injected `call_fn(system, user) -> dict`
so a Claude Code session can drive the run without an API key (the operator
does not have one — see CLAUDE.md, v4). No network, no file I/O in this
module.

The seats exist because the desk is downstream of exactly one analyst, so the
store contains no bear case and nothing outside his field of view can enter.
Their findings become theses with source "research", which scorer.py scores
asymmetrically: a research finding can correct a name downward but can never
inflate its rank or buy it tier coverage.
"""

import scorer

# Seat mandates. Each is differentiated by the QUESTION it must answer, not by
# what it is allowed to read. Naming a seat "semi-expert" does not create
# semiconductor expertise — it is the same model with a different instruction
# and web access. What this buys is three separate passes so three different
# questions actually get asked, and forced outside research so new facts enter.
SEATS = {
    "semi-expert": {
        "label": "Semiconductor expert",
        "question": "Is the technical claim true?",
        "brief": ("Ramp timelines, process and packaging limits, yields, "
                  "qualification status, capacity assumptions."),
    },
    "fundamental": {
        "label": "Fundamental analyst",
        "question": "Do the numbers work?",
        "brief": ("Revenue maths, dilution, margins, customer concentration, "
                  "valuation against peers."),
    },
    "pm": {
        "label": "Portfolio manager",
        "question": "Is this a good bet at this price?",
        "brief": ("What is already priced in, what the downside is, what "
                  "would force an exit."),
    },
}

MAX_FINDING_WORDS = 60
MAX_THESES_IN_PROMPT = 12

_SYSTEM = """You are the {label} on a one-person research desk.

Your mandate — the ONE question you answer: {question}
Scope: {brief}

You are reviewing a name the desk already tracks. The desk follows a single
long-only analyst, so it has no bear case and cannot see anything outside his
field of view. Your job is to bring in what he missed, not to agree with him.

Rules:
- Your finding is at most {max_words} words. One claim. No hedging.
- direction must be exactly one of: bull, bear, neutral (lowercase).
- basis must be a list of URLs to primary or near-primary sources: SEC
  filings, earnings-call transcripts, company IR material, exchange notices,
  or established industry data providers. Content aggregators and
  search-engine-optimised summaries do not qualify.
- If you cannot cite such a source, return an empty basis. The finding will be
  recorded as unverified and forced to neutral so it cannot move any number.
  That is the correct outcome — do not invent a citation to avoid it.
- confidence must be exactly one of: high, medium, low.

Return ONLY a JSON object:
{{"seat": "{seat}", "ticker": "<TICKER>", "direction": "...",
  "finding": "...", "basis": ["https://..."], "confidence": "..."}}"""


def build_seat_prompt(seat, ticker, theses):
    """Return (system, user) for one seat reviewing one ticker.

    Raises KeyError for an unknown seat — a typo must not silently produce a
    generic reviewer.
    """
    meta = SEATS[seat]
    system = _SYSTEM.format(
        label=meta["label"], question=meta["question"], brief=meta["brief"],
        max_words=MAX_FINDING_WORDS, seat=seat)

    recent = sorted(theses, key=lambda t: t.get("postedAt") or "",
                    reverse=True)[:MAX_THESES_IN_PROMPT]
    lines = ["Ticker under review: {}".format(ticker), ""]
    if recent:
        lines.append("What the analyst has said (most recent first):")
        for t in recent:
            lines.append("- [{}] {}".format(
                (t.get("postedAt") or "")[:10], (t.get("text") or "").strip()))
    else:
        lines.append("The analyst has said nothing about this name.")
    return system, "\n".join(lines)
