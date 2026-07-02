# Roadmap & Status — AI Infrastructure Explorer

_Last updated: 2026-07-02. Living document — update as things ship or change._

---

## Current snapshot

| | |
|---|---|
| Tickers tracked | ~83 (check `ingest/store/tickers.json` for exact) |
| Categorized layers | 9 (`photonics, memory, fabs, neoclouds, materials, networking, glass, robotics, accelerators`) |
| Unsorted (needs triage) | ~63 — see "Classify unsorted tickers" below |
| Theses ingested | ~70 |
| Brain digests | Synthesized for every category with theses (networking & glass are empty — no theses reference their tickers yet) |
| GitHub repo | Public — github.com/nainaii1/ai-infrastructure-explorer, branch `feat/brain-synthesis` |

Counts drift constantly as posts get ingested — treat this table as
"roughly here," and trust `ingest/store/*.json` / `git log` over this file
when they disagree.

---

## What's built

| Area | Status | Notes |
|---|---|---|
| Supply Chain Map — flow-pipeline layout | ✅ Done | 9 layers grouped into Demand/Chip/Supply zones with a flow rail; click-to-filter + expandable "what to watch" investor angle per layer |
| Watchlist tab (sortable table, 7D/1M, rating) | ✅ Done | Ratings persist to localStorage |
| Yahoo price fetcher (`fetch_prices.py`) | ✅ Done | Run via button in app or CLI |
| Local server for price fetch (`serve.py`) | ✅ Done | `python3 ingest/serve.py` → port 8765 |
| Telegram ingest bot (`bot.py`) | ✅ Done | Auto-fetches tweet text from URL-only messages |
| fxtwitter auto-fetch (`fetcher.py`) | ✅ Done | Resolves x.com URLs → full tweet text, no API key |
| Thesis tab (feed of ingested ideas) | ✅ Done | Date, conviction badge, source link, ticker chips |
| **Brain tab (AI theme digests)** | ✅ Done | `synthesize.py` groups theses by category, one narrative digest per theme. **No live Anthropic API key currently** — refresh manually by asking Claude Code (see `docs/GUIDE.md` §3) |
| Ticker triage CLI (`review.py`) | ✅ Done | `classify` / `approve` / `reject` for auto-added `unsorted` tickers — not yet documented in GUIDE.md (todo below) |
| Telegram setup guide | ✅ Done | `docs/TELEGRAM_SETUP.md` → `docs/GUIDE.md` |
| GitHub repo (public) | ✅ Done | github.com/nainaii1/ai-infrastructure-explorer |

---

## Current issues to fix

### HIGH — affects daily use

**1. Bot must be started from the project directory**
Every terminal session requires `cd ~/Documents/Claude/ai-supply-desk` before
running any Python script. Easy to forget.
- Fix: Create a `start_bot.sh` convenience script (one file, runs everything). Still not built.

**2. `ingest/.env` iCloud sync**
If the project folder is under iCloud Drive sync, `.env` can occasionally
show a sync conflict/error in Finder, which can make the bot fail to read
the token.
- Workaround: `export TELEGRAM_BOT_TOKEN=...` directly in the terminal session,
  or move the project out of iCloud sync / mark it "not synced."

### MEDIUM — affects ingest quality

**3. `review.py classify` isn't documented in `docs/GUIDE.md`**
The triage CLI exists and works (`python3 ingest/review.py classify SYM
--category photonics --company "..." ...`), and ~63 tickers currently sit in
`unsorted` waiting for it — but a fresh session/new operator has to find
`ingest/README.md` to learn the command. Add a short section to
`docs/GUIDE.md`. *(Addressed in this pass — see GUIDE.md §5.)*

**4. SSL certificate verification globally disabled in `bot.py`**
`bot.py` has a blanket SSL bypass (`ssl._create_default_https_context =
ssl._create_unverified_context`) added as a workaround for macOS Python
3.14's missing CA bundle. Works but skips cert verification on all outbound
requests.
- Proper fix: reuse the `_ssl_context()` approach already in `fetch_prices.py`
  (tries system CA → `/etc/ssl/cert.pem` → certifi in order). Still open.
