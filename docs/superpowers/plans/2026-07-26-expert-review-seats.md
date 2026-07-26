# Expert Review Seats Implementation Plan (Phase 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let three expert reviewers research a shortlist of Core names each week and write their findings into the thesis feed as a checked second source, so the desk stops being downstream of one person.

**Architecture:** A new pure module `ingest/seats.py` mirrors the existing `ingest/synthesize.py` pattern exactly — prompt building, output validation, and orchestration are pure functions taking an **injected `call_fn(system, user) -> dict`**, with no network and no file I/O. The operator has no Anthropic API key, so a Claude Code session supplies `call_fn` by acting as the seats itself. Validated findings become theses with `source: "research"`, which `scorer.py` already scores asymmetrically. A new `/pre-review` skill drives the run.

**Tech Stack:** Python 3 standard library only, `unittest`. No new dependencies. One small change to `desk.html` (vanilla JS, no build step).

**Source spec:** `docs/superpowers/specs/2026-07-26-expert-review-team-design.md` (Phase 2)
**Prior plan:** `docs/superpowers/plans/2026-07-26-direction-aware-scoring.md` (Phase 1, shipped)

---

## Background the engineer needs

### Why there is no API call in this plan

`CLAUDE.md` records that the Brain feature (`ingest/synthesize.py`) "requires a paid Anthropic API key the operator doesn't currently have". The established workaround is that every intelligent step is a **pure function taking an injected `call_fn`**, so a Claude Code session can drive it in-session and produce output byte-identical to a real API run. `synthesize.synthesize_all(theses, tickers, categories, call_fn, ...)` is the reference implementation — read it before writing `seats.py`.

**Do not add an API client, an SDK dependency, or a network call to `seats.py`.**

### What Phase 1 already built (do not rebuild)

`ingest/scorer.py` already handles research theses:
- `RESEARCH_SOURCE = "research"` and `_direction_weight()` — a research thesis scores `-1.0` if `direction == "bear"`, otherwise `0.0`. It can correct a score downward but never inflate one.
- `weightedMentions` skips research entirely, so research cannot promote a name to a tier.
- `_normalize_direction()` — absent direction reads `neutral` (full weight); a present-but-unrecognized value is `UNKNOWN_DIRECTION` and scores `0.0`.

**Import these from `scorer` rather than redefining them.** A second copy of `"research"` in `seats.py` is a drift bug waiting to happen.

### The hole Task 1 closes

Verified on 2026-07-26 against the live scorer:

```
2 research theses with conviction="high":
  score: 0.0   weightedMentions: 0.0   convictionHits: 2
  TIER: core
```

`compute_priorities` increments `convictionHits` without checking `is_research`, and `assign_tiers` promotes on `hits >= TIER_CORE_MIN_CONVICTION_HITS` (2). So the `weighted` guard is bypassed and the model can still write its own names into Core. This is the same defect class Phase 1 fixed for `weighted`, reappearing on the conviction path. Task 1 closes it in the scorer — not by trusting the writer.

### Deliberate deviation from the spec

The spec's seat output shape includes a `claims` array. **This plan drops it.** `claims.json` does not exist until Phase 3, so capturing dated predictions with nowhere to put them is speculative work. Claims can be extracted from finding text later. Record the deviation; do not build `claims` here.

## File structure

| File | Responsibility | Action |
|---|---|---|
| `ingest/scorer.py` | Research must not contribute conviction hits; expose `researchMentions` | Modify |
| `ingest/seats.py` | Seat definitions, prompt building, finding validation, thesis conversion, coverage selection, orchestration. Pure — no I/O, no network. | Create |
| `ingest/tests/test_seats.py` | All of the above | Create |
| `ingest/generate_data_js.py` | Pass `researchMentions` through the ticker priority stamp | Modify |
| `desk.html` | Stop attributing research findings to the analyst | Modify |
| `.claude/skills/pre-review/SKILL.md` | The operator-facing procedure | Create |
| `.claude/skills/weekly-review/SKILL.md` | Point step 1 at `/pre-review` | Modify |
| `CLAUDE.md`, `docs/ROADMAP.md` | Status and schema | Modify |

`seats.py` is one file because every function in it is part of one pipeline and they are all pure and small. If it passes ~350 lines, stop and report it rather than splitting on your own.

---

## Task 1: Research theses must not buy tier coverage through conviction

**Files:**
- Modify: `ingest/scorer.py`
- Test: `ingest/tests/test_scorer.py`

- [ ] **Step 1: Write the failing tests**

Append to the `TestDirection` class in `ingest/tests/test_scorer.py`:

```python
    def test_research_conviction_hits_do_not_promote_a_tier(self):
        # Verified hole, 2026-07-26: two research theses with conviction
        # "high" gave score 0.0 and weightedMentions 0.0 but convictionHits 2,
        # and assign_tiers promotes on 2 hits — so the model could write its
        # own name into Core straight past the weightedMentions guard.
        theses = [
            thesis(["Z"], "2026-06-26T00:00:00Z",
                   conviction="high", direction="bull", source="research"),
            thesis(["Z"], "2026-06-25T00:00:00Z",
                   conviction="high", direction="bull", source="research"),
        ]
        pri = scorer.compute_priorities(theses, now=NOW)
        self.assertEqual(pri[0]["convictionHits"], 0)
        self.assertEqual(scorer.assign_tiers(["Z"], pri)["Z"], "radar")

    def test_analyst_conviction_hits_still_promote_a_tier(self):
        theses = [
            thesis(["Z"], "2026-06-26T00:00:00Z", conviction="high"),
            thesis(["Z"], "2026-06-25T00:00:00Z", conviction="high"),
        ]
        pri = scorer.compute_priorities(theses, now=NOW)
        self.assertEqual(pri[0]["convictionHits"], 2)
        self.assertEqual(scorer.assign_tiers(["Z"], pri)["Z"], "core")

    def test_research_mentions_are_counted_separately(self):
        theses = [
            thesis(["Z"], "2026-06-26T00:00:00Z", direction="bull"),
            thesis(["Z"], "2026-06-26T00:00:00Z",
                   direction="bear", source="research"),
        ]
        r = scorer.compute_priorities(theses, now=NOW)[0]
        self.assertEqual(r["mentions"], 2)
        self.assertEqual(r["researchMentions"], 1)
```

- [ ] **Step 2: Run and confirm they fail**

Run: `python3 -m unittest discover -s ingest/tests -k TestDirection -v 2>&1 | tail -20`
Expected: FAIL — `2 != 0` on the first test, `KeyError: 'researchMentions'` on the third.

