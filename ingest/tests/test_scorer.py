import math
import sys
import pathlib
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import scorer  # noqa: E402

NOW = datetime(2026, 6, 26, tzinfo=timezone.utc)


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


class TestPriority(unittest.TestCase):
    def test_recent_outranks_old(self):
        theses = [
            thesis(["OLD"], "2026-01-01T00:00:00Z"),
            thesis(["NEW"], "2026-06-25T00:00:00Z"),
        ]
        ranked = scorer.compute_priorities(theses, now=NOW)
        self.assertEqual(ranked[0]["ticker"], "NEW")

    def test_mentions_counted(self):
        theses = [
            thesis(["AAOI"], "2026-06-20T00:00:00Z"),
            thesis(["AAOI"], "2026-06-21T00:00:00Z"),
            thesis(["MU"], "2026-06-21T00:00:00Z"),
        ]
        ranked = {r["ticker"]: r for r in scorer.compute_priorities(theses, now=NOW)}
        self.assertEqual(ranked["AAOI"]["mentions"], 2)
        self.assertEqual(ranked["MU"]["mentions"], 1)

    def test_conviction_no_longer_boosts_score_but_is_still_counted(self):
        # Superseded 2026-07-26 (Task 6, operator sign-off): this test used to
        # assertGreater(boosted, base) because CONVICTION_WEIGHT=0.5 multiplied
        # score by up to 6x on keyword-matched rhetoric alone. That multiplier
        # is retired (CONVICTION_WEIGHT=0.0) — conviction language must no
        # longer move score, only convictionHits (which assign_tiers reads
        # directly). See TestConvictionRetired below for the full coverage.
        base = scorer.compute_priorities([thesis(["X"], "2026-06-25T00:00:00Z")], now=NOW)
        boosted = scorer.compute_priorities(
            [thesis(["X"], "2026-06-25T00:00:00Z", conviction="high")], now=NOW
        )
        self.assertEqual(boosted[0]["score"], base[0]["score"])
        self.assertEqual(boosted[0]["convictionHits"], 1)

    def test_last_mentioned_is_most_recent(self):
        theses = [
            thesis(["AAOI"], "2026-06-10T00:00:00Z"),
            thesis(["AAOI"], "2026-06-24T00:00:00Z"),
        ]
        ranked = scorer.compute_priorities(theses, now=NOW)
        self.assertEqual(ranked[0]["lastMentioned"], "2026-06-24T00:00:00Z")

    def test_empty_input(self):
        self.assertEqual(scorer.compute_priorities([], now=NOW), [])


class TestAssignTiers(unittest.TestCase):
    def _tiers(self, theses, symbols):
        priorities = scorer.compute_priorities(theses, now=NOW)
        return scorer.assign_tiers(symbols, priorities)

    def test_repeated_mentions_make_core(self):
        theses = [thesis(["SIVE"], "2026-06-2%d T00:00:00Z".replace(" ", "") % d) for d in range(1, 6)]
        tiers = self._tiers(theses, ["SIVE"])
        self.assertEqual(tiers["SIVE"], "core")

    def test_conviction_promotes_to_core_with_few_mentions(self):
        theses = [
            thesis(["POET"], "2026-06-20T00:00:00Z", conviction="high"),
            thesis(["POET"], "2026-06-21T00:00:00Z", conviction="high"),
        ]
        tiers = self._tiers(theses, ["POET"])
        self.assertEqual(tiers["POET"], "core")

    def test_two_mentions_is_watch(self):
        theses = [
            thesis(["AMAT"], "2026-06-20T00:00:00Z"),
            thesis(["AMAT"], "2026-06-21T00:00:00Z"),
        ]
        tiers = self._tiers(theses, ["AMAT"])
        self.assertEqual(tiers["AMAT"], "watch")

    def test_single_high_conviction_mention_is_watch(self):
        theses = [thesis(["AMZN"], "2026-06-20T00:00:00Z", conviction="high")]
        tiers = self._tiers(theses, ["AMZN"])
        self.assertEqual(tiers["AMZN"], "watch")

    def test_single_normal_mention_is_radar(self):
        theses = [thesis(["ZZZZ"], "2026-06-20T00:00:00Z")]
        tiers = self._tiers(theses, ["ZZZZ"])
        self.assertEqual(tiers["ZZZZ"], "radar")

    def test_never_mentioned_is_radar(self):
        tiers = self._tiers([], ["GHOST"])
        self.assertEqual(tiers["GHOST"], "radar")

    def test_every_symbol_gets_a_tier(self):
        theses = [thesis(["A"], "2026-06-20T00:00:00Z")]
        tiers = self._tiers(theses, ["A", "B", "C"])
        self.assertEqual(sorted(tiers.keys()), ["A", "B", "C"])


