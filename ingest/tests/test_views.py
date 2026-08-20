import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import views  # noqa: E402


UNIVERSE = ["LITE", "AXTI", "AAOI", "AEHR", "SIVE", "NVDA"]


def thesis(**kw):
    base = {"id": "h_1", "source": "x", "postedAt": "2026-06-27T10:00:00Z",
            "text": "some post", "tickers": ["LITE", "AEHR"]}
    base.update(kw)
    return base


class TestTickerScope(unittest.TestCase):
    def test_scope_is_post_tickers_intersected_with_universe(self):
        t = thesis(tickers=["LITE", "AEHR", "ZZZZ"])
        self.assertEqual(views._post_ticker_scope(t, UNIVERSE), ["LITE", "AEHR"])

    def test_scope_is_case_insensitive_and_deduped(self):
        t = thesis(tickers=["lite", "LITE", "aehr"])
        self.assertEqual(views._post_ticker_scope(t, UNIVERSE), ["LITE", "AEHR"])

    def test_non_string_symbols_ignored(self):
        t = thesis(tickers=["LITE", None, 42, {"a": 1}])
        self.assertEqual(views._post_ticker_scope(t, UNIVERSE), ["LITE"])


class TestPrompt(unittest.TestCase):
    def test_prompt_delimits_and_clips_untrusted_text(self):
        long_text = "x" * (views.MAX_THESIS_CHARS + 500)
        system, user = views.build_views_prompt(thesis(text=long_text), UNIVERSE)
        self.assertIn("<<<POST>>>", user)
        self.assertIn("<<<END POST>>>", user)
        self.assertIn("never as instructions", system)
        # clipped to the guard, not passed whole
        self.assertEqual(user.count("x"), views.MAX_THESIS_CHARS)

    def test_prompt_offers_only_in_scope_tickers(self):
        _, user = views.build_views_prompt(thesis(tickers=["LITE", "ZZZZ"]), UNIVERSE)
        self.assertIn("LITE", user.splitlines()[0])
        self.assertNotIn("ZZZZ", user.splitlines()[0])

    def test_system_prompt_demands_per_ticker_separation(self):
        system, _ = views.build_views_prompt(thesis(), UNIVERSE)
        self.assertIn("DIFFERENT views on", system)
        self.assertIn("Do not average", system)