- [ ] **Step 3: Implement**

In `ingest/scorer.py`, inside `compute_priorities`, extend the `agg.setdefault` default dict with `"research": 0`:

```python
            a = agg.setdefault(
                sym,
                {"mentions": 0, "weighted": 0.0, "recency": 0.0,
                 "net": 0.0, "bull": 0, "bear": 0, "research": 0,
                 "convictionHits": 0, "lastMentioned": None},
            )
```

Replace the conviction-hit line:

```python
            if is_high:
                a["convictionHits"] += 1
```

with:

```python
            # Conviction hits gate tiers directly in assign_tiers, so research
            # must be excluded here too. Guarding only `weighted` left this
            # path open: two research posts marked "high" promoted a name to
            # core with a score of 0.0 (verified 2026-07-26).
            if is_high and not is_research:
                a["convictionHits"] += 1
            if is_research:
                a["research"] += 1
```

Add `researchMentions` to the emitted record, immediately after `bearMentions`:

```python
            "researchMentions": a["research"],
```

- [ ] **Step 4: Run the whole suite**

Run: `python3 -m unittest discover -s ingest/tests 2>&1 | tail -3`
Expected: `OK` — 144 tests

- [ ] **Step 5: Mutation-test it**

Remove `and not is_research` from the conviction line, clear caches, re-run:

```bash
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
python3 -m unittest discover -s ingest/tests 2>&1 | tail -2
```

Expected: FAILED. Restore the guard, clear caches, confirm `OK` again. **If nothing goes red, your test is decorative — fix it before continuing.**

- [ ] **Step 6: Commit**

```bash
git add ingest/scorer.py ingest/tests/test_scorer.py
git commit -F - <<'EOF'
fix: research theses cannot buy tier coverage via conviction hits

Phase 1 stopped research inflating weightedMentions, but assign_tiers
also promotes on convictionHits >= 2, and that path was unguarded. Two
research theses marked conviction "high" produced score 0.0,
weightedMentions 0.0, convictionHits 2 -- and tier core.

Also exposes researchMentions so the UI can distinguish analyst
attention from the desk's own findings.
EOF
```

---

## Task 2: Seat definitions and prompt building

**Files:**
- Create: `ingest/seats.py`
- Create: `ingest/tests/test_seats.py`

- [ ] **Step 1: Write the failing tests**

Create `ingest/tests/test_seats.py`:

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import seats  # noqa: E402

NOW = "2026-07-26T12:00:00Z"


def thesis(text, tickers, posted_at="2026-07-20T00:00:00Z"):
    return {"id": "h_" + text[:8], "text": text, "tickers": tickers,
            "postedAt": posted_at, "source": "x", "author": "aleabitoreddit"}


class TestSeats(unittest.TestCase):
    def test_three_seats_defined(self):
        self.assertEqual(sorted(seats.SEATS), ["fundamental", "pm", "semi-expert"])

    def test_every_seat_has_a_question_and_brief(self):
        for key, seat in seats.SEATS.items():
            self.assertTrue(seat["label"], key)
            self.assertTrue(seat["question"], key)
            self.assertTrue(seat["brief"], key)


class TestBuildPrompt(unittest.TestCase):
    def test_prompt_names_the_seat_and_ticker(self):
        system, user = seats.build_seat_prompt(
            "semi-expert", "SIVE", [thesis("CPO ramp looks real", ["SIVE"])])
        self.assertIn("Semiconductor expert", system)
        self.assertIn("Is the technical claim true?", system)
        self.assertIn("SIVE", user)
        self.assertIn("CPO ramp looks real", user)

    def test_prompt_states_the_word_cap_and_vocabulary(self):
        system, _ = seats.build_seat_prompt("pm", "MU", [])
        self.assertIn("60 words", system)
        for word in ("bull", "bear", "neutral"):
            self.assertIn(word, system)

    def test_prompt_states_the_verification_rule(self):
        system, _ = seats.build_seat_prompt("fundamental", "MU", [])
        self.assertIn("basis", system)
        self.assertIn("unverified", system)

    def test_unknown_seat_raises(self):
        with self.assertRaises(KeyError):
            seats.build_seat_prompt("chief-vibes-officer", "MU", [])

    def test_theses_are_capped(self):
        many = [thesis("post %d" % i, ["MU"]) for i in range(50)]
        _, user = seats.build_seat_prompt("pm", "MU", many)
        self.assertLessEqual(user.count("post "), seats.MAX_THESES_IN_PROMPT)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and confirm failure**

Run: `python3 -m unittest discover -s ingest/tests -k test_seats -v 2>&1 | tail -10`
Expected: FAIL — `ModuleNotFoundError: No module named 'seats'`

- [ ] **Step 3: Implement**

Create `ingest/seats.py`:

