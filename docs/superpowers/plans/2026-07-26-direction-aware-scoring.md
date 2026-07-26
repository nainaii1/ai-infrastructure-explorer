# Direction-Aware Scoring Implementation Plan (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach `ingest/scorer.py` that a thesis can argue *against* a ticker, retire the conviction multiplier, and stop `data.js` from ever being written in a truncated state.

**Architecture:** Every thesis gains an optional `direction` field (`bull` / `bear` / `neutral`). `compute_priorities` sums a *signed* contribution per mention instead of an unsigned one. Bear findings subtract; research-sourced bull findings contribute zero so the model cannot amplify its own view; absent directions read as `neutral` and weigh exactly 1.0, so migrating the existing 258 theses changes no score. Separately, `CONVICTION_WEIGHT` drops to `0.0`, which is the only thing in this phase that re-ranks anything. Finally `write_data_js` refuses to write a payload missing expected top-level blocks.

**Tech Stack:** Python 3 standard library only, `unittest`. No new dependencies. This phase touches no HTML, CSS or JavaScript.

**Source spec:** `docs/superpowers/specs/2026-07-26-expert-review-team-design.md`

---

## Background the engineer needs

`ingest/scorer.py` ranks tickers by how much the tracked analyst talks about them. Today:

```
score = Σ(recency_weight × focus_weight) × (1 + CONVICTION_WEIGHT × conviction_hits)
```

- `recency_weight` is exponential decay, half-life 14 days.
- `focus_weight` is `1/√(tickers in the post)`, so a name buried in a 12-ticker list post counts less than a dedicated post.
- `conviction_hits` counts posts where `parser.py` keyword-matched phrases like "top pick" or "high conviction".

Two facts that shape this plan:

1. **`assign_tiers` does not read `score`.** It reads `weightedMentions` and `convictionHits` directly. Retiring the conviction multiplier therefore changes the score ranking but moves **no ticker between core / watch / radar**. Do not "fix" this — it is intended.
2. **The store grows every week.** `ingest/tests/test_generate.py` says so in a comment: assert structural invariants, never live counts. All permanent tests in this plan use synthetic fixtures. The one check against real store numbers is a manual verification step, not a test.
3. **No store migration script is written, and none should be.** The spec says the 258 existing theses "default to `neutral`". That default is implemented by *reading* an absent `direction` as `neutral` in `_direction_weight`, not by rewriting `theses.json`. Rewriting 258 records to add a field whose value is already the default would be churn with no behavioural difference, and `theses.json` is append-only in practice — `bot.py` appends to it while this work happens. Do not add a backfill script.

## File structure

| File | Responsibility | Action |
|---|---|---|
| `ingest/scorer.py` | Signed per-mention weighting, retired multiplier, richer priority record | Modify |
| `ingest/generate_data_js.py` | Refuse to write a truncated `data.js` | Modify |
| `ingest/tests/test_scorer.py` | Direction and conviction behaviour | Modify |
| `ingest/tests/test_generate.py` | Completeness guard behaviour | Modify |
| `CLAUDE.md` | Scoring formula is documented there and will be stale | Modify |
| `docs/ROADMAP.md` | Living status doc | Modify |

No files are created. No files are deleted.

---

## Task 1: Refuse to write a truncated data.js

Guards the failure seen on 2026-07-26: a `bot.py` process running since 30 June held a stale module in memory and rewrote `data.js` without `glossary`, `desk`, `memos`, `vault`, `calls` or `benchmarkQuote` on every ingest. Four pages broke for days with no signal.

**Files:**
- Modify: `ingest/generate_data_js.py`
- Test: `ingest/tests/test_generate.py`

- [ ] **Step 1: Write the failing tests**

Append to `ingest/tests/test_generate.py`:

