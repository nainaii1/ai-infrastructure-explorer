# Roadmap & Status — AI Infrastructure Explorer

_Last updated: 2026-06-27. Living document — update as things ship or change._

---

## What's built

| Area | Status | Notes |
|---|---|---|
| Supply Chain Map (layer stack, click-to-filter) | ✅ Done | 9 layers, demand hub, ticker cards |
| Watchlist tab (sortable table, 7D/1M, rating) | ✅ Done | Ratings persist to localStorage |
| Yahoo price fetcher (`fetch_prices.py`) | ✅ Done | Run via button in app or CLI |
| Local server for price fetch (`serve.py`) | ✅ Done | `python3 ingest/serve.py` → port 8765 |
| Telegram ingest bot (`bot.py`) | ✅ Done | Auto-fetches tweet text from URL-only messages |
| fxtwitter auto-fetch (`fetcher.py`) | ✅ Done | Resolves x.com URLs → full tweet text, no API key |
| Thesis tab (feed of ingested ideas) | ✅ Done | Date, conviction badge, source link, ticker chips |
| Telegram setup guide | ✅ Done | `docs/TELEGRAM_SETUP.md` |
| GitHub repo (public) | ✅ Done | github.com/nainaii1/ai-infrastructure-explorer |

---

## Current issues to fix

### HIGH — affects daily use

**1. `ingest/.env` iCloud sync error**
The `.env` file shows a cloud error in Finder. iCloud tried to sync it and failed. This can cause the bot to fail reading the token.
- Fix: Move the project folder out of iCloud sync, or mark it as "not synced" in System Settings → iCloud Drive → Options.
- Workaround until fixed: Use `export TELEGRAM_BOT_TOKEN=...` directly in the terminal session.

**2. Bot must be started from the project directory**
Every terminal session requires `cd ~/Documents/Claude/ai-supply-desk` before running any Python script. Easy to forget.
- Fix: Create a `start_bot.sh` convenience script (one file, runs everything).

**3. `README.md` has a broken link**
`README.md` says "See [ingest/README.md](ingest/README.md)" — that file does not exist.
- Fix: Change the reference to `docs/TELEGRAM_SETUP.md`.

### MEDIUM — affects ingest quality

**4. Auto-added tickers land in "unsorted" with no UI to classify them**
When the bot sees a new ticker it does not recognize, it creates it with `category: "unsorted"`. These show in "All sectors" with a gray badge but cannot be reclassified inside the app.
- Fix needed: Either a CLI flow or a written guide explaining how to edit `tickers.json` and re-run `generate_data_js.py`.

**5. SSL certificate verification globally disabled in `bot.py`**
`bot.py` has a blanket SSL bypass (`ssl._create_default_https_context = ssl._create_unverified_context`) added as a workaround for macOS Python 3.14's missing CA bundle. Works but skips cert verification on all outbound requests.
- Proper fix: Use the same `_ssl_context()` approach from `fetch_prices.py` (tries system CA → `/etc/ssl/cert.pem` → certifi in order).
- Risk: Low for a personal local tool; worth fixing before sharing the machine.

### LOW — polish

**6. Watchlist sticky table header has no z-index** — on some browsers, row content can bleed through the header on scroll.

**7. Conviction badge label "Note" is ambiguous** — posts without high-conviction language show "Note". Could be clearer as "Normal" or left unlabeled.

---

## Discussed but not yet built

### 1. Brain synthesis — NEXT PRIORITY

Agreed design: `ingest/synthesize.py` reads `theses.json` → calls Claude API (Sonnet) → writes `synthesis.json` using an **incremental approach** (existing summary + new theses → updated summary). Cost stays flat forever regardless of corpus size.

Output per run:
- `current_view` — his thesis in one paragraph, right now
- `per_category` — bullish / neutral / cautious per supply chain layer
- `per_ticker` — conviction level + trajectory (rising / stable / cooling)
- `themes` — recurring ideas across posts (e.g. "HBM bottleneck", "1.6T optical timing")

UI: a pinned "Current View" card at the top of the Thesis tab. Updates each time you run `python3 ingest/synthesize.py` after ingesting new posts.

### 2. Make.com auto-forward (optional alternative to manual forwarding)

Make.com free tier (1,000 ops/month) can auto-post @aleabitoreddit tweets to your Telegram bot via Make.com's built-in X connection — no manual forwarding. Worth trying if X integration still works post-API changes.
- Status: Not set up. User is doing manual forwarding for now.

### 3. Historical backfill (last 6 months)

User wants to capture @aleabitoreddit's posts going back ~6 months. Priority is last 2 weeks first, then add older posts gradually over time.
- Process: Same as current — send the x.com URL to the bot (auto-fetches text), or paste text + URL together.
- No time pressure. Add a few at a time as convenient.

### 4. Design brief items not yet addressed

From the earlier design review session:
- **#2** — Watchlist empty state (no prices yet → better first-use guidance)
- **#4** — Dim empty layer bands (layers with 0 tickers should look visually quieter)

---

## Guides available

| Guide | Location | Covers |
|---|---|---|
| Telegram bot setup | `docs/TELEGRAM_SETUP.md` | BotFather, user ID, `.env`, run bot, test, troubleshoot |
| Product requirements | `docs/PRD.md` | Problem, jobs, success criteria, architecture |
| Engineering rules | `CLAUDE.md` | Build constraints, design system, data schema |

### Guides still needed

**`docs/DAILY_WORKFLOW.md`** — Step-by-step for a normal day:
1. Start the bot (right directory, env vars, `python3 ingest/bot.py`)
2. See a tweet → send URL or paste text + URL to the bot
3. Bot replies ✅ → hard refresh the app → check Thesis tab
4. Weekly: `python3 ingest/serve.py` → open localhost:8765 → Fetch prices
5. After synthesis is built: `python3 ingest/synthesize.py` → refresh → read Current View

**`docs/CLASSIFY_TICKERS.md`** — How to categorize auto-added "unsorted" tickers:
1. Open `ingest/store/tickers.json`
2. Find entries with `"category": "unsorted"`
3. Change `category` to the right layer id (photonics / memory / fabs / neoclouds / materials / networking / glass / robotics / accelerators)
4. Fill in `company`, `whatTheyDo`, `whyNVDA`, `marketCapTier`, `market`, `exchange`
5. Run `python3 ingest/generate_data_js.py`
6. Hard refresh the app

---

## Build order (recommended)

1. **Fix `README.md` broken link** — 2-minute edit
2. **Create `start_bot.sh`** — one script: cd + export + launch bot
3. **Build `synthesize.py` + Current View UI card** — the brain feature
4. **Write `docs/DAILY_WORKFLOW.md`** — document the full loop once synthesis is live
5. **Fix SSL bypass in `bot.py`** — swap global patch for the `_ssl_context()` pattern from `fetch_prices.py`
6. **Improve unsorted ticker handling** — UI or guided CLI flow
7. **Make.com setup** — when manual forwarding becomes a chore

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
                      ↓
                  generate_data_js.py  →  data.js
─────────────────────────────────────────────────────────────────
       ↓
Hard refresh app → data.js re-seeded into localStorage → UI updates
```
