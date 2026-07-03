"""Composite priority scoring — ranks what the author prioritizes.

    score = sum(recency_weight * focus_weight) * (1 + CONVICTION_WEIGHT * conviction_hits)

Recency uses exponential decay with a configurable half-life, so a ticker the
author mentions often AND recently AND with conviction language rises to the top.

Focus weight (1/sqrt(tickers-in-post)) discounts names buried in long list-posts:
a ticker that shows up in a 12-name Bloomberg-selloff dump counts far less than
one in a dedicated single-name thesis. This keeps mention-heavy digest baskets
from inflating the conviction tiers. Pure and deterministic; unit-tested in
tests/test_scorer.py.
"""

import math
from datetime import datetime, timezone

HALF_LIFE_DAYS = 14.0
CONVICTION_WEIGHT = 0.5

# Tier thresholds on *focus-weighted* mentions — signal, not price targets. A
# name is "core" when the author keeps coming back to it in a focused way (or
# pounds the table twice with conviction language), "watch" when there's some
# repeat/conviction signal, and "radar" for one-off name-drops. A single
# dedicated post carries a focus weight of 1.0, so these thresholds read like
# raw mention counts for names the author writes about directly; only
# list-dump appearances get discounted below 1.0 each.
TIER_CORE_MIN_MENTIONS = 5
TIER_CORE_MIN_CONVICTION_HITS = 2
TIER_WATCH_MIN_MENTIONS = 2
TIER_WATCH_MIN_CONVICTION_HITS = 1


def _focus_weight(num_tickers):
    """1/sqrt(N): a dedicated single-name post = 1.0; a 12-name dump ~= 0.29 each."""
    return 1.0 / math.sqrt(num_tickers) if num_tickers > 0 else 0.0


def _parse_dt(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def compute_priorities(theses, now=None, half_life_days=HALF_LIFE_DAYS):
    """Return a list of {ticker, score, mentions, convictionHits, lastMentioned}
    ranked by score descending (then mentions)."""
    now = now or datetime.now(timezone.utc)
    agg = {}

    for th in theses:
        posted = _parse_dt(th.get("postedAt")) or now
        age_days = max(0.0, (now - posted).total_seconds() / 86400.0)
        weight = 0.5 ** (age_days / half_life_days)
        is_high = th.get("conviction") == "high"
        syms = th.get("tickers", [])
        focus = _focus_weight(len(syms))
        for sym in syms:
            a = agg.setdefault(
                sym,
                {"mentions": 0, "weighted": 0.0, "recency": 0.0,
                 "convictionHits": 0, "lastMentioned": None},
            )
            a["mentions"] += 1              # raw count, for display ("12x mentioned")
            a["weighted"] += focus          # focus-weighted count, for tiering
            a["recency"] += weight * focus  # recency + focus, for the priority score
            if is_high:
                a["convictionHits"] += 1
            current = _parse_dt(a["lastMentioned"])
            if current is None or (posted and posted > current):
                a["lastMentioned"] = th.get("postedAt")

    ranked = []
    for sym, a in agg.items():
        score = a["recency"] * (1 + CONVICTION_WEIGHT * a["convictionHits"])
        ranked.append({
            "ticker": sym,
            "score": round(score, 4),
            "mentions": a["mentions"],
            "weightedMentions": round(a["weighted"], 4),
            "convictionHits": a["convictionHits"],
            "lastMentioned": a["lastMentioned"],
        })

    ranked.sort(key=lambda r: (r["score"], r["mentions"]), reverse=True)
    return ranked


def assign_tiers(symbols, priorities):
    """Map every symbol to a conviction tier: "core" | "watch" | "radar".

    Pure function over compute_priorities() output. Symbols with no
    priority row (never mentioned in a thesis) are "radar".
    """
    by_symbol = {p["ticker"]: p for p in priorities}
    tiers = {}
    for sym in symbols:
        p = by_symbol.get(sym)
        # Fall back to raw mentions if weightedMentions is absent (older data).
        weighted = p.get("weightedMentions", p.get("mentions", 0)) if p else 0
        hits = p["convictionHits"] if p else 0
        if weighted >= TIER_CORE_MIN_MENTIONS or hits >= TIER_CORE_MIN_CONVICTION_HITS:
            tiers[sym] = "core"
        elif weighted >= TIER_WATCH_MIN_MENTIONS or hits >= TIER_WATCH_MIN_CONVICTION_HITS:
            tiers[sym] = "watch"
        else:
            tiers[sym] = "radar"
    return tiers