```python
class TestCompletenessGuard(unittest.TestCase):
    def test_build_data_has_every_required_key(self):
        d = gen.build_data()
        for key in gen.REQUIRED_KEYS:
            self.assertIn(key, d, "build_data() dropped %r" % key)

    def test_missing_key_raises_and_names_it(self):
        d = gen.build_data()
        del d["calls"]
        with self.assertRaises(RuntimeError) as ctx:
            gen._assert_complete(d)
        self.assertIn("calls", str(ctx.exception))

    def test_emptied_store_backed_key_raises(self):
        # verdicts.json is non-empty in this repo, so an empty desk block in a
        # built payload means assembly lost it.
        d = gen.build_data()
        d["desk"] = {}
        with self.assertRaises(RuntimeError) as ctx:
            gen._assert_complete(d)
        self.assertIn("verdicts.json", str(ctx.exception))

    def test_none_benchmark_quote_is_allowed(self):
        # benchmarkQuote is legitimately None when SMH has no price row; the
        # guard checks presence, not truthiness, for non-store-backed keys.
        d = gen.build_data()
        d["benchmarkQuote"] = None
        gen._assert_complete(d)
```

- [ ] **Step 2: Run the tests to verify they fail**

All commands in this plan run from the repo root. Targeted runs use `-k`.

Run: `python3 -m unittest discover -s ingest/tests -k TestCompletenessGuard -v 2>&1 | tail -20`
Expected: FAIL — `AttributeError: module 'generate_data_js' has no attribute 'REQUIRED_KEYS'`

- [ ] **Step 3: Write the implementation**

In `ingest/generate_data_js.py`, add after the `PRICE_FIELDS` line (around line 34):

```python
# Every top-level key build_data() is contracted to emit. A payload missing any
# of these is refused rather than written — see _assert_complete.
REQUIRED_KEYS = (
    "meta", "countries", "categories", "center", "mapIntro", "glossary",
    "zones", "tickers", "theses", "priorities", "brain", "desk", "memos",
    "vault", "calls", "benchmarkQuote",
)

# Keys whose content comes from a store file. If the file has content, the
# assembled block must too.
STORE_BACKED = {
    "brain": "brain.json",
    "desk": "verdicts.json",
    "memos": "memos.json",
    "vault": "vault.json",
    "calls": "calls.json",
}
```

Then add this function immediately above `def render(data):` (around line 157):

```python
def _assert_complete(data):
    """Refuse to write a data.js that has silently lost a block.

    On 2026-07-26 a long-running bot.py held a June-era module in memory and
    rewrote data.js without six top-level keys on every ingest, breaking the
    memo reader, vault, glossary and performance page for days. Nothing warned,
    because ticker-level verdicts are stamped onto ticker records and survived,
    so the watchlist still looked healthy. This makes that failure loud.
    """
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise RuntimeError(
            "data.js assembly is missing top-level keys: %s. If a long-running "
            "process produced this, restart it — it is probably holding a stale "
            "module." % ", ".join(missing)
        )
    for key, filename in STORE_BACKED.items():
        if not (STORE / filename).exists():
            continue
        if _load_optional(filename, {}) and not data.get(key):
            raise RuntimeError(
                "store/%s has content but data['%s'] is empty — refusing to "
                "write a truncated data.js." % (filename, key)
            )
```

Finally, in `write_data_js`, call it before writing. Replace:

```python
    DATA_JS.write_text(render(data), encoding="utf-8")
    return DATA_JS
```

with:

```python
    _assert_complete(data)
    DATA_JS.write_text(render(data), encoding="utf-8")
    return DATA_JS
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s ingest/tests -k TestCompletenessGuard -v 2>&1 | tail -20`
Expected: PASS, `OK`

- [ ] **Step 5: Run the whole suite**

Run: `python3 -m unittest discover -s ingest/tests 2>&1 | tail -4`
Expected: `OK` — 116 tests

- [ ] **Step 6: Commit**

