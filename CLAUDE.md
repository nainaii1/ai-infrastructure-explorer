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

## Current status (handover, 24 Oct 2026)

- **Checks:** `check.py` 0 errors (8 warnings: FN, ANET, CRDO, LRCX, KLAC, CEG,
  VRT, ETN have no sourced facts yet; ASX got its first on 24 Oct); `build.py`
  no errors.
- **Memos:** 24 Sep (trial), 2 Oct, 10 Oct (scheduled), 15 Oct and 24 Oct (both
  by hand). The 3 Oct and 17 Oct scheduled runs skipped themselves (memo under
  4 days old), as designed. The 24 Oct memo ran at 02:30 MYT, so that day's
  10:04 scheduled run skips too. **Next scheduled memo: Sat 31 Oct, 10:04
  MYT**, after SK hynix, Sandisk, Intel and Samsung have reported. The 26 Sep
  run failed on the account's monthly spend limit, so check the limit before
  Friday.
- **Scorecard (vs the price at opening; sheet snapshot of 23 Oct; SMH -12.2%
  since 24 Sep):** Micron $883.44 (-17.6%), Sandisk $1,260.13 (-30.6%),
  Coherent $210.01 (-30.1%), Samsung ₩215,500 (-21.9%, opened 2 Oct; SMH
  -14.5% since then). TSMC opened 24 Oct at $416.87. **Closed:** SK hynix on
  24 Oct at ₩1,277,000 (-31.4%), moved to watch until its 28 Oct results (the
  list keeps at most five accumulate names). Every open call trails SMH.
- **Alert levels (buy / add / stop adding, 24 Oct memo):** Micron $880 / $804
  / $1,411; Samsung ₩210,600 / ₩189,200 / ₩316,000; Sandisk $1,290 / $998 /
  $1,934; Coherent $211 / $175 / $282; TSMC $420 / $386 / $469; SK hynix is a
  watch name with a ₩1,283,000 revisit level. Sandisk and Coherent broke their
  chart floors on 22 Oct and their lines were reset. Holdings have their own
  levels in the memo (never name them here).
- **Events ahead:** SK hynix 28 Oct (results before 9:00 Seoul, call at 9:00),
  Fed 28 Oct, Microsoft and Alphabet 28 Oct (expected), Sandisk and Intel 29
  Oct, Amazon 29 Oct (expected), Samsung about 30 Oct (expected), Coherent 4
  Nov, Lumentum 5 Nov. A holding has a decision deadline on 29 Oct (see the
  24 Oct memo's flags). The daily digest triggers event updates from the
  memo's calendar.
- **Running:** collector every 6h (alerts inside; last launchd run 19:24 MYT on
  23 Oct, plus a manual run at 02:24 MYT on 24 Oct), daily digest Sun-Fri
  11:00 MYT, weekly memo Sat 10:04 MYT. The nightly backup **failed at 23:33
  on 23 Oct** at `gh repo view` (exit 1, no reason logged); `gh` was logged in
  fine at 03:45 and a manual run on 24 Oct pushed. Check that night's run.
- **Sheet:** TSMC was added to the `price_history` tab on 24 Oct (columns
  BS-BX). The tab has 80 columns, so the next block needs columns added first.
  The main tab's `Chg1W` column currently measures from about 12 days back
  (the 12 Oct close at the 23 Oct snapshot), not 7; the memo text uses the
  change since the last memo's snapshot instead.
- **Known limits:** subscriber posts need text or a screenshot and a link;
  CXMT has no sheet price; the Mac must be awake for the collector; fxtwitter
  returns occasional 404s (four accounts failed once on 23 Oct, then
  recovered). In Claude's browser pane a `file://` page is a static snapshot
  with no scripts, so check the page through the `explorer` preview server
  (port 8791, `.claude/launch.json`).

### Open issues (24 Oct)

1. **Backup failure message is vague.** `backup.py` prints the command and
   "exit status 1", not the reason from `gh` or git (seen again on 23 Oct). It
   does refuse to push unless the repo is private.
2. **Sheet `Chg1W` column** covers about 12 days, not 7 (see Sheet above). Fix
   the formula in the sheet's main tab.
3. **Clean:** nothing private is tracked by git; the sheet's public CSV holds
   prices only (no quantities or balances); page text is escaped on render.

Fixed on 5-6 Oct and still holding: the collector's time limits and watchdog,
the 1.5% alert buffer (`BUFFER` in `desk/alerts.py`), frozen memo price
snapshots (the collector writes `prices_latest.json`), and the seen-posts list
trimming its oldest IDs.

### Direction

- The 28-30 Oct results decide the memory book: SK hynix's HBM4 share at
  Nvidia into 2027 (re-open its call if the share holds), and the
  hyperscalers' 2027 capex.
- Concentration: three of five calls are memory, plus Coherent (optics) and
  TSMC (foundry). TSMC dilutes the memory bet but does not hedge it.
- Track record, first read (five memos): the four analysts with 8+ scored
  calls all trail SMH on average (-5.5 to -9.1 points), mostly beta in a
  falling month. Not yet a reason to drop anyone; the roster still has no
  sceptic (two candidates in the 24 Oct memo). The operator decides.
- Guide: fill the 8 sourced-fact gaps only when a development earns it
  (`log-development`); do not pad.
- On request, a management slide deck is built from the latest memo as a
  private Slides artifact (24 Oct: 10 slides, holdings left out).

## Desk files

```
desk/analysts.json    the roster (edit to add/drop an analyst)
desk/collect.py       every 6h: timelines + Telegram inbox -> desk/store/posts/
desk/prices.py        price snapshot from the Google Sheet -> desk/store/prices/ (memo) and prices_latest.json (collector)
desk/support.py       chart floors from the sheet's price_history tab (gid 175825543) for support-based levels
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
desk/store/holdings.json the operator's holdings (tickers only, private): action "holding", levels + alerts, never scored
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
