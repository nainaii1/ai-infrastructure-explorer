"""Composite priority scoring — ranks what the author prioritizes.

    net   = sum(recency_weight * focus_weight * direction_weight)
    score = max(net, 0)

Recency uses exponential decay with a configurable half-life, so a ticker the
author mentions often AND recently rises to the top. Conviction language no
longer lifts a score at all (see CONVICTION_WEIGHT), though conviction hits are
still counted and still drive tiers.

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

# Retired 2026-07-26 (operator sign-off). `conviction` is assigned by keyword
# match in parser.py against phrases like "top pick" and "high conviction". It
# fired on 17 of 258 posts and multiplied a score by up to 6x — SIVE scored
# 91.11 on 10 hits, versus ~15 without (14.99 when measured on 2026-07-26; it
# drifts with recency decay). That is rhetoric driving a ranking.
# Kept as a constant, not deleted, so this is reversible by restoring 0.5.
# Note: assign_tiers still reads convictionHits directly, so tiers are
# unaffected by this change.
CONVICTION_WEIGHT = 0.0

# Signed contribution of one mention. Research findings may subtract but never
# add: the same model that writes the desk verdicts must not be able to agree
# with itself three times and inflate a rank. Analyst bull and neutral posts
# both weigh 1.0, so migrating undirected theses to "neutral" changes no score.
RESEARCH_SOURCE = "research"

# The only directions a thesis can express.
VALID_DIRECTIONS = {"bull", "bear", "neutral"}

# A present-but-unrecognized direction — a typo ("bearish", "BEAR", "short"),
# an empty string, a future value nobody wired up yet. Kept distinct from
# "neutral" because the two must score differently: see _direction_weight.
UNKNOWN_DIRECTION = "unknown"


def is_research(thesis):
    """True when a thesis is a desk research finding rather than an analyst post.

    Case-insensitive on purpose. These records are hand-authored by an agent,
    and a miscased "Research" must not silently revert the name to full analyst
    treatment — that would restore both the score weight and the tier coverage
    the asymmetry exists to withhold, which is the wrong direction to fail in.
    An absent or None source still reads as analyst: that is every one of the
    258 captured posts, and they are genuinely his.

    Public (no leading underscore) because this is a shared rule, not a private
    helper: three call sites now, and two of them are in other modules —
    pre_review.select_coverage and pre_review.merge_research_theses, which
    exclude research from the coverage aggregate and gate what may enter the
    thesis store, for the same reason the other call sites exclude it from
    score and tier. One definition so they can never drift apart.
    """
    source = thesis.get("source")
    return isinstance(source, str) and source.strip().lower() == RESEARCH_SOURCE


def _normalize_direction(thesis):
    """The single source of truth for what a thesis's direction "really" is.

    Absent key -> "neutral": that is every one of the migrated records, which
    must keep scoring exactly as they did before directions existed.
    Present but unrecognized -> "unknown", which is NOT the same thing. These
    records get hand-authored by an agent, and a typo'd "bearish" was meant as
    a bear; scoring it as neutral would contribute +1.0 and swing the score two
    points the wrong way. Distinguishing the two lets a bad value fall back to
    "no opinion" instead of silently becoming the vote it was not.
    """
    raw = thesis.get("direction")
    if raw is None:
        return "neutral"
    return raw if raw in VALID_DIRECTIONS else UNKNOWN_DIRECTION


def _direction_weight(thesis):
    direction = _normalize_direction(thesis)
    if direction == UNKNOWN_DIRECTION:
        return 0.0          # can't read it, so it doesn't get a vote
    if direction == "bear":
        return -1.0
    if is_research(thesis):
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
    """Return a list of {ticker, score, net, attention, mentions,
    analystMentions, bullMentions, bearMentions, researchMentions,
    weightedMentions, convictionHits, lastMentioned} ranked by
    score descending, then net (so a net-negative name doesn't out-rank a
    less-hated one just because both floor to score 0), then raw mentions."""
    now = now or datetime.now(timezone.utc)
    agg = {}

    for th in theses:
        posted = _parse_dt(th.get("postedAt")) or now
        age_days = max(0.0, (now - posted).total_seconds() / 86400.0)
        weight = 0.5 ** (age_days / half_life_days)
        is_high = th.get("conviction") == "high"
        syms = th.get("tickers", [])
        focus = _focus_weight(len(syms))
        direction = _normalize_direction(th)
        research = is_research(th)   # local name differs: `is_research` is the function
        signed = weight * focus * _direction_weight(th)
        for sym in syms:
            a = agg.setdefault(
                sym,
                {"mentions": 0, "weighted": 0.0, "recency": 0.0,
                 "net": 0.0, "bull": 0, "bear": 0, "research": 0,
                 "convictionHits": 0, "lastMentioned": None},
            )
            a["mentions"] += 1              # raw count, for display ("12x mentioned")
            # Research findings never create coverage — only analyst attention
            # feeds the focus-weighted count that assign_tiers() gates on.
            # Without this, a model could zero its own score contribution via
            # RESEARCH_SOURCE and still promote a name to "core" through
            # weightedMentions, which the score guard never touches.
            if not research:
                a["weighted"] += focus
            # `attention` is an aggregate, so the asymmetry applies here too:
            # research may subtract but never add. It is also presented as the
            # analyst's attention, which desk findings are not.
            if not research:
                a["recency"] += weight * focus  # recency + focus, for `attention`
            a["net"] += signed
            if direction == "bear":
                a["bear"] += 1
            elif direction == "bull":
                a["bull"] += 1
            # Conviction hits gate tiers directly in assign_tiers, so research
            # must be excluded here too. Guarding only `weighted` left this
            # path open: two research posts marked "high" promoted a name to
            # core with a score of 0.0 (verified 2026-07-26).
            if is_high and not research:
                a["convictionHits"] += 1
            if research:
                a["research"] += 1
            # "Last mentioned" is rendered as "Last cited" on the analyst's own
            # vault page, so a finding the desk wrote today must not become his
            # most recent word on the name.
            if not research:
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
            "attention": round(a["recency"], 4),
            "mentions": a["mentions"],
            # Derived here, once, rather than left to each surface to subtract:
            # every "by @aleabitoreddit" label in the app reads this, and a
            # subtraction repeated at four call sites is four chances to forget.
            "analystMentions": a["mentions"] - a["research"],
            "bullMentions": a["bull"],
            "bearMentions": a["bear"],
            "researchMentions": a["research"],
            "weightedMentions": round(a["weighted"], 4),
            "convictionHits": a["convictionHits"],
            "lastMentioned": a["lastMentioned"],
        })

    ranked.sort(key=lambda r: (r["score"], r["net"], r["mentions"]), reverse=True)
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
        # No fallback to `mentions`: mentions counts desk research, so an
        # absent weightedMentions must read as zero attention, not as research
        # attention. Every caller computes fresh rows that carry the field.
        weighted = p.get("weightedMentions", 0) if p else 0
        hits = p["convictionHits"] if p else 0
        if weighted >= TIER_CORE_MIN_MENTIONS or hits >= TIER_CORE_MIN_CONVICTION_HITS:
            tiers[sym] = "core"
        elif weighted >= TIER_WATCH_MIN_MENTIONS or hits >= TIER_WATCH_MIN_CONVICTION_HITS:
            tiers[sym] = "watch"
        else:
            tiers[sym] = "radar"
    return tiers