```bash
git add ingest/generate_data_js.py ingest/tests/test_generate.py
git commit -m "fix: refuse to write a data.js missing top-level blocks

Guards the 2026-07-26 failure where a long-running bot.py held a stale
module and silently stripped glossary, desk, memos, vault, calls and
benchmarkQuote on every ingest, breaking four pages for days."
```

---

## Task 2: Extend the test helper to express direction and source

The existing `thesis()` helper in `test_scorer.py` cannot build a directed or research-sourced thesis. Every later task needs it, so it changes once, here.

**Files:**
- Modify: `ingest/tests/test_scorer.py:12-13`

- [ ] **Step 1: Replace the helper**

Replace these two lines in `ingest/tests/test_scorer.py`:

```python
def thesis(tickers, posted_at, conviction="normal"):
    return {"tickers": tickers, "postedAt": posted_at, "conviction": conviction}
```

with:

```python
def thesis(tickers, posted_at, conviction="normal", direction=None, source="x"):
    """Build a thesis fixture.

    direction=None omits the key entirely, which is how all 258 migrated
    records look — the scorer must read that as "neutral".
    """
    t = {"tickers": tickers, "postedAt": posted_at,
         "conviction": conviction, "source": source}
    if direction is not None:
        t["direction"] = direction
    return t
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `python3 -m unittest discover -s ingest/tests 2>&1 | tail -4`
Expected: `OK` — the added `source` key is inert until Task 4, so nothing changes.

- [ ] **Step 3: Commit**

```bash
git add ingest/tests/test_scorer.py
git commit -m "test: let the thesis fixture express direction and source"
```

---

## Task 3: Bear theses subtract, absent direction stays neutral

**Files:**
- Modify: `ingest/scorer.py`
- Test: `ingest/tests/test_scorer.py`

- [ ] **Step 1: Write the failing tests**

Append to `ingest/tests/test_scorer.py`:

```python
class TestDirection(unittest.TestCase):
    def test_absent_direction_scores_as_neutral(self):
        implicit = [thesis(["NVDA"], "2026-06-26T00:00:00Z")]
        explicit = [thesis(["NVDA"], "2026-06-26T00:00:00Z", direction="neutral")]
        self.assertEqual(
            scorer.compute_priorities(implicit, now=NOW)[0]["score"],
            scorer.compute_priorities(explicit, now=NOW)[0]["score"],
        )

    def test_bear_cancels_an_equal_bull(self):
        bull = [thesis(["AAOI"], "2026-06-26T00:00:00Z", direction="bull")]
        mixed = bull + [thesis(["AAOI"], "2026-06-26T00:00:00Z", direction="bear")]
        only_bull = scorer.compute_priorities(bull, now=NOW)[0]
        both = scorer.compute_priorities(mixed, now=NOW)[0]
        self.assertEqual(only_bull["score"], 1.0)
        self.assertEqual(both["score"], 0.0)

    def test_score_floors_at_zero_while_net_goes_negative(self):
        theses = [thesis(["POET"], "2026-06-26T00:00:00Z", direction="bear")]
        r = scorer.compute_priorities(theses, now=NOW)[0]
        self.assertEqual(r["score"], 0.0)
        self.assertEqual(r["net"], -1.0)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest discover -s ingest/tests -k TestDirection -v 2>&1 | tail -20`
Expected: FAIL — `KeyError: 'net'` and a score of `1.0` where `0.0` was expected.

- [ ] **Step 3: Write the implementation**

In `ingest/scorer.py`, add below `CONVICTION_WEIGHT = 0.5` (line 19):

```python
# Signed contribution of one mention. Research findings may subtract but never
# add: the same model that writes the desk verdicts must not be able to agree
# with itself three times and inflate a rank. Analyst bull and neutral posts
# both weigh 1.0, so migrating undirected theses to "neutral" changes no score.
RESEARCH_SOURCE = "research"


