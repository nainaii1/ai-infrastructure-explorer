import sys
import pathlib
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import scorer  # noqa: E402

NOW = datetime(2026, 6, 26, tzinfo=timezone.utc)


def thesis(tickers, posted_at, conviction="normal"):
    return {"tickers": tickers, "postedAt": posted_at, "conviction": conviction}


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

    def test_conviction_boosts_score(self):
        base = scorer.compute_priorities([thesis(["X"], "2026-06-25T00:00:00Z")], now=NOW)
        boosted = scorer.compute_priorities(
            [thesis(["X"], "2026-06-25T00:00:00Z", conviction="high")], now=NOW
        )
        self.assertGreater(boosted[0]["score"], base[0]["score"])
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


if __name__ == "__main__":
    unittest.main()
