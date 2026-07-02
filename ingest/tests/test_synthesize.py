import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import synthesize  # noqa: E402
import generate_data_js as gen  # noqa: E402

NOW = "2026-06-26T00:00:00Z"


def thesis(tid, tickers, text="some text", posted_at="2026-06-20T00:00:00Z", conviction="normal"):
    return {
        "id": tid,
        "tickers": tickers,
        "text": text,
        "postedAt": posted_at,
        "conviction": conviction,
    }


# Synthetic store, deliberately independent of the live store files.
TICKERS = [
    {"ticker": "AAOI", "company": "Applied Optoelectronics", "category": "photonics"},
    {"ticker": "LITE", "company": "Lumentum", "category": "photonics"},
    {"ticker": "MU", "company": "Micron", "category": "memory"},
    {"ticker": "NVDA", "company": "Nvidia", "category": "fabs"},
    {"ticker": "JUNK", "company": "Junk Co", "category": "unsorted"},
]
# Mirrors base["categories"] — note: NO "unsorted" key, and "glass" has no tickers.
CATEGORIES = {
    "photonics": {"id": "photonics", "label": "Photonics", "subtitle": "Optical Interconnects",
                  "color": "#3b82f6", "tooltip": "light-based data transmission"},
    "memory": {"id": "memory", "label": "Memory", "subtitle": "HBM",
               "color": "#8b5cf6", "tooltip": "high bandwidth memory"},
    "fabs": {"id": "fabs", "label": "Fabs", "subtitle": "Foundry",
             "color": "#f59e0b", "tooltip": "chip fabrication"},
    "glass": {"id": "glass", "label": "Glass Substrates", "subtitle": "Packaging",
              "color": "#a855f7", "tooltip": "glass core substrates"},
}


def good_call(system, user):
    """A fake Claude that returns a well-formed (but slightly dirty) digest."""
    return {
        "narrative": "He likes this theme.",
        "conviction": "high",
        "keyPoints": ["point one", "point two"],
        "tickers": ["AAOI", "MU", "FAKE"],  # FAKE + cross-category must be filtered out
        "category": "hacked-by-model",       # must be ignored
        "sourceThesisIds": ["model-made-this-up"],  # must be ignored
    }


class TestGrouping(unittest.TestCase):
    def test_thesis_lands_in_every_category_its_tickers_touch(self):
        theses = [thesis("t1", ["AAOI", "MU"])]
        groups = synthesize.group_theses_by_category(theses, TICKERS, CATEGORIES)
        self.assertIn(theses[0], groups["photonics"])
        self.assertIn(theses[0], groups["memory"])
        self.assertNotIn(theses[0], groups["fabs"])

    def test_all_categories_seeded_including_empty(self):
        groups = synthesize.group_theses_by_category([], TICKERS, CATEGORIES)
        self.assertEqual(set(groups.keys()), set(CATEGORIES.keys()))
        self.assertEqual(groups["glass"], [])

    def test_orphan_symbol_skipped(self):
        theses = [thesis("t1", ["WTFNOTREAL"])]
        groups = synthesize.group_theses_by_category(theses, TICKERS, CATEGORIES)
        self.assertTrue(all(g == [] for g in groups.values()))

    def test_unsorted_not_grouped(self):
        theses = [thesis("t1", ["JUNK"])]
        groups = synthesize.group_theses_by_category(theses, TICKERS, CATEGORIES)
        self.assertNotIn("unsorted", groups)
        self.assertTrue(all(theses[0] not in g for g in groups.values()))

    def test_no_double_add_within_one_category(self):
        theses = [thesis("t1", ["AAOI", "LITE"])]  # both photonics
        groups = synthesize.group_theses_by_category(theses, TICKERS, CATEGORIES)
        self.assertEqual(len(groups["photonics"]), 1)