def _direction_weight(thesis):
    direction = thesis.get("direction") or "neutral"
    if direction == "bear":
        return -1.0
    if thesis.get("source") == RESEARCH_SOURCE:
        return 0.0
    return 1.0
```

In `compute_priorities`, after the line `focus = _focus_weight(len(syms))` (line 88), add:

```python
        direction = th.get("direction") or "neutral"
        signed = weight * focus * _direction_weight(th)
```

Change the `agg.setdefault` default dict (lines 90-94) to:

```python
            a = agg.setdefault(
                sym,
                {"mentions": 0, "weighted": 0.0, "recency": 0.0, "net": 0.0,
                 "bull": 0, "bear": 0, "convictionHits": 0,
                 "lastMentioned": None},
            )
```

Directly after `a["recency"] += weight * focus` (line 97), add:

```python
            a["net"] += signed
            if direction == "bear":
                a["bear"] += 1
            elif direction == "bull":
                a["bull"] += 1
```

Replace the score line (line 106):

```python
        score = a["recency"] * (1 + CONVICTION_WEIGHT * a["convictionHits"])
```

with:

```python
        score = max(a["net"] * (1 + CONVICTION_WEIGHT * a["convictionHits"]), 0.0)
```

And add `"net"` to the emitted record, after `"score"`:

```python
            "net": round(a["net"], 4),
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest discover -s ingest/tests -k test_scorer -v 2>&1 | tail -20`
Expected: PASS, `OK`

- [ ] **Step 5: Commit**

```bash
git add ingest/scorer.py ingest/tests/test_scorer.py
git commit -m "feat: bear theses subtract from a ticker's priority score

Absent direction reads as neutral and weighs 1.0, so the existing 258
theses score exactly as before. Score floors at zero; net retains the
true signed value for display."
```

---

## Task 4: Research findings subtract but never add

**Files:**
- Modify: `ingest/tests/test_scorer.py`

No production change is needed — `_direction_weight` already implements this. These tests pin the asymmetry so a later refactor cannot quietly remove it.

- [ ] **Step 1: Write the tests**

Append to the `TestDirection` class in `ingest/tests/test_scorer.py`:

```python
    def test_research_bull_adds_nothing(self):
        analyst = [thesis(["MU"], "2026-06-26T00:00:00Z", direction="bull")]
        plus_research = analyst + [
            thesis(["MU"], "2026-06-26T00:00:00Z",
                   direction="bull", source="research")
        ]
        a = scorer.compute_priorities(analyst, now=NOW)[0]
        b = scorer.compute_priorities(plus_research, now=NOW)[0]
        self.assertEqual(a["score"], b["score"])
        self.assertEqual(b["mentions"], 2)

    def test_research_bear_still_subtracts(self):
        base = [thesis(["GFS"], "2026-06-26T00:00:00Z", direction="bull")]
        with_bear = base + [
            thesis(["GFS"], "2026-06-26T00:00:00Z",
                   direction="bear", source="research")
        ]
        self.assertEqual(
            scorer.compute_priorities(with_bear, now=NOW)[0]["score"], 0.0)

    def test_analyst_bull_still_adds(self):
        one = [thesis(["LITE"], "2026-06-26T00:00:00Z", direction="bull")]
        two = one + [thesis(["LITE"], "2026-06-26T00:00:00Z", direction="bull")]
        self.assertEqual(scorer.compute_priorities(one, now=NOW)[0]["score"], 1.0)
        self.assertEqual(scorer.compute_priorities(two, now=NOW)[0]["score"], 2.0)
```

- [ ] **Step 2: Run to verify pass**

Run: `python3 -m unittest discover -s ingest/tests -k TestDirection -v 2>&1 | tail -12`
Expected: PASS, `OK`

- [ ] **Step 3: Commit**

```bash
git add ingest/tests/test_scorer.py
git commit -m "test: pin the research-source asymmetry

