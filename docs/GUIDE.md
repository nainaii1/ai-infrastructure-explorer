# Operating Guide & FAQ

Everything you need to run this project day-to-day — and why the Telegram bot
sometimes "doesn't reply." If you read one doc, read this one.

---

## The one mental model that explains everything

This project has **two halves**, and they run in completely different places:

| Half | What it is | Where it runs | When it's "on" |
|---|---|---|---|
| **The app** (`index.html` + `data.js`) | The website you look at | Your browser | Always — just open the file |
| **The backend** (`ingest/*.py`) | Scripts that *update* the data | Your Mac | Three scripts (bot, prices, X watcher) run automatically as launchd agents; everything else **only while you run it** |

**The Telegram bot is part of the backend.** It is **not** a cloud service —
but since 8 Aug 2026 it **is** always-on on your Mac: a launchd agent
(`com.aie.bot`) keeps `ingest/bot.py` running in the background, restarts it
if it crashes, and relaunches it at login. You don't need a terminal window
open for it. It only goes silent if your Mac is off/asleep, or if the agent
itself is unloaded (see the FAQ).

Nothing the backend does reaches the browser directly — every script just
rewrites `data.js`, and the app reads `data.js` when you open/refresh it.

---

## Your routine, start to finish

If you only remember one page of this doc, remember this one. Three of the four
things below are automatic or take seconds.

### Every day — nothing, unless he posts (10 seconds)

Forward his post to your Telegram bot. That's it. The bot saves it and updates
the site by itself.

**The bot runs automatically** as a launchd agent (`com.aie.bot`) — no need to
start it or keep a window open. If it stops replying, check
`launchctl list | grep com.aie.bot` (see the FAQ).

> ⚠️ **The bot needs a restart after Claude Code changes anything in
> `ingest/`.** A bot left running holds an old copy of the code in memory.
> There's a guard that makes it refuse to save rather than corrupt your data —
> but "refuse to save" looks like "the bot ignored me".
>
> **Just ask Claude to restart it** — it is one command and Claude should run
> it for you, not hand it to you. If you ever do want it yourself:
> ```bash
> launchctl kickstart -k gui/$(id -u)/com.aie.bot
> ```
> That kills and instantly relaunches it. **Do not use `pkill`** — launchd
> restarts the bot the moment you kill it, so `pkill` plus a manual start
> leaves you running two bots that fight over the same Telegram connection.

### Prices — automatic, nothing to do

A scheduled job refreshes prices twice a day. If you want them *right now*:
`desk.command` → option **2**.

### Whenever you have a view — the AI-exposure worklist

Say **"the worklist"** in chat. Claude shows which companies still need your
judgement on how much of them is genuinely AI, gives you the evidence, and
records your answer. Nothing is automatic here and nothing is invented — see
§11. Do one name or ten; stopping early is fine.

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

### Step 4 — Install the bot as a background service (one-time)
The bot runs as a **launchd agent** (`com.aie.bot`) — always on, no terminal
window to keep open, and it survives sleep/reboot/login. The plist lives in
the project at `com.aie.bot.plist`:

```bash
cd ~/Documents/Claude/ai-supply-desk
cp com.aie.bot.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.aie.bot.plist
```

That's it — it's running now (`RunAtLoad`) and will relaunch itself if it
ever exits (`KeepAlive`), including after a `launchctl kickstart -k` restart.
It loads `ingest/.env` itself, the same way the manual run below did, so
Step 3 above still applies unchanged.

Check it's up: `launchctl list | grep com.aie.bot` — a numeric PID in the
first column means running; `-` means it's not. Logs (stdout and stderr
together): `~/Library/Logs/aie-bot.log`.

