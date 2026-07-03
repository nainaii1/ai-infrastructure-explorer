# Signal Digest — Design Spec

_Written 2026-07-03. Status: **approved design, not yet implemented** — no code
exists for this feature. This document is the terminal artifact of a
brainstorming session; the next step is `writing-plans` to turn it into an
implementation plan._

## Problem

Raw theses forwarded from @aleabitoreddit are full-length social posts —
often 500-1,500+ characters, sometimes covering half a dozen tickers in one
stream-of-consciousness message. Displayed verbatim in the Evidence chapter,
they read as a wall of text, which is a poor fit for a web "field guide" meant
to be skimmed. The operator wants something closer to how "AI Signal Watch" (a
third-party Telegram bot that already monitors the same analyst) presents its
output: a short header, a one-paragraph overview, and one crisp stance line
per ticker — "Serenity is bullish on $AAOI, projecting over 800% Y/Y
growth..." — instead of a raw copy-paste of the source post.

## Constraint that shaped the design

Telegram bots cannot read messages posted by other bots (a platform rule, not
a config issue) — so this app's bot can never passively "listen" to a
channel like AI Signal Watch. Tweet discovery therefore **stays exactly as it
is today**: the operator forwards posts to the existing Telegram bot
(`ingest/bot.py`), which appends them to `theses.json` unchanged. Nothing
about ingestion changes.

## What's new: a periodic, Claude-authored rollup

A **Signal Digest** is a new artifact, generated on demand (not on a fixed
schedule), that takes every thesis ingested since the last digest and asks
Claude to write:

1. One short overview paragraph for the window.
2. One stance line per ticker mentioned (direction + one-sentence reasoning),
   in the terse "Serenity" voice — synthesized, not copy-pasted.

This mirrors the existing Brain digest pattern (`ingest/synthesize.py`) —
Claude reads raw theses and writes structured prose — but on a rolling time
window across all tickers, rather than a cumulative per-category theme.

## Scope decision

This is a **feature of `ai-supply-desk`**, not a standalone product. It has no
new Telegram bot identity, no public channel, no external distribution. The
digest is stored and rendered inside the existing app, alongside
`theses.json`/`brain.json`/`verdicts.json`.

## Data model

New store file `ingest/store/signal_digests.json`:

```json
{
  "meta": {
    "lastDigestedThroughId": "h_abc123",
    "schemaVersion": 1
  },
  "digests": [
    {
      "id": "d_20260703_1400",
      "windowStart": "2026-07-03T14:00:00Z",
      "windowEnd": "2026-07-03T18:00:00Z",
      "overview": "One paragraph, Claude-authored.",
      "tickers": [
        {
          "ticker": "AAOI",
          "stance": "bullish",
          "text": "Bullish on $AAOI — projecting 800%+ Y/Y growth into 2028.",
          "sourceThesisIds": ["h_111", "h_222"]
        }
      ],
      "generatedAt": "2026-07-03T18:05:00Z",
      "model": "claude-sonnet-5"
    }
  ]
}
```

- `meta.lastDigestedThroughId` is the watermark: the generator reads every
  thesis in `theses.json` appended after this id and treats them as the new
  window. First run has no watermark — it digests everything not yet covered.
- `stance` is a fixed, small vocabulary — `bullish | bearish | cautious |
  neutral` — a **direction**, not a **confidence level**. This is
  deliberately kept visually and semantically distinct from the existing
  conviction badges (`high|medium|low` / `core|watch|radar`), which measure a
  different axis (how sure, not which way).
- `sourceThesisIds` on each ticker line points back to the raw receipts —
  the drill-down target.
- Digests are **append-only** — never rewritten wholesale like Brain digests
  are on each re-synthesis. This is the key lifecycle difference from
  `brain.json` and the reason this isn't just folded into that file's shape.

`generate_data_js.py` passes the store through untouched as
`AIE_DATA.signalDigests` (same pattern as the `glossary` passthrough added in
the v6 redesign).

## Generation mechanism

New pure module `ingest/digest.py`, structured exactly like
`ingest/synthesize.py`:

- `build_digest(theses, tickers, call_fn, *, since_id=None, now=None) ->
  {digest, newWatermark} | None` — groups the new theses by ticker, calls
  `call_fn(system, user) -> raw dict` once for the whole window, validates the
  response against a small schema (overview + per-ticker stance/text,
  tickers restricted to the known ticker universe same as Brain's
  `validate_digest`), stamps `sourceThesisIds` per ticker line, and returns
  `None` if there are zero new theses since the watermark (idempotent no-op —
  never writes an empty digest).
- Pure and unit-testable with a fake `call_fn`, no network/SDK dependency —
  same firewall pattern as `synthesize.py` (the `anthropic` import stays
  isolated to that file's real API shell; `digest.py`'s core logic never
  imports it).

A new project skill, `.claude/skills/signal-digest/SKILL.md`, documents the
manual-authoring procedure (mirrors `/weekly-review`'s no-API-key workaround
already used for Brain refreshes): read theses since the watermark, author
the overview + stance lines in Claude Code, run them through
`digest.build_digest()` with an injected `call_fn` that returns the
hand-written JSON, save the store, regenerate `data.js`.

## Rendering — Evidence chapter (Chapter 03) restructure

Per the operator's choice, digests **replace** the raw thesis feed as the
primary content of the Evidence chapter (not an additional strip above it):

- Digest cards render newest-first: window label, overview paragraph, then
  one row per ticker (ticker chip + stance word + stance line).
- Each ticker row is expandable via the same CSS `grid-template-rows: 0fr ->
  1fr` drill-down already built for the Brain chapter's source reveal —
  expanding shows the raw source thesis card(s) behind that line, reusing
  `makeThesisCard(th, {compact: true})` unchanged.
- Existing category/high-conviction filter chips adapt: filtering by category
  filters ticker *rows* within each digest (via the existing
  `tickerCategoryMap()` lookup), not whole digests.
- Raw theses forwarded since the last digest but not yet digested show in a
  small "Undigested — N new posts, run `/signal-digest`" strip below the
  feed, so nothing silently disappears while waiting on the next run.
- Empty state (no digests yet) follows the existing Brain/Thesis empty-state
  pattern: explain what's missing and give the exact command to run.

No changes to `theses.json`, `bot.py`, or `parser.py` — raw ingestion is
completely unaffected; this is a read/rendering layer on top of it.

## Testing plan

- `ingest/tests/test_digest.py`, following `test_synthesize.py`'s shape:
  grouping by ticker, watermark advance, idempotent no-op on zero new
  theses, schema validation/coercion with a fake `call_fn`.
- End-to-end: forward a couple of test posts via `bot.py --text`, run the
  skill by hand with a stubbed digest, verify in the Claude Preview browser
  that the digest renders and the per-ticker drill-down reveals the correct
  raw thesis card(s).

## Explicitly out of scope (for this spec)

- Automated tweet discovery (no X API, no Telethon watcher) — ingestion stays
  manual-forward, unchanged.
- Posting the digest to Telegram — this is a web-app-only artifact for now;
  distribution can be added later without reworking the schema above.
- A fixed cron/schedule — the skill is run on demand, like `/weekly-review`.
