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


if __name__ == "__main__":
    unittest.main()