Research findings correct a score downward but cannot inflate one."
```

---

## Task 5: Expose attention and direction counts on the priority record

The ticker card needs to render "93 mentions · 3 against", which needs unsigned attention alongside the signed score.

**Files:**
- Modify: `ingest/scorer.py`
- Test: `ingest/tests/test_scorer.py`

- [ ] **Step 1: Write the failing test**

Append to the `TestDirection` class:

```python
    def test_attention_and_direction_counts_exposed(self):
        theses = [
            thesis(["SIVE"], "2026-06-26T00:00:00Z", direction="bull"),
            thesis(["SIVE"], "2026-06-26T00:00:00Z", direction="bull"),
            thesis(["SIVE"], "2026-06-26T00:00:00Z", direction="bear"),
        ]
        r = scorer.compute_priorities(theses, now=NOW)[0]
        self.assertEqual(r["attention"], 3.0)   # unsigned, all three mentions
        self.assertEqual(r["net"], 1.0)         # 1 + 1 - 1
        self.assertEqual(r["bullMentions"], 2)
        self.assertEqual(r["bearMentions"], 1)
        self.assertEqual(r["mentions"], 3)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest discover -s ingest/tests -k test_attention_and_direction_counts_exposed -v 2>&1 | tail -8`
Expected: FAIL — `KeyError: 'attention'`

- [ ] **Step 3: Write the implementation**

In `ingest/scorer.py`, in the record built inside `compute_priorities`, add three fields. The full emitted dict becomes:

```python
        ranked.append({
            "ticker": sym,
            "score": round(score, 4),
            "net": round(a["net"], 4),
            "attention": round(a["recency"], 4),
            "mentions": a["mentions"],
            "bullMentions": a["bull"],
            "bearMentions": a["bear"],
            "weightedMentions": round(a["weighted"], 4),
            "convictionHits": a["convictionHits"],
            "lastMentioned": a["lastMentioned"],
        })
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest discover -s ingest/tests -k test_scorer -v 2>&1 | tail -8`
Expected: PASS, `OK`

- [ ] **Step 5: Commit**

```bash
git add ingest/scorer.py ingest/tests/test_scorer.py
git commit -m "feat: expose attention, net and bull/bear counts on priorities"
```

---

## Task 6: Retire the conviction multiplier

Signed off by the operator on 2026-07-26. `CONVICTION_WEIGHT` goes to `0.0` rather than deleting the code path, so the decision is reversible by changing one constant.

**Files:**
- Modify: `ingest/scorer.py:19`, and the module docstring at `ingest/scorer.py:1-13`
- Test: `ingest/tests/test_scorer.py`

- [ ] **Step 1: Write the failing tests**

Append to `ingest/tests/test_scorer.py`:

```python
class TestConvictionRetired(unittest.TestCase):
    def test_conviction_language_no_longer_multiplies_score(self):
        plain = [thesis(["X"], "2026-06-26T00:00:00Z")]
        loud = [thesis(["X"], "2026-06-26T00:00:00Z", conviction="high")]
        self.assertEqual(
            scorer.compute_priorities(plain, now=NOW)[0]["score"],
            scorer.compute_priorities(loud, now=NOW)[0]["score"],
        )

    def test_conviction_hits_are_still_counted(self):
        loud = [thesis(["X"], "2026-06-26T00:00:00Z", conviction="high")]
        self.assertEqual(
            scorer.compute_priorities(loud, now=NOW)[0]["convictionHits"], 1)

    def test_conviction_hits_still_drive_tiers(self):
        # assign_tiers reads convictionHits directly, never score, so retiring
        # the multiplier must not move any ticker between tiers. Two hits is
        # core even though weightedMentions (2) is below the core floor of 5.
        theses = [
            thesis(["A"], "2026-06-26T00:00:00Z", conviction="high"),
            thesis(["A"], "2026-06-25T00:00:00Z", conviction="high"),
        ]
        pri = scorer.compute_priorities(theses, now=NOW)
        self.assertEqual(scorer.assign_tiers(["A"], pri)["A"], "core")
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest discover -s ingest/tests -k TestConvictionRetired -v 2>&1 | tail -12`
Expected: FAIL on the first test — `1.5 != 1.0`

- [ ] **Step 3: Write the implementation**

In `ingest/scorer.py` replace line 19:

```python
CONVICTION_WEIGHT = 0.5
```

with:

```python
# Retired 2026-07-26 (operator sign-off). `conviction` is assigned by keyword
# match in parser.py against phrases like "top pick" and "high conviction". It
# fired on 17 of 258 posts and multiplied a score by up to 6x — SIVE scored
# 91.11 on 10 hits, versus 15.19 without. That is rhetoric driving a ranking.
# Kept as a constant, not deleted, so this is reversible by restoring 0.5.
# Note: assign_tiers still reads convictionHits directly, so tiers are
# unaffected by this change.
CONVICTION_WEIGHT = 0.0
```

Then replace the module docstring formula on line 3:

```
    score = sum(recency_weight * focus_weight) * (1 + CONVICTION_WEIGHT * conviction_hits)
