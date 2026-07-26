"""Composite priority scoring — ranks what the author prioritizes.

    net   = sum(recency_weight * focus_weight * direction_weight)
    score = max(net * (1 + CONVICTION_WEIGHT * conviction_hits), 0)

Recency uses exponential decay with a configurable half-life, so a ticker the
author mentions often AND recently AND with conviction language rises to the top.

Focus weight (1/sqrt(tickers-in-post)) discounts names buried in long list-posts:
a ticker that shows up in a 12-name Bloomberg-selloff dump counts far less than
one in a dedicated single-name thesis. This keeps mention-heavy digest baskets
from inflating the conviction tiers.

Direction weight (see _direction_weight) signs each mention: bull/neutral
analyst posts count +1, bear posts count -1, so a name the author keeps
defending while arguing against it nets out rather than climbing the rank
purely on mention volume. `score` floors at zero (a net-negative name still
ranks, just at the bottom) but `net` itself is exposed unclamped so callers
can see when attention is negative, not merely low. Pure and deterministic;
unit-tested in tests/test_scorer.py.
"""

import math
from datetime import datetime, timezone

HALF_LIFE_DAYS = 14.0
CONVICTION_WEIGHT = 0.5

# Signed contribution of one mention. Research findings may subtract but never
# add: the same model that writes the desk verdicts must not be able to agree
# with itself three times and inflate a rank. Analyst bull and neutral posts
# both weigh 1.0, so migrating undirected theses to "neutral" changes no score.
RESEARCH_SOURCE = "research"


def _direction_weight(thesis):
    direction = thesis.get("direction") or "neutral"
    if direction == "bear":
        return -1.0
    if thesis.get("source") == RESEARCH_SOURCE:
        return 0.0
    return 1.0

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


def canonicalize_theses(theses, aliases=None, theme_tags=None):
    """Return a new thesis list with each post's ticker symbols cleaned for
    scoring: alias symbols remapped to their canonical listing (SIVEF -> SIVE,
    duplicates collapsed) and theme tags dropped (pseudo-tickers like DRAM or
    SPCX that name a theme, not a tradable stock). Original records are never
    mutated and post text is untouched — this only affects counting.

    Config lives in base.json ("tickerAliases", "themeTags"); callers load it
    and pass it in so this stays a pure function.
    """
    aliases = aliases or {}
    excluded = set(theme_tags or [])
    out = []
    for th in theses:
        seen = set()
        syms = []
        for sym in th.get("tickers", []):
            canon = aliases.get(sym, sym)
            if canon in excluded or canon in seen:
                continue
            seen.add(canon)
            syms.append(canon)
        out.append({**th, "tickers": syms})
    return out


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
        direction = th.get("direction") or "neutral"
        signed = weight * focus * _direction_weight(th)
        for sym in syms:
            a = agg.setdefault(
                sym,
                {"mentions": 0, "weighted": 0.0, "recency": 0.0,
                 "net": 0.0, "bull": 0, "bear": 0,
                 "convictionHits": 0, "lastMentioned": None},
            )
            a["mentions"] += 1              # raw count, for display ("12x mentioned")
            a["weighted"] += focus          # focus-weighted count, for tiering
            a["recency"] += weight * focus  # recency + focus, for the priority score
            a["net"] += signed
            if direction == "bear":
                a["bear"] += 1
            elif direction == "bull":
                a["bull"] += 1
            if is_high:
                a["convictionHits"] += 1
            current = _parse_dt(a["lastMentioned"])
            if current is None or (posted and posted > current):
                a["lastMentioned"] = th.get("postedAt")

    ranked = []
    for sym, a in agg.items():
        score = max(a["net"] * (1 + CONVICTION_WEIGHT * a["convictionHits"]), 0.0)
        ranked.append({
            "ticker": sym,
            "score": round(score, 4),
            "net": round(a["net"], 4),
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
