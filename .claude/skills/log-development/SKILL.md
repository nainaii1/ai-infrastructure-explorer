---
name: log-development
description: Add a dated, sourced development (and any new facts) to data.js from a filing, release or post the operator shares, then validate and show the change. Use when the operator says "/log-development", "add this to the explorer", "log this", "this happened", or pastes a link or a post about an AI infrastructure company.
---

# Log a development

The operator shares something that happened (a link, a pasted post, a filing).
Your job is to decide whether it changes the picture and, if so, record it in
`data.js` with a source.

## Steps

1. **Read the source.** If it is a URL, fetch it. If it is a post that cites a
   filing or release, find and read the primary source; cite that, and cite the
   post as `analyst` only when nothing better exists.
2. **Decide.** Does it change what a layer is constrained by, what a company's
   bull or bear case rests on, or a narrative's status? If not, tell the
   operator in one line that it was noted but does not change the reading, and
   stop.
3. **Edit `data.js`.**
   - Append to `developments`: `date` (ISO, the date of the event or filing),
     `title` (one line, specific, with the number in it if there is one),
     `summary` (two sentences: what happened, why it matters), `companies`,
     `narratives`, `sourceType`, `source`.
   - If a number matters going forward, add it to the company's `facts` with
     `asOf` and `source`.
   - If the reading has changed, edit that company's `bull`, `bear` or `watch`,
     or the narrative's `status`, `case` or `counter`. Keep triggers, not
     prices.
   - Bump `meta.updated`.
4. **Validate:** `python3 check.py` must report 0 errors.
5. **Show it:** open `index.html#timeline` in the browser and confirm the entry
   renders with its source link.
6. **Report** in three lines: what was logged, what reading changed (if any),
   and the commit. Commit as `data: <what happened>`.

## Rules

- Never write a number you did not read in the source.
- One development per event. Do not log the same event twice from two posts.
- A company that is not on the map does not get added just because it was
  mentioned. Add it only if it sits on a constraint, and say so in `role`.
