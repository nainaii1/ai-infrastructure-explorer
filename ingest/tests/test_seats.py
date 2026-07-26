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

    def test_theses_are_capped(self):
        many = [thesis("post %d" % i, ["MU"]) for i in range(50)]
        _, user = seats.build_seat_prompt("pm", "MU", many)
        self.assertLessEqual(user.count("post "), seats.MAX_THESES_IN_PROMPT)


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
        f = seats.validate_finding(dict(GOOD, basis=[]), "semi-expert", ALLOWED)
        self.assertEqual(f["verification"], "unverified")
        self.assertEqual(f["direction"], "neutral")

    def test_non_url_basis_is_rejected_entirely(self):
        f = seats.validate_finding(
            dict(GOOD, basis=["I read it somewhere", "trust me"]),
            "semi-expert", ALLOWED)
        self.assertEqual(f["basis"], [])
        self.assertEqual(f["verification"], "unverified")
        self.assertEqual(f["direction"], "neutral")

    def test_unknown_direction_becomes_neutral(self):
        f = seats.validate_finding(dict(GOOD, direction="bearish"),
                                   "semi-expert", ALLOWED)
        self.assertEqual(f["direction"], "neutral")

    def test_seat_is_taken_from_the_caller_not_the_model(self):
        f = seats.validate_finding(dict(GOOD, seat="pm"), "semi-expert", ALLOWED)
        self.assertEqual(f["seat"], "semi-expert")

    def test_out_of_universe_ticker_is_rejected(self):
        self.assertIsNone(
            seats.validate_finding(dict(GOOD, ticker="TSLA"), "semi-expert", ALLOWED))

    def test_empty_finding_text_is_rejected(self):
        self.assertIsNone(
            seats.validate_finding(dict(GOOD, finding="  "), "semi-expert", ALLOWED))

    def test_non_dict_is_rejected(self):
        self.assertIsNone(seats.validate_finding("nope", "semi-expert", ALLOWED))
        self.assertIsNone(seats.validate_finding(None, "semi-expert", ALLOWED))

    def test_overlong_finding_is_truncated_to_the_word_cap(self):
        f = seats.validate_finding(dict(GOOD, finding=" ".join(["word"] * 200)),
                                   "semi-expert", ALLOWED)
        self.assertEqual(len(f["finding"].split()), seats.MAX_FINDING_WORDS)

    def test_unknown_confidence_becomes_low(self):
        f = seats.validate_finding(dict(GOOD, confidence="certain"),
                                   "semi-expert", ALLOWED)
        self.assertEqual(f["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
