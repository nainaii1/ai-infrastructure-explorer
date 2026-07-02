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