class TestValidateDigest(unittest.TestCase):
    def test_drops_hallucinated_and_cross_category_tickers(self):
        d = synthesize.validate_digest(good_call("", ""), "photonics", {"AAOI", "LITE"})
        self.assertEqual(d["tickers"], ["AAOI"])

    def test_conviction_clamped_to_enum(self):
        d = synthesize.validate_digest({"conviction": "extremely bullish"}, "memory", {"MU"})
        self.assertEqual(d["conviction"], "medium")

    def test_valid_conviction_passes_through_case_insensitive(self):
        self.assertEqual(synthesize.validate_digest({"conviction": "High"}, "memory", set())["conviction"], "high")
        self.assertEqual(synthesize.validate_digest({"conviction": "low"}, "memory", set())["conviction"], "low")

    def test_keypoints_non_list_becomes_empty(self):
        d = synthesize.validate_digest({"keyPoints": "not a list"}, "memory", set())
        self.assertEqual(d["keyPoints"], [])

    def test_narrative_defaults_to_empty_string(self):
        d = synthesize.validate_digest({}, "memory", set())
        self.assertEqual(d["narrative"], "")

    def test_category_set_from_arg_not_model(self):
        d = synthesize.validate_digest(good_call("", ""), "photonics", {"AAOI"})
        self.assertEqual(d["category"], "photonics")

    def test_does_not_trust_model_source_ids(self):
        d = synthesize.validate_digest(good_call("", ""), "photonics", {"AAOI"})
        self.assertNotIn("model-made-this-up", d.get("sourceThesisIds", []))


class TestBuildPrompt(unittest.TestCase):
    def test_system_has_injection_firewall(self):
        system, _ = synthesize.build_prompt(CATEGORIES["photonics"], [thesis("t1", ["AAOI"])])
        self.assertIn("instruction", system.lower())

    def test_system_specifies_json_contract(self):
        system, _ = synthesize.build_prompt(CATEGORIES["photonics"], [thesis("t1", ["AAOI"])])
        for key in ("narrative", "conviction", "keyPoints"):
            self.assertIn(key, system)

    def test_user_includes_category_label_and_text(self):
        _, user = synthesize.build_prompt(CATEGORIES["photonics"], [thesis("t1", ["AAOI"], text="optical boom")])
        self.assertIn("Photonics", user)
        self.assertIn("optical boom", user)

    def test_long_thesis_is_clipped(self):
        long_text = "x" * (synthesize.MAX_THESIS_CHARS + 500)
        _, user = synthesize.build_prompt(CATEGORIES["photonics"], [thesis("t1", ["AAOI"], text=long_text)])
        self.assertNotIn("x" * (synthesize.MAX_THESIS_CHARS + 1), user)


