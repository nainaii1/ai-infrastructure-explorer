# Operating Guide & FAQ

Everything you need to run this project day-to-day — and why the Telegram bot
sometimes "doesn't reply." If you read one doc, read this one.

---

## The one mental model that explains everything

This project has **two halves**, and they run in completely different places:

| Half | What it is | Where it runs | When it's "on" |
|---|---|---|---|
| **The app** (`index.html` + `data.js`) | The website you look at | Your browser | Always — just open the file |
| **The backend** (`ingest/*.py`) | Scripts that *update* the data | Your Mac's terminal | **Only while you run them** |

**The Telegram bot is part of the backend.** It is **not** a cloud service.
It only answers messages **while `python3 ingest/bot.py` is actively running in
a terminal on your Mac.** Close the terminal → the bot goes silent. That is the
single most common point of confusion (see the FAQ).

Nothing the backend does reaches the browser directly — every script just
rewrites `data.js`, and the app reads `data.js` when you open/refresh it.

---

## 1. Just view the app

Double-click **`index.html`**. It works fully offline (no server, no internet).
Four tabs:

- **Supply Chain Map** — click a layer to filter the company cards.
- **Watchlist** — sortable table of every ticker (price, 7D/1M %, your rating).
- **Thesis** — the raw feed of ideas captured from @aleabitoreddit.
- **Brain** — AI-synthesized digest of those ideas, one per theme, with
  drill-down to the source theses.

That's all you need for reading. The rest of this guide is about *updating* the data.

---

## 2. The Telegram bot (capture new ideas)

Forward a post from @aleabitoreddit to your bot and it becomes a thesis in the
app. **One-time setup (~5 min), then it only works while the bot is running.**

### Step 1 — Create the bot
1. In Telegram, search **@BotFather** (official, blue check).
2. Send `/newbot`. Give it a name (e.g. `AI Supply Desk`) and a username ending
   in `bot` (e.g. `aisupplydesk_bot`).
3. BotFather replies with a **token** like `1234567890:AAE-abc123…`. Copy it.
   **Treat it like a password.**

### Step 2 — Find your Telegram user id
1. Search **@userinfobot**, send it `/start`.
2. It replies with your numeric **Id** (e.g. `987654321`). Copy it.

### Step 3 — Put both in `ingest/.env`
Open `ingest/.env` in a text editor and fill in the two lines:
```
TELEGRAM_BOT_TOKEN=1234567890:AAE-abc123…
ALLOWED_TELEGRAM_USER_ID=987654321
```
(`ingest/.env` is gitignored — it is never committed or pushed.)

### Step 4 — Run the bot
From the project root, in a terminal:
```bash
set -a; . ./ingest/.env; set +a     # load the token into this terminal
python3 ingest/bot.py
```
You should see: `Bot polling. Only Telegram user id 987654321 is processed. Ctrl-C to stop.`
**Leave this terminal open.** The bot replies only while this is running.

### Step 5 — Use it
- **Forward** an @aleabitoreddit post to your bot, **or paste text** (include the
  `x.com/...` link so the thesis is sourced).
- The bot replies with a summary (ingested id, tickers added/queued) and rewrites
  `data.js`. Refresh the app to see it.
- **Stop** the bot with **Ctrl-C**. Your data is safe (saved before each rewrite).

> Only your user id is accepted; messages from anyone else are silently ignored.

---

## 3. The Brain (synthesize ideas into theme digests)

The Brain turns the raw theses into one digest per supply-chain theme. It needs
an LLM. Two ways:

- **Ask Claude Code** to "refresh the brain" — it reads the theses and rewrites
  `brain.json` + `data.js`. No API key, no cost beyond your Claude usage.
- **Run it yourself** (once a Gemini/Anthropic backend is wired in):
  ```bash
  python3 ingest/synthesize.py --dry-run   # preview grouping, no spend
  python3 ingest/synthesize.py             # real run → brain.json + data.js
  ```
  It auto-loads `ingest/.env`, so just put your key there first. `--only photonics,memory`
  refreshes specific themes without touching the others.

---

## 4. Weekly prices (Watchlist)

Browsers can't fetch Yahoo from `file://`, so prices use a tiny local server:
```bash
python3 ingest/serve.py        # then open http://localhost:8765/
```
Go to **Watchlist → Fetch prices**. It pulls Yahoo, computes 7D/1M %, and rewrites
`data.js`. Afterward, plain double-click shows the last-fetched prices.

---

## 5. Classify unsorted tickers

When the bot sees a `$CASHTAG` it doesn't recognize, it auto-adds the ticker
with `category: "unsorted"` and empty details — it shows in the app under
"Unsorted" with a gray badge until you classify it. Check how many are
waiting: **Supply Chain Map → Unsorted layer** (shows the count), or
`python3 ingest/review.py list`.

Classify one from the terminal:
```bash
python3 ingest/review.py classify CCXI \
  --category robotics \
  --company "Agility Robotics" \
  --market US --exchange NASDAQ --tier Mid \
  --what "What the company does." \
  --why "Why it matters to the NVDA/AI supply chain."
```
`--category` must be one of the ids in `AIE_DATA.categories` (see `CLAUDE.md`
for the current list). This rewrites `tickers.json` **and** regenerates
`data.js` automatically — refresh the app to see it move out of Unsorted.

Not interested in a symbol? `python3 ingest/review.py reject SYM` removes it
from the store entirely.

