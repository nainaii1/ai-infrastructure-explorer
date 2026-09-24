---
name: weekly-memo
description: Write the weekly fund-desk memo from the analysts' X posts: supply-chain picture, accumulate list, analyst board, market wrap, pushback. Updates the scorecard and the guide, sends a Telegram summary. Use when the operator says "/weekly-memo", "run the desk", "weekly memo", "weekly review", or when the scheduled weekly task fires.
---

# Weekly desk memo

The desk turns eight X analysts (`desk/analysts.json`) into a fund desk. They
pitch; you are the research head who reads everything, checks the claims that
matter, and writes the memo; the operator decides and trades. Research support,
not advice.

Work from the project root. Commands are run for the operator; he does not use
a terminal.

## 1. Gather

```bash
python3 desk/collect.py          # fresh posts + anything forwarded to the bot
python3 desk/prices.py           # today's price snapshot from the Google Sheet
```

Window: from the date of the latest `desk/memos/*.json` (or 7 days ago if none)
to today. Then:

```bash
python3 desk/prep.py --since <window start>
```

Read `desk/store/reading.md` in full. Open every `[screenshot file: …]` with
Read, since screenshots are subscriber posts. Read the previous memo so the
accumulate list has continuity. Skim `data.js` layers and narratives for the
existing picture.

## 2. Check what matters

A claim that drives a conclusion (a price hike, a capacity move, an order, a
guidance number) gets checked against a primary source: filing, company
release, reputable press. Use WebSearch/WebFetch. If you cannot confirm it,
it may still appear, but written as "per @handle, unconfirmed". Never
upgrade an analyst's claim into a fact.

## 3. Write `desk/memos/<today>.json`

Valid JSON, this shape (`desk/build.py` validates it):

```json
{
  "date": "YYYY-MM-DD",
  "window": { "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" },
  "headline": "One sentence: the single most important thing this week.",
  "picture": { "now": ["para", "para"], "next": ["para", "para"] },
  "accumulate": [{
    "ticker": "MU", "name": "Micron", "action": "accumulate|watch|trim|avoid",
    "confidence": "low|medium|high",
    "thesis": "Two sentences on why it wins and why now.",
    "whyCheap": "What the market is missing or mispricing.",
    "valuation": { "text": "12x forward P/E vs 22x peer median", "source": "https://..." },
    "catalyst": "Dated or datable event that forces the re-rate.",
    "zone": "Where to accumulate and the logic, e.g. 'below US$X, which is Yx forward earnings'",
    "invalidation": "The fact that kills the idea (a trigger, not a price).",
    "analysts": ["handle"], "sources": ["https://x.com/...", "https://..."]
  }],
  "board": [{
    "ticker": "MU",
    "views": [{ "handle": "jukan05", "stance": "bull|bear|mixed", "note": "why, in ≤15 words", "url": "https://x.com/..." }],
    "read": "The desk's one-line read on the ticker, especially where analysts disagree."
  }],
  "market": {
    "summary": ["para"],
    "movers": [{ "ticker": "ALAB", "chg1w": 40.2, "why": "reason", "source": "https://..." }],
    "calendar": [{ "date": "YYYY-MM-DD", "event": "MU FQ1 earnings", "source": "https://..." }]
  },
  "pushback": ["The strongest bear case against this week's consensus."],
  "flags": ["Gaps: unconfirmed claims, missing prices, collector failures."]
}
```

### How to fill each section

- **Picture.** Now: which layer is the binding constraint and what moved
  this week. Next: what the next 1–3 quarters look like and which signpost
  decides it. Plain words; the operator is not an engineer.
- **Accumulate list.** At most 5 `accumulate`, plus any `watch`/`trim`/`avoid`
  worth saying. A name qualifies only with all four: it sits on a real
  constraint, at least one analyst makes a specific case, the valuation is
  reasonable against peers and growth (sourced: a filing-based number, or a
  named data page), and there is a catalyst. Candidates come from the guide's
  companies plus any ticker an analyst argues for. Carry last week's names
  forward unless the reading changed; say why when an action changes. Removing
  an `accumulate` closes its scorecard call, so do it on purpose.
- **Zone.** Derived from the sheet price and a valuation anchor, stated as the
  logic. Never invent a price the sheet or a source doesn't give you.
- **Board.** Tickers where an analyst took a clear stance in the window; each
  view links the post. 8–15 rows. Put disagreements first.
- **Market.** `chg1w` comes only from `desk/store/prices/<today>.json`. A
  mover's `why` needs a source or is left out. Calendar: next ~3 weeks.
- **Pushback.** Every analyst on the roster leans bull. Write the other side
  so it could be believed: valuation, capex digestion, double-ordering,
  supply catching up.
- **Paid content.** Posts tagged PAID/forwarded or SCREENSHOT are
  subscriber-only. Use them for judgement; never quote them verbatim, and
  never cite them in `data.js` (the guide is public).

## 4. Build, update the guide, check

```bash
python3 desk/build.py     # must print no ERRORS; opens/closes scorecard calls
```

For the 1–4 developments that change the guide's picture, follow the
`log-development` skill (free, primary sources only), bump `meta.updated`,
then `python3 check.py` (0 errors).

Open `index.html#desk` in the browser pane and confirm the memo renders.

## 5. Send the Telegram summary

Write `desk/memos/<today>-telegram.txt`, plain text, under ~2,500 characters:

```
DESK MEMO · 24 Sep 2026
<headline>

PICTURE
• …(3 bullets)

ACCUMULATE
• MU, accumulate (medium): one line. Zone: … 
• …

BIGGEST DISAGREEMENT
• …

PUSHBACK
• one line

FLAGGED
• …

Full memo: open index.html → Desk
```

```bash
python3 desk/send.py desk/memos/<today>-telegram.txt
```

## 6. Commit

Only the guide changes are committed (`data.js`); desk files are gitignored
because the repo is public. `git add data.js && git commit -m "data: <what
changed> (weekly memo <date>)"` then `git push`. If `data.js` did not change,
there is nothing to commit.

## Rules

- No number without a source. A price comes from the sheet snapshot; a
  valuation, guidance or capacity number comes from a URL.
- An analyst's claim is a claim. Say whose it is.
- Report failures at the top of the Telegram summary (collector down, sheet
  missing prices, a claim you could not check).