```python
"""The expert review seats — three reviewers with different mandates.

Mirrors ingest/synthesize.py: every function here is PURE. Prompt building,
validation and orchestration take an injected `call_fn(system, user) -> dict`
so a Claude Code session can drive the run without an API key (the operator
does not have one — see CLAUDE.md, v4). No network, no file I/O in this
module.

The seats exist because the desk is downstream of exactly one analyst, so the
store contains no bear case and nothing outside his field of view can enter.
Their findings become theses with source "research", which scorer.py scores
asymmetrically: a research finding can correct a name downward but can never
inflate its rank or buy it tier coverage.
"""

import sys

import scorer

# Seat mandates. Each is differentiated by the QUESTION it must answer, not by
# what it is allowed to read. Naming a seat "semi-expert" does not create
# semiconductor expertise — it is the same model with a different instruction
# and web access. What this buys is three separate passes so three different
# questions actually get asked, and forced outside research so new facts enter.
SEATS = {
    "semi-expert": {
        "label": "Semiconductor expert",
        "question": "Is the technical claim true?",
        "brief": ("Ramp timelines, process and packaging limits, yields, "
                  "qualification status, capacity assumptions."),
    },
    "fundamental": {
        "label": "Fundamental analyst",
        "question": "Do the numbers work?",
        "brief": ("Revenue maths, dilution, margins, customer concentration, "
                  "valuation against peers."),
    },
    "pm": {
        "label": "Portfolio manager",
        "question": "Is this a good bet at this price?",
        "brief": ("What is already priced in, what the downside is, what "
                  "would force an exit."),
    },
}

MAX_FINDING_WORDS = 60
MAX_THESES_IN_PROMPT = 12

_SYSTEM = """You are the {label} on a one-person research desk.

Your mandate — the ONE question you answer: {question}
Scope: {brief}

You are reviewing a name the desk already tracks. The desk follows a single
long-only analyst, so it has no bear case and cannot see anything outside his
field of view. Your job is to bring in what he missed, not to agree with him.

Rules:
- Your finding is at most {max_words} words. One claim. No hedging.
- direction must be exactly one of: bull, bear, neutral (lowercase).
- basis must be a list of URLs to primary or near-primary sources: SEC
  filings, earnings-call transcripts, company IR material, exchange notices,
  or established industry data providers. Content aggregators and
  search-engine-optimised summaries do not qualify.
- If you cannot cite such a source, return an empty basis. The finding will be
  recorded as unverified and forced to neutral so it cannot move any number.
  That is the correct outcome — do not invent a citation to avoid it.
- confidence must be exactly one of: high, medium, low.

Return ONLY a JSON object:
{{"seat": "{seat}", "ticker": "<TICKER>", "direction": "...",
  "finding": "...", "basis": ["https://..."], "confidence": "..."}}"""


def build_seat_prompt(seat, ticker, theses):
    """Return (system, user) for one seat reviewing one ticker.

    Raises KeyError for an unknown seat — a typo must not silently produce a
    generic reviewer.
    """
    meta = SEATS[seat]
    system = _SYSTEM.format(
        label=meta["label"], question=meta["question"], brief=meta["brief"],
        max_words=MAX_FINDING_WORDS, seat=seat)

    recent = sorted(theses, key=lambda t: t.get("postedAt") or "",
                    reverse=True)[:MAX_THESES_IN_PROMPT]
    lines = ["Ticker under review: {}".format(ticker), ""]
    if recent:
        lines.append("What the analyst has said (most recent first):")
        for t in recent:
            lines.append("- [{}] {}".format(
                (t.get("postedAt") or "")[:10], (t.get("text") or "").strip()))
    else:
        lines.append("The analyst has said nothing about this name.")
    return system, "\n".join(lines)
```

- [ ] **Step 4: Run and confirm pass**

Run: `python3 -m unittest discover -s ingest/tests -k test_seats -v 2>&1 | tail -10`
Expected: PASS, `OK`

- [ ] **Step 5: Commit**

```bash
git add ingest/seats.py ingest/tests/test_seats.py
git commit -m "feat: seat definitions and prompt building"
```

---

## Task 3: Finding validation — the verification rule

This is the most important function in the plan. It is the write-time gate the Phase 1 final review found missing, and it is where the spec's verification rule lives.

**Files:**
- Modify: `ingest/seats.py`
- Test: `ingest/tests/test_seats.py`

- [ ] **Step 1: Write the failing tests**

Append to `ingest/tests/test_seats.py`, above the `if __name__` block:

```python
GOOD = {
    "seat": "semi-expert",
    "ticker": "SIVE",
    "direction": "bear",
    "finding": "Fab-light capacity assumes an unsigned Win Semi allocation.",
    "basis": ["https://www.sec.gov/Archives/edgar/data/1/x.htm"],
    "confidence": "high",
}
ALLOWED = {"SIVE", "MU", "LITE"}


class TestValidateFinding(unittest.TestCase):
    def test_good_finding_passes_through(self):
        f = seats.validate_finding(GOOD, "semi-expert", ALLOWED)
        self.assertEqual(f["direction"], "bear")
        self.assertEqual(f["verification"], "verified")
        self.assertEqual(f["ticker"], "SIVE")

    def test_empty_basis_forces_unverified_and_neutral(self):
        raw = dict(GOOD, basis=[])
        f = seats.validate_finding(raw, "semi-expert", ALLOWED)
        self.assertEqual(f["verification"], "unverified")
        self.assertEqual(f["direction"], "neutral")

    def test_non_url_basis_is_rejected_entirely(self):
        raw = dict(GOOD, basis=["I read it somewhere", "trust me"])
        f = seats.validate_finding(raw, "semi-expert", ALLOWED)
        self.assertEqual(f["basis"], [])
        self.assertEqual(f["verification"], "unverified")
        self.assertEqual(f["direction"], "neutral")

    def test_unknown_direction_becomes_neutral(self):
        raw = dict(GOOD, direction="bearish")
        f = seats.validate_finding(raw, "semi-expert", ALLOWED)
        self.assertEqual(f["direction"], "neutral")

    def test_seat_is_taken_from_the_caller_not_the_model(self):
        raw = dict(GOOD, seat="pm")
        f = seats.validate_finding(raw, "semi-expert", ALLOWED)
        self.assertEqual(f["seat"], "semi-expert")

    def test_out_of_universe_ticker_is_rejected(self):
        raw = dict(GOOD, ticker="TSLA")
        self.assertIsNone(seats.validate_finding(raw, "semi-expert", ALLOWED))

    def test_empty_finding_text_is_rejected(self):
        self.assertIsNone(
            seats.validate_finding(dict(GOOD, finding="  "), "semi-expert", ALLOWED))

    def test_non_dict_is_rejected(self):
        self.assertIsNone(seats.validate_finding("nope", "semi-expert", ALLOWED))
        self.assertIsNone(seats.validate_finding(None, "semi-expert", ALLOWED))

    def test_overlong_finding_is_truncated_to_the_word_cap(self):
        raw = dict(GOOD, finding=" ".join(["word"] * 200))
        f = seats.validate_finding(raw, "semi-expert", ALLOWED)
        self.assertEqual(len(f["finding"].split()), seats.MAX_FINDING_WORDS)

    def test_unknown_confidence_becomes_low(self):
        f = seats.validate_finding(dict(GOOD, confidence="certain"),
                                   "semi-expert", ALLOWED)
        self.assertEqual(f["confidence"], "low")
```

Add `import scorer  # noqa: E402` below the `import seats` line at the top of the test file.

- [ ] **Step 2: Run and confirm failure**

Run: `python3 -m unittest discover -s ingest/tests -k TestValidateFinding -v 2>&1 | tail -10`
Expected: FAIL — `module 'seats' has no attribute 'validate_finding'`

- [ ] **Step 3: Implement**

Append to `ingest/seats.py`:

