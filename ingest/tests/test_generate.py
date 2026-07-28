import sys
import re
import json
import pathlib
import subprocess
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import generate_data_js as gen  # noqa: E402


def reparse(js_text):
    m = re.search(r"window\.AIE_DATA\s*=\s*(\{.*\});\s*$", js_text, re.S)
    return json.loads(m.group(1))


class TestBuild(unittest.TestCase):
    def test_core_structure(self):
        # Assert structural invariants, not exact counts: the store grows with
        # every ingest, so hardcoded counts are brittle by design.
        d = gen.build_data()
        self.assertIsInstance(d["tickers"], list)
        self.assertGreaterEqual(len(d["tickers"]), 1)
        self.assertGreaterEqual(len(d["categories"]), 6)
        self.assertTrue(all("layer" in c for c in d["categories"].values()))
        self.assertIsInstance(d["theses"], list)
        self.assertIsInstance(d["priorities"], list)
        self.assertEqual(d["center"]["title"], "NVIDIA + Hyperscalers")

    def test_brain_key_present(self):
        # build_data always exposes a `brain` key; {} until synthesize.py runs.
        d = gen.build_data()
        self.assertIn("brain", d)
        self.assertIsInstance(d["brain"], dict)


class TestIconValidation(unittest.TestCase):
    def test_valid_icon_passes(self):
        gen._validate_icon('<path d="M3 12h18" fill="none" stroke="currentColor" stroke-width="1.5"/>')

    def test_onload_is_rejected(self):
        with self.assertRaises(ValueError):
            gen._validate_icon('<path d="M3 12h18" onload="alert(1)"/>')

    def test_script_is_rejected(self):
        with self.assertRaises(ValueError):
            gen._validate_icon('<script>alert(1)</script>')

    def test_href_is_rejected(self):
        with self.assertRaises(ValueError):
            gen._validate_icon('<path d="M3 12h18" href="https://example.com"/>')

    def test_missing_icon_is_tolerated(self):
        gen._validate_icon(None)


class TestRenderSafety(unittest.TestCase):
    def test_render_roundtrips(self):
        d = gen.build_data()
        out = gen.render(d)
        self.assertIn("window.AIE_DATA =", out)
        self.assertTrue(out.rstrip().endswith(";"))
        reparse(out)  # must be valid JSON

    def test_injection_is_neutralized(self):
        hostile = '"}; </script><script>alert(1)</script>'
        d = gen.build_data()
        d["theses"] = [{"id": "x_1", "text": hostile, "tickers": []}]
        out = gen.render(d)
        # No raw closing tag can appear in the emitted JS source.
        self.assertNotIn("</script>", out)
        # ...yet the value is preserved exactly after JSON/JS unescaping.
        parsed = reparse(out)
        self.assertEqual(parsed["theses"][0]["text"], hostile)


class TestTiersAndDesk(unittest.TestCase):
    def test_every_ticker_has_a_tier(self):
        d = gen.build_data()
        for t in d["tickers"]:
            self.assertIn(t.get("tier"), ("core", "watch", "radar"), t["ticker"])

    def test_desk_key_present(self):
        # build_data always exposes a `desk` key; {} until verdicts.json exists.
        d = gen.build_data()
        self.assertIn("desk", d)
        self.assertIsInstance(d["desk"], dict)

    def test_desk_verdicts_stamped_onto_tickers(self):
        d = gen.build_data()
        verdicts = (d["desk"].get("verdicts") or [])
        if not verdicts:
            self.skipTest("no verdicts in store yet")
        by_sym = {t["ticker"]: t for t in d["tickers"]}
        for v in verdicts:
            if v["ticker"] in by_sym:
                self.assertEqual(by_sym[v["ticker"]].get("verdict"), v)

    def test_priority_block_survives_a_net_negative_zero_score(self):
        # Regression for the `if p and p["score"] > 0` gate: a name argued
        # against on every mention floors to score 0.0, which used to make it
        # indistinguishable from "never mentioned" — the priority block (and
        # its mentions/lastMentioned) disappeared entirely. Being discussed
        # and being net-positive are different facts; only mentions should
        # gate the block.
        d = gen.build_data()
        sym = d["tickers"][0]["ticker"]
        orig_load = gen._load

        def fake(name):
            if name == "theses.json":
                return [
                    {"tickers": [sym], "postedAt": "2026-07-01T00:00:00Z",
                     "conviction": "normal", "source": "x", "direction": "bear"}
                    for _ in range(5)
                ]
            return orig_load(name)

        gen._load = fake
        try:
            d2 = gen.build_data()
        finally:
            gen._load = orig_load

        t = next(x for x in d2["tickers"] if x["ticker"] == sym)
        self.assertIn("priority", t)
        self.assertEqual(t["priority"]["score"], 0.0)
        self.assertEqual(t["priority"]["mentions"], 5)