<details><summary>Running it manually instead (only if you don't want the background service)</summary>

```bash
cd ~/Documents/Claude/ai-supply-desk
set -a; . ./ingest/.env; set +a     # load the token into this terminal
python3 ingest/bot.py
```
You should see: `Bot polling. Only Telegram user id 987654321 is processed. Ctrl-C to stop.`

**Never run this while the launchd agent is also loaded.** Telegram allows
only one poller per bot token — a second concurrent one causes both to fail
with `409 Conflict`. Unload the agent first
(`launchctl unload ~/Library/LaunchAgents/com.aie.bot.plist`) if you need to
run it by hand.
</details>

**`desk.command` option 1** ("Start the capture bot") also runs `bot.py`
directly in a terminal — it predates the launchd install and has the same
409-conflict risk if the agent is loaded. Leave it alone; use it only if
you've deliberately unloaded the agent. Options 2–4 (prices, server, status)
are unaffected and safe to use as normal.

### Step 5 — Use it
- **Forward** an @aleabitoreddit post to your bot, **or paste text** (include the
  `x.com/...` link so the thesis is sourced).
- The bot replies with a summary (ingested id, tickers added/queued) and rewrites
  `data.js`. Refresh the app to see it.
- **To stop it**, unload the agent rather than killing the process — a plain
  `kill` just gets relaunched by `KeepAlive`:
  ```bash
  launchctl unload ~/Library/LaunchAgents/com.aie.bot.plist
  ```
  Your data is safe either way (saved before each rewrite).

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
  as 7D / 1M / 1Y %) and `MarketCapUSD` (see below). Missing optional
  columns are simply skipped.
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

**`MarketCapUSD` — what makes the Mkt Cap column sortable.**
Market caps arrive in each listing's own currency, so ranking the raw
figure is arithmetically meaningless: SK Hynix reads ₩1,210T against
Apple's $4.9T and would sort to the top of any list. The watchlist
therefore leaves **Mkt Cap unsortable until this column exists**, and says
so in the header tooltip. Add the column and the sort arms itself on the
next refresh — no code change needed.

Add one column named exactly `MarketCapUSD`. **Check your own header row for
the actual column letters before pasting** — a formula written against the
wrong column silently returns blank for every row (`IFERROR` swallows the
type mismatch), which is exactly what happened the first time this was
tried. As of 2026-08-19 the sheet's columns are `Ticker`(A)
`GoogleFinanceSymbol`(B) `Price`(C) `MarketCap`(D) `Currency`(E) `Chg1W`(F)
`Chg1M`(G) `Chg1Y`(H) — confirm yours still match, then:

```
=IFERROR(
   IF($E2="USD", $D2,
   IF($E2="GBX", $D2/100*GOOGLEFINANCE("CURRENCY:GBPUSD"),
                 $D2*GOOGLEFINANCE("CURRENCY:"&$E2&"USD"))), "")
```

Three things that formula is doing deliberately:
- **USD rows short-circuit** rather than paying for a lookup that returns 1.
- **`GBX` is handled separately.** IQE is quoted in pence, and `GBX` is not
  an ISO currency code — `GOOGLEFINANCE("CURRENCY:GBXUSD")` errors. Convert
  via `GBP` and divide by 100.
- **`IFERROR(..., "")` leaves the cell blank** on any failure. A blank cell
  makes the field absent rather than zero, so a name with a broken rate
  sorts last instead of pretending to be worthless.

Currently in play: USD, EUR, KRW, SEK, CAD, CNY, GBX. The other six all
have working `CURRENCY:xxxUSD` pairs.

**`Chg1MUSD` — what makes returns comparable across markets.**
A percentage change from GOOGLEFINANCE is a **local-currency** return, so it
blends the stock with its currency. SIVE prices in SEK: part of its 1M move
is the krona, not the company. Putting that number beside a USD name's move
in the same chart or ranking is not a like-for-like comparison.

Add `Chg1WUSD` / `Chg1MUSD` / `Chg1YUSD` (any subset — each is optional and
independent). **Same warning as above: verify the column letters against
your own header row.** Using the 2026-08-19 layout (`Currency` in `E`,
`Chg1M` in `G`):

```
=IFERROR(
   IF($E2="USD", $G2,
      ((1+$G2/100) *
       GOOGLEFINANCE("CURRENCY:"&IF($E2="GBX","GBP",$E2)&"USD") /
       INDEX(GOOGLEFINANCE("CURRENCY:"&IF($E2="GBX","GBP",$E2)&"USD",
                           "price", TODAY()-30), 2, 2) - 1) * 100), "")
```