```python
CONFIDENCES = ("high", "medium", "low")
DEFAULT_CONFIDENCE = "low"
MAX_BASIS = 5


def _coerce_str(value):
    return value.strip() if isinstance(value, str) else ""


def _clean_basis(raw):
    """Keep only http(s) URLs. A citation that is not a link is not a citation."""
    out = []
    if isinstance(raw, list):
        for item in raw:
            url = _coerce_str(item)
            if url.startswith("http://") or url.startswith("https://"):
                out.append(url)
    return out[:MAX_BASIS]


def validate_finding(raw, seat, allowed_tickers):
    """Coerce one seat's JSON into a trusted finding, or return None to drop it.

    THE VERIFICATION RULE lives here: a finding with no citable basis is marked
    unverified AND forced to direction "neutral". Because scorer weighs a
    research neutral at exactly 0.0, an unverified finding is visible in the
    brief and cannot move a single number. That is the guard against the model
    asserting something it cannot support.

    Never trusts the model for the seat name, the ticker universe, or the
    direction vocabulary — all three are checked against the caller's values.
    """
    if not isinstance(raw, dict):
        return None

    finding = _coerce_str(raw.get("finding"))
    if not finding:
        return None

    ticker = _coerce_str(raw.get("ticker")).upper()
    if ticker not in {t.upper() for t in allowed_tickers}:
        return None

    words = finding.split()
    if len(words) > MAX_FINDING_WORDS:
        finding = " ".join(words[:MAX_FINDING_WORDS])

    direction = _coerce_str(raw.get("direction")).lower()
    if direction not in scorer.VALID_DIRECTIONS:
        direction = "neutral"

    basis = _clean_basis(raw.get("basis"))
    verification = "verified" if basis else "unverified"
    if not basis:
        direction = "neutral"

    confidence = _coerce_str(raw.get("confidence")).lower()
    if confidence not in CONFIDENCES:
        confidence = DEFAULT_CONFIDENCE

    return {
        "seat": seat,                 # the caller's, never the model's
        "ticker": ticker,
        "direction": direction,
        "finding": finding,
        "basis": basis,
        "verification": verification,
        "confidence": confidence,
    }
```

- [ ] **Step 4: Run and confirm pass**

Run: `python3 -m unittest discover -s ingest/tests -k test_seats -v 2>&1 | tail -6`
Expected: PASS, `OK`

- [ ] **Step 5: Commit**

```bash
git add ingest/seats.py ingest/tests/test_seats.py
git commit -m "feat: finding validation and the verification rule

An uncited finding is marked unverified and forced to neutral. Since
scorer weighs a research neutral at 0.0, it is visible but inert."
```

---

## Task 4: Turn a finding into a thesis record

**Files:**
- Modify: `ingest/seats.py`
- Test: `ingest/tests/test_seats.py`

- [ ] **Step 1: Write the failing tests**

Append to `ingest/tests/test_seats.py`:

```python
class TestFindingToThesis(unittest.TestCase):
    def _thesis(self, **over):
        f = seats.validate_finding(dict(GOOD, **over), "semi-expert", ALLOWED)
        return seats.finding_to_thesis(f, now=NOW)

    def test_source_is_research_so_the_scorer_treats_it_asymmetrically(self):
        self.assertEqual(self._thesis()["source"], scorer.RESEARCH_SOURCE)

    def test_author_is_the_seat_not_the_analyst(self):
        self.assertEqual(self._thesis()["author"], "semi-expert")

    def test_conviction_is_never_high(self):
        # convictionHits gate tiers. A research thesis must never claim high
        # conviction, belt-and-braces alongside the scorer guard.
        self.assertEqual(self._thesis()["conviction"], "normal")

    def test_direction_and_verification_ride_along(self):
        t = self._thesis()
        self.assertEqual(t["direction"], "bear")
        self.assertEqual(t["verification"], "verified")

    def test_ticker_list_is_exactly_the_reviewed_name(self):
        self.assertEqual(self._thesis()["tickers"], ["SIVE"])

    def test_source_url_is_the_first_basis_entry(self):
        self.assertEqual(self._thesis()["sourceUrl"], GOOD["basis"][0])

    def test_id_is_stable_for_the_same_finding(self):
        self.assertEqual(self._thesis()["id"], self._thesis()["id"])

    def test_id_differs_for_a_different_finding(self):
        self.assertNotEqual(self._thesis()["id"],
                            self._thesis(finding="Something else entirely.")["id"])

    def test_text_names_the_seat_so_the_feed_is_readable(self):
        self.assertIn("Semiconductor expert", self._thesis()["text"])

    def test_a_research_thesis_scores_zero_when_bullish(self):
        t = self._thesis(direction="bull")
        self.assertEqual(scorer._direction_weight(t), 0.0)

    def test_a_research_thesis_subtracts_when_bearish(self):
        self.assertEqual(scorer._direction_weight(self._thesis()), -1.0)

    def test_an_uncited_finding_is_visible_but_inert(self):
        # The verification rule end to end: no basis -> unverified -> forced
        # neutral -> research neutral weighs 0.0. It reaches the brief and
        # cannot move a single number.
        f = seats.validate_finding(dict(GOOD, basis=[]), "semi-expert", ALLOWED)
        th = seats.finding_to_thesis(f, now=NOW)
        self.assertEqual(th["verification"], "unverified")
        self.assertEqual(th["direction"], "neutral")
        self.assertEqual(scorer._direction_weight(th), 0.0)
```

- [ ] **Step 2: Run and confirm failure**

Run: `python3 -m unittest discover -s ingest/tests -k TestFindingToThesis -v 2>&1 | tail -8`
Expected: FAIL — `module 'seats' has no attribute 'finding_to_thesis'`

- [ ] **Step 3: Implement**

Add `import parser as msgparser` to the imports at the top of `ingest/seats.py` (below `import scorer`). **Use the alias** — `ingest/bot.py:30` does the same, because a bare `parser` is confusable with the module of that name that Python used to ship. Then append:

```python
def finding_to_thesis(finding, now):
    """Build the thesis record a validated finding becomes.

    `now` is required rather than defaulted so this stays pure and testable —
    the caller stamps the time.

    conviction is hard-coded "normal": convictionHits gate tiers in
    assign_tiers, and although scorer now excludes research from that count,
    writing "high" here would be a second way in if that guard ever regresses.
    """
    label = SEATS[finding["seat"]]["label"]
    text = "{}: {}".format(label, finding["finding"])
    source_url = finding["basis"][0] if finding["basis"] else ""
    return {
        "id": msgparser.derive_source_id(text, source_url, now),
        "source": scorer.RESEARCH_SOURCE,
        "author": finding["seat"],
        "sourceUrl": source_url,
        "postedAt": now,
        "ingestedAt": now,
        "text": text,
        "tickers": [finding["ticker"]],
        "conviction": "normal",
        "tags": ["research", finding["seat"]],
        "direction": finding["direction"],
        "verification": finding["verification"],
    }
```

- [ ] **Step 4: Run the whole suite**

