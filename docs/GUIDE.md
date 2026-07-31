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

## Your routine, start to finish

If you only remember one page of this doc, remember this one. Three of the four
things below are automatic or take seconds.

### Every day — nothing, unless he posts (10 seconds)

Forward his post to your Telegram bot. That's it. The bot saves it and updates
the site by itself.

**The bot only works while it's running on your Mac.** It is not a cloud
service. If it stops replying, double-click **`desk.command`** → option **1**.

> ⚠️ **Restart the bot after anything changes in `ingest/`.** A bot left
> running holds an old copy of the code in memory. There's now a guard that
> makes it refuse to save rather than corrupt your data — but "refuse to save"
> looks like "the bot ignored me". If Claude Code has been working on this
> project, restart the bot before you next forward anything.

### Prices — automatic, nothing to do

A scheduled job refreshes prices twice a day. If you want them *right now*:
`desk.command` → option **2**.

### Once a week — three commands, in this order

Open Claude Code in this project and type them one at a time. Each one finishes
before you start the next.

| # | Type this | What it does | Roughly |
|---|---|---|---|
| 1 | `pre-review` | Three reviewers go and research the top names and file what they find, so the review below has a bear case in front of it | 10–20 min |
| 2 | `weekly review` | Re-scores everything, updates the tiers, rewrites the desk's verdict on each Core name, refreshes the theme summaries | 15–30 min |
| 3 | `judge claims` | Checks any prediction whose deadline has passed | Usually seconds |

**The order matters for 1 and 2.** Run the review first and it writes its
verdicts having seen only his (bullish) posts. If you skip step 1, the review
tells you so at the top of its report, so you always know which kind you got.

**Step 3 will usually say "nothing is due" and stop.** That is correct — it
only does work when a deadline has actually arrived. The first one is
31 Dec 2026.

### Then look at the site

Double-click **`desk.html`**. Nothing you did above reaches the browser until
you open or refresh it.

### Occasionally, only if you want it

| Type this | What it does |
|---|---|
| `coverage-note SIVE` | Write or refresh the full research memo on one name |
| `vault-note sive` | Write the knowledge-base page for one name or theme |

---

## 1. Just view the app

Double-click **`index.html`**. It works fully offline (no server, no internet).
It's one long scrolling page with a floating nav bar to jump between four
chapters:

- **01 · The Map** — click a layer to filter the company cards.
- **02 · The Watchlist** — sortable table of every ticker (price, 7D/1M %,
  your rating). Opens narrowed to the highest-conviction names.
- **03 · The Evidence** — the raw feed of ideas captured from @aleabitoreddit.
  Only the 10 most recent show by default; older ones are one click away.
- **04 · The Synthesis** — AI-written digest of those ideas, one per theme,
  with drill-down to the source posts.

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
**The easy way (no terminal commands):** double-click **`desk.command`** in
the project folder and pick **1**. It loads `.env` and starts the bot for you.
**Leave that window open** — the bot replies only while it's running.

The same menu also does prices (**2**), the local server (**3**), and a
status check (**4** — is the bot up, how fresh are prices, what's awaiting
triage).

<details><summary>The manual way (what option 1 runs for you)</summary>

```bash
cd ~/Documents/Claude/ai-supply-desk
set -a; . ./ingest/.env; set +a     # load the token into this terminal
python3 ingest/bot.py
```
You should see: `Bot polling. Only Telegram user id 987654321 is processed. Ctrl-C to stop.`
</details>

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
- **Run it yourself with an API key** (added 18 Jul 2026):
  ```bash
  cd ~/Documents/Claude/ai-supply-desk
  python3 ingest/synthesize.py --dry-run   # preview grouping, no spend
  python3 ingest/synthesize.py             # real run → brain.json + data.js
  ```
  It auto-loads `ingest/.env` and picks the backend from what's filled in:
  1. `OPENROUTER_API_KEY` → **OpenRouter** (recommended: cheap, no SDK to
     install). Get a key at https://openrouter.ai/keys, put it in `ingest/.env`
     yourself, and optionally set `OPENROUTER_MODEL` to any model id from
     https://openrouter.ai/models (default: `nousresearch/hermes-4-405b` —
     check current pricing before a full run).
  2. `ANTHROPIC_API_KEY` → Anthropic (needs `pip install anthropic`).

  Either way the same guardrails run: the injection firewall around thesis
  text, and `validate_digest()` never trusting the model for ids, categories,
  or out-of-universe tickers. `--only photonics,memory` refreshes specific
  themes without touching the others. The Brain is the only thing the key is
  for — desk verdicts, memos, and vault notes stay with the weekly review.

---

## 4. Weekly prices (Watchlist)

