# ingest/ — Telegram → data.js pipeline

Backend tooling that turns posts by **@aleabitoreddit** into the product's
`data.js`. The Twitter API is blocked, so instead of scraping X we use
**Telegram** (open, reliable Bot API) as the inbox: you forward each post to a
bot, and this pipeline appends a **thesis**, auto-grows the **ticker** set, and
recomputes a **priority** ranking of what the author focuses on.

This directory is **dev tooling** — it is never loaded by the browser. The app
stays the two-file, offline, double-clickable `index.html` + `data.js`.

## How it flows
```
@aleabitoreddit posts → you Forward to your Telegram bot
  → bot.py reads it (Bot API)  → parser.py extracts text/url/date/tickers
  → store/*.json updated        → scorer.py recomputes priority
  → generate_data_js.py rewrites ../data.js  → app shows it (version re-seed)
```

## Files
- `bot.py` — Telegram long-poll listener + the shared `ingest_message()` core. Also a `--text` mode for local testing without Telegram.
- `parser.py` — text → thesis + ticker detection (high-confidence `$CASHTAG`/known symbol vs low-confidence bareword).
- `scorer.py` — composite priority: `recency_weighted_mentions * (1 + 0.5 * conviction_hits)`.
- `generate_data_js.py` — renders `../data.js` from the store via `json.dumps` (injection-safe).
- `review.py` — triage CLI: classify auto-added `unsorted` tickers, approve/reject queued candidates.
- `store/` — source of truth: `base.json`, `tickers.json`, `theses.json`, `pending_tickers.json`.
- `tests/` — `unittest` suite (no pytest needed).

## Requirements
Core pipeline uses the **Python 3 standard library only** — nothing to install.
(`requirements.txt` lists an optional `anthropic` for Claude enrichment in review.)

## Setup
1. In Telegram, message **@BotFather** → `/newbot` → copy the token.
2. Message **@userinfobot** to get your numeric user id.
3. `cp .env.example .env` and fill `TELEGRAM_BOT_TOKEN` + `ALLOWED_TELEGRAM_USER_ID`.
4. Load env and run the bot:
   ```bash
   set -a; . ./.env; set +a
   python3 bot.py
   ```
5. In Telegram, **forward** (or paste) an @aleabitoreddit post to your bot.
   It replies with what it ingested; `../data.js` updates; refresh the app.

## Test locally without Telegram
```bash
python3 bot.py --text '$AAOI is my top pick https://x.com/aleabitoreddit/status/123'
python3 -m unittest discover -s tests -v
python3 generate_data_js.py        # regenerate data.js from the store
```

## Triage
```bash
python3 review.py list
python3 review.py classify NVTS --category photonics --company "Navitas" --market US --exchange NASDAQ --tier Small
python3 review.py reject ZZZZ
```

## Security notes
- Bot token / API keys live in `.env` (gitignored), read from env only.
- The bot processes messages **only** from `ALLOWED_TELEGRAM_USER_ID`.
- All ingested text is serialized with `json.dumps` (and `<`/`>` escaped) when
  writing `data.js`, so a hostile post cannot inject script into the app.