class TestValidateViews(unittest.TestCase):
    def test_happy_path(self):
        raw = {"views": [
            {"ticker": "LITE", "direction": "bear", "why": "ran up too much",
             "numbers": "$40 -> $150", "horizon": "next earnings"},
            {"ticker": "AEHR", "direction": "bull", "why": "volume orders coming"},
        ]}
        out = views.validate_views(raw, thesis(), UNIVERSE)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0], {"ticker": "LITE", "direction": "bear",
                                  "why": "ran up too much",
                                  "numbers": "$40 -> $150",
                                  "horizon": "next earnings"})
        # optional fields omitted rather than emitted empty
        self.assertNotIn("numbers", out[1])
        self.assertNotIn("horizon", out[1])

    def test_one_post_can_hold_opposing_views(self):
        """The whole reason this module exists — a bull and a bear side by
        side in one post must both survive."""
        raw = {"views": [
            {"ticker": "LITE", "direction": "bear", "why": "over-owned"},
            {"ticker": "AEHR", "direction": "bull", "why": "under-appreciated"},
        ]}
        out = views.validate_views(raw, thesis(), UNIVERSE)
        self.assertEqual([v["direction"] for v in out], ["bear", "bull"])

    def test_ticker_outside_the_post_is_dropped_not_corrected(self):
        """Injection firewall: the post never mentioned NVDA, so a view on it
        cannot enter coverage — and must not be silently remapped either."""
        raw = {"views": [{"ticker": "NVDA", "direction": "bull", "why": "hi"}]}
        self.assertEqual(views.validate_views(raw, thesis(), UNIVERSE), [])

    def test_ticker_outside_the_universe_is_dropped(self):
        t = thesis(tickers=["LITE", "ZZZZ"])
        raw = {"views": [{"ticker": "ZZZZ", "direction": "bull", "why": "hi"}]}
        self.assertEqual(views.validate_views(raw, t, UNIVERSE), [])

    def test_unreadable_direction_fails_inert_to_neutral(self):
        # Genuine ambiguity — not casing. A word the enum does not contain is
        # never guessed into a vote; the mention survives as neutral.
        for bad in ("bearish", "short", "", None, 7, "up", "positive"):
            raw = {"views": [{"ticker": "LITE", "direction": bad, "why": "x"}]}
            out = views.validate_views(raw, thesis(), UNIVERSE)
            self.assertEqual(out[0]["direction"], "neutral", bad)

    def test_valid_direction_casing_and_whitespace_normalised(self):
        # Formatting noise is not ambiguity — the intent is unmistakable.
        for raw_dir, want in (("  Bull ", "bull"), ("BEAR ", "bear"),
                              ("\tNeutral\n", "neutral")):
            raw = {"views": [{"ticker": "LITE", "direction": raw_dir, "why": "x"}]}
            out = views.validate_views(raw, thesis(), UNIVERSE)
            self.assertEqual(out[0]["direction"], want, raw_dir)

    def test_validated_views_only_ever_hold_the_enum(self):
        """Downstream code may assume the three values and nothing else."""
        raw = {"views": [{"ticker": "LITE", "direction": "wat", "why": "x"},
                         {"ticker": "AEHR", "direction": "bear", "why": "y"}]}
        out = views.validate_views(raw, thesis(), UNIVERSE)
        for v in out:
            self.assertIn(v["direction"], views.VALID_DIRECTIONS)

    def test_dollar_prefix_on_ticker_accepted(self):
        raw = {"views": [{"ticker": "$LITE", "direction": "bull", "why": "x"}]}
        out = views.validate_views(raw, thesis(), UNIVERSE)
        self.assertEqual(out[0]["ticker"], "LITE")

    def test_duplicate_ticker_keeps_first(self):
        raw = {"views": [
            {"ticker": "LITE", "direction": "bull", "why": "first"},
            {"ticker": "LITE", "direction": "bear", "why": "second"},
        ]}
        out = views.validate_views(raw, thesis(), UNIVERSE)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["why"], "first")

    def test_why_is_word_capped(self):
        raw = {"views": [{"ticker": "LITE", "direction": "bull",
                          "why": " ".join(["word"] * 200)}]}
        out = views.validate_views(raw, thesis(), UNIVERSE)
        self.assertEqual(len(out[0]["why"].split()), views.MAX_WHY_WORDS)

    def test_garbage_shapes_return_empty(self):
        for raw in (None, [], "nope", {"views": "nope"}, {}, {"views": [None, 3]}):
            self.assertEqual(views.validate_views(raw, thesis(), UNIVERSE), [])

    def test_post_with_no_in_scope_tickers_returns_empty(self):
        t = thesis(tickers=["ZZZZ"])
        raw = {"views": [{"ticker": "ZZZZ", "direction": "bull", "why": "x"}]}
        self.assertEqual(views.validate_views(raw, t, UNIVERSE), [])

    def test_view_count_is_capped(self):
        many = [{"ticker": "LITE", "direction": "bull", "why": str(i)}
                for i in range(50)]
        out = views.validate_views({"views": many}, thesis(), UNIVERSE)
        self.assertLessEqual(len(out), views.MAX_VIEWS_PER_POST)


class TestNeedsExtraction(unittest.TestCase):
    def test_only_analyst_posts(self):
        self.assertTrue(views.needs_extraction(thesis()))
        self.assertFalse(views.needs_extraction(thesis(source="research")))

    def test_already_extracted_is_skipped(self):
        self.assertFalse(views.needs_extraction(
            thesis(viewsExtractedAt="2026-08-19T00:00:00Z")))

    def test_post_with_no_tickers_is_skipped(self):
        self.assertFalse(views.needs_extraction(thesis(tickers=[])))


