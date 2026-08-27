import sys
import pathlib
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import watcher  # noqa: E402

HANDLE = "aleabitoreddit"


def item(href, social=""):
    return {"href": href, "socialContext": social}


class TestParsePermalink(unittest.TestCase):
    def test_extracts_handle_and_id(self):
        self.assertEqual(watcher.parse_permalink("/aleabitoreddit/status/123"),
                         ("aleabitoreddit", "123"))

    def test_ignores_query_string(self):
        self.assertEqual(watcher.parse_permalink("/x/status/9?s=20"), ("x", "9"))

    def test_rejects_non_status_paths(self):
        for href in ["/aleabitoreddit", "/a/status/notanumber", "", None,
                     "/a/photo/1", "/i/web/status"]:
            self.assertEqual(watcher.parse_permalink(href), (None, None), href)


class TestClassifyItems(unittest.TestCase):
    def test_keeps_own_posts(self):
        got = watcher.classify_items([item("/aleabitoreddit/status/5")], HANDLE)
        self.assertEqual(len(got), 1)
        self.assertFalse(got[0]["isRepost"])
        self.assertEqual(got[0]["url"], "https://x.com/aleabitoreddit/status/5")

    def test_drops_foreign_post_without_repost_marker(self):
        """A stranger's reply rendered as thread context must NOT be ingested.

        Observed live 30 Jul 2026: /stockprodigyman/status/... appeared on his
        profile because he was in the thread. Filing it would attribute another
        person's words to him.
        """
        got = watcher.classify_items([item("/stockprodigyman/status/7")], HANDLE)
        self.assertEqual(got, [])

    def test_keeps_foreign_post_when_marked_repost(self):
        got = watcher.classify_items(
            [item("/someone/status/8", social="Serenity reposted")], HANDLE)
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0]["isRepost"])
        self.assertEqual(got[0]["author"], "someone")

    def test_own_post_is_never_marked_repost(self):
        got = watcher.classify_items(
            [item("/aleabitoreddit/status/9", social="Serenity reposted")], HANDLE)
        self.assertFalse(got[0]["isRepost"])

    def test_dedupes_repeated_hrefs_across_scrolls(self):
        raw = [item("/aleabitoreddit/status/1"), item("/aleabitoreddit/status/1"),
               item("/aleabitoreddit/status/2")]
        self.assertEqual([p["id"] for p in watcher.classify_items(raw, HANDLE)],
                         ["1", "2"])

    def test_handle_match_is_case_insensitive(self):
        got = watcher.classify_items([item("/AleAbitoReddit/status/3")], HANDLE)
        self.assertEqual(len(got), 1)
        self.assertFalse(got[0]["isRepost"])


class TestNewerThan(unittest.TestCase):
    def posts(self, *ids):
        return [{"id": str(i)} for i in ids]

    def test_filters_and_sorts_newest_first(self):
        got = watcher.newer_than(self.posts(10, 30, 20), "15")
        self.assertEqual([p["id"] for p in got], ["30", "20"])

    def test_no_since_returns_everything(self):
        self.assertEqual(len(watcher.newer_than(self.posts(1, 2), None)), 2)

    def test_garbage_since_is_treated_as_zero(self):
        self.assertEqual(len(watcher.newer_than(self.posts(1, 2), "oops")), 2)

    def test_compares_numerically_not_lexically(self):
        # "9" > "10" as strings; snowflake ids must compare as integers.
        got = watcher.newer_than(self.posts(10), "9")
        self.assertEqual([p["id"] for p in got], ["10"])

    def test_max_id(self):
        self.assertEqual(watcher.max_id(self.posts(5, 100, 20)), "100")
        self.assertIsNone(watcher.max_id([]))


def _posts(*ids):
    return [{"id": str(i), "url": "https://x.com/h/status/{}".format(i)} for i in ids]