A quick way to check the formula actually worked before trusting it: put it
next to a plain-USD row (NVDA, AMD) first. `$E2="USD"` should short-circuit
to `=$G2` — if that cell comes back blank instead of matching Chg1M exactly,
the column letters are wrong, not the exchange-rate math.

The move is compounded, not added: a 10% stock gain with a 5% currency gain
is +15.5%, not +15%. `GBX` maps to `GBP` for the rate — the /100 pence
scaling cancels out in a ratio, so unlike `MarketCapUSD` there is no divide
here. Match the `TODAY()-30` offset to the window (`-7`, `-365`).

Until these columns exist, anything doing a cross-market comparison must
**say so and exclude the affected names** rather than pool them silently —
absent stays absent, and is never backfilled from the local figure.

*Why not Yahoo:* Yahoo's key-free endpoints were retired from this project
on 2026-07-16 after chronic HTTP 429s — that is the reason the sheet exists
at all. Reintroducing them for FX would reintroduce that failure. The sheet
already has GOOGLEFINANCE, costs no extra request (the CSV comes down in
one fetch either way), and keeps the rate fresh on Google's side.

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
automatically" does not work.

Manual forwarding is still fine — zero code, ~seconds per post, and you stay
the editorial filter for what enters the corpus. But you don't need it as
the daily path anymore: **the X watcher (`ingest/watcher.py`, done 2026-07-30)
finds new posts for you**, no forwarding required. See `docs/WATCHER.md` for
how it works and how to use it day to day.

---

## 10. Per-ticker views — reading what he argued, not counting mentions

`ingest/views.py` turns "SIVE: 113 mentions" into a dated list of what he
actually said about SIVE each time — bull or bear, why, any numbers, any
timing. One post routinely holds different stances on different tickers (a
17-ticker recap might be bullish on three names and neutral on the rest), so
this lives at the `(post, ticker)` level, not per post. Full rationale and the
live numbers are in `PROJECT.md` — this section is just how to run it.

**Why it's a manual two-step, not one command:** there's no paid API key on
this project (same reason `/pre-review` and the Brain use an injected
`call_fn`), so a Claude Code session does the reading itself.

```
python3 ingest/extract_views.py --status
```
Shows how many analyst posts still need a read, split into "all pending" and
"pending Core/Watch" (the ones actually worth reading first).

```
python3 ingest/extract_views.py --emit --limit 14 --core-only
```
Writes the next batch of unread posts to `ingest/store/.views_batch.json`.
Drop `--core-only` to include radar/unsorted names too; `--limit` controls
batch size (14 is a comfortable single-sitting read). Ask Claude Code to read
the batch and write an answers file — one JSON object keyed by thesis id, each
value `{"views": [{"ticker", "direction", "why", "numbers"?, "horizon"?}]}` —
save it under the scratchpad, not the repo.

```
python3 ingest/extract_views.py --apply /path/to/answers.json
```
Validates every answer through the same firewall the API path would use — a
ticker the post itself never mentioned is silently dropped, never smuggled in
— merges into `theses.json`, and regenerates `data.js`. Prints a summary:
applied count, bull/bear/neutral split, and how many claimed views got
dropped by validation (should normally be 0; a handful is fine and usually
means the original ticker-tagger missed a symbol in the post text — see
`PROJECT.md` for two confirmed examples).

Re-running `--emit` is idempotent — a post that already has `viewsExtractedAt`
is skipped, so batches never overlap and a partial pass is always safe to
resume.

**If an API key ever gets added** (`OPENROUTER_API_KEY` or
`ANTHROPIC_API_KEY` in `ingest/.env`), plain `python3 ingest/extract_views.py`
with no flags runs the whole remaining pass unattended, reusing
`synthesize.py`'s backend picker.

**What this does *not* do:** move any score, tier, or ranking. `scorer.py` is
untouched — views are additive metadata. Wiring `direction` into scoring is a
deliberate future step, not a side effect of running this; see PROJECT.md
"Scoring impact" before ever doing that.