class TestCanonicalize(unittest.TestCase):
    """canonicalize_theses: alias remap + theme-tag drop, no mutation."""

    def test_alias_remaps_to_canonical_symbol(self):
        theses = [thesis(["SIVEF"], "2026-06-20T00:00:00Z")]
        out = scorer.canonicalize_theses(theses, aliases={"SIVEF": "SIVE"})
        self.assertEqual(out[0]["tickers"], ["SIVE"])

    def test_alias_collapses_duplicate_in_same_post(self):
        theses = [thesis(["SIVE", "SIVEF"], "2026-06-20T00:00:00Z")]
        out = scorer.canonicalize_theses(theses, aliases={"SIVEF": "SIVE"})
        self.assertEqual(out[0]["tickers"], ["SIVE"])

    def test_theme_tag_dropped(self):
        theses = [thesis(["MU", "DRAM"], "2026-06-20T00:00:00Z")]
        out = scorer.canonicalize_theses(theses, theme_tags=["DRAM"])
        self.assertEqual(out[0]["tickers"], ["MU"])

    def test_originals_not_mutated(self):
        theses = [thesis(["SIVEF", "DRAM"], "2026-06-20T00:00:00Z")]
        scorer.canonicalize_theses(
            theses, aliases={"SIVEF": "SIVE"}, theme_tags=["DRAM"])
        self.assertEqual(theses[0]["tickers"], ["SIVEF", "DRAM"])

    def test_no_config_is_identity(self):
        theses = [thesis(["MU"], "2026-06-20T00:00:00Z")]
        out = scorer.canonicalize_theses(theses)
        self.assertEqual(out[0]["tickers"], ["MU"])

    def test_alias_mentions_merge_in_priorities(self):
        theses = [
            thesis(["SIVE"], "2026-06-20T00:00:00Z"),
            thesis(["SIVEF"], "2026-06-21T00:00:00Z"),
        ]
        out = scorer.canonicalize_theses(theses, aliases={"SIVEF": "SIVE"})
        ranked = scorer.compute_priorities(out, now=NOW)
        self.assertEqual(ranked[0]["ticker"], "SIVE")
        self.assertEqual(ranked[0]["mentions"], 2)


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

    def test_attention_and_direction_counts_exposed(self):
        theses = [
            thesis(["SIVE"], "2026-06-26T00:00:00Z", direction="bull"),
            thesis(["SIVE"], "2026-06-26T00:00:00Z", direction="bull"),
            thesis(["SIVE"], "2026-06-26T00:00:00Z", direction="bear"),
        ]
        r = scorer.compute_priorities(theses, now=NOW)[0]
        self.assertEqual(r["attention"], 3.0)
        self.assertEqual(r["net"], 1.0)
        self.assertEqual(r["bullMentions"], 2)
        self.assertEqual(r["bearMentions"], 1)
        self.assertEqual(r["mentions"], 3)

    def test_research_never_inflates_weighted_or_tier(self):
        # Reviewer-found gap: research posts already zero out score/net, but
        # weightedMentions (what assign_tiers reads) accumulated regardless of
        # source. Five research-sourced bull posts used to promote a name to
        # "core" while its score sat at 0.0 — research correcting a score is
        # fine; research creating coverage on its own is the exact self-dealing
        # the model must not be able to do.
        theses = [
            thesis(["ZETA"], "2026-06-26T00:00:00Z", direction="bull", source="research")
            for _ in range(5)
        ]
        priorities = scorer.compute_priorities(theses, now=NOW)
        r = priorities[0]
        self.assertEqual(r["score"], 0.0)
        self.assertEqual(r["net"], 0.0)
        self.assertEqual(r["mentions"], 5)          # raw count still honest
        self.assertEqual(r["weightedMentions"], 0.0)  # but contributes no tiering signal
        tiers = scorer.assign_tiers(["ZETA"], priorities)
        self.assertEqual(tiers["ZETA"], "radar")

    def test_unknown_direction_does_not_score_like_neutral(self):
        # Superseded an earlier test that asserted the opposite. Normalizing a
        # typo to "neutral" gives it +1.0 — but "bearish" was meant as a bear,
        # so that swings the score two points the wrong way. An unreadable
        # direction must be inert, which is strictly different from neutral.
        for bad in ("bearish", "BEAR", "short", "gibberish"):
            with self.subTest(direction=bad):
                weird = [thesis(["QQQQ"], "2026-06-26T00:00:00Z", direction=bad)]
                neutral = [thesis(["QQQQ"], "2026-06-26T00:00:00Z", direction="neutral")]
                r_weird = scorer.compute_priorities(weird, now=NOW)[0]
                r_neutral = scorer.compute_priorities(neutral, now=NOW)[0]
                self.assertEqual(r_weird["net"], 0.0)
                self.assertEqual(r_neutral["net"], 1.0)
                self.assertNotEqual(r_weird["net"], r_neutral["net"])
                self.assertEqual(r_weird["bullMentions"], 0)
                self.assertEqual(r_weird["bearMentions"], 0)
                self.assertEqual(r_weird["mentions"], 1)

    def test_bear_mention_in_list_post_subtracts_only_its_focus_share(self):
        # A bear vote buried in a 12-name dump should cost a name its
        # focus-discounted share (~0.289), not a full -1.0 — otherwise a
        # refactor that drops `focus` from the `signed` product (leaving only
        # weight * direction_weight) would sail through every other test in
        # this file untouched.
        dedicated_bull = thesis(["POET"], "2026-06-26T00:00:00Z", direction="bull")
        dump_tickers = ["POET"] + [f"X{i}" for i in range(11)]  # 12 names total
        bear_in_dump = thesis(dump_tickers, "2026-06-26T00:00:00Z", direction="bear")

        r = scorer.compute_priorities([dedicated_bull, bear_in_dump], now=NOW)
        poet = next(x for x in r if x["ticker"] == "POET")

        expected_net = round(1.0 - (1.0 / math.sqrt(12)), 4)
        self.assertEqual(poet["net"], expected_net)
        self.assertGreater(poet["net"], 0.0)  # sanity: NOT fully cancelled

    def test_assign_tiers_uses_weighted_mentions_not_score(self):
        # Every other tier test uses neutral theses, where score and
        # weightedMentions rise together — a refactor that swapped
        # assign_tiers to gate on `score` instead of `weightedMentions` would
        # still pass all of them. Five dedicated bear posts give
        # weightedMentions=5.0 (core-eligible attention) while net/score sit
        # at 0.0 (nothing to rank) — tier must still come out "core".
        theses = [
            thesis(["POET"], f"2026-06-{20 + i}T00:00:00Z", direction="bear")
            for i in range(5)
        ]
        priorities = scorer.compute_priorities(theses, now=NOW)
        p = priorities[0]
        self.assertEqual(p["score"], 0.0)
        self.assertEqual(p["weightedMentions"], 5.0)
        tiers = scorer.assign_tiers(["POET"], priorities)
        self.assertEqual(tiers["POET"], "core")

    def test_unrecognized_direction_is_inert_not_a_bull_vote(self):
        # "bearish" was meant as a bear. Falling back to neutral would score it
        # +1.0 and swing the result two points the wrong way, so a direction we
        # cannot read contributes nothing at all.
        for typo in ("bearish", "BEAR", "short", ""):
            with self.subTest(direction=typo):
                r = scorer.compute_priorities(
                    [thesis(["X"], "2026-06-26T00:00:00Z", direction=typo)],
                    now=NOW)[0]
                self.assertEqual(r["net"], 0.0)
                self.assertEqual(r["bullMentions"], 0)
                self.assertEqual(r["bearMentions"], 0)
                self.assertEqual(r["mentions"], 1)

    def test_absent_direction_is_not_treated_as_malformed(self):
        # The migrated records have no direction key at all. Absent must keep
        # its full 1.0 weight, or re-scoring the existing store would silently
        # zero every historical mention.
        r = scorer.compute_priorities(
            [thesis(["X"], "2026-06-26T00:00:00Z")], now=NOW)[0]
        self.assertEqual(r["net"], 1.0)

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