class TestNextWatermark(unittest.TestCase):
    def test_all_verified_advances_to_top(self):
        top, retry, gave_up = watcher.next_watermark(_posts(10, 11, 12), [], {})
        self.assertEqual(top, "12")
        self.assertEqual((retry, gave_up), ([], []))

    def test_mark_stops_below_the_failed_post(self):
        # 12 failed -> the mark must not pass it, or it is lost forever.
        top, retry, gave_up = watcher.next_watermark(
            _posts(10, 11, 12, 13), _posts(12), {})
        self.assertEqual(top, "11")
        self.assertEqual(retry, ["12"])
        self.assertEqual(gave_up, [])

    def test_oldest_failure_wins_when_several_fail(self):
        top, _, _ = watcher.next_watermark(
            _posts(10, 11, 12, 13), _posts(13, 11), {})
        self.assertEqual(top, "10")

    def test_mark_does_not_move_when_the_oldest_post_failed(self):
        top, retry, _ = watcher.next_watermark(_posts(10, 11), _posts(10), {})
        self.assertIsNone(top)
        self.assertEqual(retry, ["10"])

    def test_gives_up_after_max_attempts_and_moves_on(self):
        attempts = {"12": watcher.MAX_VERIFY_ATTEMPTS - 1}
        top, retry, gave_up = watcher.next_watermark(
            _posts(10, 11, 12, 13), _posts(12), attempts)
        self.assertEqual(gave_up, ["12"])
        self.assertEqual(retry, [])
        self.assertEqual(top, "13")  # no longer held back

    def test_a_post_still_under_the_limit_is_retried_not_abandoned(self):
        attempts = {"12": watcher.MAX_VERIFY_ATTEMPTS - 2}
        top, retry, gave_up = watcher.next_watermark(
            _posts(11, 12, 13), _posts(12), attempts)
        self.assertEqual((retry, gave_up), (["12"], []))
        self.assertEqual(top, "11")

    def test_empty_page_moves_nothing(self):
        self.assertEqual(watcher.next_watermark([], [], {}), (None, [], []))


class TestStaleness(unittest.TestCase):
    def state(self, hours_ago, alarm_hours_ago=None):
        now = datetime.now(timezone.utc)
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        s = {"lastPostFoundAt": (now - timedelta(hours=hours_ago)).strftime(fmt)}
        if alarm_hours_ago is not None:
            s["lastAlarmAt"] = (now - timedelta(hours=alarm_hours_ago)).strftime(fmt)
        return s

    def test_fresh_is_not_stale(self):
        self.assertFalse(watcher.is_stale(self.state(2)))

    def test_old_is_stale(self):
        self.assertTrue(watcher.is_stale(self.state(30)))

    def test_never_found_does_not_cry_wolf(self):
        self.assertFalse(watcher.is_stale({}))

    def test_unparseable_timestamp_fails_quiet(self):
        self.assertFalse(watcher.is_stale({"lastPostFoundAt": "not-a-date"}))

    def test_alarm_respects_cooldown(self):
        self.assertFalse(watcher.should_alarm(self.state(30, alarm_hours_ago=1)))
        self.assertTrue(watcher.should_alarm(self.state(30, alarm_hours_ago=48)))

    def test_alarm_fires_when_never_alarmed(self):
        self.assertTrue(watcher.should_alarm(self.state(30)))


class TestDeliveryWindow(unittest.TestCase):
    def test_delivers_at_midnight_and_noon(self):
        for h in (0, 12):
            self.assertTrue(watcher.is_delivery_time(datetime(2026, 7, 30, h, 5)))

    def test_silent_otherwise(self):
        for h in (1, 6, 11, 13, 23):
            self.assertFalse(watcher.is_delivery_time(datetime(2026, 7, 30, h, 5)))


class TestFormatting(unittest.TestCase):
    def test_own_post_header(self):
        msg = watcher.format_post_message(
            {"author": HANDLE, "url": "u", "text": "hello", "postedAt": "t"})
        self.assertIn("🆕 New post", msg)
        self.assertIn("hello", msg)

    def test_repost_header_names_original_author(self):
        msg = watcher.format_post_message(
            {"author": "bob", "isRepost": True, "url": "u", "text": "x", "postedAt": "t"})
        self.assertIn("🔁", msg)
        self.assertIn("bob", msg)

    def test_long_text_is_truncated_for_telegram(self):
        msg = watcher.format_post_message(
            {"author": HANDLE, "url": "u", "text": "z" * 6000, "postedAt": "t"})
        self.assertLess(len(msg), 4096)
        self.assertIn("truncated", msg)


