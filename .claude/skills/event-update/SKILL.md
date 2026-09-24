---
name: event-update
description: Write a short update on the desk's call right after a company event (earnings, guidance, a big deal) for a name on the accumulate or watch list, and send it to Telegram. Use when the operator says "/event-update", "Micron reported, what now", "update the call on X", or when the daily digest or a scheduled task finds a calendar event from the latest memo that has just happened.
---

# Event update

The weekly memo sets the calls. Results land midweek, and the operator should
not wait until Saturday to know whether a result confirmed or broke a call.
This is a short, sourced read on one event. It does **not** open or close
scorecard calls: that stays with the weekly memo. It may reset the alert levels
if the valuation anchor moved.

Work from the project root.

## 1. Gather

```bash
python3 desk/collect.py        # fresh posts, prices, alerts
```

- Read the company's own release (investor relations page, 8-K on SEC EDGAR,
  or the exchange filing). That is the primary source; cite it.
- Read the latest `desk/memos/*.json` entry for this ticker: its thesis,
  catalyst, zone, `levels` and invalidation, and what the memo's calendar
  said to watch for.
- Run `python3 desk/prep.py --hours 36` and read what the analysts said about
  the result.
- Today's price is in `desk/store/prices/<today>.json`.

## 2. Judge

- **confirms**: the result supports the thesis and the invalidation trigger
  was not hit.
- **mixed**: some of each. Say which part weakened.
- **breaks**: the invalidation trigger in the memo was hit. Say so plainly;
  the weekly memo will close the call.

Compare against what the memo said mattered (for Micron, the next-quarter
guide mattered more than the beat). Never write a number you did not read in
the release or a cited source.

## 3. Write `desk/memos/events/<today>-<ticker>.json`

```json
{
  "date": "YYYY-MM-DD",
  "ticker": "MU",
  "event": "Micron fiscal Q4 2026 results",
  "verdict": "confirms|mixed|breaks",
  "headline": "One sentence: what happened and what it means for the call.",
  "summary": ["What they reported against the bar.", "What the guide implies.", "What the analysts said."],
  "numbers": [{ "text": "Revenue $X vs guidance $50.0bn ±$1.0bn", "source": "https://..." }],
  "callImpact": "Keep / keep but lower confidence / the weekly memo should close it, and why.",
  "levels": { "currency": "USD", "buyBelow": 0, "addBelow": 0, "stopAbove": 0 },
  "sources": ["https://..."]
}
```

Include `levels` only if the valuation anchor moved (for example forward
earnings estimates changed enough to move the zone). Show the arithmetic in
`callImpact`. Otherwise leave `levels` out and the memo's levels stand.

## 4. Build, check, send

```bash
python3 desk/build.py          # must show no ERRORS; shows the event on the Desk page
```

Write `desk/store/event.txt` (plain text, under ~1,200 characters):

```
DESK EVENT · MU · 1 Oct 2026 · CONFIRMS
<headline>

• 3 bullets: the numbers against the bar
• what the analysts said (name them; mark unconfirmed claims)

CALL: <callImpact>
ZONE: unchanged / new zone …
```

```bash
python3 desk/send.py desk/store/event.txt
```

Do not commit anything (desk files are private). If the event changes the
guide's picture, follow `log-development` for `data.js` and commit that only.
