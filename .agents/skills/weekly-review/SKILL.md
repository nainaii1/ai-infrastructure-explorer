---
name: weekly-review
description: Run the weekly desk review — refresh prices, re-tier tickers, refresh Brain digests, and update Codex's per-ticker desk verdicts in verdicts.json, then regenerate data.js. Use when the operator says "weekly review", "refresh the desk", "update your verdicts", or "run the weekly".
---

# Weekly Desk Review

The operator forwards @aleabitoreddit posts to the Telegram bot during the
week; this skill is the weekly synthesis pass that turns that raw capture
into tiers, digests, and desk verdicts. Runs entirely in a Codex
session — no Anthropic API key needed.

## Token budget rule

Verdicts are written for the **Core tier only, top 12–15 by priority
score** — never for the whole universe. Everything else is covered by tier
badges and per-theme Brain digests. Do not expand coverage without the
operator asking.

## Procedure

1. **Refresh prices** (needs network):
   `python3 ingest/fetch_prices.py`
   If it fails (offline/rate-limited), continue — prices are cosmetic to this pass.

2. **Read the week's signal**: load `ingest/store/theses.json`, compute
   priorities with `ingest/scorer.py` (`compute_priorities` + `assign_tiers`),
   and diff against last week: which names entered/left Core, which theses
   are new since `verdicts.json`'s `meta.reviewedAt`.

3. **Triage Core-tier unsorted names**: any Core/Watch ticker still in
   `category: "unsorted"` gets classified via
   `python3 ingest/review.py classify SYM --category <id> --company "..." ...`
   (Radar-tier unsorted can wait.)

4. **Update `ingest/store/verdicts.json`** (the heart of the pass):
   - For each Core name (top 12–15 by score): re-read its theses, then write
     or update `{ticker, stance, view, execution, changesMind,
     basedOnThesisIds, updatedAt}`.
   - `stance` ∈ `act | accumulate | watch | pass`.
   - `view` must take a position on the analyst's take — agree with evidence
     or push back (bias check: is he talking his book? is the mention count
     inflated by list-posts?).
   - `execution` is a concrete suggestion (entry discipline, sizing tier,
     trigger), not a hedge. `changesMind` names the falsifier.
   - Cite real thesis ids in `basedOnThesisIds`.
   - Bump `meta.reviewedAt`, `meta.thesesConsidered`.
   - Names that dropped out of Core: remove their verdict (the UI hides
     verdicts for absent names automatically via the stamp).

5. **Refresh Brain digests** for categories with new theses — author digests
   grouped by category and run them through
   `synthesize.synthesize_all()` with an injected `call_fn` (see
   `docs/GUIDE.md` §3) so output stays byte-identical to an API run.

6. **Bump `base.json` `meta.version`** (e.g. 1.78 → 1.79) and set
   `meta.lastUpdated` — this is what makes the app re-seed localStorage.

7. **Regenerate + verify**:
   - `python3 ingest/generate_data_js.py`
   - `python3 -m unittest discover -s ingest/tests`
   - Open the app (preview server or `index.html`) and confirm: tier counts
     changed as expected, verdict badges render, no console errors.

8. **Report to the operator**: tier moves (who entered/left Core), stance
   changes vs last week, and the 2–3 sentences that matter this week.

## Hard rules

- `verdicts.json` is the only store file this skill authors directly;
  everything else flows through the existing pipeline scripts.
- Never hand-edit `data.js` (AGENTS.md rule #6).
- Always include the disclaimer in `meta.disclaimer` — this is research
  support, not investment advice.