---

## 11. Company numbers, and how much of each one is AI

Two things sit on every ticker card and every watchlist row you open, just
under what the analyst argued and just above your own call.

### Revenue — automatic, nothing to do

Real revenue, straight from the companies' own filings with the US regulator.
Six years of it, drawn as six bars so you can see the shape at a glance:
NVIDIA climbs steeply, Intel shrinks.

This refreshes itself when asked; you never have to do anything. **37 of your
46 main names have it.** The other nine say why they don't, rather than showing
a blank:

- *"Not a US filer, so nothing to read"* — Sivers, IQE, X-FAB, LPKF, Soitec
  and CXMT are listed outside the US, which is the one place this data comes
  from.
- *"Registered with the SEC but files no revenue figures"* — SK Hynix.
- *"Ticker clashes with a different company"* — CCXI. On the US register that
  symbol belongs to a shell company, not Agility Robotics, so the numbers are
  refused rather than attached to the wrong business.

### AI exposure — your judgement, and only yours

Underneath the revenue sits one line: **how much of this company is genuinely
the AI buildout**, as opposed to its older business. Nokia sells telecoms kit
*and* optical parts for datacentres. Vishay sells resistors to everyone. The
share that is AI is the whole question this desk implies and has never
answered.

**Nobody publishes it.** It genuinely cannot be looked up — company filings
report one consolidated number, not a breakdown. So it is a judgement call,
and it has to be yours.

Right now **none of your 46 names have one**, on purpose. Nothing invents these.

### How to do it — just ask

Say **"the worklist"** or **"assess exposure"** in chat and Claude will:

1. show you which names still need a call, biggest company first
2. put the evidence in front of you for each one — what they do, their revenue
   trend, what the analyst has argued
3. take your number and your reasoning
4. record it and confirm what landed

You never touch a terminal. Claude runs it.

Stop whenever you want. A judgement made to clear a list is worth less than no
judgement, and half a list of real calls beats a full list of guesses.

### What gets refused

The store deliberately will not accept:

- a percentage with **no reason attached** — "88%" alone is rejected, and so is
  a reason like "obvious"
- a percentage without **how sure you are** (high / medium / low), because that
  is shown next to the number so a rough call never looks like a hard fact
- **0.45 when you mean 45%** — it could mean half a percent, and it will ask
  rather than guess

Once a name has both a filed revenue and your judgement, the card shows the
result — e.g. *88% · roughly $190B of FY2026 · high confidence* — always with
the confidence next to it, because it multiplies an audited number by your
estimate.

## 12. The price record — why the app now remembers

Until 21 Aug 2026 this project kept **one price per company**, overwritten
twice a day. Every older price was thrown away.

That made one question permanently unanswerable: *"he argued Sivers on
13 August — what happened next?"* You have 1,200 dated arguments from him and,
until now, nothing to score them against.

### What changed

Every price refresh now also **appends** that day's closes to
`ingest/store/price_history.csv`. It happens automatically inside the twice-daily
job — there is nothing for you to run, and nothing new in your routine.

**Storage is a non-issue:** about 4 KB a day, 1 MB a year, 10 MB a decade.
Your `data.js` is already 1.4 MB. The file is plain CSV and deliberately does
*not* load into the app — it is there for analysis, not for the page.

### "Why not just call an API when I need it?"

Fair question, and the answer is specific to this project rather than a
principle:

- **Yahoo and FMP were already retired** (16 Jul 2026) because their free
  endpoints rate-limited almost every run.
- **Stooq**, the usual free fallback, returns a bot-challenge page instead of
  data (checked 21 Aug 2026).
- Your prices come from **your own Google Sheet**, which serves today's number,
  not a history.

So the data you need is already flowing through the app twice a day — it was
just being discarded. Keeping it costs one line per company and can't be
rate-limited, retired, or put behind a paywall later.

### What it can already tell you

