# CLAUDE.md — AI Infrastructure Explorer

Rebuilt from scratch on 18 Sep 2026. The previous six months of work (ingest
pipeline, scoring, tiers, expert seats, claims ledger, vault, watcher, Telegram
bot, price plumbing) is preserved at git tag `v1-archive` and is not to be
revived. Read `README.md` first; it is short and current.

## What this is

A static, offline-first field guide to the AI hardware supply chain. One HTML
page, one stylesheet, one script, one data file. The data file is the product.

## Hard rules

1. **Five app files, no more.** `index.html`, `style.css`, `app.js`, `data.js`,
   `check.py`. No frameworks, no build step, no CDN, no fetch of local files.
   `file://` must work.
2. **`data.js` is hand-maintained and valid JSON** after the `window.DATA =`
   prefix. Edit it directly; never generate it.
3. **No number without a source.** A fact or development carries a URL to a
   primary source (filing, company release, press, or the X post it came from).
   A figure with no source does not go in. Say "not on file" instead.
4. **No live data.** No prices, no market caps, no scoring, no automation. If a
   number changes daily it does not belong here.
5. **Curated, not exhaustive.** A company earns its place by sitting on a
   constraint. Do not grow the roster to track every ticker someone mentions.
6. **Run `python3 check.py` before committing.** It must report 0 errors.

## The routine

When the operator shares a filing, a release, or a post:

1. Decide whether it changes the picture. Most posts do not; skip them.
2. Add a `developments` entry (date, title, two-sentence summary, companies,
   narratives, sourceType, source URL).
3. If a number matters, add it to the company's `facts` with `asOf` and
   `source`. Update the company's `bull`, `bear` or `watch` only if the reading
   has changed.
4. If a narrative's status has moved, change it and say why in `case` or
   `counter`.
5. Bump `meta.updated`, run `check.py`, open `index.html` and look at the
   change, then commit with `type: description`.

The operator does not use a terminal. Run the commands for him and describe the
change in plain language.

## Data shape

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

Private companies use an uppercase slug as `ticker` (`OPENAI`) with
`listed: false`; the page renders the name instead of the slug.

## Voice

Short sentences. Plain words. The bull and bear cases are both written to be
believed. "Watch" names the fact that would change the reading, as a trigger,
never as a price level.
