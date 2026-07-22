---
name: weekly-review
description: Run the weekly desk review — refresh prices, re-tier tickers, refresh Brain digests, and update Claude's per-ticker desk verdicts in verdicts.json, then regenerate data.js. Use when the operator says "weekly review", "refresh the desk", "update your verdicts", or "run the weekly".
---

# Weekly Desk Review

The operator forwards @aleabitoreddit posts to the Telegram bot during the
week; this skill is the weekly synthesis pass that turns that raw capture
into tiers, digests, and desk verdicts. Runs entirely in a Claude Code
session — no Anthropic API key needed.

## Token budget rule

Verdicts are written for the **Core tier only: top 15 by priority score,
plus sticky holdovers** — a name with a live act/accumulate verdict stays
on the roster even if its score slips out of the top 15, until its stance
drops to watch/pass (operator decision, 2026-07-16). Score decides who
*enters*. Never write verdicts for the whole universe — everything else is
covered by tier badges and per-theme Brain digests. Do not expand coverage
further without the operator asking.

## Procedure

1. **Refresh prices** (needs network):
   `python3 ingest/fetch_prices.py`
   If it fails (offline/rate-limited), continue — prices are cosmetic to this pass.

2. **Read the week's signal**: load `ingest/store/theses.json`, compute
   priorities with `ingest/scorer.py` (`compute_priorities` + `assign_tiers`),
   and diff against last week: which names entered/left Core, which theses
   are new since `verdicts.json`'s `meta.reviewedAt`.