> **Copying commands from this guide:** copy only the plain command lines
> below (e.g. `cd ~/Documents/Claude/ai-supply-desk`) — never the ` ``` `
> fence lines around them. If you paste a fence line into the terminal by
> accident, backticks trigger shell command substitution and can spawn a
> stuck-looking nested shell. Get out of it with `exit`, then try again with
> just the command line itself.

Browsers can't fetch price data from `file://`, so prices use a tiny local
server. Open Terminal and run:
```bash
cd ~/Documents/Claude/ai-supply-desk
python3 ingest/serve.py        # then open http://localhost:8765/
```
Go to **http://localhost:8765/** in your browser (not a double-clicked
`index.html`), scroll to **02 · The Watchlist**, and click **Fetch prices**. It
rewrites `data.js` with price / market cap / currency (and 7D/1M % when
available). Afterward, plain double-click shows the last-fetched prices.

**The data source (since 2026-07-16): the operator's Google Sheet.**
Yahoo/FMP fetching was retired — Yahoo rate-limited (HTTP 429) most runs.
Instead, a Google Sheet keeps every quote live via `GOOGLEFINANCE()`
formulas (Google refreshes them itself, ~20-min delayed), and
`ingest/fetch_prices.py` just downloads the sheet's CSV export in one
request — no API key, no rate limits.

- Sheet: https://docs.google.com/spreadsheets/d/1Zeqqq01H1KiSvJnNArm0kr2rcn-F3FV8uxYjjX8mihA
  (override with `PRICES_SHEET_URL` in `ingest/.env` if the sheet moves —
  use the `/export?format=csv` form of the URL).
- Expected columns: `Ticker` (must match the `ticker` field in
  `tickers.json`, e.g. `000660.KS`, `SOI.PA`), `GoogleFinanceSymbol`
  (what the formulas use, e.g. `KRX:000660`), `Price`, `MarketCap`, and
  optionally `Currency`, `Chg1W`, `Chg1M`, `Chg1Y` (baked into the site
  as 7D / 1M / 1Y %). Missing optional columns are simply skipped.
- Tickers not present in the sheet are reported in the run summary
  (`notInSheet`) and keep their last-known price — add a row to the sheet
  to start tracking them. `#N/A` cells are treated as "no data", never 0.

