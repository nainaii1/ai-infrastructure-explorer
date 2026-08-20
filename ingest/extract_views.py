"""Runner for the per-ticker view extraction (see views.py and PROJECT.md).

Three ways to run, first match wins — mirrors synthesize.py:

  1. OPENROUTER_API_KEY / ANTHROPIC_API_KEY set  ->  runs the whole pass itself
  2. no key, in-session Claude Code             ->  the two-step manual path:

         python3 ingest/extract_views.py --emit --limit 40 [--core-only]
             writes store/.views_batch.json — the posts still needing a read

         (Claude reads that file and writes an answers file:
            {"<thesisId>": {"views":[{ticker,direction,why,numbers?,horizon?}]}} )

         python3 ingest/extract_views.py --apply answers.json
             validates every answer through views.validate_views, merges,
             regenerates data.js

The apply path runs the SAME validation as the API path, so a hand-authored
answer cannot smuggle in a ticker the post never mentioned. That is deliberate:
the injection firewall must not be bypassable by the convenient route.

This module does the I/O; views.py stays pure (invariant 6).
"""

import os
import sys
import json
import argparse
import pathlib

import generate_data_js as gen
import views as views_mod
from dotenv_util import _load_dotenv
from store_io import (
    load_json as _load,
    save_json as _save_json,
    now_iso as _now_iso,
)

ING = pathlib.Path(__file__).resolve().parent
STORE = ING / "store"
BATCH_PATH = STORE / ".views_batch.json"

# Keep a manual batch readable in one sitting; the API path has no such limit.
DEFAULT_EMIT_LIMIT = 40


def _save(name, data):
    _save_json(name, data, trailing_newline=True)


def _aliases():
    """base.json tickerAliases — the same map scorer.canonicalize_theses uses.

    Loaded here, never inside views.py: that module must stay free of file I/O
    (invariant 6), so the map is injected into every call instead.
    """
    base = _load("base.json") or {}
    raw = base.get("tickerAliases") or {}
    return {str(k).upper(): str(v).upper() for k, v in raw.items()
            if isinstance(k, str) and isinstance(v, str) and v.strip()}


def _universe(tickers):
    return [t["ticker"] for t in tickers if t.get("ticker")]


def _core_symbols(tickers, theses):
    """Core/Watch symbols, derived the same way generate_data_js does.

    `tier` is NOT stored in tickers.json — it is computed at generate time from
    the priority table. Reading `t["tier"]` here returns None for every ticker
    and makes --core-only silently match nothing, which is worse than an error:
    the pass reports success having read no posts.
    """
    import scorer
    # Canonicalize with the SAME maps generate_data_js.build_data uses, or this
    # computes a different tier table than the app shows. Measured 2026-08-21
    # with the maps omitted: 000660.KS read radar (really watch), SOI.PA read
    # watch (really core), SPCX read core (really radar, it is a themeTag).
    base = _load("base.json") or {}
    canon = scorer.canonicalize_theses(
        theses, base.get("tickerAliases"), base.get("themeTags"))
    priorities = scorer.compute_priorities(canon)
    symbols = [t["ticker"] for t in tickers if t.get("ticker")]
    tiers = scorer.assign_tiers(symbols, priorities)
    core = {s for s in symbols if tiers.get(s) in ("core", "watch")}
    if not core:
        sys.exit("--core-only matched no tickers; refusing to run a pass that "
                 "would read nothing. Check scorer.assign_tiers output.")
    return core


def _alias_gap(theses, tickers):
    """Already-extracted posts the old, un-canonicalized scope read too narrowly.

    Kept separate from _pending because these posts are STAMPED — needs_extraction
    refuses them by design. Re-reading one replaces its whole views array, so an
    answer for it must cover every ticker in scope, not only the missing one.
    """
    universe = _universe(tickers)
    aliases = _aliases()
    out = [t for t in theses
           if views_mod.needs_alias_recheck(t, universe, aliases)]
    out.sort(key=lambda t: t.get("postedAt") or "", reverse=True)
    return out


def _pending(theses, tickers, core_only=False):
    """Posts still needing a read, most recent first.

    Recent-first because a stale view on a name he has since re-argued is worth
    less than his current one, and a partial pass should leave the freshest
    reasoning extracted rather than the oldest.
    """
    core = _core_symbols(tickers, theses) if core_only else None
    aliases = _aliases()
    out = []
    for t in theses:
        if not views_mod.needs_extraction(t):
            continue
        # Canonicalize before the tier test for the same reason the scope does:
        # a post whose only symbol is $LPK would otherwise never intersect a
        # core set holding LPK.DE, and --core-only would skip it forever.
        if core is not None:
            syms = set(views_mod._post_ticker_scope(t, _universe(tickers), aliases))
            if not (syms & core):
                continue
        out.append(t)
    out.sort(key=lambda t: t.get("postedAt") or "", reverse=True)
    return out


def emit(limit=DEFAULT_EMIT_LIMIT, core_only=False, alias_gap=False):
    theses = _load("theses.json")
    tickers = _load("tickers.json")
    universe = _universe(tickers)
    aliases = _aliases()
    selected = _alias_gap(theses, tickers) if alias_gap \
        else _pending(theses, tickers, core_only)
    pending = selected[:limit]

    batch = []
    for t in pending:
        batch.append({
            "id": t.get("id"),
            "postedAt": t.get("postedAt"),
            "allowedTickers": views_mod._post_ticker_scope(t, universe, aliases),
            "aliasNotes": ["%s is written $%s in this post" % (canon, written)
                           for canon, written in
                           views_mod.alias_notes(t, universe, aliases)],
            "text": (t.get("text") or "")[:views_mod.MAX_THESIS_CHARS],
        })

    _save(".views_batch.json", {
        "meta": {
            "generatedAt": _now_iso(),
            "count": len(batch),
            "instructions": (
                "For each post, report what the analyst said about EACH allowed "
                "ticker separately. One post may hold opposing views. direction "
                "is bull|bear|neutral; use neutral for a bare mention or genuine "
                "ambiguity. Answer file shape: "
                "{\"<id>\": {\"views\": [{\"ticker\",\"direction\",\"why\","
                "\"numbers\",\"horizon\"}]}}"
            ),
        },
        "posts": batch,
    })

    total_pending = len(selected)
    print(json.dumps({
        "emitted": len(batch),
        "stillPending": max(0, total_pending - len(batch)),
        "path": str(BATCH_PATH),
    }))
    return batch