Run: `python3 -m unittest discover -s ingest/tests 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add ingest/seats.py ingest/tests/test_seats.py
git commit -m "feat: convert a validated finding into a research thesis"
```

---

## Task 5: Choose which names get covered

**Files:**
- Modify: `ingest/seats.py`
- Test: `ingest/tests/test_seats.py`

- [ ] **Step 1: Write the failing tests**

Append to `ingest/tests/test_seats.py`:

```python
class TestSelectCoverage(unittest.TestCase):
    def _pri(self, pairs):
        return [{"ticker": t, "score": s} for t, s in pairs]

    def test_stance_changes_come_first(self):
        pri = self._pri([("AAA", 90), ("BBB", 80), ("CCC", 1)])
        verdicts = [{"ticker": "CCC", "updatedAt": "2026-07-25T00:00:00Z"}]
        picked, _ = seats.select_coverage(
            pri, verdicts, [], since="2026-07-20", cap=2)
        self.assertEqual(picked[0], "CCC")

    def test_names_with_enough_new_theses_come_next(self):
        pri = self._pri([("AAA", 90), ("DDD", 2)])
        theses = [thesis("t%d" % i, ["DDD"], "2026-07-24T00:00:00Z")
                  for i in range(3)]
        picked, _ = seats.select_coverage(
            pri, [], theses, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["DDD"])

    def test_remainder_fills_by_score(self):
        pri = self._pri([("AAA", 90), ("BBB", 80), ("CCC", 70)])
        picked, _ = seats.select_coverage(pri, [], [], since="2026-07-20", cap=2)
        self.assertEqual(picked, ["AAA", "BBB"])

    def test_cap_is_respected_and_drops_are_reported(self):
        pri = self._pri([("A%d" % i, 100 - i) for i in range(20)])
        picked, dropped = seats.select_coverage(
            pri, [], [], since="2026-07-20", cap=12)
        self.assertEqual(len(picked), 12)
        self.assertEqual(len(dropped), 8)
        self.assertNotIn(picked[0], dropped)

    def test_no_duplicates_when_a_name_qualifies_twice(self):
        pri = self._pri([("AAA", 90)])
        verdicts = [{"ticker": "AAA", "updatedAt": "2026-07-25T00:00:00Z"}]
        theses = [thesis("t%d" % i, ["AAA"], "2026-07-24T00:00:00Z")
                  for i in range(5)]
        picked, _ = seats.select_coverage(
            pri, verdicts, theses, since="2026-07-20", cap=12)
        self.assertEqual(picked, ["AAA"])

    def test_old_verdicts_and_old_theses_do_not_qualify(self):
        pri = self._pri([("AAA", 90), ("ZZZ", 1)])
        verdicts = [{"ticker": "ZZZ", "updatedAt": "2026-07-01T00:00:00Z"}]
        theses = [thesis("t%d" % i, ["ZZZ"], "2026-07-01T00:00:00Z")
                  for i in range(9)]
        picked, _ = seats.select_coverage(
            pri, verdicts, theses, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])
```

- [ ] **Step 2: Run and confirm failure**

Run: `python3 -m unittest discover -s ingest/tests -k TestSelectCoverage -v 2>&1 | tail -8`
Expected: FAIL — `module 'seats' has no attribute 'select_coverage'`

- [ ] **Step 3: Implement**

Append to `ingest/seats.py`:

```python
MAX_COVERAGE = 12
NEW_THESIS_TRIGGER = 3


def select_coverage(priorities, verdicts, theses, since, cap=MAX_COVERAGE):
    """Pick which names the seats review this run. Returns (selected, dropped).

    Priority order, because the cap is tight and decisions matter more than
    coverage: names whose stance moved at the last review, then names the
    analyst has posted about at least NEW_THESIS_TRIGGER times since, then the
    highest-scoring remainder.

    Reviewing every Core name weekly is deliberately rejected — roughly three
    times the cost for names where no decision is pending. `dropped` is
    returned so the caller can log what the cap cut; silent truncation reads
    as full coverage when it is not.
    """
    ranked = [p["ticker"] for p in priorities]
    rank_of = {t: i for i, t in enumerate(ranked)}

    changed = [v["ticker"] for v in verdicts
               if (v.get("updatedAt") or "") >= since and v.get("ticker") in rank_of]

    counts = {}
    for th in theses:
        if (th.get("postedAt") or "") < since:
            continue
        for sym in th.get("tickers", []):
            counts[sym] = counts.get(sym, 0) + 1
    busy = [t for t, n in counts.items()
            if n >= NEW_THESIS_TRIGGER and t in rank_of]

    selected = []
    for group in (changed, busy, ranked):
        for sym in sorted(group, key=lambda s: rank_of[s]):
            if sym not in selected:
                selected.append(sym)
            if len(selected) >= cap:
                break
        if len(selected) >= cap:
            break

    dropped = [t for t in ranked if t not in selected]
    return selected, dropped
```

- [ ] **Step 4: Run and confirm pass**

Run: `python3 -m unittest discover -s ingest/tests 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add ingest/seats.py ingest/tests/test_seats.py
git commit -m "feat: coverage selection with an explicit cap and reported drops"
```

---

## Task 6: Orchestrate the run with an injected call_fn

**Files:**
- Modify: `ingest/seats.py`
- Test: `ingest/tests/test_seats.py`

- [ ] **Step 1: Write the failing tests**

Append to `ingest/tests/test_seats.py`:

```python
class TestRunSeats(unittest.TestCase):
    def _call_fn(self, direction="bear"):
        def call_fn(system, user):
            sym = user.split("\n")[0].split(": ")[1].strip()
            return dict(GOOD, ticker=sym, direction=direction)
        return call_fn

    def test_one_thesis_per_seat_per_ticker(self):
        out = seats.run_seats(["SIVE", "MU"], {}, self._call_fn(),
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(len(out["theses"]), 6)
        self.assertEqual(out["meta"]["seatsRun"], 3)
        self.assertEqual(out["meta"]["tickersCovered"], 2)

    def test_a_failing_seat_does_not_abort_the_run(self):
        calls = {"n": 0}

        def flaky(system, user):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            sym = user.split("\n")[0].split(": ")[1].strip()
            return dict(GOOD, ticker=sym)

        out = seats.run_seats(["SIVE"], {}, flaky,
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(len(out["theses"]), 2)
        self.assertEqual(len(out["meta"]["failures"]), 1)

    def test_a_rejected_finding_is_dropped_not_written(self):
        def bad(system, user):
            return {"finding": "", "ticker": "SIVE"}

        out = seats.run_seats(["SIVE"], {}, bad,
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(out["theses"], [])
        self.assertEqual(out["meta"]["rejected"], 3)

    def test_every_written_thesis_is_research_sourced(self):
        out = seats.run_seats(["SIVE"], {}, self._call_fn(),
                              allowed_tickers=ALLOWED, now=NOW)
        for t in out["theses"]:
            self.assertEqual(t["source"], scorer.RESEARCH_SOURCE)

    def test_theses_by_ticker_reaches_the_prompt(self):
        seen = {}

        def spy(system, user):
            seen["user"] = user
            return dict(GOOD, ticker="SIVE")

        seats.run_seats(["SIVE"],
                        {"SIVE": [thesis("fab-light ramp", ["SIVE"])]},
                        spy, allowed_tickers=ALLOWED, now=NOW)
        self.assertIn("fab-light ramp", seen["user"])
```