**Three ways to refresh (any of them, once or twice a day is plenty):**
1. **Automatic** — a launchd agent
   (`~/Library/LaunchAgents/com.aie.refresh-prices.plist`) runs the fetch
   daily at 09:00 and 21:00. One-time macOS permission needed: System
   Settings → Privacy & Security → Full Disk Access → add
   `/usr/bin/python3` (background jobs can't read ~/Documents otherwise).
   Log: `~/Library/Logs/aie-refresh-prices.log`.
2. **Double-click `refresh-prices.command`** in the project root.
3. The **Fetch prices** button (via `serve.py`, as above).

**Non-US tickers:** the sheet's `Ticker` column carries the suffixed
symbol (`.ST` Stockholm, `.PA` Paris, `.DE` Frankfurt, `.KS` Korea) so it
matches `tickers.json`, while `GoogleFinanceSymbol` uses Google's
exchange-prefix form (`STO:SIVE`, `EPA:SOI`, `ETR:LPK`, `KRX:000660`).
Prices stay in the listing's native currency — fill the `Currency` column
so the watchlist labels them correctly.

---

## 5. Classify unsorted tickers

When the bot sees a `$CASHTAG` it doesn't recognize, it auto-adds the ticker
with `category: "unsorted"` and empty details — it shows in the app under
"Unsorted" with a gray badge until you classify it. Check how many are
waiting: **Supply Chain Map → Unsorted layer** (shows the count), or
`python3 ingest/review.py list`.

Classify one from the terminal:
```bash
cd ~/Documents/Claude/ai-supply-desk
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

## 6. The second opinion (`/pre-review`)

**The problem this fixes.** Everything in this tool comes from one person. He
is long-only and bullish by temperament, so the store has no bear case and
nothing he hasn't looked at can ever get in. Reading his posts more carefully
does not fix that — the missing information simply isn't there.

**What a "seat" is.** Three reviewers, each being Claude with a different
instruction and permission to go and look things up on the web:

| Seat | The one question it has to answer |
|---|---|
| Semiconductor expert | Is the technical claim actually true? |
| Fundamental analyst | Do the numbers work? |
| Portfolio manager | Is this a good bet *at this price*? |

**A seat is not an expert.** Calling one "semiconductor expert" does not create
semiconductor expertise — it is the same model with a different brief. What the
structure buys you is three separate passes, so three different questions
genuinely get asked instead of one blurry one, and it is forced to go and find
outside facts. Never treat a finding as if a chip engineer reviewed it.

**How to run it.** Open Claude Code in this project and say **"pre-review"**
(or `/pre-review`). Do this **before** the weekly review, so the verdicts get
written with both sides on the table. It picks up to 12 names, researches each,
and writes what it finds into the thesis feed marked `research` so you can
always tell it apart from his posts.

**The rule that keeps it honest.** A finding has to cite a real primary source
— an SEC filing, an earnings-call transcript, company IR material. If it can't,
the finding is recorded as **unverified** and made worth exactly zero to every
number in the app. It still shows up in the brief so you can read it; it just
can't move a ranking. **That is the correct outcome, not a failure.** The
alternative is a model inventing a citation to look useful.

**Outside research can only ever lower a name, never raise it.** A seat cannot
promote a stock into Core, add to its mention count, or make it look like the
analyst talked about it. This is deliberate: the same model writes the desk
verdicts, and without that rule it could agree with itself three times and
manufacture conviction out of nothing.

## 7. The weekly desk review (tiers + Claude's verdicts)

Once a week, open Claude Code in this project and say **"run the weekly
review"** (it's a project skill: `.claude/skills/weekly-review/SKILL.md`).
**Run `/pre-review` first** (section 6) so the verdicts are written with a bear
case on the table rather than from his posts alone — the weekly review will say
so at the top of its report if you skipped it.
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

## 8. Keeping score (`/judge-claims`)

**What this is for.** Anyone can sound convincing. The only way to know whether
a source is worth following is to write down what they predicted, with a date,
and go back later to check. `ingest/store/claims.json` is that record, and the
**Claims** half of the Performance page is where you read it.

**Three things can happen to a claim:**

| Outcome | What it means |
|---|---|
| **Open** | Its date hasn't arrived yet. Nothing to do. |
| **Correct / Wrong** | The date came, someone checked, and there's a citation. |
| **Untestable** | Nothing could ever settle it either way. |

**"Untestable" is the interesting one.** "Sivers grows from a $1B company to
$10B+" has no date and no test — it can never be wrong, so it can never be
scored. Those claims are *recorded*, not thrown away, and the page always shows
what share of a source's talk falls into that bucket.

**Right now that share is 52% — 13 of the 25 claims captured so far.** Over
half of what this desk's only source says cannot be checked even generously
read. That is worth knowing, and it is the entire reason this ledger exists.

**How to run it.** Say **"judge claims"** (or `/judge-claims`) in Claude Code.
It only does work when a deadline has actually passed, so most weeks it will
tell you there's nothing due and stop. The weekly review also tells you when
claims have come ripe.

**Why the page sometimes refuses to show a percentage:**

- **"No judged claims yet"** — nothing has been checked. It deliberately does
  *not* say 0%, because zero would read as "always wrong", and no record is not
  a bad record.
- **"2 of 3 right"** — fewer than 20 judged claims, so you get raw counts. A
  percentage built on three data points looks like a track record and isn't one.
- A real hit rate appears only past 20 judged claims, and **always** with the
  untestable share printed next to it. A source who only ever says untestable
  things would otherwise never be wrong and would look flawless.

Nothing in this ledger moves any score or tier today. Letting a track record
feed back into the rankings is a later phase, deliberately held until there are
enough judged claims for it to mean anything.

## 9. Backfill & auto-capture (getting posts in with less manual work)

> **Superseded 30 Jul 2026 — read `docs/WATCHER.md` first.** New posts now find
> *you*: a headless browser reads the public X profile every 4 hours and sends
> anything new to Telegram with ✅ Ingest / ❌ Skip buttons at midnight and
> noon. It costs nothing and needs no API key or account. The manual-forwarding
> routine below still works and is still the fallback if X ever closes the
> logged-out view — but it is no longer the daily path.
>
> The conclusion at the end of this section — "building our own watcher on X
> itself would need paid API access or scraping; not worth it" — turned out to
> be **wrong**, which is why it got built. The logged-out profile page renders
> fine without any account.

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

### "The Synthesis chapter says 'No brain digests yet.'"
The summaries haven't been generated. Ask Claude Code to "refresh the brain," or run
`python3 ingest/synthesize.py` (needs an API key in `ingest/.env`).

### "The Performance page says 'No judged claims yet'. Is that a bug?"

No — it's the honest answer. A claim can only be judged once its deadline has
passed, and the earliest one in the ledger is **31 Dec 2026**. Until then there
is genuinely nothing to score. The page refuses to print "0%" for this, because
zero would read as "always wrong" when the truth is "not checked yet".

### "Why does it say 52% untestable? That seems harsh."

It's a count, not an opinion. Of the 25 claims captured from the analyst so
far, 13 have no date and no test attached — things like "this grows into a
$10B company" with no when and no threshold. Those can never be marked right
or wrong. The number sits next to the hit rate on purpose: without it, a source
who only ever says untestable things would look like they'd never been wrong.

### "A seat said something and it didn't change any ranking."

That's the design. Outside research can lower a name but never raise it, and a
finding with no citable source is recorded as *unverified* and made worth
exactly zero. You can still read it in the brief and on the ticker card — it
just isn't allowed to move the numbers. Without that rule, the same model that
writes the desk verdicts could agree with itself and manufacture conviction.

### "Do I have to run `/pre-review` before the weekly review?"

No, but you should. If you skip it, the weekly review says so at the top of its
report, so you always know whether you're reading a review that had a bear case
in front of it or one written from his posts alone.

### "Nothing appeared in the Claims section after I ran /pre-review."

Normal. Most findings and most posts contain no dated prediction at all, and
the tooling is explicitly told **not** to invent a deadline to make a vague
statement look testable. No claim is a real outcome, not a silent failure.

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
