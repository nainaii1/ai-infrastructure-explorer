---
name: assess-exposure
description: Work through the AI-exposure worklist — show which tracked names still need a judgement on how much of their revenue is genuinely the AI buildout, take the operator's number and reasoning in conversation, and record it. Use when the operator says "/assess-exposure", "the worklist", "AI exposure", "how much of X is AI", or asks what still needs a call.
---

# Assess AI exposure — the one number nobody publishes

`aiExposure` is the share of a company's revenue tied to the AI datacentre
buildout rather than its legacy business. It is the question the supply-chain
map implies on every page and has never answered with a number.

**It cannot be fetched or computed.** Verified 21 Aug 2026: SEC
`companyfacts` carries no segment dimension at all — every row is consolidated,
so NVDA's Data Center share is simply not in the payload `fundamentals.py`
reads. There is no free API for it. It is a judgement.

**The judgement is the operator's, not yours.** This skill's job is to make it
easy for him to make, not to make it for him.

## The absolute rule

> Never write a number the operator did not give you.

Not a "reasonable estimate", not "roughly, based on what's publicly known",
not a placeholder to show how the UI looks. If he has not said it, it does not
get recorded. A fabricated percentage sitting in `exposure.json` with a
confident-sounding basis is the single most damaging thing this project could
produce — it would look exactly like the researched fields around it.

You may **propose a range with your reasoning in chat** and ask him to confirm
or correct it. That is a conversation, not a write. The write happens only
after he gives a number.

## The operator does not use a terminal

He works through chat. So: **you run the commands, he makes the calls.** Never
answer "how do I record this?" with a command for him to type. Take the number
and the reasoning from what he says, run the CLI yourself, and show him what
landed.

## Procedure

1. **Show the worklist.**

   ```
   python3 ingest/assess_exposure.py --todo
   ```

   Unassessed Core/Watch names, ordered by filed revenue, biggest first —
   that is the order in which a judgement changes the picture. Present the top
   handful in chat as a short table, not the raw output. Say how many are left
   out of the total.

2. **Give him what he needs to decide, per name.** Before asking for a number,
   put the evidence already in the store in front of him — you have it, so he
   should not have to go looking:
   - what the company does (`whatTheyDo`, `whyNVDA` on the ticker record)
   - filed revenue and its trend (`AIE_DATA.fundamentals`)
   - what the analyst has argued about it (`views[]` on the theses)
   - the desk's own verdict if one exists (`verdicts.json`)

   Then ask for: the percentage, how sure he is, and why. The "why" is not
   optional — the store refuses a number without it.

3. **Record it.** One name at a time:

   ```
   python3 ingest/assess_exposure.py --set <TICKER> --exposure <0-100> \
       --confidence high|medium|low \
       --basis "<his reasoning, in his words>" \
       --source "<where it came from, repeatable>"
   ```

   Optional: `--revenue-inflection "H2 2027"`, `--content-per-rack "..."`.

   Write his reasoning, not a tidied-up version of it. If he says "gut feel
   from the JBL teardown", the basis is that — with `--confidence low`.

4. **Confirm what landed.** The command prints the stored record and
   regenerates `data.js`. Tell him the derived figure it now produces
   (filed revenue x his percentage) and where to see it: the revenue block on
   the ticker card and the watchlist row.

5. **Stop when he stops.** Do not push through all 46 in one sitting. A
   judgement made to clear a list is worth less than no judgement.

## What the store refuses, and why

`exposure.validate_assessment` raises rather than storing:

- a number with **no basis**, or a basis under four words ("obvious" is not a
  reason)
- a **missing or invented confidence** level — the figure is always rendered
  next to it, so a rough call can never read as a measurement
- a **fraction**: `0.45` is refused, not multiplied by 100, because it could
  mean 45% or half a percent and guessing between them is not this desk's habit
- anything outside 0-100

If a command is refused, the message says what to fix. Relay it plainly and
ask him for the missing piece — never work around it.

## Checking state

```
python3 ingest/assess_exposure.py --status      # coverage + confidence mix
python3 ingest/assess_exposure.py --show NVDA   # one record
python3 ingest/assess_exposure.py --clear NVDA  # a call he no longer stands behind
```

`--clear` is for retracting a judgement, and it is his call, not yours. Do not
clear a record to "clean up".

## Where it shows

`store/exposure.json` -> `data.js` -> `AIE.makeExposureRow`, rendered inside
the revenue block on the ticker card and the watchlist row detail. An
unassessed name reads "Not assessed yet" — never 0%.

Once both halves exist, `AIE.aiRevenue(sym)` produces the payoff: filed
revenue x judged exposure, always shown next to its confidence chip because it
multiplies an audited number by an unaudited one.

## Related

- `PROJECT.md` — Step 3, why this exists and why it cannot be derived
- `ingest/exposure.py` — the pure validation module (invariant 6)
- `/weekly-review` — a good moment to revisit a low-confidence call