- [ ] **Step 2: Run and confirm failure**

Run: `python3 -m unittest discover -s ingest/tests -k TestRunSeats -v 2>&1 | tail -8`
Expected: FAIL — `module 'seats' has no attribute 'run_seats'`

- [ ] **Step 3: Implement**

Append to `ingest/seats.py` (`sys` is already imported at the top of the module):

```python
def run_seats(tickers, theses_by_ticker, call_fn, *, allowed_tickers, now,
              only_seats=None):
    """Run every seat over every ticker. Returns {theses, meta}.

    `call_fn(system, user) -> dict` is injected so this module never touches
    the network — a Claude Code session supplies it (see synthesize.py for the
    same pattern and docs/GUIDE.md section 3).

    One seat failing on one ticker is isolated: it is recorded in
    meta.failures and the run continues. A finding that fails validation is
    counted in meta.rejected and simply not written — a bad finding must never
    become a thesis.
    """
    seat_keys = [s for s in SEATS if not only_seats or s in only_seats]
    out = []
    failures = []
    rejected = 0

    for ticker in tickers:
        context = theses_by_ticker.get(ticker, [])
        for seat in seat_keys:
            system, user = build_seat_prompt(seat, ticker, context)
            try:
                raw = call_fn(system, user)
            except Exception as exc:  # noqa: BLE001 — isolate this one call
                failures.append({"seat": seat, "ticker": ticker,
                                 "error": str(exc)})
                print("WARN seat {} failed on {}: {}".format(seat, ticker, exc),
                      file=sys.stderr)
                continue
            finding = validate_finding(raw, seat, allowed_tickers)
            if finding is None:
                rejected += 1
                continue
            out.append(finding_to_thesis(finding, now))

    return {
        "theses": out,
        "meta": {
            "generatedAt": now,
            "seatsRun": len(seat_keys),
            "tickersCovered": len(tickers),
            "written": len(out),
            "rejected": rejected,
            "failures": failures,
        },
    }
```

- [ ] **Step 4: Run the whole suite**

Run: `python3 -m unittest discover -s ingest/tests 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add ingest/seats.py ingest/tests/test_seats.py
git commit -m "feat: orchestrate the seats with an injected call_fn

Per-call failures are isolated and rejected findings are counted, never
written. No network in this module -- a Claude Code session supplies
call_fn, matching the synthesize.py pattern."
```

---

## Task 7: Merge research theses into the store safely

**Files:**
- Modify: `ingest/seats.py`
- Test: `ingest/tests/test_seats.py`

- [ ] **Step 1: Write the failing tests**

Append to `ingest/tests/test_seats.py`:

```python
class TestMerge(unittest.TestCase):
    def _research(self, text="x", ident="r1"):
        return {"id": ident, "source": "research", "author": "pm",
                "text": text, "tickers": ["MU"], "postedAt": NOW,
                "direction": "bear", "verification": "verified"}

    def test_new_research_is_appended(self):
        existing = [thesis("analyst post", ["MU"])]
        merged = seats.merge_research_theses(existing, [self._research()])
        self.assertEqual(len(merged), 2)

    def test_analyst_theses_are_never_modified(self):
        analyst = thesis("analyst post", ["MU"])
        merged = seats.merge_research_theses([analyst], [self._research()])
        self.assertEqual(merged[0], analyst)

    def test_duplicate_research_id_replaces_not_duplicates(self):
        existing = [self._research(text="old")]
        merged = seats.merge_research_theses(existing, [self._research(text="new")])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["text"], "new")

    def test_research_cannot_overwrite_an_analyst_thesis_with_the_same_id(self):
        analyst = dict(thesis("analyst post", ["MU"]), id="clash")
        incoming = dict(self._research(ident="clash"), text="research")
        merged = seats.merge_research_theses([analyst], [incoming])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["text"], "analyst post")

    def test_input_list_is_not_mutated(self):
        existing = [thesis("analyst post", ["MU"])]
        seats.merge_research_theses(existing, [self._research()])
        self.assertEqual(len(existing), 1)
```

- [ ] **Step 2: Run and confirm failure**

Run: `python3 -m unittest discover -s ingest/tests -k TestMerge -v 2>&1 | tail -8`
Expected: FAIL — `module 'seats' has no attribute 'merge_research_theses'`

- [ ] **Step 3: Implement**

Append to `ingest/seats.py`:

```python
def merge_research_theses(existing, incoming):
    """Return a new list with `incoming` research theses merged into `existing`.

    Re-running a review replaces that run's own findings rather than stacking
    duplicates, because finding_to_thesis derives a stable id from the text.

    An analyst thesis is never modified or replaced, even on an id collision:
    the analyst feed is the operator's captured record and this module has no
    business editing it. On a clash the incoming research finding is dropped.
    """
    out = [dict(t) for t in existing]
    by_id = {t.get("id"): i for i, t in enumerate(out)}
    for th in incoming:
        idx = by_id.get(th.get("id"))
        if idx is None:
            by_id[th.get("id")] = len(out)
            out.append(dict(th))
        elif out[idx].get("source") == scorer.RESEARCH_SOURCE:
            out[idx] = dict(th)
    return out
```

- [ ] **Step 4: Run the whole suite**

Run: `python3 -m unittest discover -s ingest/tests 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add ingest/seats.py ingest/tests/test_seats.py
git commit -m "feat: merge research theses without ever touching the analyst feed"
```

---

## Task 8: Stop attributing research findings to the analyst

`desk.html:1998` renders the tooltip `"Mentioned N× by @aleabitoreddit"` from `priority.mentions`, and `mentions` counts research theses too. The moment a research thesis exists, that tooltip credits the desk's own findings to the analyst.

