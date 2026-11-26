---
name: daily-digest
description: Send the operator a 60-second Telegram digest of the analyst posts since the last scan (about 12 hours), led by anything he needs to do. Runs after each scan, 10:20 and 23:20 MYT. Use when the operator says "/daily-digest", "daily digest", "what did the analysts say today", or when the scheduled digest task fires.
---

# Digest (twice a day, since 27 Nov 2026)

**First, read `desk/store/HANDOVER.md`** (private status, zones, open issues).

The collector scans X at 10:00 and 23:00 MYT. This digest follows each scan
at :20 and covers the posts since the previous one. It is a **60-second read
on the phone**: about 800 characters, never over 1,000. No guide edits, no
scorecard changes, no commit.

**Saturday morning is skipped.** If it is Saturday before 13:30 MYT, stop: send
nothing (the weekly memo at 13:30 covers it). Saturday night runs as normal.

```bash
python3 desk/collect.py --skip-if-recent 60
python3 desk/prep.py --hours 13
python3 desk/build.py
```

The first line runs the scan only if the 10:00/23:00 scan has not already run
(the Mac was asleep, say). `--hours 13` overlaps the last digest by an hour.

Read `desk/store/reading.md` (open any screenshot files it lists), the latest
`desk/memos/*.json` (rows, sleeves, `market.calendar`), `desk/store/decision.txt`,
`desk/store/notices.json`, `desk/store/alerts.json` and the roles in
`desk/analysts.json`.

**Morning run only (10:20):** the event check. For any `market.calendar` item
with a `ticker` dated today or in the last 3 days and no file yet in
`desk/memos/events/` for it on or after that date, run the `event-update` skill
first. Hyperscalers (MSFT, GOOGL, AMZN, META, ORCL) get a "capex read"; several
on one day share one file. For tomorrow's items marked "expected", check the IR
page for whether the date is confirmed.

## What goes in, in this order

1. **ACTION** — only what changed or needs him now: a notice from
   `notices.json` dated in the window (freeze, thaw, trigger, exit step), a price
   alert from the window, a name that moved into a buy or add zone, a name
   within 3% of its buy or break line, an event update just written. A name that
   was already frozen or already in its zone yesterday is not news; leave it
   out. Add the TIDE line only if the tide changed. Nothing → "Nothing to do."
2. **BY NAME** — the window's news grouped under the ticker it touches, held
   names and shots first, then core list, then the fund ETFs. One line each,
   naming the analyst. At most 4 names; skip names with nothing new. Prefer new
   numbers, guidance, stance changes. Mark anything you did not check
   "unconfirmed".
3. **BULLS vs SCEPTICS** — one line for the bull side, one for the sceptic
   seats (`role: sceptic` in `analysts.json`), on the single biggest debate in
   the window. If the sceptics were quiet, say so.
4. **NEXT 7 DAYS** — earnings and hyperscaler capex prints from
   `market.calendar`, date plus ticker, "(expected)" if not confirmed. Max 4.

Leave out reposts of news everyone has, hype with no number ("BUY BUY BUY"),
and the money and pots lines (they are on the page). Never quote subscriber
(PAID/SCREENSHOT) posts verbatim. If the collector reported failures, put one
line at the very top.

## Shape

Write `desk/store/digest.txt`, plain text:

```
DESK · <date> AM · <n> posts

ACTION
• <name> within 3% of its buy line
• (or: Nothing to do.)

BY NAME
• <ticker>: @<analyst>, <the news in one line>
• <ticker>: @<analyst>, <the news> (unconfirmed)

BULLS vs SCEPTICS
Bulls: <one line>.
Sceptics: @<sceptic seat>, <one line>.

NEXT 7 DAYS
<date> <ticker> · <date> <ticker> (expected)
```

(The lines above show the shape only; every name, number and date comes from
the window's posts and the memo.)

"AM" for the 10:20 run, "PM" for 23:20. Then send it:

```bash
python3 desk/send.py desk/store/digest.txt
```