class TestResearchSourceIsFailSafe(unittest.TestCase):
    def test_miscased_research_source_is_still_research(self):
        # These records are hand-authored by an agent. A miscased "Research"
        # must not revert the name to full analyst treatment — that would hand
        # back both the score weight and the tier coverage the asymmetry
        # exists to withhold.
        for spelling in ("research", "Research", "RESEARCH", " research "):
            with self.subTest(source=spelling):
                theses = [
                    thesis(["Z"], "2026-06-26T00:00:00Z",
                           conviction="high", direction="bull", source=spelling),
                    thesis(["Z"], "2026-06-25T00:00:00Z",
                           conviction="high", direction="bull", source=spelling),
                ]
                pri = scorer.compute_priorities(theses, now=NOW)
                self.assertEqual(pri[0]["convictionHits"], 0)
                self.assertEqual(pri[0]["weightedMentions"], 0.0)
                self.assertEqual(scorer.assign_tiers(["Z"], pri)["Z"], "radar")

    def test_absent_source_still_reads_as_analyst(self):
        # Every one of the captured posts predates the field and is genuinely
        # his, so absent must keep full weight.
        th = {"tickers": ["Z"], "postedAt": "2026-06-26T00:00:00Z",
              "conviction": "normal"}
        r = scorer.compute_priorities([th], now=NOW)[0]
        self.assertEqual(r["net"], 1.0)
        self.assertEqual(r["researchMentions"], 0)

    def test_tiers_do_not_fall_back_to_raw_mentions(self):
        # `mentions` counts research, so a row missing weightedMentions must
        # read as zero attention rather than as research attention.
        rows = [{"ticker": "Z", "mentions": 6, "convictionHits": 0}]
        self.assertEqual(scorer.assign_tiers(["Z"], rows)["Z"], "radar")