---

## 6. The weekly desk review (tiers + Claude's verdicts)

Once a week, open Claude Code in this project and say **"run the weekly
review"** (it's a project skill: `.claude/skills/weekly-review/SKILL.md`).
In one pass it refreshes prices, re-tiers every ticker
(Core / Watch / Radar), refreshes Brain digests for themes with new theses,
and rewrites **Claude's desk verdicts** — a second opinion on each Core name
with a stance (`act / accumulate / watch / pass`), an execution suggestion,
and "what changes my mind", each citing the source theses.

Where it shows up in the app:
- **Watchlist** — tier filter chips (defaults to *Signal = Core + Watch*),
  a sortable **Desk** column, and a provenance line ("Desk verdicts reviewed
  \<date\>").
- **Supply Chain Map** — ticker cards get a tier badge and, for Core names,
  the full "Claude's desk view" block; Radar names are hidden behind a
  "Show N radar names" toggle.

Verdicts live in `ingest/store/verdicts.json` (the only store file the
review authors directly) and are capped at the **top 12–15 Core names** to
keep each weekly session cheap. Everything is regenerated into `data.js`
through the normal pipeline — never hand-edit `data.js`.

## 7. Backfill & auto-capture (getting posts in with less manual work)

**Backfill from your existing signal bots.** If you already follow
@aleabitoreddit alert bots on Telegram, just **forward their messages to
your ingest bot** — `bot.py` reads forwarded text exactly like a pasted
tweet, and URL-only forwards get auto-fetched via fxtwitter. Work backwards
through the signal bot's history a screen at a time; duplicates are cheap to
ignore and the priority scorer is recency-weighted anyway.

**Why your bot can't auto-read those alert bots:** Telegram's Bot API
deliberately prevents bots from seeing other bots' messages, even in the
same group. So "add my bot to the alert channel and let it ingest
automatically" does not work. The two real options:

1. **Keep forwarding (recommended for now).** Zero code, ~seconds per post,
   and you stay the editorial filter for what enters the corpus.
2. **A userbot watcher (`ingest/watcher.py`, not built yet).** A
   [Telethon](https://docs.telethon.dev) script logged in as *your user
   account* (not a bot) can read the alert-bot chats you subscribe to and
   pipe new posts into the same ingest path. This is the true
   automation path — roadmap item; ask Claude Code to build it when
   forwarding becomes a chore. Caveats: needs a Telegram API id/hash from
   my.telegram.org stored in `ingest/.env`, and account-level automation
   sits in a greyer zone of Telegram's ToS than bots do.

**Alerts when he tweets:** you already have this — your existing signal
bots *are* the alert layer. Building our own watcher on X itself would need
paid API access or scraping; not worth it while the signal bots work.

---

## FAQ / Troubleshooting

### "I sent a message to the bot and nothing replied."
The #1 cause: **the bot isn't running.** It's not a cloud bot — it only answers
while `python3 ingest/bot.py` is open in a terminal. Check, in order:
1. **Is the bot running?** Open a terminal: `pgrep -fl bot.py`. Nothing listed →
   it's off. Start it (Section 2, Step 4).
2. **Is the token set?** Open `ingest/.env` — `TELEGRAM_BOT_TOKEN` and
   `ALLOWED_TELEGRAM_USER_ID` must both be filled in (not blank). Blank token →
   the bot exits immediately with an error.
3. **Are you messaging from the right account?** Only the `ALLOWED_TELEGRAM_USER_ID`
   account is accepted; everyone else is ignored with no reply.
4. **Did you load the env first?** You must run `set -a; . ./ingest/.env; set +a`
   in the *same* terminal before `python3 ingest/bot.py` (the bot reads the token
   from the environment).

### "poll error: HTTP Error 404: Not Found"
Your `TELEGRAM_BOT_TOKEN` is wrong or revoked. Telegram returns 404 when the token
in the request is invalid. Re-copy the token from @BotFather (or `/revoke` and make
a new one), update `ingest/.env`, and restart the bot.

### "The bot stopped working after a while."
The terminal session ended (closed window, sleep, logout). The bot only runs while
that terminal is open. Restart it. (To keep it always-on, that's a separate setup —
ask Claude Code about a macOS `launchd` service.)

### "The bot replied, but the app didn't change."
Refresh the browser (or re-open `index.html`). The bot rewrites `data.js`; the app
only reads it on load. If the bot reply showed an error, check the terminal output.

### "Prices won't update / Fetch prices does nothing."
Prices need the local server — run `python3 ingest/serve.py` and use the app at
`http://localhost:8765/` (not the double-clicked `file://` version) when fetching.

### "The Brain tab says 'No brain digests yet.'"
The Brain hasn't been generated. Ask Claude Code to "refresh the brain," or run
`python3 ingest/synthesize.py` (needs an API key in `ingest/.env`).

### "Do I need to `pip install` anything?"
Only for the Brain (`synthesize.py` needs `anthropic`): `pip install -r ingest/requirements.txt`.
The bot, prices, and data generation use the Python standard library only.

### "Is my data safe / private?"
`ingest/.env` (your token + keys) is gitignored and never committed. The app and
data are local. The Brain step sends thesis text to the LLM provider you configure.

---

## Where things live
See [README.md](../README.md) for the full file map. Quick version:
`index.html` + `data.js` = the app · `ingest/` = the Python backend ·
`docs/` = these docs.