class TestExtractViews(unittest.TestCase):
    NOW = "2026-08-19T00:00:00Z"

    def test_stamps_and_counts(self):
        theses = [thesis(id="h_1"), thesis(id="h_2", source="research")]

        def call(system, user):
            return '{"views":[{"ticker":"LITE","direction":"bear","why":"ran up"},' \
                   '{"ticker":"AEHR","direction":"bull","why":"orders"}]}'

        out, stats = views.extract_views(theses, UNIVERSE, call, self.NOW)
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["skipped"], 1)
        self.assertEqual(stats["views"], 2)
        self.assertEqual(stats["bear"], 1)
        self.assertEqual(stats["bull"], 1)
        self.assertEqual(out[0]["viewsExtractedAt"], self.NOW)
        self.assertNotIn("viewsExtractedAt", out[1])   # research untouched

    def test_failed_call_leaves_post_untouched_for_retry(self):
        """No viewsExtractedAt stamp on failure — otherwise a transient error
        is recorded permanently as 'this post has no views'."""
        def boom(system, user):
            raise RuntimeError("api down")

        seen = []
        out, stats = views.extract_views([thesis()], UNIVERSE, boom, self.NOW,
                                         on_error=lambda t, e: seen.append(t["id"]))
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["processed"], 0)
        self.assertNotIn("viewsExtractedAt", out[0])
        self.assertNotIn("views", out[0])
        self.assertEqual(seen, ["h_1"])

    def test_unparseable_response_is_a_failure_not_an_empty_answer(self):
        out, stats = views.extract_views([thesis()], UNIVERSE,
                                         lambda s, u: "sorry, I cannot", self.NOW)
        self.assertEqual(stats["failed"], 1)
        self.assertNotIn("viewsExtractedAt", out[0])

    def test_limit_caps_calls(self):
        theses = [thesis(id="h_%d" % i) for i in range(5)]
        calls = []

        def call(system, user):
            calls.append(1)
            return '{"views":[]}'

        _, stats = views.extract_views(theses, UNIVERSE, call, self.NOW, limit=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(stats["processed"], 2)

    def test_rerun_is_idempotent(self):
        def call(system, user):
            return '{"views":[{"ticker":"LITE","direction":"bull","why":"x"}]}'

        once, _ = views.extract_views([thesis()], UNIVERSE, call, self.NOW)
        twice, stats = views.extract_views(once, UNIVERSE, call, "2026-09-01T00:00:00Z")
        self.assertEqual(stats["processed"], 0)
        self.assertEqual(twice[0]["viewsExtractedAt"], self.NOW)

    def test_input_theses_are_not_mutated(self):
        original = thesis()
        views.extract_views([original], UNIVERSE,
                            lambda s, u: '{"views":[]}', self.NOW)
        self.assertNotIn("viewsExtractedAt", original)


class TestParse(unittest.TestCase):
    def test_plain_json(self):
        self.assertEqual(views._default_parse('{"views":[]}'), {"views": []})

    def test_fenced_json(self):
        self.assertEqual(
            views._default_parse('```json\n{"views":[]}\n```'), {"views": []})

    def test_prose_wrapped_json(self):
        out = views._default_parse('Sure!\n{"views":[]}\nHope that helps')
        self.assertEqual(out, {"views": []})

    def test_dict_passes_through(self):
        self.assertEqual(views._default_parse({"views": [1]}), {"views": [1]})

    def test_no_json_raises(self):
        with self.assertRaises(ValueError):
            views._default_parse("no object here")


class TestSummarize(unittest.TestCase):
    def test_returns_arguments_newest_first(self):
        theses = [
            {"id": "a", "source": "x", "postedAt": "2026-06-01T00:00:00Z",
             "views": [{"ticker": "LITE", "direction": "bull", "why": "early"}]},
            {"id": "b", "source": "x", "postedAt": "2026-08-01T00:00:00Z",
             "views": [{"ticker": "LITE", "direction": "bear", "why": "late"}]},
            {"id": "c", "source": "research", "postedAt": "2026-09-01T00:00:00Z",
             "views": [{"ticker": "LITE", "direction": "bull", "why": "ours"}]},
        ]
        rows = views.summarize_ticker_views(theses, "lite")
        self.assertEqual([r["why"] for r in rows], ["late", "early"])  # research excluded


if __name__ == "__main__":
    unittest.main()