class TestMemos(unittest.TestCase):
    def test_memos_key_absent_defaults_to_empty(self):
        # When memos.json is missing, build_data still exposes a `memos` key
        # as {} (same optional-load contract as brain/desk).
        orig = gen._load_optional

        def fake(name, default):
            if name == "memos.json":
                return default  # simulate file absent
            return orig(name, default)

        gen._load_optional = fake
        try:
            d = gen.build_data()
        finally:
            gen._load_optional = orig
        self.assertIn("memos", d)
        self.assertEqual(d["memos"], {})

    def test_memos_passthrough_intact(self):
        # When memos.json is present, it is passed through verbatim.
        payload = {
            "meta": {"schemaVersion": 1, "author": "claude-desk"},
            "memos": [{"id": "m_TEST_2026w28", "ticker": "TEST", "rating": "watch"}],
        }
        orig = gen._load_optional

        def fake(name, default):
            if name == "memos.json":
                return payload
            return orig(name, default)

        gen._load_optional = fake
        try:
            d = gen.build_data()
        finally:
            gen._load_optional = orig
        self.assertEqual(d["memos"], payload)


class TestCalls(unittest.TestCase):
    def _with_fake(self, calls_payload, prices_payload=None):
        orig = gen._load_optional

        def fake(name, default):
            if name == "calls.json":
                return default if calls_payload is None else calls_payload
            if name == "prices.json" and prices_payload is not None:
                return prices_payload
            return orig(name, default)

        gen._load_optional = fake
        try:
            return gen.build_data()
        finally:
            gen._load_optional = orig

    def test_calls_key_absent_defaults_to_empty(self):
        # calls.json missing -> `calls` key still present as {} (same
        # optional-load contract as brain/desk/memos/vault).
        d = self._with_fake(None)
        self.assertIn("calls", d)
        self.assertEqual(d["calls"], {})

    def test_calls_passthrough_intact(self):
        payload = {
            "meta": {"schemaVersion": 1, "benchmark": "SMH"},
            "calls": [{
                "id": "c_AAOI_2026-07-12", "ticker": "AAOI",
                "kind": "add-on-dip", "calledAt": "2026-07-12",
                "entryPrice": 113.84, "entryCurrency": "USD",
                "stanceAtCall": "accumulate", "memoId": "m_AAOI_2026w28",
                "thesisIds": [], "closedAt": None, "exitPrice": None,
                "outcome": "open",
                "benchmark": {"symbol": "SMH", "priceAtCall": 300.0},
            }],
        }
        d = self._with_fake(payload)
        self.assertEqual(d["calls"], payload)

    def test_benchmark_quote_from_prices(self):
        # When prices.json carries the benchmark symbol, its quote is exposed
        # top-level so performance.html can compute vs-SMH without fetch().
        prices = {"SMH": {"price": 301.5, "currency": "USD", "asOf": "2026-07-12T00:00:00Z"}}
        d = self._with_fake({"meta": {"benchmark": "SMH"}, "calls": []}, prices)
        self.assertEqual(d["benchmarkQuote"]["price"], 301.5)

    def test_price_fields_merged_onto_ticker(self):
        d = gen.build_data()
        sym = d["tickers"][0]["ticker"]
        prices = {sym: {"price": 10.5, "currency": "USD", "chg7d": 1.1,
                        "chg1m": 2.2, "chg1y": 33.3, "marketCap": 999,
                        "asOf": "2026-07-16T00:00:00Z"}}
        d2 = self._with_fake({"meta": {}, "calls": []}, prices)
        t = next(t for t in d2["tickers"] if t["ticker"] == sym)
        for f in gen.PRICE_FIELDS:
            self.assertEqual(t[f], prices[sym][f], f)

    def test_benchmark_quote_none_when_unpriced(self):
        d = self._with_fake({"meta": {"benchmark": "SMH"}, "calls": []}, {})
        self.assertIsNone(d["benchmarkQuote"])