class TestSynthesizeAll(unittest.TestCase):
    def _theses(self):
        return [
            thesis("p1", ["AAOI"], posted_at="2026-06-20T00:00:00Z"),
            thesis("p2", ["LITE"], posted_at="2026-06-21T00:00:00Z"),
            thesis("m1", ["MU"], posted_at="2026-06-22T00:00:00Z"),
        ]

    def test_digest_per_nonempty_category(self):
        brain = synthesize.synthesize_all(self._theses(), TICKERS, CATEGORIES, good_call, now=NOW)
        by_cat = {d["category"]: d for d in brain["digests"]}
        self.assertEqual(by_cat["photonics"]["narrative"], "He likes this theme.")
        self.assertEqual(by_cat["memory"]["narrative"], "He likes this theme.")

    def test_empty_category_gets_empty_digest(self):
        brain = synthesize.synthesize_all(self._theses(), TICKERS, CATEGORIES, good_call, now=NOW)
        by_cat = {d["category"]: d for d in brain["digests"]}
        self.assertEqual(by_cat["glass"]["thesesCount"], 0)
        self.assertEqual(by_cat["glass"]["narrative"], "")

    def test_source_ids_and_count_set_by_backend(self):
        brain = synthesize.synthesize_all(self._theses(), TICKERS, CATEGORIES, good_call, now=NOW)
        by_cat = {d["category"]: d for d in brain["digests"]}
        self.assertEqual(set(by_cat["photonics"]["sourceThesisIds"]), {"p1", "p2"})
        self.assertEqual(by_cat["photonics"]["thesesCount"], 2)

    def test_caps_theses_per_category_to_most_recent(self):
        theses = [
            thesis("old", ["AAOI"], posted_at="2026-01-01T00:00:00Z"),
            thesis("mid", ["AAOI"], posted_at="2026-03-01T00:00:00Z"),
            thesis("new", ["AAOI"], posted_at="2026-06-01T00:00:00Z"),
        ]
        brain = synthesize.synthesize_all(theses, TICKERS, CATEGORIES, good_call, now=NOW, max_per_cat=2)
        by_cat = {d["category"]: d for d in brain["digests"]}
        self.assertEqual(set(by_cat["photonics"]["sourceThesisIds"]), {"new", "mid"})

    def test_one_category_failure_does_not_abort_run(self):
        def flaky(system, user):
            if "Memory" in user:
                raise RuntimeError("api boom")
            return good_call(system, user)

        brain = synthesize.synthesize_all(self._theses(), TICKERS, CATEGORIES, flaky, now=NOW)
        by_cat = {d["category"]: d for d in brain["digests"]}
        # photonics still synthesized despite memory failing
        self.assertEqual(by_cat["photonics"]["narrative"], "He likes this theme.")
        self.assertIn("memory", by_cat)  # run completed, memory present (degraded)

    def test_failed_category_carries_forward_previous_digest(self):
        def flaky(system, user):
            if "Memory" in user:
                raise RuntimeError("api boom")
            return good_call(system, user)

        prev = [{"category": "memory", "narrative": "OLD MEMORY VIEW", "conviction": "high",
                 "keyPoints": [], "tickers": ["MU"], "sourceThesisIds": ["m0"], "thesesCount": 1,
                 "lastSynthesized": "2026-05-01T00:00:00Z"}]
        brain = synthesize.synthesize_all(self._theses(), TICKERS, CATEGORIES, flaky, now=NOW, prev_digests=prev)
        by_cat = {d["category"]: d for d in brain["digests"]}
        self.assertEqual(by_cat["memory"]["narrative"], "OLD MEMORY VIEW")

    def test_only_filters_categories(self):
        brain = synthesize.synthesize_all(self._theses(), TICKERS, CATEGORIES, good_call, now=NOW, only={"photonics"})
        cats = {d["category"] for d in brain["digests"]}
        self.assertEqual(cats, {"photonics"})

    def test_only_carries_forward_untargeted_prev_digests(self):
        # A --only run must NOT drop previously-synthesized untargeted categories.
        prev = [{"category": "memory", "narrative": "OLD MEM", "conviction": "high",
                 "keyPoints": [], "tickers": ["MU"], "sourceThesisIds": ["m0"],
                 "thesesCount": 1, "lastSynthesized": "2026-05-01T00:00:00Z"}]
        brain = synthesize.synthesize_all(self._theses(), TICKERS, CATEGORIES, good_call,
                                          now=NOW, only={"photonics"}, prev_digests=prev)
        by_cat = {d["category"]: d for d in brain["digests"]}
        self.assertEqual(by_cat["photonics"]["narrative"], "He likes this theme.")  # fresh
        self.assertEqual(by_cat["memory"]["narrative"], "OLD MEM")  # carried forward

    def test_categories_synthesized_counts_only_fresh(self):
        prev = [{"category": "memory", "narrative": "OLD MEM", "conviction": "high",
                 "keyPoints": [], "tickers": ["MU"], "sourceThesisIds": ["m0"],
                 "thesesCount": 1, "lastSynthesized": "2026-05-01T00:00:00Z"}]
        brain = synthesize.synthesize_all(self._theses(), TICKERS, CATEGORIES, good_call,
                                          now=NOW, only={"photonics"}, prev_digests=prev)
        # only photonics was synthesized this run, even though memory is carried in digests
        self.assertEqual(brain["meta"]["categoriesSynthesized"], 1)

    def test_meta_records_run_context(self):
        brain = synthesize.synthesize_all(self._theses(), TICKERS, CATEGORIES, good_call, now=NOW, model="claude-test")
        self.assertEqual(brain["meta"]["model"], "claude-test")
        self.assertEqual(brain["meta"]["generatedAt"], NOW)
        self.assertEqual(brain["meta"]["thesesConsidered"], 3)


