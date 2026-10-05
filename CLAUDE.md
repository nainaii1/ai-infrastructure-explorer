# CLAUDE.md — AI Infrastructure Explorer + fund desk

Rebuilt from scratch on 18 Sep 2026 as a static guide. On 24 Sep 2026 the
operator asked for the automation back in a narrower form: a **fund desk** that
follows seven X analysts, collects their posts automatically, and turns them
into a weekly memo. The old v1 system (scoring, tiers, expert seats, claims
ledger, vault, price plumbing) stays archived at git tag `v1-archive` and is not
to be revived; the desk replaces it with something much smaller. Read
`README.md` first.

## What this is

Two parts, one page:

- **The guide** (`index.html`, `style.css`, `app.js`, `data.js`, `check.py`): a
  static, offline-first field guide to the AI hardware supply chain. `data.js`
  is the curated product.
- **The desk** (`desk/`): collects the analysts' posts every six hours, and a weekly
  memo turns them into four things the operator asked for: the supply-chain
  picture now and next, an accumulate list, the analyst bull/bear board, and a
  market wrap. It renders in the page's **Desk** tab from `desk.js`.

## Hard rules

1. **Guide files stay five.** `index.html`, `style.css`, `app.js`, `data.js`,
   `check.py`. No frameworks, no build step, no CDN, no fetch of local files.
   `file://` must work. The page also loads `desk.js` if present.
2. **`data.js` is hand-maintained and valid JSON** after the `window.DATA =`
   prefix. Edit it directly; never generate it. (`desk.js` is the one generated
   file, written by `desk/build.py`.)
3. **No number without a source.** A fact, development, valuation or
   memo figure carries a URL. Prices come only from the Google Sheet snapshot.
   Say "not available" instead of estimating.
4. **No live data in the guide.** Prices, multiples and scorecards live only in
   the desk (dated memos). Never put a price into `data.js`.
5. **Automation lives only in `desk/`, and stays small:** plain Python, standard
   library, no long-running process. No scoring of posting frequency, no expert
   seats, no claims ledger, no extra pages.
6. **The repo is public (GitHub Pages).** Everything the desk collects or writes
   is gitignored: `desk/store/`, `desk/memos/`, `desk.js`, `desk/.env`. Never
   commit or quote subscriber (paid) posts; `data.js` cites free sources only.
7. **Curated, not exhaustive.** A company joins the guide only by sitting on a
   constraint. The accumulate list may name others; the guide does not have to.
8. **Run `python3 check.py` (0 errors) and `python3 desk/build.py` (no ERRORS)**
   before committing.

## Routines (skills in `.claude/skills/`)

| Skill | When | What |
|---|---|---|
| `weekly-memo` | Saturday 10:00 MYT (scheduled), or "run the desk" | Collect, price snapshot, read everything, check claims, write the memo, update scorecard and guide, Telegram summary |
| `daily-digest` | Sun–Fri 11:00 MYT (scheduled) | Short Telegram digest of the last 24h |
| `event-update` | Day after a calendar event for a listed name (triggered by the daily digest or a one-off scheduled task) | Short sourced read: confirms / mixed / breaks the call; may reset alert levels |
| `log-development` | Operator shares a filing, release or post | One dated, sourced entry in `data.js` |

**Also automatic:** price alerts run inside every collector pass (`desk/alerts.py`
against `desk/store/levels.json`); a nightly backup at 23:30 MYT pushes
`desk/store/` and `desk/memos/` to the PRIVATE repo `nainaii1/ai-desk-private`
(launchd `com.aie.desk-backup`, log `~/Library/Logs/desk-backup.log`).

The collector runs on its own every six hours (launchd `com.aie.desk-collect`, log at
`~/Library/Logs/desk-collect.log`). It reads timelines through the free
fxtwitter API and picks up whatever the operator forwarded to the Telegram bot
(subscriber posts, replies, screenshots). It exits after each run, so there is
no bot process to crash.

The operator does not use a terminal. Run the commands for him and describe the
change in plain language.

## Current status (handover, 5 Oct 2026)

- **Checks:** `check.py` 0 errors (9 warnings: FN, ANET, CRDO, ASX, LRCX, KLAC,
  CEG, VRT, ETN have no sourced facts yet); `build.py` no errors.
- **Memos:** 24 Sep (trial) and 2 Oct (by hand). The 3 Oct scheduled run
  skipped itself (memo under 4 days old), as designed. The 26 Sep run had
  failed on the account's monthly spend limit, not a desk bug. **First full
  scheduled memo: Sat 10 Oct, 10:04 MYT.** If the spend limit is hit again it
  fails again, so check the limit before Friday.
- **Scorecard (5 open, against the sheet on 5 Oct, vs the price at opening):**
  Micron $1,074.89 (+0.3%), SK hynix ₩1,841,000 (-1.1%), Sandisk $1,719.99
  (-5.3%), Samsung ₩276,000 (0.0%, opened 2 Oct), Coherent $337.04 (+12.1%).
  Four of five are memory: one risk bucket. Returns are not compared with SMH
  here; the Desk tab does that.