**Files:**
- Modify: `ingest/generate_data_js.py`
- Modify: `desk.html:1996-2000`
- Test: `ingest/tests/test_generate.py`

- [ ] **Step 1: Write the failing test**

Append to `ingest/tests/test_generate.py`, above the `if __name__` block:

```python
class TestResearchMentionsStamp(unittest.TestCase):
    def test_research_mentions_reaches_the_ticker_stamp(self):
        # desk.html reads t["priority"], not the top-level priorities array,
        # so the analyst-vs-research split has to be mirrored here or the
        # ticker tooltip cannot tell them apart.
        d = gen.build_data()
        stamped = [t for t in d["tickers"] if t.get("priority")]
        self.assertTrue(stamped, "no ticker carried a priority stamp")
        self.assertIn("researchMentions", stamped[0]["priority"])
```

- [ ] **Step 2: Run and confirm failure**

Run: `python3 -m unittest discover -s ingest/tests -k TestResearchMentionsStamp -v 2>&1 | tail -8`
Expected: FAIL — `'researchMentions' not found in {...}`

- [ ] **Step 3: Implement the passthrough**

In `ingest/generate_data_js.py`, add `researchMentions` to the per-ticker priority stamp, immediately after `"bearMentions"`:

```python
                "researchMentions": p["researchMentions"],
```

- [ ] **Step 4: Fix the tooltip**

In `desk.html`, replace the block at lines 1996-2000:

```javascript
        if (ticker.priority) {
          var prio = el("span", "tk-badge tk-prio", ticker.priority.mentions + "× mentioned");
          prio.title = "Mentioned " + ticker.priority.mentions + "× by @aleabitoreddit"
            + (ticker.priority.convictionHits ? " · " + ticker.priority.convictionHits + " with high-conviction language" : "");
          badges.appendChild(prio);
        }
```

with:

```javascript
        if (ticker.priority) {
          var research = ticker.priority.researchMentions || 0;
          var analyst = ticker.priority.mentions - research;
          var prio = el("span", "tk-badge tk-prio", ticker.priority.mentions + "× mentioned");
          // `mentions` counts desk research too, so the tooltip must split them
          // — crediting the desk's own findings to the analyst would be a lie.
          prio.title = "Mentioned " + analyst + "× by @aleabitoreddit"
            + (research ? " · " + research + " desk research finding" + (research === 1 ? "" : "s") : "")
            + (ticker.priority.bearMentions ? " · " + ticker.priority.bearMentions + " against" : "")
            + (ticker.priority.convictionHits ? " · " + ticker.priority.convictionHits + " with high-conviction language" : "");
          badges.appendChild(prio);
        }
```

- [ ] **Step 5: Regenerate and verify in the browser**

```bash
python3 -c "import json;print(json.load(open('ingest/store/base.json'))['meta'])"
```

Bump `meta.version` by one thousandth and set `meta.lastUpdated` to the current UTC time as `YYYY-MM-DDTHH:MM:SSZ`, then:

```bash
python3 ingest/generate_data_js.py
python3 -m unittest discover -s ingest/tests 2>&1 | tail -3
nohup python3 -m http.server 8801 --bind 127.0.0.1 > /tmp/aie-verify.log 2>&1 &
```

Open `http://127.0.0.1:8801/desk.html`, expand any ticker tile, and hover the "N× mentioned" badge. With no research theses in the store yet the tooltip must read exactly as before (research count is 0, so no extra clause). Check the browser console is clean. Then `pkill -f "http.server 8801"`.

- [ ] **Step 6: Commit**

```bash
git add ingest/generate_data_js.py ingest/tests/test_generate.py desk.html ingest/store/base.json data.js
git commit -m "fix: do not credit desk research findings to the analyst

mentions counts research theses too, so the ticker tooltip would have
attributed the desk's own findings to @aleabitoreddit the moment Phase 2
wrote one. Splits the count and surfaces the bear tally alongside."
```

---

## Task 9: The /pre-review skill

**Files:**
- Create: `.claude/skills/pre-review/SKILL.md`
- Modify: `.claude/skills/weekly-review/SKILL.md`

- [ ] **Step 1: Write the skill**

Create `.claude/skills/pre-review/SKILL.md`:

```markdown
---
name: pre-review
description: Run the three expert review seats over this week's shortlist before the weekly desk review, writing checked outside research into the thesis feed. Use when the operator says "/pre-review", "run the seats", "pre-review", or "research before the weekly".
---

# Pre-Review — the three expert seats

The desk follows one long-only analyst, so `theses.json` contains no bear case
and nothing outside his field of view. This pass brings in what he missed. Run
it BEFORE `/weekly-review`, so the verdicts are written with both sides on the
table.

## What the seats are

| Seat | The one question it answers |
|---|---|
| `semi-expert` | Is the technical claim true? Ramp timelines, process and packaging limits, yields, qualification status, capacity assumptions. |
| `fundamental` | Do the numbers work? Revenue maths, dilution, margins, customer concentration, valuation against peers. |
| `pm` | Is this a good bet at this price? What is priced in, what the downside is, what would force an exit. |

**A seat is not an expert.** It is this same model with a different instruction
and web access. What the structure buys is three separate passes so three
different questions actually get asked, and forced outside research so new
facts enter the store. Never present a finding as though a domain engineer
reviewed it.

## Procedure

1. **Refresh prices** (needs network): `python3 ingest/fetch_prices.py`.
   Continue if it fails — prices are context here, not the point.

2. **Pick the shortlist.** Load the store and call
   `seats.select_coverage(priorities, verdicts, theses, since, cap=12)`, where
   `since` is `verdicts.json` `meta.reviewedAt`. Report the returned `dropped`
   list to the operator — never let a cap read as full coverage.

3. **Run the seats.** For each selected ticker and each seat, build the prompt
   with `seats.build_seat_prompt(seat, ticker, context)`, then **do the
   research yourself**: search for primary sources, read them, and answer the
   seat's one question. Supply the result through an injected `call_fn`, the
   same way `docs/GUIDE.md` section 3 describes for the Brain.

   **The basis rule is absolute.** Cite SEC filings, earnings-call
   transcripts, company IR material, exchange notices, or established industry
   data providers (TrendForce, SEMI, Counterpoint). Content aggregators and
   SEO summaries do not qualify. If you cannot cite one, return an empty
   `basis` — the finding is then recorded unverified and forced to neutral so
   it cannot move a number. **That is the correct outcome. Never invent a
   citation to avoid it.**

4. **Write the findings.** Merge with
   `seats.merge_research_theses(existing, out["theses"])`, save `theses.json`,
   bump `base.json` `meta.version`, and regenerate:
   `python3 ingest/generate_data_js.py`.

5. **Report to the operator**, in this order:
   - Anything the seats found that CONTRADICTS the analyst — this is the
     entire reason the pass exists, so it leads.
   - Which names were covered, and which the cap dropped.
   - How many findings came back unverified, and on what.
   - Any seat that failed and on which name.

## Hard rules

- The seats write ONLY research theses into `theses.json`. They never touch
  `verdicts.json`, `memos.json`, `calls.json`, or an analyst thesis.
- Every finding is at most 60 words. The whole report is one page. Three
  essays the operator skims are worse than one page he finishes.
- `direction` is exactly `bull`, `bear` or `neutral`, lowercase. Anything else
  scores 0.0 and the bear case is thrown away.
- Research corrects a score downward but never inflates one, and never buys a
  name tier coverage. That asymmetry is deliberate — do not work around it.
- Never hand-edit `data.js` (CLAUDE.md rule 6).
- Research support, not investment advice.
```