```

with:

```
    score = max(sum(recency_weight * focus_weight * direction_weight), 0)
```

and replace lines 5-6:

```
Recency uses exponential decay with a configurable half-life, so a ticker the
author mentions often AND recently AND with conviction language rises to the top.
```

with:

```
Recency uses exponential decay with a configurable half-life, so a ticker
mentioned often AND recently rises to the top. Direction weight signs each
mention: bear theses subtract, and research-sourced bull theses contribute
nothing, so outside research can correct a score but never inflate one.
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest discover -s ingest/tests -k test_scorer -v 2>&1 | tail -8`
Expected: PASS, `OK`

- [ ] **Step 5: Run the whole suite**

Run: `python3 -m unittest discover -s ingest/tests 2>&1 | tail -4`
Expected: `OK` — 126 tests

- [ ] **Step 6: Manually verify the real-store re-rank**

This is a one-time check against live data, deliberately **not** a permanent test — the store grows weekly and pinned counts would rot.

Run:

```bash
python3 - <<'EOF'
import json, sys
sys.path.insert(0, 'ingest')
import scorer
base = json.load(open('ingest/store/base.json'))
rows = json.load(open('ingest/store/theses.json'))
rows = rows['theses'] if isinstance(rows, dict) else rows
tk = json.load(open('ingest/store/tickers.json'))
syms = [t['ticker'] for t in (tk['tickers'] if isinstance(tk, dict) else tk)]
canon = scorer.canonicalize_theses(rows, base.get('tickerAliases'), base.get('themeTags'))
pri = scorer.compute_priorities(canon)
tiers = scorer.assign_tiers(syms, pri)
print('SIVE score:', next(p['score'] for p in pri if p['ticker'] == 'SIVE'))
print('top 15:', [p['ticker'] for p in pri[:15]])
print('core count:', sum(1 for s in syms if tiers[s] == 'core'))
EOF
```

Expected:
- `SIVE score:` approximately `15.19` (drifts with recency decay; it must be near 15, not near 91)
- `top 15:` contains AXTI, CCXI, COHR and SNDK, and does **not** contain GFS, JBL, MRVL or POET
- `core count:` **28** — unchanged, because tiers do not read the score

If the core count moved, stop: something touched `assign_tiers` that should not have.

- [ ] **Step 7: Commit**

```bash
git add ingest/scorer.py ingest/tests/test_scorer.py
git commit -m "feat: retire the conviction multiplier (CONVICTION_WEIGHT = 0.0)