- **Alert zones now:** Micron, SK hynix, Samsung, Sandisk are all inside the
  accumulate zone (none in the "add" zone). Coherent is above its stop-adding
  level of $283 (since 29 Sep). Intel is a watch name at $119.33, above its
  $98 revisit level.
- **Events:** Micron 1 Oct update confirmed the call. Next: SK hynix Q3 ~27 Oct
  (expected), Fed 28 Oct, Samsung Q3 ~29 Oct (expected).
- **Running:** collector every 6h (alerts inside), nightly private backup,
  daily digest Sun-Fri 11:00 MYT, weekly memo Sat 10:04 MYT. Both launchd jobs
  loaded and last exited 0.
- **Known limits:** subscriber posts need text or a screenshot and a link;
  Vicor, FormFactor, Cerebras and CXMT have no sheet price; the Mac must be
  awake for the collector (no price file for 4 Oct, so no run that day).

### Review of 5 Oct (what to know, in order of weight)

1. **FIXED 5 Oct: a hung collector used to block every later run.** `collect.py`
   now has a 3-minute limit per step (one timeline, the Telegram inbox, the
   alert check) and a 15-minute backstop that ends the whole process, so
   launchd can start the next run. If the backstop fires nothing is saved and
   the next run collects the same posts again. The Telegram read position now
   moves only after the inbox is fully handled, so a cut-short run loses no
   forwarded messages.
2. **FIXED 5 Oct: alerts have a 1.5% buffer.** A name changes zone only once it
   is 1.5% past the line it crossed (`BUFFER` in `desk/alerts.py`).
3. **Price snapshots are overwritten.** `prices.py` keeps one file per day and
   every collector run replaces it, so "the price the memo used" can drift
   a few hours. Its docstring still says "run by the memo, not on a timer".
   Scorecard opening prices are frozen at first build, so past calls are safe.
4. **Latent bug, not urgent:** `collect.py` trims the seen-posts list with
   `list(set)[-20000:]`, which drops random IDs, not the oldest. It holds 1,544
   now, so it bites in months, as duplicate posts.
5. **Backup failure message is vague.** `backup.py` reports "exit status 1",
   not git's reason. It does refuse to push unless the repo is private.
6. **Clean:** nothing private is tracked by git; the sheet's public CSV holds
   prices only (no holdings or balances); page text is escaped on render.

### Direction

- Near term: items 1 and 2 are fixed; next is the snapshot overwrite (item 3),
  then the seen-posts trim (item 4).
- Watch the 10 Oct memo as the first real test of the schedule and the skip
  rule, then judge whether the 4-day rule suits a Saturday cadence.
- Concentration: four of five calls are memory. A non-memory name on the
  list, or a stated cap, would make the book less one-bet.
- Guide: fill the 9 sourced-fact gaps only when a development earns it
  (`log-development`); do not pad.
- Track record is still one week of data: do not read the analyst scores yet.

## Desk files

```
desk/analysts.json    the roster (edit to add/drop an analyst)
desk/collect.py       every 6h: timelines + Telegram inbox -> desk/store/posts/
desk/prices.py        price snapshot from the Google Sheet -> desk/store/prices/
desk/prep.py          bundle a window of posts -> desk/store/reading.md
desk/build.py         validate memos, keep the scorecard, write desk.js
desk/send.py          send a text file to the operator's Telegram
desk/alerts.py        zone alerts: price vs the memo's levels, Telegram on a zone change
desk/backup.py        nightly copy of store + memos to the private backup repo
desk/common.py        shared plumbing
desk/.env             TELEGRAM_BOT_TOKEN (never committed)
desk/memos/           one JSON memo per week + its Telegram text (private)
desk/memos/events/    event updates between memos (<date>-<ticker>.json)
desk/store/calls.json the scorecard: opened/closed only by build.py, never by hand
desk/store/stances.json analyst track record: one row per stance run, never by hand
desk/store/levels.json  alert levels (latest memo + later events), built by build.py
desk/store/alerts.json  every alert sent
```

## Data shape (guide)

```
meta:          { title, updated (ISO), disclaimer }
layers[]:      { id, name, stage: demand|compute|supply, summary, constraint, watch }
companies[]:   { ticker, name, layer, hq, listed, what, role, bull, bear, watch,
                 facts[]: { text, asOf (ISO or "Q2 2026"), source } }
narratives[]:  { id, title, status: building|consensus|contested|fading,
                 summary, case, counter, signposts[], companies[] }
developments[]:{ date (ISO), title, summary, companies[], narratives[],
                 sourceType: filing|company|press|analyst, source }
```

The memo shape is documented in `.claude/skills/weekly-memo/SKILL.md` and
enforced by `desk/build.py`.

Private companies use an uppercase slug as `ticker` (`OPENAI`) with
`listed: false`; the page renders the name instead of the slug.

## Voice

Short sentences. Plain words. The bull and bear cases are both written to be
believed. In the guide, "watch" names a trigger, never a price level. In the
memo, the accumulate zone is a price range with its valuation logic and sizing;
it is research support, not advice.
