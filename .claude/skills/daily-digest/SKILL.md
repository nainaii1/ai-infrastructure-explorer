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