import bot  # noqa: E402


class TestHandleCallback(unittest.TestCase):
    """Button taps. The store is stubbed — these must never touch real data."""

    ALLOWED = "555"

    def setUp(self):
        self.queue = [{
            "id": "100", "url": "https://x.com/aleabitoreddit/status/100",
            "author": "aleabitoreddit", "verifiedAuthor": "aleabitoreddit",
            "isRepost": False, "text": "$NVDA up", "postedAt": "2026-07-30T00:00:00Z",
            "status": "pending", "notifiedAt": None,
        }]
        self.saved = []
        self.ingested = []
        self._orig = (bot._load_pending_posts, bot.save_json, bot.ingest_message)
        bot._load_pending_posts = lambda: self.queue
        bot.save_json = lambda name, data, **kw: self.saved.append((name, data))

        def fake_ingest(text, source_url="", posted_at=None, author="aleabitoreddit"):
            self.ingested.append({"text": text, "url": source_url, "author": author})
            return {"id": "h_new", "tickers": ["NVDA"], "added": [], "queued": []}
        bot.ingest_message = fake_ingest

    def tearDown(self):
        bot._load_pending_posts, bot.save_json, bot.ingest_message = self._orig

    def test_rejects_other_telegram_users(self):
        reply, answer = bot.handle_callback("ok:100", "999", self.ALLOWED)
        self.assertIsNone(reply)
        self.assertIn("authoris", answer.lower())
        self.assertEqual(self.ingested, [])

    def test_rejects_unknown_button_data(self):
        for data in ["", "weird", "maybe:100", "ok:"]:
            reply, _ = bot.handle_callback(data, self.ALLOWED, self.ALLOWED)
            self.assertIsNone(reply)
        self.assertEqual(self.ingested, [])

    def test_unknown_post_id_is_reported_not_ingested(self):
        reply, answer = bot.handle_callback("ok:999", self.ALLOWED, self.ALLOWED)
        self.assertIsNone(reply)
        self.assertIn("no longer", answer)
        self.assertEqual(self.ingested, [])

    def test_approve_ingests_and_marks_the_post(self):
        reply, answer = bot.handle_callback("ok:100", self.ALLOWED, self.ALLOWED)
        self.assertEqual(len(self.ingested), 1)
        self.assertEqual(self.ingested[0]["text"], "$NVDA up")
        self.assertEqual(self.queue[0]["status"], "ingested")
        self.assertEqual(self.queue[0]["thesisId"], "h_new")
        self.assertIn("Ingested", answer)
        self.assertIn("NVDA", reply)

    def test_skip_does_not_ingest(self):
        reply, answer = bot.handle_callback("no:100", self.ALLOWED, self.ALLOWED)
        self.assertEqual(self.ingested, [])
        self.assertEqual(self.queue[0]["status"], "skipped")
        self.assertIn("Skipped", reply)

    def test_second_tap_is_refused(self):
        bot.handle_callback("ok:100", self.ALLOWED, self.ALLOWED)
        reply, answer = bot.handle_callback("ok:100", self.ALLOWED, self.ALLOWED)
        self.assertIsNone(reply)
        self.assertIn("Already", answer)
        self.assertEqual(len(self.ingested), 1, "must not ingest twice")

    def test_repost_is_filed_under_the_original_author(self):
        self.queue[0].update(isRepost=True, author="bob", verifiedAuthor="bob")
        bot.handle_callback("ok:100", self.ALLOWED, self.ALLOWED)
        self.assertEqual(self.ingested[0]["author"], "bob",
                         "a repost must not be credited to @aleabitoreddit")

    def test_failed_ingest_leaves_post_pending_for_retry(self):
        def boom(*a, **kw):
            raise RuntimeError("disk full")
        bot.ingest_message = boom
        reply, answer = bot.handle_callback("ok:100", self.ALLOWED, self.ALLOWED)
        self.assertEqual(self.queue[0]["status"], "pending")
        self.assertIn("disk full", reply)


if __name__ == "__main__":
    unittest.main()