3. **Triage unsorted names — propose, confirm, apply** (the operator never
   types `review.py` flags himself):
   - Read every ticker with `category: "unsorted"` in `tickers.json` and the
     candidates in `pending_tickers.json`. Core/Watch-tier unsorted names are
     mandatory this pass; Radar-tier and pending candidates are triaged
     opportunistically (batch the obvious ones, skip the noise).
   - Present ONE batch table to the operator: symbol → proposed
     category / company / market / tier, plus a one-line "what/why". Only
     propose facts you can ground in the captured theses or verifiable
     knowledge — an unknown company gets flagged "needs your input", never
     invented.
   - After the operator confirms/edits the batch, apply it with
     `python3 ingest/review.py classify ...` / `approve` / `reject` calls
     (review.py stays the low-level tool; this step is its front-end).

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

   (No Focus card any more — the v8 app is a dense analysis tool, not an
   editorial product. The week's one headline goes in the report to the
   operator at step 8, not into the store. `meta.focus` may still exist in
   verdicts.json but nothing renders it; leave it alone, don't hand-edit it.)

4b. **Write/refresh coverage memos** in `ingest/store/memos.json` — only for
   Core names whose **stance changed** in step 4 or that gained **≥3 new
   theses** since the last review (don't rewrite the whole book weekly):
   - Record shape: `{ id: "m_<TICKER>_<yyyy>w<ww>", ticker, kind:
     "coverage" (first memo) | "update" (stance/thesis evolution) |
     "exit-note" (dropped from Core or stance → pass), title, dek,
     publishedAt, updatedAt, rating, sections, sourceThesisIds,
     basedOnVerdict: true }`.
   - `rating` **MUST equal the ticker's current desk stance** in
     verdicts.json (`act | accumulate | watch | pass`) — never let the memo
     and the verdict disagree.
   - `sections` follow the fixed order: **Snapshot / Thesis / Why own it /
     Risks / Bottom line** (each `{heading, body}`; bodies are plain
     paragraphs on `\n\n`, allowed inline markup: `**bold**`, `$TICK`,
     `[[wikilink]]` only — no other markdown).
   - Cite the real thesis ids that ground the memo in `sourceThesisIds`.
   - Never put live numbers (price, market cap, tier) in the body — the
     memo page pulls those live from the ticker record. Analyst-stated
     targets from theses are fine (they're claims, not data).
   - Bump `meta.updatedAt` in memos.json.
   - Updating an existing memo in place (same week, new info): keep `id`
     and `publishedAt`, refresh `updatedAt` + body. A new week's revisit
     gets a new `id` (new week number) with `kind: "update"`.

4c. **Enrich touched vault pages** in `ingest/store/vault.json` — only the
   pages whose story actually moved this week: any ticker whose **tier or
   stance changed** in step 4, and the **theme** of any such ticker. Follow
   the `/vault-note` skill rules — write 1–3 paragraphs of wikilinked prose
   into that page's `note` (never touch `auto.*`), stamp `noteUpdatedAt`.
   Don't re-enrich the whole vault weekly; leave unchanged pages alone. New
   ticker pages appear automatically (sync runs during regen) — they start as
   stubs and can be enriched on demand via `/vault-note SLUG`.

4d. **Stamp calls** in `ingest/store/calls.json` — ONLY when this week's pass
   produced a **discrete, forward-looking event**:
   - a verdict **newly flipping to act/accumulate** (kind `new-position`),
   - a **declared dip-buy** on an already-accumulating name (kind `add-on-dip`),
   - a stance stepping down with a trim suggestion (kind `trim`), or
   - an **exit** (stance → pass / dropped from Core; kind `exit` — also set
     `closedAt`, `exitPrice`, and grade `outcome` win|loss|wash vs entry).
   **Explicitly no retro-fitting**: never stamp a call for something that
   already happened, and never backdate `calledAt`. If prices are stale, run
   `python3 ingest/fetch_prices.py` first — `entryPrice` comes from
   `prices.json` (same day), `benchmark.priceAtCall` from its `SMH` row.
   Record shape: `{ id: "c_<TICKER>_<yyyy-mm-dd>", ticker, kind:
   "new-position"|"add-on-dip"|"trim"|"exit", calledAt, entryPrice,
   entryCurrency, stanceAtCall, memoId (or null), thesisIds, closedAt: null,
   exitPrice: null, outcome: "open"|"win"|"loss"|"wash",
   benchmark: {symbol: "SMH", priceAtCall} }`. Bump `meta.updatedAt`.
   No qualifying event this week → stamp nothing (most weeks stamp nothing).

5. **Refresh Brain digests** for categories with new theses — author digests
   grouped by category and run them through
   `synthesize.synthesize_all()` with an injected `call_fn` (see
   `docs/GUIDE.md` §3) so output stays byte-identical to an API run.
   Set `brain.json` `meta.model` to a short human-readable provenance string
   (e.g. `"weekly desk review"`) — it may surface in tooling, and pipeline
   jargon like "injected call_fn" must never be written there. The UI itself
   renders only the date + "weekly desk review".

6. **Bump `base.json` `meta.version`** (e.g. 1.78 → 1.79) and set
   `meta.lastUpdated` — this is what makes the app re-seed localStorage.

7. **Regenerate + verify**:
   - `python3 ingest/generate_data_js.py`
   - `python3 -m unittest discover -s ingest/tests`
   - Open the app (preview server or `index.html`) and confirm: tier counts
     changed as expected, verdict badges render, no console errors.

8. **Report to the operator**: lead with **the week's one headline** — the
   single most decision-relevant development from this pass, short and
   declarative (this is what used to be the Focus card; it now lives only in
   the report). Then: tier moves (who entered/left Core), stance changes vs
   last week, and the 2–3 sentences that matter this week.

## Hard rules

- `verdicts.json`, `memos.json`, `calls.json`, and the `note` fields of
  `vault.json` are the only store data this skill authors directly (vault
  `auto.*` is owned by `vault_sync.py`); everything else flows through the
  existing pipeline scripts.
- Calls are stamped forward-only. A missed entry is a missed entry — the
  ledger's honesty is the product.
- Never hand-edit `data.js` (CLAUDE.md rule #6).
- Always include the disclaimer in `meta.disclaimer` — this is research
  support, not investment advice.
