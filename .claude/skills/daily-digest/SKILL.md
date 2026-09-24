---
name: daily-digest
description: Send the operator a short Telegram digest of the last 24 hours of analyst posts, flagging anything that touches the accumulate list. Use when the operator says "/daily-digest", "daily digest", "what did the analysts say today", or when the scheduled daily task fires.
---

# Daily digest

A five-minute read on the phone, not a memo. No guide edits, no scorecard
changes, no commit.

```bash
python3 desk/collect.py
python3 desk/prep.py --hours 24
```

Read `desk/store/reading.md` (open any screenshot files it lists). Read the
latest `desk/memos/*.json` for the current accumulate list.

**Event check first.** Look at the latest memo's `market.calendar`. For any
item with a `ticker` whose date is today or in the last 3 days, and with no
file yet in `desk/memos/events/` for that ticker on or after that date, run the
`event-update` skill for it before writing the digest, and mention it in one
line in the digest. If a company's results are not out yet (a delayed or
expected date), say so and check again tomorrow.

**Price alerts.** Read `desk/store/alerts.json`; mention any alert from the
last 24 hours in one line (the alert itself was already sent).

Write `desk/store/digest.txt`, plain text, under ~1,500 characters:

```
DESK DIGEST · 24 Sep 2026 · 57 posts

WORTH KNOWING
• @jukan05: Samsung to double HBM4 output next year (Korean press, unconfirmed)
• … (3–6 bullets, each names the analyst, links nothing, says "unconfirmed" unless you checked it)

ON THE LIST
• MU: two analysts more bullish after … / nothing new

QUIET: @dylan522p, @damnang2
```

Skip reposts of news everyone has. Prefer new numbers, stance changes, and
disagreements between analysts. If nothing matters, say so in one line; a
quiet day is a valid digest. Do not quote subscriber (PAID/SCREENSHOT) posts
verbatim.

```bash
python3 desk/send.py desk/store/digest.txt
```

If the collector reported failures, put that first.