- Risk: Low for a personal local tool; worth fixing before sharing the machine.

### LOW — polish

**5. Watchlist sticky table header has no z-index** — on some browsers, row
content can bleed through the header on scroll.

**6. Conviction badge label "Note" is ambiguous** — posts without
high-conviction language show "Note." Could be clearer as "Normal" or left
unlabeled.

---

## Discussed but not yet built

### 1. Self-serve Brain refresh without a paid API key

Right now the Brain either needs `ANTHROPIC_API_KEY` in `ingest/.env`, or a
manual pass (ask Claude Code to "refresh the brain," which reads
`theses.json`, authors digests, and runs them through
`synthesize.synthesize_all()` so the output shape matches a real API run).
Worth exploring a cheaper/free backend (e.g. Gemini) as an alternative to
requiring a paid Anthropic subscription for a fully automated refresh.

### 2. Make.com auto-forward (optional alternative to manual forwarding)

Make.com free tier (1,000 ops/month) can auto-post @aleabitoreddit tweets to
your Telegram bot via Make.com's built-in X connection — no manual
forwarding. Worth trying if X integration still works post-API changes.
- Status: Not set up. User is doing manual forwarding for now.

### 3. Historical backfill (last 6 months)

User wants to capture @aleabitoreddit's posts going back ~6 months. Priority
is recent posts first, then add older posts gradually over time.
- Process: Same as current — send the x.com URL to the bot (auto-fetches
  text), or paste text + URL together.
- No time pressure. Add a few at a time as convenient.

### 4. Design brief items not yet addressed

From an earlier design review session:
- Watchlist empty state (no prices yet → better first-use guidance)
- Dim empty layer bands (layers with 0 tickers should look visually quieter)

---

## Guides available

| Guide | Location | Covers |
|---|---|---|
| Operating guide + FAQ | `docs/GUIDE.md` | Bot setup, Brain refresh, price fetch, troubleshooting, ticker triage |
| Telegram bot setup | `docs/TELEGRAM_SETUP.md` | Pointer into GUIDE.md |
| Product requirements | `docs/PRD.md` | Problem, jobs, success criteria, architecture, data model |
| Engineering rules + current status | `CLAUDE.md` | Build constraints, design system, data schema — **read this first in a new session** |
| Ingest backend reference | `ingest/README.md` | Pipeline file-by-file, triage commands, security notes |

---

## Build order (recommended, next up first)

1. **Create `start_bot.sh`** — one script: cd + export + launch bot.
2. **Fix SSL bypass in `bot.py`** — swap the global patch for the
   `_ssl_context()` pattern already in `fetch_prices.py`.
3. **Reduce the `unsorted` backlog** — triage with `review.py classify`
   (~63 tickers currently waiting).
4. **Evaluate a self-serve Brain backend** that doesn't need a paid API key.
5. **Make.com setup** — when manual forwarding becomes a chore.
6. **Watchlist/empty-state polish** — items 5–6 above under "Current issues" and item 4 under "Discussed but not yet built."

---

## Architecture reminder

```
You open index.html (file://, no server needed)
       ↓
data.js loaded first (window.AIE_DATA — single source of truth)
       ↓
App reads tickers / theses / settings from localStorage

─── Ingest pipeline (runs separately, locally) ──────────────────
  Telegram bot  →  bot.py
                      ↓
                  fetcher.py  (fxtwitter, URL-only messages)
                      ↓
                  parser.py  (extract tickers, conviction)
                      ↓
                  store/*.json  (theses, tickers, priorities)
                      ↓          ↘
                      ↓        synthesize.py (Brain — needs API key or manual run)
                      ↓          ↙
                  generate_data_js.py  →  data.js
─────────────────────────────────────────────────────────────────
       ↓
Hard refresh app → data.js re-seeded into localStorage → UI updates
```
