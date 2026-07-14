# Roadmap & Status — AI Infrastructure Explorer

_Last updated: 2026-07-15 (Phase 6 "Unpacked" rebrand shipped — v7 upgrade complete). Living document — update as things ship or change._

> **Private Coverage upgrade (v7) — ✅ all six phases shipped.** Multi-page split,
> memo-style coverage notes, Obsidian-style knowledge Vault + graph, minimal
> performance hooks, and the "Unpacked" cool rebrand. The authoritative **phase
> table + step-by-step prompt guide is [EXECUTION.md](EXECUTION.md)** — check the
> boxes there for live status.
> - **Phase 1 ✅ (2026-07-08)** — multi-page editorial foundation: `shared/theme.css`,
>   `shared/common.js` (`window.AIE`), `index.html` → `desk.html`, new front page.
> - **Phase 2 ✅ (2026-07-12)** — coverage memos (`memos.json` → `memo.html`, ledger, skills).
> - **Phase 3 ✅ (2026-07-12)** — knowledge Vault + graph (`vault.json`, index/page/graph views).
> - **Phase 4 ✅** — site-wide cross-linking (`AIE.linkForTicker`, `$TICK` / `[[wikilink]]` markup).
> - **Phase 5 ✅ (2026-07-12)** — performance hooks (`calls.json` + minimal page, greyed until 3+ calls).
> - **Phase 6 ✅ (2026-07-15)** — "Unpacked" cool rebrand (U1–U8): cool neutral-grey canvas,
>   geometric display type, ONE blue→violet brand gradient, true-black stage surfaces, data-owned
>   category icons, the weekly Focus card, Chapter 01 ticker-tile grid + expand-in-place, and the
>   docs/alias cleanup (`--serif` retired for `--display`).
>
> (This upgrade superseded the Signal Digest spec — coverage memos replaced it.)

---

## Current snapshot

| | |
|---|---|
| Tickers tracked | ~109 — now tiered: **23 Core / 21 Watch / 65 Radar** (check `data.js` tiers for exact) |
| Categorized layers | 10 (`photonics, memory, fabs, neoclouds, materials, networking, glass, robotics, accelerators, hyperscalers`) |
| Unsorted (needs triage) | ~10 Watch-tier names (CRCL, EWY, VPG, RKLB, NVTS, HOOD, SMTC, SPCX, DRAM) **+ 1 Core-tier name (RDDT)** still unsorted — RDDT doesn't cleanly fit any of the 10 categories (Reddit/AI-training-data play), left in triage rather than misclassified |
| Theses ingested | 170 |
| Brain digests | 10 themes; 8 re-synthesized 2026-07-06 (manual Claude Code pass, 90 new theses since prior run), materials/glass carried forward unchanged (no new theses) |
| **Desk verdicts** | **15 Core names** with Claude's stance + execution note (`ingest/store/verdicts.json`, reviewed 2026-07-06). Stance moves this pass: AAOI/LITE/AXTI watch→accumulate (SemiAnalysis photonics washout + Nomura InP price-hike confirmation), TSLA dropped out of Core (verdict removed), XFAB/AMZN/GFS added |
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

**4. Mention-count inflation from list-posts** ✅ FIXED (2026-07-03)
`scorer.py` now focus-weights each mention by `1/√(tickers-in-post)`, so a name
in a 12-ticker digest dump counts ~0.29 vs. 1.0 for a dedicated post. Tiers are
assigned on `weightedMentions`; raw `mentions` is kept for display. This
dropped Core from an inflated 35 back to a meaningful 21 after the backfill.

### NEW — biggest scroll problem (2026-07-03)

**Evidence chapter (03) is ~90,000px tall.** After the June-July backfill the
raw thesis feed is 154 full-text digest cards. This is the real "too long to
scroll" surface (the Watchlist, chapter 02, is now a tidy ~1,500px). The proper
fix is the **Signal Digest** feature (spec'd in
`docs/superpowers/specs/2026-07-03-signal-digest-design.md`) — replace the raw
feed with short per-ticker digests, raw posts behind a drill-down. Cheap
interim option if Signal Digest isn't built soon: line-clamp each `.th-text` to
~5 lines with a "show full" expander (reuses the grid drill-down).

### LOW — polish

**5. Watchlist sticky header z-index** ✅ RESOLVED (2026-07-03) — the Watchlist
now opens on Core with natural page flow (no nested scroll / sticky header), so
the bleed-through issue is gone.
**6. "Note" conviction badge is ambiguous** — rename to "Normal" or drop.
**7. Desk verdict on watchlist is tooltip-only** — consider an expandable
row so verdicts are readable without hovering (mobile especially).

### Decisions taken (2026-07-03) — deliberate non-actions

**No "Power / 800V DC" category (yet).** Names like NVTS, BE, FCEL, EOS, VRT
recur but mostly as *followers'* recommendations the analyst explicitly
disclaims ("these are follower recommendations, not my own") — thin personal
conviction. Adding an 11th map layer for a weak theme would dilute the map's
honesty. Revisit if he posts dedicated 800V-DC conviction; the names stay
radar/unsorted until then.

**Foreign / numeric-symbol names are intentionally not tracked.** Recurring
names like LeaderDrive (688017), Foosung (093370), Etron, Win Semi, Ayar,
O-Net, Shunsin, VisEra live only in thesis prose. They're mostly
untradeable-from-a-US-brokerage (Korea/Taiwan/China listings) or private
companies — promoting them to tracked ticker cards would add noise to a
US-retail Watchlist/Map without actionable value. The prose context is
preserved in the theses; the `parser.py` cashtag regex stays letter-only by
design.

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