def apply_answers(path):
    """Merge a hand-authored answers file, validating exactly like the API path."""
    answers = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(answers, dict):
        sys.exit("answers file must be an object keyed by thesis id")

    theses = _load("theses.json")
    tickers = _load("tickers.json")
    universe = _universe(tickers)
    aliases = _aliases()
    now = _now_iso()

    by_id = {t.get("id"): t for t in theses}
    unknown = [k for k in answers if k not in by_id]
    if unknown:
        sys.exit("unknown thesis ids in answers file: %s" % ", ".join(unknown[:5]))

    stats = {"applied": 0, "views": 0, "bull": 0, "bear": 0, "neutral": 0,
             "dropped": 0}
    updated = []
    for t in theses:
        ans = answers.get(t.get("id"))
        if ans is None:
            updated.append(t)
            continue
        claimed = len((ans or {}).get("views") or [])
        v = views_mod.validate_views(ans, t, universe, aliases)
        stats["dropped"] += max(0, claimed - len(v))
        record = dict(t)
        record["views"] = v
        record["viewsExtractedAt"] = now
        stats["applied"] += 1
        stats["views"] += len(v)
        for item in v:
            stats[item["direction"]] += 1
        updated.append(record)

    _save("theses.json", updated)
    gen.write_data_js()
    print(json.dumps(stats))
    return stats


def run_with_api(limit=None, core_only=False):
    """Whole pass via an API backend. Reuses synthesize.py's backend picker so
    there is one place that knows how to reach a model."""
    import synthesize

    backend, model = synthesize.pick_backend()
    if backend is None:
        sys.exit(
            "No API key set (OPENROUTER_API_KEY or ANTHROPIC_API_KEY in "
            "ingest/.env). Use the manual path instead:\n"
            "  python3 ingest/extract_views.py --emit --limit 40\n"
            "then have Claude write an answers file and:\n"
            "  python3 ingest/extract_views.py --apply answers.json"
        )

    theses = _load("theses.json")
    tickers = _load("tickers.json")
    universe = _universe(tickers)

    if core_only:
        core = _core_symbols(tickers, theses)
        targets = {t.get("id") for t in theses
                   if set(t.get("tickers") or []) & core}
    else:
        targets = None

    def call_fn(system, user):
        if backend == "anthropic":
            return synthesize.call_claude(synthesize._get_client(), model, system, user)
        return synthesize.call_openrouter(
            model, system, user, os.environ.get("OPENROUTER_API_KEY"))

    scoped = theses if targets is None else [
        t if (t.get("id") in targets) else dict(t, viewsExtractedAt="skip")
        for t in theses
    ]

    updated, stats = views_mod.extract_views(
        scoped, universe, call_fn, _now_iso(), limit=limit, aliases=_aliases(),
        on_error=lambda t, e: print("WARN view extraction failed on %s: %s"
                                    % (t.get("id"), e), file=sys.stderr))

    # strip the temporary scoping marker
    cleaned = []
    for t in updated:
        if t.get("viewsExtractedAt") == "skip":
            t = {k: v for k, v in t.items() if k != "viewsExtractedAt"}
        cleaned.append(t)

    _save("theses.json", cleaned)
    gen.write_data_js()
    print(json.dumps(stats))
    return stats


def status():
    theses = _load("theses.json")
    tickers = _load("tickers.json")
    analyst = [t for t in theses if t.get("source") == "x"]
    done = [t for t in analyst if t.get("viewsExtractedAt")]
    views_total, dirs = 0, {"bull": 0, "bear": 0, "neutral": 0}
    for t in done:
        for v in (t.get("views") or []):
            views_total += 1
            if v.get("direction") in dirs:
                dirs[v["direction"]] += 1
    print(json.dumps({
        "analystPosts": len(analyst),
        "extracted": len(done),
        "pending": len(_pending(theses, tickers)),
        "pendingCoreWatch": len(_pending(theses, tickers, core_only=True)),
        "aliasGap": len(_alias_gap(theses, tickers)),
        "views": views_total,
        "directions": dirs,
    }, indent=2))


def main():
    _load_dotenv()
    ap = argparse.ArgumentParser(description="Extract per-ticker analyst views")
    ap.add_argument("--emit", action="store_true",
                    help="write a batch of posts for manual extraction")
    ap.add_argument("--apply", metavar="FILE", help="merge a hand-authored answers file")
    ap.add_argument("--status", action="store_true", help="show extraction progress")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--core-only", action="store_true",
                    help="only posts touching Core/Watch names")
    ap.add_argument("--alias-gap", action="store_true",
                    help="re-read extracted posts whose alias symbol was skipped")
    args = ap.parse_args()

    if args.status:
        return status()
    if args.apply:
        return apply_answers(args.apply)
    if args.emit:
        return emit(args.limit or DEFAULT_EMIT_LIMIT, args.core_only,
                    args.alias_gap)
    return run_with_api(args.limit, args.core_only)


if __name__ == "__main__":
    main()
