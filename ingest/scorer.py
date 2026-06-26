"""Composite priority scoring — ranks what the author prioritizes.

    score = recency_weighted_mentions * (1 + CONVICTION_WEIGHT * conviction_hits)

Recency uses exponential decay with a configurable half-life, so a ticker the
author mentions often AND recently AND with conviction language rises to the top.
Pure and deterministic; unit-tested in tests/test_scorer.py.
"""

from datetime import datetime, timezone

HALF_LIFE_DAYS = 14.0
CONVICTION_WEIGHT = 0.5


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
        for sym in th.get("tickers", []):
            a = agg.setdefault(
                sym,
                {"mentions": 0, "recency": 0.0, "convictionHits": 0, "lastMentioned": None},
            )
            a["mentions"] += 1
            a["recency"] += weight
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
            "convictionHits": a["convictionHits"],
            "lastMentioned": a["lastMentioned"],
        })

    ranked.sort(key=lambda r: (r["score"], r["mentions"]), reverse=True)
    return ranked