class TestResearchIsNotAnalystAttention(unittest.TestCase):
    """Everything the app labels "@aleabitoreddit" must exclude desk research.

    The tier and score guards already exist. These cover the *attribution*
    surfaces: a count, a recency figure or a date presented as the analyst's
    must not silently include findings the desk wrote itself.
    """

    def _rows(self, theses):
        return {r["ticker"]: r for r in scorer.compute_priorities(theses, now=NOW)}

    def test_analyst_mentions_exclude_research(self):
        theses = [
            thesis(["MU"], "2026-06-20T00:00:00Z"),
            thesis(["MU"], "2026-06-21T00:00:00Z"),
            thesis(["MU"], "2026-06-22T00:00:00Z", source="research"),
            thesis(["MU"], "2026-06-23T00:00:00Z", source="research"),
        ]
        r = self._rows(theses)["MU"]
        self.assertEqual(r["mentions"], 4)          # raw total, unchanged
        self.assertEqual(r["researchMentions"], 2)
        self.assertEqual(r["analystMentions"], 2)   # what the tooltip may claim

    def test_a_miscased_research_source_still_does_not_count_as_analyst(self):
        theses = [thesis(["MU"], "2026-06-20T00:00:00Z", source="Research")]
        r = self._rows(theses)["MU"]
        self.assertEqual(r["analystMentions"], 0)

    def test_research_adds_no_attention(self):
        # attention is an aggregate; research may subtract but never add.
        analyst_only = self._rows([thesis(["MU"], "2026-06-20T00:00:00Z")])["MU"]
        with_research = self._rows([
            thesis(["MU"], "2026-06-20T00:00:00Z"),
            thesis(["MU"], "2026-06-20T00:00:00Z", source="research"),
        ])["MU"]
        self.assertEqual(with_research["attention"], analyst_only["attention"])
        research_only = self._rows(
            [thesis(["MU"], "2026-06-20T00:00:00Z", source="research")])["MU"]
        self.assertEqual(research_only["attention"], 0.0)

    def test_last_mentioned_ignores_research(self):
        # The vault renders this as "Last cited" on the analyst's own page. A
        # desk finding written today must not become his most recent word.
        theses = [
            thesis(["MU"], "2026-06-20T00:00:00Z"),
            thesis(["MU"], "2026-06-25T00:00:00Z", source="research"),
        ]
        self.assertEqual(self._rows(theses)["MU"]["lastMentioned"],
                         "2026-06-20T00:00:00Z")

    def test_a_research_only_name_has_no_last_mentioned(self):
        theses = [thesis(["MU"], "2026-06-25T00:00:00Z", source="research")]
        self.assertIsNone(self._rows(theses)["MU"]["lastMentioned"])


if __name__ == "__main__":
    unittest.main()