class TestCompletenessGuard(unittest.TestCase):
    def test_build_data_keys_match_required_keys_exactly(self):
        # Equality, not subset: a key added to build_data() and forgotten in
        # REQUIRED_KEYS is exactly the kind of drift this guard exists to catch,
        # and a one-directional assertIn check would never notice it.
        d = gen.build_data()
        self.assertEqual(
            set(d.keys()), set(gen.REQUIRED_KEYS),
            "build_data() output and REQUIRED_KEYS have drifted apart"
        )

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

    def test_corrupt_store_file_raises_runtimeerror_naming_the_file(self):
        # _load_optional swallows bad JSON and returns {} — which would make a
        # corrupt verdicts.json look "legitimately empty" to the completeness
        # check and pass silently. _read_store_or_empty must not make that
        # mistake: a present-but-broken file has to raise RuntimeError (NOT
        # the bare ValueError json.loads raises — bot.py's ingest_message
        # only catches RuntimeError from write_data_js, so anything else
        # escapes into its generic "ingest error"/"Skipped" handler, exactly
        # the misleading message this guard exists to prevent).
        #
        # Uses a scratch store directory, never the real one: ingest/store/
        # is hand-authored, source-of-truth data with no backup — no test may
        # ever write to it.
        orig_store = gen.STORE
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_store = pathlib.Path(tmp_dir)
            (tmp_store / "verdicts.json").write_text("{not valid json", encoding="utf-8")
            gen.STORE = tmp_store
            try:
                with self.assertRaises(RuntimeError) as ctx:
                    gen._read_store_or_empty("verdicts.json")
                self.assertIn("verdicts.json", str(ctx.exception))
            finally:
                gen.STORE = orig_store


class TestFreshnessGuard(unittest.TestCase):
    def setUp(self):
        # Snapshot so a test's mutations to the process-wide baseline dict
        # can't leak into other tests regardless of run order.
        self._orig_baseline = dict(gen._SOURCE_HASHES_BASELINE)

    def tearDown(self):
        gen._SOURCE_HASHES_BASELINE.clear()
        gen._SOURCE_HASHES_BASELINE.update(self._orig_baseline)

    def test_fresh_process_passes(self):
        gen._assert_fresh()  # establishes/confirms baseline; no raise
        gen._assert_fresh()  # second call compares against it; still no raise

    def test_stale_module_raises_and_names_it(self):
        gen._assert_fresh()  # ensure a baseline is actually established first
        # Simulate scorer.py's contents having changed since this process
        # first saw it: the recorded baseline no longer matches reality.
        gen._SOURCE_HASHES_BASELINE["scorer.py"] = "0" * 64
        with self.assertRaises(RuntimeError) as ctx:
            gen._assert_fresh()
        self.assertIn("scorer.py", str(ctx.exception))

    def test_unrecordable_baseline_is_retried_not_skipped_forever(self):
        # A file that fails to hash on its first sighting (a transient read
        # hiccup) must not be permanently treated as "unknown, skip forever" —
        # the next call has to try again and actually establish a baseline.
        gen._SOURCE_HASHES_BASELINE.pop("scorer.py", None)
        orig_safe_hash = gen._safe_hash

        def fail_for_scorer(path):
            if pathlib.Path(path).name == "scorer.py":
                return None
            return orig_safe_hash(path)

        gen._safe_hash = fail_for_scorer
        try:
            gen._assert_fresh()
            self.assertNotIn("scorer.py", gen._SOURCE_HASHES_BASELINE)
        finally:
            gen._safe_hash = orig_safe_hash

        gen._assert_fresh()  # real _safe_hash this time -> baseline established
        self.assertIn("scorer.py", gen._SOURCE_HASHES_BASELINE)

    def test_baseline_populated_at_import_before_any_assert_fresh_call(self):
        # Pins capture timing, not comparison: a fresh interpreter that only
        # imports generate_data_js, and never calls _assert_fresh(), must
        # already have a baseline recorded for generate_data_js.py itself —
        # the module that actually broke on 2026-07-26. Run in a subprocess
        # so no other test's _assert_fresh() call (which would also populate
        # it) can hide a regression to lazy-only capture.
        script = (
            "import sys; sys.path.insert(0, {ing!r}); "
            "import generate_data_js as gen; "
            "assert 'generate_data_js.py' in gen._SOURCE_HASHES_BASELINE, "
            "gen._SOURCE_HASHES_BASELINE"
        ).format(ing=str(gen.ING))
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class TestWriteDataJsGuardWiring(unittest.TestCase):
    def test_write_data_js_refuses_incomplete_payload_and_writes_nothing(self):
        # Proves _assert_complete is actually wired into write_data_js, not
        # just defined and unused: delete the _assert_complete(data) call
        # from write_data_js and this test fails, because tmp_path ends up
        # written despite the incomplete payload.
        bad = gen.build_data()
        del bad["calls"]
        orig_data_js = gen.DATA_JS
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir) / "data.js"
            gen.DATA_JS = tmp_path
            try:
                with self.assertRaises(RuntimeError):
                    gen.write_data_js(data=bad)
                self.assertFalse(
                    tmp_path.exists(),
                    "write_data_js wrote a file despite an incomplete payload"
                )
            finally:
                gen.DATA_JS = orig_data_js


