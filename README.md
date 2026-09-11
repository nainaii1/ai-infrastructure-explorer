# AI Infrastructure Explorer

A private research desk for the AI hardware supply chain — the companies
NVIDIA and the big cloud firms depend on to build AI chips: laser makers,
memory makers, chip factories, cloud providers, materials.

It does three things:

1. **Captures** one analyst's ideas so they don't scroll away
2. **Checks** them — against SEC filings, and against a second opinion
3. **Scores** both of us, so being wrong is on the record

> Personal project. Single user. Not investment advice.

---

## Open it

**Double-click `desk.html`.** That's it — no internet, no server, nothing to
install. Every page works offline.

For backend chores (bot, prices, status) double-click **`desk.command`** and
pick from the menu.

---

## The five pages

| Page | What it's for |
|---|---|
| **desk.html** | The main surface — watchlist, supply-chain map, theme summaries |
| **index.html** | The memo index |
| **memo.html** | Reads one memo |
| **vault.html** | Wiki-style notes, one page per company and theme |
| **performance.html** | The scoreboard — my calls and everyone's predictions |

---

## Your weekly loop

This is the whole routine. It takes about 20 minutes a week.

**Daily — 2 minutes.** Telegram sends you candidate posts. Tap ✅ or ❌.
Nothing enters the system without your tap.

**Weekly — two commands in Claude Code:**

```
/pre-review      three expert reviewers research this week's shortlist
/weekly-review   prices refresh, tiers recompute, verdicts get rewritten
```

Then read the report and decide. `/pre-review` puts a bear case on the table
before the verdicts are written — don't skip it.

**Occasionally:** `/judge-claims` when predictions come due.

---

## What's in it right now

_As of 11 Sep 2026. These change constantly — read `ingest/store/` for truth._

```
178 companies       38 Core · 13 Watch · 127 Radar
656 captured posts  464 his · 192 my own research
1,330 arguments     what he actually argued, per post per company
21 verdicts         my call on each name that matters
80 memos            the written-up version of those calls
77 predictions      3 judged · 13 untestable · 61 open
16 calls            12 open · 4 closed (1 win · 2 losses · 1 wash)
```

---

## Why it's built this way

**One analyst is not enough.** He is long-only, so the data has no bear case
by construction. That's why three expert reviewers — a chip expert, a numbers
person and a portfolio manager — research the shortlist before each weekly
review, and why every finding they can't tie to a real filing is marked
unverified and counts for zero.

**Counting mentions tells you nothing.** Testing showed almost no relationship
between how often he names a stock and how it performs. So the desk now reads
*what he argued* about each company in each post, not how often he typed the
ticker. NVIDIA: 81 mentions, 12 actual arguments. Sivers: 125 and 115.

**Being wrong has to be recorded.** Every call gets an entry price and a
benchmark. Every prediction gets a deadline. And "couldn't be tested" is a
real outcome, reported next to the hit rate — when this was first run on the
analyst's predictions, **13 of 25 were untestable.**

**Numbers must be real or clearly labelled.** Revenue comes from SEC filings.
AI-exposure percentages are judgements, and every one displays a chip saying
whether it came from a company's own disclosure or is an estimate.

---

## Where things live

```
desk.html, index.html, memo.html, vault.html, performance.html   the pages
shared/          the shared look and helpers (2 files only)
data.js          everything the pages read — GENERATED, never edit by hand
ingest/          the Python backend that rebuilds data.js
ingest/store/    the real data (JSON files) — this is the source of truth
docs/            guides and reference
```

---

## Docs, in the order worth reading

| Doc | Read it when |
|---|---|
| **[docs/GUIDE.md](docs/GUIDE.md)** | Something isn't working, or you forgot how to run a thing |
| **[docs/ROADMAP.md](docs/ROADMAP.md)** | You want to know what's done and what's next |
| **[CLAUDE.md](CLAUDE.md)** | Claude reads this first every session — the build rules |
| **[PROJECT.md](PROJECT.md)** | The "read what he argued, not how often" rework |
| **[docs/X-CONTENT.md](docs/X-CONTENT.md)** | The posting-on-X idea (draft, not built) |
| **[docs/WATCHER.md](docs/WATCHER.md)** | The thing that finds his posts automatically |
| **[docs/PRD.md](docs/PRD.md)** | What this was originally for |
| **[docs/DESIGN.md](docs/DESIGN.md)** | Colours, fonts, spacing |

---

## Known problems

- **Recorded daily closes are stamped one day late.** Both price fetches run
  outside US market hours, so each row holds the previous session's close. The
  live prices are fine; only the saved history is shifted. Blocks the
  "what happened after he argued it" feature.
- **41 of 45 AI-exposure numbers are estimates**, not researched. They show an
  `est.` chip so they can't be mistaken for data.
- **The parser invents tickers from jargon** — `CW`, `NAND`, `UTC`, `DRAM` and
  ~300 others. Harmless but noisy.