Keyword-matched rhetoric was multiplying scores by up to 6x. SIVE falls
91.11 -> 15.19; the top 15 loses GFS/JBL/MRVL/POET and gains
AXTI/CCXI/COHR/SNDK. Tiers are unaffected — assign_tiers reads
convictionHits directly, not score. Reversible by restoring 0.5."
```

---

## Task 7: Regenerate data.js and verify in the browser

**Files:**
- Modify: `ingest/store/base.json` (version bump), `data.js` (generated)

- [ ] **Step 1: Bump the store version**

The app re-seeds localStorage only when `meta.version` changes, so without this the browser keeps serving the old scores from a previous session's cache.

In `ingest/store/base.json`, bump the `meta.version` string by one thousandth and set `meta.lastUpdated` to the current UTC time as `YYYY-MM-DDTHH:MM:SSZ`. As of this plan's writing the block reads `"version": "1.278"`, so it becomes `"1.279"` — but `bot.py` bumps this on every ingest, so read the current value first rather than assuming:

```bash
python3 -c "import json;print(json.load(open('ingest/store/base.json'))['meta'])"
```

- [ ] **Step 2: Regenerate**

Run: `python3 ingest/generate_data_js.py`
Expected: `Wrote /Users/mikembp/Documents/Claude/ai-supply-desk/data.js`

- [ ] **Step 3: Verify every block survived**

Run:

```bash
for k in glossary desk memos vault calls benchmarkQuote; do printf "%-16s %s\n" "$k" "$(grep -c "^  \"$k\"" data.js)"; done
```

Expected: six lines, each ending in `1`.

- [ ] **Step 4: Verify the new priority fields reached data.js**

Run:

```bash
python3 - <<'EOF'
import json
src = open('data.js').read()
i = src.index('window.AIE_DATA =')
d = json.loads(src[i + len('window.AIE_DATA ='):].rstrip().rstrip(';')
               .replace('\\u003c', '<').replace('\\u003e', '>'))
p = d['priorities'][0]
for f in ('score', 'net', 'attention', 'bullMentions', 'bearMentions'):
    assert f in p, 'missing %s' % f
print('top priority record OK:', p['ticker'], p['score'])
EOF
```

Expected: `top priority record OK: SIVE 15.19` (or a nearby value)

- [ ] **Step 5: Verify the app renders**

Run: `nohup python3 -m http.server 8791 --bind 127.0.0.1 > /tmp/aie-verify.log 2>&1 &`

Open `http://127.0.0.1:8791/desk.html`, then check:
- The watchlist table renders with prices and desk badges
- `http://127.0.0.1:8791/performance.html` shows both calls
- The browser console has no errors

Then stop it: `pkill -f "http.server 8791"`

- [ ] **Step 6: Commit**

```bash
git add ingest/store/base.json data.js
git commit -m "chore: regenerate data.js under direction-aware scoring"
```

---

## Task 8: Update the docs that now describe the old behaviour

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/superpowers/specs/2026-07-26-expert-review-team-design.md`

- [ ] **Step 1: Fix the scoring description in CLAUDE.md**

`CLAUDE.md` describes the v5 tier system as driven by "repeat *focus-weighted* mentions or 2+ high-conviction hits". The tier half is still true; the score half is not. In the **v5** bullet, after the sentence ending "(ROADMAP issue #4, fixed 2026-07-03).", add:

```
  Since 2026-07-26 the priority *score* is direction-aware: each mention is
  signed (`bull`/`neutral` +1, `bear` −1), research-sourced bull theses
  contribute 0 so outside research can only correct a score downward, and the
  conviction multiplier is retired (`CONVICTION_WEIGHT = 0.0`). Tiers are
  unchanged — `assign_tiers` reads `convictionHits` and `weightedMentions`
  directly, never the score.
```

- [ ] **Step 2: Add the priority record fields to the CLAUDE.md schema block**

In the `data.js` schema section, the `priorities` line currently reads:

```
  priorities: [ { ticker, score, mentions, convictionHits, lastMentioned } ],