The record was seeded with a year of rough anchor points, back-calculated from
the 1-week / 1-month / 1-year changes your sheet already provides. Those are
real arithmetic on real numbers, but their **dates are approximate**, so any
answer using them is flagged `approximate: true`. Observed closes recorded from
here on are exact, and an exact close always overrides a rough anchor for the
same day.

Right now: **428 rows, 111 companies, back to Aug 2025.** Ask in chat — e.g.
*"what happened to SIVE in the year after August 2025"* — and Claude reads it
for you. The record gets more useful every day it runs.

## FAQ / Troubleshooting

### "I sent a message to the bot and nothing replied."
The #1 cause: **the bot isn't running.** Check, in order:
1. **Is the launchd agent up?** `launchctl list | grep com.aie.bot` — a
   numeric PID means it's running; `-` means it exited (check the log below)
   or was never loaded (Section 2, Step 4). You can also check the process
   directly: `pgrep -fl bot.py`.
2. **What does the log say?** `tail -30 ~/Library/Logs/aie-bot.log`. A
   `_assert_fresh` error there means the agent needs restarting after a code
   change (see the "Restart the bot" box in your daily routine, above) — it
   already saved your message, it just couldn't rewrite `data.js` yet.
3. **Is the token set?** Open `ingest/.env` — `TELEGRAM_BOT_TOKEN` and
   `ALLOWED_TELEGRAM_USER_ID` must both be filled in (not blank). Blank token →
   the bot exits immediately with an error, and `KeepAlive` will keep
   respawning and immediately re-exiting it — the log will show the same
   error repeating.
4. **Are you messaging from the right account?** Only the `ALLOWED_TELEGRAM_USER_ID`
   account is accepted; everyone else is ignored with no reply.
5. **Two pollers running at once?** If you (or `desk.command` option 1) also
   started `python3 ingest/bot.py` manually while the launchd agent is
   loaded, both fail with `409 Conflict` — see the log. Stop the manual one;
   the agent is the one that should stay running.

### "poll error: HTTP Error 404: Not Found"
Your `TELEGRAM_BOT_TOKEN` is wrong or revoked. Telegram returns 404 when the token
in the request is invalid. Re-copy the token from @BotFather (or `/revoke` and make
a new one), update `ingest/.env`, and restart the bot:
`launchctl kickstart -k gui/$(id -u)/com.aie.bot`.

### "The bot stopped working after a while."
If it's installed as the launchd agent (Section 2, Step 4), this shouldn't
happen — `KeepAlive` restarts it on any exit, and `RunAtLoad` brings it back
after a reboot or login. The only things that stop it are your Mac being off
or asleep, or the agent being unloaded (`launchctl list | grep com.aie.bot`
shows nothing at all, not even a `-`, once unloaded). If you're instead
running it manually in a terminal, closing that window stops it — install
the launchd agent instead so this stops being a recurring problem.

### "The bot replied, but the app didn't change."
Refresh the browser (or re-open `index.html`). The bot rewrites `data.js`; the app
only reads it on load. If the bot reply showed an error, check the terminal output.

### "Prices won't update / Fetch prices does nothing."
Prices need the local server — run `python3 ingest/serve.py` and use the app at
`http://localhost:8765/` (not the double-clicked `file://` version) when fetching.

### "I added/edited sheet columns and a refresh right after came back mostly blank."
A bulk edit to a sheet with 100+ `GOOGLEFINANCE` cells (inserting a column,
editing several formulas) triggers a recalculation storm — Google returns
blank for a batch of cells until it settles, sometimes for several minutes.
If a refresh runs during that window, `Chg1W`/`Chg1M`/`Chg1Y` (and any USD
variant) will look empty in the fetched CSV even though the sheet looks fine
a few minutes later in the browser. As of 2026-08-19 `fetch_prices.py`
carries the previous good value forward whenever the sheet's cell for an
optional field comes back blank (`_merge_snapshot`, same protection
`currency` already had) — so one flaky fetch during an edit no longer wipes
that ticker's history. It only recovers what was already in `prices.json`
from a prior run, though: if you're seeing blanks in the **app**, wait for
the sheet to settle in the browser (check for `#N/A` or blank on a plain-USD
row like NVDA) and refresh again.

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
