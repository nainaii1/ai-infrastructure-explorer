# CLAUDE.md — AI Infrastructure Explorer + fund desk

Rebuilt from scratch on 18 Sep 2026 as a static guide. On 24 Sep 2026 the
operator asked for the automation back in a narrower form: a **fund desk** that
follows nine X analysts (two of them sceptic seats), collects their posts automatically, and turns them
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
| `weekly-memo` | Saturday 10:00 MYT (scheduled, always runs unless a memo was written Fri/Sat), or "run the desk" | Collect, price snapshot, read everything, check claims, write the memo, update scorecard and guide, Telegram summary. Mid-week by hand: warn if a list result or hyperscaler capex print is under 48h away |
| `daily-digest` | Sun–Fri 11:00 MYT (scheduled) | Short Telegram digest of the last 24h; triggers event updates; re-checks tomorrow's "expected" dates |
| `event-update` | Day after a calendar event for a listed name or a hyperscaler (triggered by the daily digest or a one-off scheduled task) | Short sourced read: confirms / mixed / breaks the call, judged against the memo's named `test`; hyperscalers get a "capex read"; may reset alert levels |
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

## Current status (handover, 2 Nov 2026)

- **Checks:** `check.py` 0 errors (8 warnings: FN, ANET, CRDO, LRCX, KLAC, CEG,
  VRT, ETN have no sourced facts yet); `build.py` no errors.
- **Memos:** 24 Sep (trial), 2 Oct, 10 Oct, 15 Oct, 24 Oct, 28 Oct. **The
  scheduled 31 Oct memo FAILED**: the account hit its weekly usage limit at
  10:05 MYT (resets 13:00), so nothing after 28 Oct is in a memo. The cloud
  deep-dives of 1 and 2 Nov (below) cover the gap. **Next memo: Sat 7 Nov,
  10:04 MYT.** Check the usage limit on Friday.
- **Desk rules from 28 Oct** (still in force): `watch` rows need a named
  `test`; accumulate and holding rows carry `levels.trimAbove`;
  `market.positioning` asks "squeeze or re-rating?"; `support.py` flags
  `STRETCHED` names (over 8% in five sessions) so buy lines are not chased up.
  Roster is nine, two of them sceptic seats (@FundaAI, @insane_analyst).
- **Scorecard (sheet, 2 Nov; closes of 30 Oct):** Micron $884.74 (-17.5%),
  Sandisk $1,150.89 (-36.6%), Coherent $210.32 (-30.0%), all opened 24 Sep (SMH
  -13.1% since); Samsung ₩225,750 (-18.2%, opened 2 Oct; SMH -15.5%); TSMC
  $406.13 (-2.6%, opened 24 Oct; SMH -1.1%). Closed: SK hynix (-31.4%, 24 Oct).
  Every open call trails SMH; Sandisk worst at -23.5 points.
- **Zones now:** Sandisk, Coherent and TSMC sit inside their buy zones, Micron
  0.5% above its $880 buy line, Samsung in hold. SK hynix (watch) is
  STRETCHED above its ₩1,283,000 revisit level. Levels are the 28 Oct memo's:
  Micron $880 / $804 / $1,417 / trim $1,562; Samsung ₩210,600 / ₩189,200 /
  ₩316,000 / ₩395,000; Sandisk $1,290 / $998 / $1,934 / $2,144 (divide by 8
  after the split, effective after the 19 Nov close); Coherent $211 / $175 /
  $282 / $352; TSMC $420 / $386 / $475 / $584. Holdings have their own levels
  in the memo (never name them here).
- **For the 7 Nov memo** (from the cloud deep-dive): Sandisk's thesis weakened
  (Kioxia guided the December quarter about flat; NAND price gains slowed from
  about +70% to the mid-20s), so give it a named test and recheck its
  valuation anchor; Micron and Samsung are unchanged or stronger; TSMC's capex
  test passed but the market now punishes capex cash burn (Alphabet -13% on
  negative free cash flow). Two holdings failed their named tests; the memo
  must reassess them (see the private reports).