class TestWriteDataJsFreshnessWiring(unittest.TestCase):
    def setUp(self):
        self._orig_baseline = dict(gen._SOURCE_HASHES_BASELINE)

    def tearDown(self):
        gen._SOURCE_HASHES_BASELINE.clear()
        gen._SOURCE_HASHES_BASELINE.update(self._orig_baseline)

    def test_write_data_js_refuses_when_stale_and_writes_nothing(self):
        # Proves _assert_fresh is actually wired into write_data_js, not just
        # defined and unused: delete the _assert_fresh() call from
        # write_data_js and this test fails, because tmp_path ends up written
        # even though the process is (simulated) stale. This is the guard
        # that matters most — it's the one the 2026-07-26 incident actually
        # needed — so its wiring gets its own dedicated proof, same as
        # _assert_complete's above.
        good = gen.build_data()
        gen._assert_fresh()  # establish a real baseline first
        gen._SOURCE_HASHES_BASELINE["scorer.py"] = "0" * 64  # force "stale"

        orig_data_js = gen.DATA_JS
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir) / "data.js"
            gen.DATA_JS = tmp_path
            try:
                with self.assertRaises(RuntimeError) as ctx:
                    gen.write_data_js(data=good)
                self.assertIn("scorer.py", str(ctx.exception))
                self.assertFalse(
                    tmp_path.exists(),
                    "write_data_js wrote a file despite a stale process"
                )
            finally:
                gen.DATA_JS = orig_data_js




class TestPriorityStamp(unittest.TestCase):
    def test_ticker_priority_stamp_carries_direction_fields(self):
        # The ticker card reads t["priority"], not the top-level priorities
        # array, so bearMentions has to be mirrored here or the "N against"
        # count can never reach the UI it was added for.
        d = gen.build_data()
        stamped = [t for t in d["tickers"] if t.get("priority")]
        self.assertTrue(stamped, "no ticker carried a priority stamp")
        for field in ("score", "net", "attention", "mentions",
                      "bullMentions", "bearMentions", "convictionHits",
                      "lastMentioned"):
            self.assertIn(field, stamped[0]["priority"])

    def test_the_analyst_research_split_reaches_the_ticker_stamp(self):
        # desk.html reads t["priority"], not the top-level priorities array,
        # so the split has to be mirrored here or the ticker tooltip cannot
        # tell the analyst's posts from the desk's own findings.
        d = gen.build_data()
        stamped = [t for t in d["tickers"] if t.get("priority")]
        self.assertTrue(stamped, "no ticker carried a priority stamp")
        for field in ("analystMentions", "researchMentions"):
            self.assertIn(field, stamped[0]["priority"])

    def test_stamped_analyst_and_research_counts_sum_to_mentions(self):
        d = gen.build_data()
        for t in d["tickers"]:
            p = t.get("priority")
            if not p:
                continue
            self.assertEqual(p["analystMentions"] + p["researchMentions"],
                             p["mentions"], t["ticker"])


class TestClaimsBlock(unittest.TestCase):
    def test_claims_is_a_top_level_block(self):
        d = gen.build_data()
        self.assertIn("claims", d)

    def test_claims_is_guarded_against_silent_loss(self):
        # Six blocks vanished from data.js for four days in July because
        # nothing checked they were there. Every new block joins the guard.
        self.assertIn("claims", gen.REQUIRED_KEYS)
        with self.assertRaises(Exception):
            gen._assert_complete({k: {} for k in gen.REQUIRED_KEYS
                                  if k != "claims"})

    def test_every_call_records_which_source_made_it(self):
        # Phase 4 compares the desk's calls against the analyst's. A call with
        # no source cannot be attributed to either.
        d = gen.build_data()
        for call in (d["calls"] or {}).get("calls", []):
            self.assertIn(call.get("source"), ("desk", "analyst"), call.get("id"))


if __name__ == "__main__":
    unittest.main()
