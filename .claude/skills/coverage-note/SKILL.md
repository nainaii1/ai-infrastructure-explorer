---
name: coverage-note
description: Author or update one coverage memo for a single ticker in ingest/store/memos.json, then regenerate data.js. Use when the operator says "/coverage-note TICKER", "write a memo on TICKER", "update the TICKER memo", or "cover TICKER".
---

# Coverage Note — `/coverage-note TICKER`

Writes (or refreshes) **one** coverage memo for the given ticker, using the
same rules as the weekly review's step 4b, without running the whole weekly
pass. Runs entirely in a Claude Code session — no API key needed.

## Preconditions

- The ticker should normally be **Core tier with a desk verdict** in
  `ingest/store/verdicts.json`. If it has no verdict, stop and tell the
  operator: a memo's rating must mirror a desk stance, so the verdict comes
  first (offer to write one via the weekly-review rules).

## Procedure

1. **Gather the evidence** (read-only):
   - Every thesis mentioning the ticker in `ingest/store/theses.json`.
   - Its Brain digest context in `ingest/store/brain.json` (its category's
     narrative + key points).
   - Its desk verdict in `ingest/store/verdicts.json` (stance, view,
     execution, changesMind).
   - Its ticker record in `ingest/store/tickers.json` (company, category,
     whatTheyDo, whyNVDA).

2. **Author the memo** in `ingest/store/memos.json`:
   - `id: "m_<TICKER>_<yyyy>w<ww>"` (ISO week of today).
   - `kind`: `"coverage"` if this is the ticker's first memo, `"update"` if
     one exists, `"exit-note"` if the name is leaving Core / stance → pass.
   - `rating` **MUST equal the current desk stance** — never diverge.
   - `sections` in fixed order: **Snapshot / Thesis / Why own it / Risks /
     Bottom line**. Bodies are plain paragraphs on `\n\n`; inline markup
     limited to `**bold**`, `$TICK`, `[[wikilink]]`.
   - Voice: second-opinion research desk — take a position on the analyst's
     take, don't just restate it. Flag list-post mention inflation and
     talking-his-book risk where relevant.
   - **No live numbers in the body** (price/market cap/tier render live on
     the memo page). Analyst-stated targets quoted from theses are fine.
   - Cite the real grounding thesis ids in `sourceThesisIds`;
     `basedOnVerdict: true` when a verdict informed it.
   - Same-week edit: keep `id`/`publishedAt`, bump `updatedAt`. New week:
     new `id`, `kind: "update"`.
   - Bump `meta.updatedAt`.

3. **Regenerate + verify**:
   - Bump `base.json` `meta.version` (so the app re-seeds).
   - `python3 ingest/generate_data_js.py`
   - `python3 -m unittest discover -s ingest/tests`
   - Open `memo.html?ticker=<TICKER>` and `index.html` (ledger row appears)
     — no console errors.

4. **Report**: one-paragraph summary of the memo's bottom line and what
   changed vs the prior memo (if any).

## Hard rules

- Never fabricate a number — every figure in the body must trace to a cited
  thesis. A flagged gap beats a plausible guess.
- Never hand-edit `data.js`.
- Memos are research support, not investment advice; the disclaimer lives in
  `memos.json` `meta.disclaimer`.