class TestComputeDailyMentions(unittest.TestCase):
    def test_counts_by_day_for_source_theses(self):
        theses = [
            thesis("p1", ["AAOI"], posted_at="2026-06-20T00:00:00Z"),
            thesis("p2", ["AAOI"], posted_at="2026-06-20T00:00:00Z"),
            thesis("p3", ["AAOI"], posted_at="2026-06-21T00:00:00Z"),
        ]
        digests = [{"category": "photonics", "sourceThesisIds": ["p1", "p2", "p3"]}]
        out = synthesize.compute_daily_mentions(theses, digests)
        d = out[0]["dailyMentions"]
        self.assertEqual(d["days"], ["2026-06-20", "2026-06-21"])
        self.assertEqual(d["counts"], [2, 1])

    def test_days_axis_shared_across_all_theses_not_just_category(self):
        theses = [
            thesis("p1", ["AAOI"], posted_at="2026-06-20T00:00:00Z"),
            thesis("m1", ["MU"], posted_at="2026-06-25T00:00:00Z"),
        ]
        digests = [{"category": "photonics", "sourceThesisIds": ["p1"]}]
        out = synthesize.compute_daily_mentions(theses, digests)
        self.assertEqual(out[0]["dailyMentions"]["days"], ["2026-06-20", "2026-06-25"])
        self.assertEqual(out[0]["dailyMentions"]["counts"], [1, 0])

    def test_does_not_mutate_input_digests(self):
        theses = [thesis("p1", ["AAOI"], posted_at="2026-06-20T00:00:00Z")]
        digests = [{"category": "photonics", "sourceThesisIds": ["p1"]}]
        synthesize.compute_daily_mentions(theses, digests)
        self.assertNotIn("dailyMentions", digests[0])

    def test_empty_digest_gets_zeroed_counts(self):
        theses = [thesis("p1", ["AAOI"], posted_at="2026-06-20T00:00:00Z")]
        digests = [{"category": "glass", "sourceThesisIds": []}]
        out = synthesize.compute_daily_mentions(theses, digests)
        self.assertEqual(out[0]["dailyMentions"]["counts"], [0])


class TestParseDotenv(unittest.TestCase):
    def test_basic_pairs(self):
        self.assertEqual(synthesize._parse_dotenv("A=1\nB=two\n"), {"A": "1", "B": "two"})

    def test_skips_comments_and_blanks(self):
        self.assertEqual(synthesize._parse_dotenv("# c\n\nA=1\n"), {"A": "1"})

    def test_strips_only_matched_surrounding_quotes(self):
        d = synthesize._parse_dotenv('A="x"\nB=\'y\'\nC=pa"ss\n')
        self.assertEqual(d["A"], "x")
        self.assertEqual(d["B"], "y")
        self.assertEqual(d["C"], 'pa"ss')  # unmatched inner quote preserved, not truncated

    def test_value_may_contain_equals(self):
        self.assertEqual(synthesize._parse_dotenv("URL=a=b=c\n")["URL"], "a=b=c")


class TestRenderSafety(unittest.TestCase):
    def test_hostile_narrative_survives_render(self):
        hostile = '"}; </script><script>alert(1)</script>'
        brain = {"meta": {}, "digests": [{"category": "photonics", "narrative": hostile,
                 "conviction": "low", "keyPoints": [], "tickers": [], "sourceThesisIds": [],
                 "thesesCount": 0, "lastSynthesized": None}]}
        out = gen.render({"brain": brain})
        self.assertNotIn("</script>", out)


if __name__ == "__main__":
    unittest.main()