- [ ] **Step 2: Point the weekly review at it**

In `.claude/skills/weekly-review/SKILL.md`, insert immediately above the line `1. **Refresh prices** (needs network):`:

```markdown
0. **Run `/pre-review` first** (unless the operator says to skip it). The three
   expert seats research this week's shortlist and write checked outside
   research into the thesis feed, so the verdicts below are written with a bear
   case on the table rather than from one analyst's posts alone. If it was
   skipped, say so at the top of the report — a review with no counter-evidence
   is a weaker review and the operator should know which kind he got.

```

- [ ] **Step 3: Verify both skills parse**

Run:

```bash
head -5 .claude/skills/pre-review/SKILL.md
grep -n "pre-review" .claude/skills/weekly-review/SKILL.md
```

Expected: valid YAML frontmatter with `name: pre-review`, and one hit in the weekly-review skill.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/pre-review/SKILL.md .claude/skills/weekly-review/SKILL.md
git commit -m "feat: /pre-review skill runs the three seats before the weekly"
```

---

## Task 10: Docs

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/superpowers/specs/2026-07-26-expert-review-team-design.md`

- [ ] **Step 1: Add the seats to CLAUDE.md**

In `CLAUDE.md`, immediately after the `v5 — Conviction tiers + Desk verdicts` bullet, add:

```markdown
- **Expert review seats** ✅ done (2026-07-26, spec Phase 2). Three reviewers —
  `semi-expert` (is the technical claim true?), `fundamental` (do the numbers
  work?), `pm` (is this a good bet at this price?) — research a shortlist of up
  to 12 names before each weekly review and write findings into `theses.json`
  as `source: "research"` theses. `ingest/seats.py` is pure and takes an
  injected `call_fn`, exactly like `synthesize.py`, so it runs in a Claude Code
  session with no API key. **The verification rule:** a finding with no citable
  primary source is marked `unverified` and forced to `direction: "neutral"` —
  visible in the brief, and worth exactly 0.0 to any score. Research can correct
  a name downward but can never inflate its rank, buy it tier coverage, or add
  conviction hits. Run via the **`/pre-review` skill**.
```

- [ ] **Step 2: Add the thesis fields to the schema block**

In the `data.js` schema section of `CLAUDE.md`, the theses record currently ends with `direction } ],   // "bull" | "bear" | "neutral", LOWERCASE`. Replace that line with:

```
                  direction,        // "bull" | "bear" | "neutral", LOWERCASE
                  verification } ], // "verified" | "unverified" (research only)
```

And in the `priorities` record, add `researchMentions` after `bearMentions`.

- [ ] **Step 3: Add the ROADMAP entry**

In `docs/ROADMAP.md`, directly below the Phase 1 entry, add:

```markdown
> **Expert review team, Phase 2 — the three seats (✅ 2026-07-26).**
> `ingest/seats.py` runs `semi-expert`, `fundamental` and `pm` over a shortlist
> of up to 12 names (stance changes first, then names with 3+ new theses, then
> by score — drops are reported, never silent). Findings become
> `source: "research"` theses. Pure module with an injected `call_fn`, so no
> API key is needed; driven by the new `/pre-review` skill.
> **The verification rule:** no citable primary source means `unverified` and a
> forced `neutral` direction, which scores exactly 0.0 — visible but inert.
> Also closed a hole where two research theses marked `conviction: "high"`
> promoted a name to Core past the `weightedMentions` guard.
> **Not yet built — Phases 3–5:** `claims.json` and claim judging, the
> performance-page split, hit-rate weighting, the scheduled overnight run.
```

- [ ] **Step 4: Update the spec status header**

In `docs/superpowers/specs/2026-07-26-expert-review-team-design.md`, change the status line from `Phase 1 shipped 2026-07-26; Phases 2–5 not yet built.` to `Phases 1–2 shipped 2026-07-26; Phases 3–5 not yet built.`, and move the seats, verification rule and research-thesis items from the "What has not" list into "What shipped". Add one line noting that the seat output's `claims` array was deferred to Phase 3, since `claims.json` does not exist yet.

- [ ] **Step 5: Verify no doc contradicts the code**

Run:

```bash
grep -rn --include='*.md' 'claims' .claude/skills/pre-review/SKILL.md || echo "(no claims references — correct for Phase 2)"
python3 -m unittest discover -s ingest/tests 2>&1 | tail -2
```

Expected: no `claims` references in the new skill, suite `OK`.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md docs/ROADMAP.md docs/superpowers/specs/2026-07-26-expert-review-team-design.md
git commit -m "docs: describe the expert review seats and the verification rule"
```

---

## Done when

- `python3 -m unittest discover -s ingest/tests` reports `OK`
- `ingest/seats.py` has no network call, no file I/O, and no API client
- An uncited finding comes back `unverified` with `direction: "neutral"`, and `scorer._direction_weight` returns `0.0` for it
- Two research theses marked `conviction: "high"` leave a name on `radar`, not `core`
- `merge_research_theses` never modifies an analyst thesis, even on an id collision
- The ticker tooltip splits analyst mentions from desk research findings
- `/pre-review` exists and `/weekly-review` step 0 points at it

## Not in this plan

- **Plan 3 — the memory.** `ingest/store/claims.json`, extracting dated predictions from findings, judging them, hit rate with the unfalsifiable share, and splitting `performance.html` into Calls and Claims.
- **Plan 4 — hit-rate weighting.** Gated on 20+ judged claims per source, so it cannot start before Plan 3 has run for months.
- **Plan 5 — scheduling.** The unattended overnight run.
