# Roadmap & Status — AI Infrastructure Explorer

_Last updated: 2026-07-03. Living document — update as things ship or change._

---

## Current snapshot

| | |
|---|---|
| Tickers tracked | ~86 — now tiered: **22 Core / 26 Watch / 38 Radar** (check `data.js` tiers for exact) |
| Categorized layers | 10 (`photonics, memory, fabs, neoclouds, materials, networking, glass, robotics, accelerators, hyperscalers`) |
| Unsorted (needs triage) | ~59 — but **all remaining unsorted are Watch/Radar tier** (every Core name is classified); Radar-tier triage is low priority by design |
| Theses ingested | ~89 |
| Brain digests | 9 themes synthesized, refreshed 2026-07-03 (manual Claude Code pass, 22 new theses since prior run) |
| **Desk verdicts** | **13 Core names** with Claude's stance + execution note (`ingest/store/verdicts.json`, reviewed 2026-07-03) |
| GitHub repo | Public — github.com/nainaii1/ai-infrastructure-explorer, branch `feat/brain-synthesis` |

Counts drift constantly as posts get ingested — trust `ingest/store/*.json` /
`git log` over this file when they disagree.

---

## The operating loop (v5 — this is the product now)

```
He tweets → you forward to the Telegram bot (or backfill from signal bots)
     → theses.json grows, tickers auto-added
     → scorer tiers everything: Core / Watch / Radar   (noise ignored by default)
     → weekly: "run the weekly review" in Claude Code
         → prices refreshed, Brain digests updated,
           Claude's desk verdict per Core name:
           stance (act/accumulate/watch/pass) + execution + what-changes-my-mind
     → you decide, using his conviction AND Claude's second opinion
```

---

## What's built

