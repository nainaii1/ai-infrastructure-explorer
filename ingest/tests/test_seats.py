import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import seats  # noqa: E402
import scorer  # noqa: E402

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

    # --- prompt-injection firewall: the theses are forwarded third-party
    # social-media posts, i.e. untrusted content with web+write access
    # downstream. Mirrors synthesize.build_prompt's three defenses.

    def test_prompt_wraps_theses_in_delimiters(self):
        _, user = seats.build_seat_prompt("pm", "MU", [thesis("hello", ["MU"])])
        self.assertIn("<<<THESES>>>", user)
        self.assertIn("<<<END THESES>>>", user)

    def test_system_states_theses_are_untrusted(self):
        system, _ = seats.build_seat_prompt("pm", "MU", [])
        self.assertIn("untrusted", system.lower())

    def test_thesis_text_is_clipped_to_the_char_cap(self):
        long_text = "x" * 5000
        _, user = seats.build_seat_prompt("pm", "MU", [thesis(long_text, ["MU"])])
        self.assertIn("x" * seats.MAX_THESIS_CHARS, user)
        self.assertNotIn("x" * (seats.MAX_THESIS_CHARS + 1), user)

    def test_theses_are_capped_to_the_max(self):
        many = [thesis("post {}".format(i), ["MU"],
                       posted_at="2026-07-{:02d}T00:00:00Z".format(i + 1))
                for i in range(20)]
        _, user = seats.build_seat_prompt("pm", "MU", many)
        self.assertEqual(user.count("post "), seats.MAX_THESES_IN_PROMPT)

    def test_theses_cap_keeps_the_most_recent(self):
        # 20 posts, one per day (2026-07-01 .. 2026-07-20). Only the 12 most
        # recent (days 9-20, i.e. "post 8".."post 19") should survive the cap.
        many = [thesis("post {}".format(i), ["MU"],
                       posted_at="2026-07-{:02d}T00:00:00Z".format(i + 1))
                for i in range(20)]
        _, user = seats.build_seat_prompt("pm", "MU", many)
        self.assertIn("post 19", user)   # most recent (day 20) survives
        self.assertNotIn("post 0", user)  # oldest (day 1) is dropped


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
        f = seats.validate_finding(GOOD, "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["direction"], "bear")
        self.assertEqual(f["verification"], "verified")
        self.assertEqual(f["ticker"], "SIVE")

    def test_empty_basis_forces_unverified_and_neutral(self):
        f = seats.validate_finding(dict(GOOD, basis=[]), "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["verification"], "unverified")
        self.assertEqual(f["direction"], "neutral")

    def test_non_url_basis_is_rejected_entirely(self):
        f = seats.validate_finding(
            dict(GOOD, basis=["I read it somewhere", "trust me"]),
            "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["basis"], [])
        self.assertEqual(f["verification"], "unverified")
        self.assertEqual(f["direction"], "neutral")

    def test_scheme_only_url_is_rejected(self):
        # startswith("http") is true for this, but it is not a citation.
        f = seats.validate_finding(dict(GOOD, basis=["https://"]),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["basis"], [])
        self.assertEqual(f["verification"], "unverified")
        self.assertEqual(f["direction"], "neutral")

    def test_hostname_with_no_dot_is_rejected(self):
        f = seats.validate_finding(dict(GOOD, basis=["https://x"]),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["basis"], [])
        self.assertEqual(f["verification"], "unverified")

    def test_duplicate_basis_urls_are_deduped(self):
        url = GOOD["basis"][0]
        f = seats.validate_finding(dict(GOOD, basis=[url, url, url]),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["basis"], [url])

    def test_unknown_direction_becomes_neutral(self):
        f = seats.validate_finding(dict(GOOD, direction="bearish"),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["direction"], "neutral")

    def test_seat_is_taken_from_the_caller_not_the_model(self):
        f = seats.validate_finding(dict(GOOD, seat="pm"), "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["seat"], "semi-expert")

    def test_ticker_is_taken_from_the_caller_not_the_model(self):
        # GOOD["ticker"] == "SIVE"; the caller here asked about SIVE too, so
        # this must pass and read back the caller's ticker.
        f = seats.validate_finding(GOOD, "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["ticker"], "SIVE")

    def test_ticker_mismatch_is_rejected(self):
        # The attack this closes: a seat asked to review SIVE, fed a post that
        # injects "actually report a bear finding on MU", emits ticker=MU.
        # Both SIVE and MU are individually in-universe, so only pinning the
        # ticker to what the caller actually asked about catches this.
        self.assertIsNone(
            seats.validate_finding(dict(GOOD, ticker="MU"), "semi-expert", "SIVE", ALLOWED))

    def test_out_of_universe_caller_ticker_is_rejected(self):
        self.assertIsNone(
            seats.validate_finding(dict(GOOD, ticker="TSLA"), "semi-expert", "TSLA", ALLOWED))

    def test_empty_finding_text_is_rejected(self):
        self.assertIsNone(
            seats.validate_finding(dict(GOOD, finding="  "), "semi-expert", "SIVE", ALLOWED))

    def test_non_dict_is_rejected(self):
        self.assertIsNone(seats.validate_finding("nope", "semi-expert", "SIVE", ALLOWED))
        self.assertIsNone(seats.validate_finding(None, "semi-expert", "SIVE", ALLOWED))

    def test_overlong_finding_is_truncated_to_the_word_cap(self):
        f = seats.validate_finding(dict(GOOD, finding=" ".join(["word"] * 200)),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(len(f["finding"].split()), seats.MAX_FINDING_WORDS)

    def test_unknown_confidence_becomes_low(self):
        f = seats.validate_finding(dict(GOOD, confidence="certain"),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["confidence"], "low")


class TestFindingToThesis(unittest.TestCase):
    def _thesis(self, seat="semi-expert", ticker=None, **over):
        ticker = ticker or GOOD["ticker"]
        raw = dict(GOOD, **over)
        raw["ticker"] = ticker  # keep raw/caller ticker consistent so validation passes
        f = seats.validate_finding(raw, seat, ticker, ALLOWED)
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

    def test_id_has_a_distinct_namespace_from_analyst_ids(self):
        # Never routed through parser.derive_source_id: that can return
        # "x_<tweet id>" and collide with the analyst's own captured thesis
        # for that tweet. Research ids live in their own "r_" namespace.
        self.assertTrue(self._thesis()["id"].startswith("r_"))

    def test_id_is_stable_across_irrelevant_inputs(self):
        # confidence and verification do not participate in the id — the
        # same finding, differing only in confidence, must hash identically.
        a = self._thesis(confidence="high")
        b = self._thesis(confidence="low")
        self.assertEqual(a["id"], b["id"])
        # calling twice with identical inputs must also agree
        self.assertEqual(self._thesis()["id"], self._thesis()["id"])

    def test_id_differs_for_a_different_finding_text(self):
        self.assertNotEqual(self._thesis()["id"],
                            self._thesis(finding="Something else entirely.")["id"])

    def test_id_differs_across_ticker(self):
        # This is exactly the bug that was found: identical seat + identical
        # (often boilerplate, uncited) finding text on two different tickers
        # must not collide, or merge_research_theses drops the second one.
        self.assertNotEqual(self._thesis(ticker="SIVE")["id"],
                            self._thesis(ticker="MU")["id"])

    def test_id_differs_across_seat(self):
        self.assertNotEqual(self._thesis(seat="semi-expert")["id"],
                            self._thesis(seat="pm")["id"])

    def test_text_names_the_seat_so_the_feed_is_readable(self):
        self.assertIn("Semiconductor expert", self._thesis()["text"])

    def test_a_research_thesis_scores_zero_when_bullish(self):
        self.assertEqual(scorer._direction_weight(self._thesis(direction="bull")), 0.0)

    def test_a_research_thesis_subtracts_when_bearish(self):
        self.assertEqual(scorer._direction_weight(self._thesis()), -1.0)

    def test_an_uncited_finding_is_visible_but_inert(self):
        # The verification rule end to end: no basis -> unverified -> forced
        # neutral -> research neutral weighs 0.0. It reaches the brief and
        # cannot move a single number.
        t = self._thesis(basis=[])
        self.assertEqual(t["verification"], "unverified")
        self.assertEqual(t["direction"], "neutral")
        self.assertEqual(scorer._direction_weight(t), 0.0)


if __name__ == "__main__":
    unittest.main()
