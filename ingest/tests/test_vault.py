import sys
import pathlib
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import vault_sync as vs  # noqa: E402


# --- tiny fixtures --------------------------------------------------------

CATEGORIES = {
    "photonics": {"label": "Photonics", "flowRole": "supply"},
    "memory": {"label": "Memory", "flowRole": "supply"},
}

GLOSSARY = [
    {"term": "HBM", "def": "High-bandwidth memory."},
    {"term": "CoWoS", "def": "Advanced packaging."},
]

# Theses crafted so tiers are predictable via scorer:
#   AAOI: 2 high-conviction hits -> core
#   MU:   1 mention, 1 conviction -> watch
#   ZZZZ: 1 plain mention -> radar (no page)
THESES = [
    {"id": "t1", "postedAt": "2026-07-10", "conviction": "high", "tickers": ["AAOI"]},
    {"id": "t2", "postedAt": "2026-07-09", "conviction": "high", "tickers": ["AAOI"]},
    {"id": "t3", "postedAt": "2026-07-08", "conviction": "high", "tickers": ["MU"]},
    {"id": "t4", "postedAt": "2026-07-07", "conviction": "low", "tickers": ["ZZZZ"]},
]

TICKERS = [
    {"ticker": "AAOI", "company": "Applied Opto", "category": "photonics",
     "market": "US", "marketCapTier": "Small"},
    {"ticker": "MU", "company": "Micron", "category": "memory",
     "market": "US", "marketCapTier": "Large"},
    {"ticker": "ZZZZ", "company": "Radar Co", "category": "photonics",
     "market": "US", "marketCapTier": "Small"},
]

FIXED_NOW = datetime(2026, 7, 12, 0, 0, 0, tzinfo=timezone.utc)


def _build(existing=None, now=FIXED_NOW):
    priorities = vs.scorer.compute_priorities(THESES, now=now)
    return vs.build_vault(existing or {}, TICKERS, priorities, CATEGORIES, GLOSSARY, now=now)


class TestPageSet(unittest.TestCase):
    def test_expected_pages_created(self):
        v = _build()
        by_slug = {p["slug"]: p for p in v["pages"]}
        # Core+Watch ticker pages, but not the radar one
        self.assertIn("aaoi", by_slug)
        self.assertIn("mu", by_slug)
        self.assertNotIn("zzzz", by_slug)
        # theme, concept, person pages
        self.assertEqual(by_slug["photonics"]["type"], "theme")
        self.assertEqual(by_slug["hbm"]["type"], "concept")
        self.assertEqual(by_slug["aleabitoreddit"]["type"], "person")

    def test_ticker_stats_and_refs(self):
        v = _build()
        aaoi = next(p for p in v["pages"] if p["slug"] == "aaoi")
        self.assertEqual(aaoi["auto"]["stats"]["tier"], "core")
        self.assertEqual(aaoi["auto"]["stats"]["mentions"], 2)
        # structural refs: its theme + the person hub
        self.assertIn("photonics", aaoi["auto"]["refs"])
        self.assertIn(vs.PERSON_SLUG, aaoi["auto"]["refs"])
        # reciprocal membership on the theme page
        photonics = next(p for p in v["pages"] if p["slug"] == "photonics")
        self.assertIn("aaoi", photonics["auto"]["refs"])

    def test_new_pages_have_blank_note(self):
        v = _build()
        for p in v["pages"]:
            self.assertEqual(p["note"], "")
            self.assertIsNone(p["noteUpdatedAt"])


class TestIdempotency(unittest.TestCase):
    def test_second_sync_is_byte_identical(self):
        first = _build()
        # feed the first result back in, with a *later* clock
        later = datetime(2026, 8, 1, tzinfo=timezone.utc)
        second = _build(existing=first, now=later)
        self.assertEqual(first["pages"], second["pages"])
        # unchanged pages must NOT bump syncedAt
        self.assertEqual(first["meta"]["syncedAt"], second["meta"]["syncedAt"])


class TestNotePreservation(unittest.TestCase):
    def test_existing_note_is_never_touched(self):
        first = _build()
        # enrich one page by hand
        for p in first["pages"]:
            if p["slug"] == "photonics":
                p["note"] = "Optical is a forced upgrade. See [[aaoi]] and [[hbm]]."
                p["noteUpdatedAt"] = "2026-07-12T00:00:00Z"
        second = _build(existing=first)
        photonics = next(p for p in second["pages"] if p["slug"] == "photonics")
        self.assertEqual(photonics["note"], "Optical is a forced upgrade. See [[aaoi]] and [[hbm]].")
        self.assertEqual(photonics["noteUpdatedAt"], "2026-07-12T00:00:00Z")

    def test_enriched_orphan_survives_when_source_drops(self):
        first = _build()
        # a page that is no longer in the auto set but carries prose
        orphan = {"slug": "old-name", "type": "ticker", "title": "OLD",
                  "auto": {"refs": [], "stats": {}},
                  "note": "kept prose", "noteUpdatedAt": "2026-07-01T00:00:00Z"}
        first["pages"].append(orphan)
        second = _build(existing=first)
        kept = next((p for p in second["pages"] if p["slug"] == "old-name"), None)
        self.assertIsNotNone(kept)
        self.assertEqual(kept["note"], "kept prose")

    def test_stub_orphan_is_dropped(self):
        first = _build()
        stub = {"slug": "gone", "type": "ticker", "title": "GONE",
                "auto": {"refs": [], "stats": {}}, "note": "", "noteUpdatedAt": None}
        first["pages"].append(stub)
        second = _build(existing=first)
        self.assertNotIn("gone", {p["slug"] for p in second["pages"]})

    def test_event_page_carried_forward(self):
        first = _build()
        event = {"slug": "ces-2026", "type": "event", "title": "CES 2026",
                 "auto": {"refs": ["aaoi"], "stats": {}}, "note": "", "noteUpdatedAt": None}
        first["pages"].append(event)
        second = _build(existing=first)
        self.assertIn("ces-2026", {p["slug"] for p in second["pages"]})


class TestCounts(unittest.TestCase):
    def test_page_count_matches_pages(self):
        v = _build()
        self.assertEqual(v["meta"]["pageCount"], len(v["pages"]))

    def test_link_count_counts_valid_edges_only(self):
        v = _build()
        # every ticker->theme and ticker->person edge is valid; dangling excluded
        self.assertGreater(v["meta"]["linkCount"], 0)

    def test_note_wikilinks_add_to_link_count(self):
        first = _build()
        base_links = first["meta"]["linkCount"]
        for p in first["pages"]:
            if p["slug"] == "hbm":
                # concept normally has no refs; a note wikilink to an existing
                # page should add exactly one edge
                p["note"] = "Bonded next to the GPU. Central to [[photonics]]."
        second = _build(existing=first)
        self.assertEqual(second["meta"]["linkCount"], base_links + 1)

    def test_dangling_wikilink_not_counted(self):
        first = _build()
        base_links = first["meta"]["linkCount"]
        for p in first["pages"]:
            if p["slug"] == "hbm":
                p["note"] = "Points at [[nonexistent-page]]."
        second = _build(existing=first)
        self.assertEqual(second["meta"]["linkCount"], base_links)


class TestSlugify(unittest.TestCase):
    def test_matches_memo_slug_rules(self):
        self.assertEqual(vs.slugify("AAOI"), "aaoi")
        self.assertEqual(vs.slugify("@aleabitoreddit"), "aleabitoreddit")
        self.assertEqual(vs.slugify("CoWoS"), "cowos")
        self.assertEqual(vs.slugify("!!!"), "page")


if __name__ == "__main__":
    unittest.main()