| Area | Status | Notes |
|---|---|---|
| **v6 "Field Guide" redesign** | ✅ Done (2026-07-03) | Tabs → one chaptered scroll (hero prologue + 4 numbered chapters + colophon); frosted-glass capsule nav w/ sliding pill + scrollspy (bottom-floating on mobile); cool cleanroom palette; spring motion tokens; scroll reveals; unified drill-down animation; glossary strip (`AIE_DATA.glossary` from `base.json`); "New this week" strip; heat-aware cross-section legend; all DESIGN.md §7 inconsistencies resolved |
| Supply Chain Map — flow-pipeline layout | ✅ Done | 10 layers incl. new **Hyperscalers** demand layer; click-to-filter; investor angle per layer |
| **Conviction tiers (Core/Watch/Radar)** | ✅ Done (2026-07-03) | `scorer.assign_tiers()` — mentions + conviction-language thresholds; stamped on every ticker; unit-tested |
| **Map/Watchlist default to Signal (Core+Watch)** | ✅ Done (2026-07-03) | Radar (one-off mentions) hidden behind a "Show N radar names" toggle / Radar chip |
| **Desk verdicts (Claude's weekly view)** | ✅ Done (2026-07-03) | `store/verdicts.json` → `AIE_DATA.desk`, stamped per ticker; Watchlist "Desk" column + full verdict block on Core ticker cards |
| **`/weekly-review` project skill** | ✅ Done (2026-07-03) | `.claude/skills/weekly-review/SKILL.md` — the whole weekly pass in one command, no API key needed |
| Watchlist tab (sortable table, 7D/1M, rating) | ✅ Done | + tier chips, Desk column, review provenance line |
| Yahoo price fetcher / local server | ✅ Done | `fetch_prices.py` / `serve.py` (port 8765) |
| Telegram ingest bot + fxtwitter auto-fetch | ✅ Done | `bot.py` / `fetcher.py` |
| Thesis tab | ✅ Done | Date, conviction badge, source link, ticker chips |
| Brain tab (per-theme AI digests) | ✅ Done | `synthesize.py`; refreshed via the weekly review when no API key |
| Ticker triage CLI (`review.py`) | ✅ Done | Documented in GUIDE.md §5 |
| Backfill & auto-capture guide | ✅ Done (2026-07-03) | GUIDE.md §7 — forward from existing signal bots; Telethon watcher documented as the future automation path |

---

## Current issues to fix

### HIGH — affects daily use

**1. Bot must be started from the project directory**
Create a `start_bot.sh` convenience script (cd + env + launch). Still not built.

**2. `ingest/.env` iCloud sync**
`.env` can hit sync conflicts under iCloud Drive. Workaround: `export
TELEGRAM_BOT_TOKEN=...` in-session, or exclude the folder from sync.

### MEDIUM — affects ingest quality

**3. SSL certificate verification globally disabled in `bot.py`**
Swap the blanket `ssl._create_unverified_context` for the `_ssl_context()`
pattern already in `fetch_prices.py`. Still open.

**4. Mention-count inflation from list-posts**
The scorer counts a ticker named in a 10-ticker list-post the same as a
dedicated thesis (this is why MRVL/TSLA reached Core; the desk verdicts
push back manually). Idea: weight mentions by 1/√(tickers in post) in
`scorer.py`. Not built.

### LOW — polish

**5. Watchlist sticky header z-index** — rows can bleed through on scroll.
**6. "Note" conviction badge is ambiguous** — rename to "Normal" or drop.
**7. Desk verdict on watchlist is tooltip-only** — consider an expandable
row so verdicts are readable without hovering (mobile especially).

---

## Next up (build order)

1. **Backfill via signal-bot forwarding** — operator task, no code: forward
   the existing @aleabitoreddit alert-bot history into the ingest bot
   (GUIDE.md §7). Priority: most recent months first.
2. **First real `/weekly-review` cycle** (next week) — proves the loop and
   produces the first stance *changes*, which is where the value is.
3. **`start_bot.sh`** + **SSL fix in `bot.py`** (issues 1 & 3).
4. **List-post mention weighting** in `scorer.py` (issue 4) — makes tiers
   trustworthy enough to stop second-guessing counts.
5. **Telethon watcher (`ingest/watcher.py`)** — full auto-capture from the
   signal-bot chats; build when manual forwarding becomes the bottleneck.
6. **Radar-tier triage, gradually** — `review.py classify` a few per week;
   no urgency since Radar is hidden by default.
7. **Watchlist verdict expandable rows** (issue 7).

---

## Discussed but not yet built

- **Signal Digest** (full design spec, ready to plan+implement) — replaces the
  raw thesis feed in the Evidence chapter with short, Claude-authored
  per-ticker digests (AI Signal Watch style: one overview paragraph + one
  stance line per ticker), generated on demand from theses ingested since the
  last digest. Raw posts become an expandable "receipts" drill-down under
  each ticker line, reusing the same grid animation as the Brain's source
  reveal. Tweet discovery stays fully manual — Telegram bots can't read
  other bots' channel messages, so forwarding is unchanged; only the
  *authoring* step is new (mirrors the no-API-key `/weekly-review` pattern).
  See `docs/superpowers/specs/2026-07-03-signal-digest-design.md` for the
  full schema (`ingest/store/signal_digests.json`), the `ingest/digest.py`
  module design, and the rendering plan.
- **"Since mention" receipts** (from reviewing semiconstocks.com — the Serenity
  tracker of the same analyst): stamp a baseline price in `bot.py` at
  thesis-capture time so future theses can show % return since the call.
  Impossible retroactively — the sooner it lands, the sooner receipts accrue.
- **Rotation arc**: a "where the analyst's attention is moving" phase timeline
  in the Synthesis chapter, driven by the Brain's mention-trend data.

- **Self-serve Brain/verdict refresh via API key** — `synthesize.py` already
  supports it; verdicts could get the same `call_fn` treatment for a
  fully-unattended weekly cron once a paid key exists.
- **Make.com auto-forward** — superseded in spirit by the Telethon watcher
  plan (item 5 above); keep as fallback.
- **Real price history sparklines** — replace the synthetic "Trend (sample)"
  lines once `fetch_prices.py` stores dailies.

---

## Guides available

| Guide | Location | Covers |
|---|---|---|
| Operating guide + FAQ | `docs/GUIDE.md` | Bot setup, Brain refresh, prices, triage, **weekly review (§6)**, **backfill/auto-capture (§7)** |
| Weekly review procedure | `.claude/skills/weekly-review/SKILL.md` | The exact steps Claude Code runs each week |
| Product requirements | `docs/PRD.md` | Problem, jobs, success criteria, architecture, data model |
| Design system reference | `docs/DESIGN.md` | Tokens, components, states |
| Engineering rules + status | `CLAUDE.md` | **Read first in a new session** |
| Ingest backend reference | `ingest/README.md` | Pipeline file-by-file |

---

## Architecture reminder

```
You open index.html (file://, no server needed)
       ↓
data.js loaded first (window.AIE_DATA — single source of truth)
       ↓
App reads tickers / theses / settings from localStorage
(tiers + desk verdicts arrive stamped on tickers, radar hidden by default)

─── Ingest pipeline (runs separately, locally) ──────────────────
  Telegram bot  →  bot.py → fetcher.py → parser.py
                      ↓
                  store/*.json  (theses, tickers, pending)
                      ↓
                  scorer.py  (priorities + Core/Watch/Radar tiers)
                      ↓          ↘
                      ↓        synthesize.py  (Brain — per-theme digests)
                      ↓        verdicts.json  (Desk — Claude's weekly per-name view)
                      ↓          ↙
                  generate_data_js.py  →  data.js
─────────────────────────────────────────────────────────────────
       ↓
Hard refresh app → data.js re-seeded into localStorage → UI updates

Weekly: open Claude Code → "run the weekly review" → the right side of
this diagram executes end-to-end.
```