- **Events ahead:** AMD 3 Nov after the US close; Coherent 4 Nov after the
  close (about 05:00 MYT 5 Nov); Lumentum 5 Nov; a possible Marvell-Lumentum
  deal; holdings' dates are in the memo. The daily digest triggers event
  updates.
- **Running:** collector every 6h (launchd, alerts inside), daily digest
  Sun-Fri 11:00 MYT, weekly memo Sat 10:04 MYT, backup nightly 23:30 (pushing
  fine since 24 Oct).
- **Cloud routines (1-5 Nov only, Opus 5.5, no connectors):** "AI desk: daily
  deep-dive" 08:00 MYT 2-5 Nov and "AI desk: sceptic research" 20:00 MYT 2-4
  Nov (memory, optics, capex funding). They read `ai-desk-private` and push
  reports to its branch `claude/desk-reports`, never `main` (`backup.py`
  pushes `main` without pulling, so a cloud commit there would break the
  backup). They never call Telegram. The prompts stop themselves after 5 Nov;
  delete both at claude.ai/code/routines. Open question: the $100 cloud
  credit (expires 5 Nov 15:59 MYT) did not move after the first run, so
  routines may bill to the plan's usage instead. `CLOUD_BRIEF.md` is a
  self-contained prompt for a cloud session the operator starts by hand.
- **Page (rebuilt 1 Nov):** the Desk tab opens on a cockpit (every name's
  last 66 sessions drawn over its zones, calls vs SMH, next-up countdown, the
  book by layer); memo cards carry real price charts; the Map has lenses (My
  book, Analyst mood, News flow); company dossiers include the desk's view.
  `build.py` now writes `desk/store/history.json` (daily closes from the
  sheet's `price_history` tab, cached if the fetch fails) into `desk.js`.
- **Sheet:** the main tab's `Chg1W` covers about 12 days, not 7. One
  holding's main-tab price disagrees with its `price_history` close by about
  5% (see the 1 Nov private report); one is stale. Lumentum has no
  `price_history` block.
- **Known limits:** subscriber posts need text or a screenshot and a link;
  CXMT has no sheet price; the Mac must be awake for the collector; fxtwitter
  returns frequent one-off 404s (most accounts recover next run). In Claude's
  browser pane check the page through the `explorer` preview server (port
  8791), and reload scripts with a cache bypass after edits.

### Open issues (2 Nov)

1. **Weekly usage limit** stopped the 31 Oct memo. Keep Friday free of heavy
   runs, or check usage before Saturday.
2. **Backup failure message is vague** (`backup.py` prints only "exit status
   1"). It does refuse to push unless the repo is private.
3. **Sheet:** fix `Chg1W`, the holding price mismatch, and add a Lumentum block.
4. **Clean:** nothing private is tracked by git; page text is escaped on
   render; the public site has no `desk.js`, so it hides the desk-only lenses.

### Direction

- The 28-30 Oct results came in: hyperscaler 2027 capex rises, memory says
  sold out, but NAND pricing is cooling and the market now prices the cost of
  capex. SK hynix's HBM4 share at Nvidia is still unconfirmed (re-open its
  call only if the share holds).
- Concentration: three of five calls are memory, plus Coherent (optics) and
  TSMC (foundry). TSMC dilutes the memory bet but does not hedge it.
- Track record, first read (five memos): the four analysts with 8+ scored
  calls all trail SMH on average (-5.5 to -9.1 points), mostly beta in a
  falling month. Not yet a reason to drop anyone. On the 28 Oct board memory
  had 17 bull stances and 0 bear, where three of five calls sit: the sceptic
  seats and the cloud sceptic reports exist to argue that side.
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
desk/store/history.json daily closes from the sheet's price_history tab (build.py), for the page's charts
desk/store/cloud-reports/ local copies of the cloud reports (originals on ai-desk-private, branch claude/desk-reports)
CLOUD_BRIEF.md        the prompt for a hand-started cloud daily brief (public: no holdings, no data)
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
