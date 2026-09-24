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
| `log-development` | Operator shares a filing, release or post | One dated, sourced entry in `data.js` |

The collector runs on its own every six hours (launchd `com.aie.desk-collect`, log at
`~/Library/Logs/desk-collect.log`). It reads timelines through the free
fxtwitter API and picks up whatever the operator forwarded to the Telegram bot
(subscriber posts, replies, screenshots). It exits after each run, so there is
no bot process to crash.

The operator does not use a terminal. Run the commands for him and describe the
change in plain language.

## Current status (handover, 24 Sep 2026)

- **Running:** collector every 6h (last exit 0); Telegram bot
  @ai_infra_desk_bot linked to the operator's chat and tested both ways
  (sending, and receiving a forwarded subscriber post). 617 posts stored.
- **Roster:** 7 analysts. @dylan522p removed on 24 Sep (no market content).
- **Scheduled (Claude Desktop, runs only while the app is open):**
  `ai-desk-weekly-memo` Sat 10:00 MYT; `ai-desk-daily-digest` Sun–Fri 11:00 MYT.
  Neither has run yet; the operator should click "Run now" once on each so
  the tool approvals are stored.
- **Scorecard:** four calls opened 24 Sep from the trial memo: SK hynix
  (₩1,862,000), Micron ($1,071.88), Sandisk ($1,816.57), Coherent ($300.60).
- **Price sheet:** rows for 005930.KS, CRDO, SMCI, ANET and ENR.DE added
  24 Sep. Only CXMT is unpriced. The Drive connector cannot edit the sheet;
  edits go through Claude in Chrome with the operator's permission.
- **Next up:** first scheduled memo Sat 26 Sep (Samsung can open as a call if
  the reading holds). Micron reports 30 Sep, the first test of the memory calls.
  After 4 weekly memos, check whether Serenity's paid posts changed any call,
  which decides whether a @pequityresearch subscription is worth it.
- **Known limits:** first backfill of @pequityresearch only reached 21 Sep.
  Subscriber posts need the text or a screenshot; fxtwitter cannot read them.
  A forwarded link and its text are joined only if sent within 2 minutes.

## Desk files

```
desk/analysts.json    the roster (edit to add/drop an analyst)
desk/collect.py       every 6h: timelines + Telegram inbox -> desk/store/posts/
desk/prices.py        price snapshot from the Google Sheet -> desk/store/prices/
desk/prep.py          bundle a window of posts -> desk/store/reading.md
desk/build.py         validate memos, keep the scorecard, write desk.js
desk/send.py          send a text file to the operator's Telegram
desk/common.py        shared plumbing
desk/.env             TELEGRAM_BOT_TOKEN (never committed)
desk/memos/           one JSON memo per week + its Telegram text (private)
desk/store/calls.json the scorecard: opened/closed only by build.py, never by hand
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