```

Replace it with:

```
  priorities: [ { ticker, score, net, attention, mentions, bullMentions,
                  bearMentions, weightedMentions, convictionHits,
                  lastMentioned } ],
```

- [ ] **Step 3: Record the phase in ROADMAP.md**

Add this entry to `docs/ROADMAP.md`, under whichever heading the file uses for shipped work (match the surrounding bullet style):

```markdown
- **Expert review team, Phase 1 — direction-aware scoring** ✅ done
  (2026-07-26). Theses carry an optional `direction` (`bull`/`bear`/`neutral`);
  `scorer.compute_priorities` now sums a signed contribution per mention, so a
  bear thesis lowers a score instead of raising it. Research-sourced bull
  theses weigh 0 — outside research can correct a score downward but never
  inflate one, which stops the model amplifying its own view. The conviction
  multiplier is retired (`CONVICTION_WEIGHT = 0.0`, reversible): SIVE falls
  91.11 → 15.19 and the top 15 loses GFS/JBL/MRVL/POET while gaining
  AXTI/CCXI/COHR/SNDK. **Tiers are unchanged** — `assign_tiers` reads
  `convictionHits` and `weightedMentions`, never the score. `write_data_js`
  now refuses to write a payload missing any expected top-level block, after a
  stale long-running `bot.py` silently stripped six of them for four days.
  Spec: `docs/superpowers/specs/2026-07-26-expert-review-team-design.md`.
  **Not yet built:** Phases 2–5 — the three review seats, `claims.json` and
  claim judging, the performance page split, hit-rate weighting, and the
  scheduled overnight run.
```

- [ ] **Step 4: Correct the spec's test description**

The spec's testing section says the re-rank should be "asserted against these exact figures". That conflicts with the codebase rule against pinning live-store counts, and this plan implements it as a manual verification step instead. In the spec's Testing section, replace the bullet beginning "- conviction retirement: with `CONVICTION_WEIGHT = 0.0`, SIVE scores 15.19" with:

```
- conviction retirement: unit-tested against synthetic fixtures — a `high`
  conviction thesis scores identically to a `normal` one, while
  `convictionHits` is still counted and still drives tiers. The real-store
  re-rank (SIVE 91.11 -> 15.19; GFS/JBL/MRVL/POET out, AXTI/CCXI/COHR/SNDK in)
  is a one-time manual verification, not a permanent assertion — the store
  grows weekly and pinned counts would rot.
```

- [ ] **Step 5: Verify no doc claims the old formula**

Run: `grep -rn "CONVICTION_WEIGHT \* conviction_hits\|1 + CONVICTION_WEIGHT" --include=*.md --include=*.py . | grep -v superpowers/plans`
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md docs/ROADMAP.md docs/superpowers/specs/2026-07-26-expert-review-team-design.md
git commit -m "docs: describe direction-aware scoring and the retired multiplier"
```

---

## Done when

- `python3 -m unittest discover -s ingest/tests` reports `OK` with 126 tests
- `SIVE` scores near 15, not near 91, against the real store
- The Core count is still 28 — no ticker changed tier
- All six previously-stripped blocks are present in `data.js`
- `desk.html` and `performance.html` render with no console errors
- No markdown or Python file still documents the conviction multiplier as live

## Not in this plan

Phases 2–5 of the spec, each of which needs its own plan:

- **Plan 2 — the three seats.** `semi-expert`, `fundamental` and `pm` agents, the 150-word output contract, the verification rule that keeps unverified findings inert, and research theses entering the feed with `source: "research"`.
- **Plan 3 — the memory.** `ingest/store/claims.json`, claim extraction, judging, hit rate with the unfalsifiable share, and splitting `performance.html` into Calls and Claims.
- **Plan 4 — hit-rate weighting.** Gated on 20+ judged claims per source, so it cannot start before Plan 3 has run for months.
- **Plan 5 — scheduling.** The overnight run and the 12-name coverage cap.
