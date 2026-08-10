"""Design-system guard: every shipped colour pair must clear its WCAG floor.

This reads the SHIPPED :root out of shared/theme.css and the category hues out
of ingest/store/base.json, so it fails when someone changes a token, not when
someone forgets to update a fixture.

Floors (see docs/DESIGN.md section 2):
  - text pairs        4.5:1  (WCAG AA, normal text)
  - UI / fill pairs   3.0:1  (WCAG 1.4.11 non-text contrast)

Run with the rest of the suite:
    python3 -m unittest discover -s ingest/tests
"""

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

TEXT = 4.5
UI = 3.0


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_colour):
    h = hex_colour.lstrip("#")
    return (0.2126 * _lin(int(h[0:2], 16))
            + 0.7152 * _lin(int(h[2:4], 16))
            + 0.0722 * _lin(int(h[4:6], 16)))


def contrast(a, b):
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _root_block():
    css = (ROOT / "shared" / "theme.css").read_text()
    root = re.search(r":root\s*\{(.*?)\n\}", css, re.S)
    assert root, "could not find :root in shared/theme.css"
    return root.group(1)


def load_tokens():
    """Literal hex tokens from theme.css's :root, keyed without the leading --."""
    return {k.lstrip("-"): v for k, v in
            re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", _root_block())}


def load_px_tokens():
    """Literal px tokens (the type and spacing scales)."""
    return {k.lstrip("-"): v for k, v in
            re.findall(r"(--[\w-]+)\s*:\s*([0-9.]+px)\s*;", _root_block())}


# (label, foreground token, background token, floor)
PAIRS = [
    ("ink on bg",              "ink",    "bg",          TEXT),
    ("ink on card",            "ink",    "card",        TEXT),
    ("ink on violet-wash",     "ink",    "violet-wash", TEXT),
    ("ink on teal-wash",       "ink",    "teal-wash",   TEXT),
    ("text on bg",             "text",   "bg",          TEXT),
    ("text on card",           "text",   "card",        TEXT),
    ("muted on bg",            "muted",  "bg",          TEXT),
    ("muted on card",          "muted",  "card",        TEXT),
    ("muted on paper-sink",    "muted",  "paper-sink",  TEXT),
    ("muted on paper-tint",    "muted",  "paper-tint",  TEXT),
    ("violet on card",         "violet", "card",        TEXT),
    ("violet on bg",           "violet", "bg",          TEXT),
    ("violet on violet-wash",  "violet", "violet-wash", TEXT),
    ("violet-hi on card",      "violet-hi", "card",     TEXT),
    ("teal on card",           "teal",   "card",        TEXT),
    ("teal on bg",             "teal",   "bg",          TEXT),
    ("teal on teal-wash",      "teal",   "teal-wash",   TEXT),
    ("teal on violet-wash",    "teal",   "violet-wash", TEXT),
    ("teal on paper-sink",     "teal",   "paper-sink",  TEXT),
    ("pos on card",            "pos",    "card",        TEXT),
    ("neg on card",            "neg",    "card",        TEXT),
    ("pos on bg",              "pos",    "bg",          TEXT),
    ("neg on bg",              "neg",    "bg",          TEXT),
    ("sem act",         "sem-act-fg",        "sem-act-bg",        TEXT),
    ("sem accumulate",  "sem-accumulate-fg", "sem-accumulate-bg", TEXT),
    ("sem watch",       "sem-watch-fg",      "sem-watch-bg",      TEXT),
    ("sem pass",        "sem-pass-fg",       "sem-pass-bg",       TEXT),
    # The canvas gradient's deepest stop still has to hold every text colour.
    ("muted on canvas-bot",  "muted",  "canvas-bot", TEXT),
    ("ink on canvas-bot",    "ink",    "canvas-bot", TEXT),
    ("text on canvas-bot",   "text",   "canvas-bot", TEXT),
    ("violet on canvas-bot", "violet", "canvas-bot", TEXT),
    ("teal on canvas-bot",   "teal",   "canvas-bot", TEXT),
    # Text on the dark stage surfaces.
    ("on-stage on stage",      "on-stage",     "stage",    TEXT),
    ("on-stage-dim on stage",  "on-stage-dim", "stage",    TEXT),
    ("pos-stage on stage",     "pos-stage",    "stage",    TEXT),
    ("neg-stage on stage",     "neg-stage",    "stage",    TEXT),
    ("flat-stage on stage",    "flat-stage",   "stage",    TEXT),
    ("on-stage on stage-hi",   "on-stage",     "stage-hi", TEXT),
    # Decorative / fill colours: UI floor only. These must NEVER carry small text.
    ("teal-ui fill on card",     "teal-ui",     "card",       UI),
    ("violet-soft on card",      "violet-soft", "card",       UI),
    ("violet-soft on bg",        "violet-soft", "bg",         UI),
    ("violet-soft on canvas-bot","violet-soft", "canvas-bot", UI),
]


def _mix(fg, bg, pct):
    """color-mix(in srgb, fg pct%, bg) — approximated in sRGB, as CSS does."""
    a, b = fg.lstrip("#"), bg.lstrip("#")
    return "#%02x%02x%02x" % tuple(
        round(int(a[i:i + 2], 16) * pct / 100 + int(b[i:i + 2], 16) * (1 - pct / 100))
        for i in (0, 2, 4))


class TestPaletteContrast(unittest.TestCase):
    def setUp(self):
        self.tok = load_tokens()

    def test_token_pairs_clear_their_floor(self):
        failures = []
        for label, fg, bg, floor in PAIRS:
            self.assertIn(fg, self.tok, f"{label}: token --{fg} is missing")
            self.assertIn(bg, self.tok, f"{label}: token --{bg} is missing")
            ratio = contrast(self.tok[fg], self.tok[bg])
            if ratio < floor:
                failures.append(
                    f"{label}: {self.tok[fg]} on {self.tok[bg]} = {ratio:.2f}:1 "
                    f"(needs {floor})")
        self.assertEqual([], failures, "\n" + "\n".join(failures))

    def test_category_hues_clear_the_ui_floor(self):
        """Category colours are painted as fills/marks, so they need 3:1."""
        base = json.loads((ROOT / "ingest" / "store" / "base.json").read_text())
        failures = []
        for cat_id, cat in base["categories"].items():
            colour = cat.get("color")
            if not colour:
                continue
            ratio = contrast(colour, self.tok["card"])
            if ratio < UI:
                failures.append(f"{cat_id}: {colour} = {ratio:.2f}:1 (needs {UI})")
        self.assertEqual([], failures, "\n" + "\n".join(failures))

    def test_active_category_chip_keeps_ink_readable(self):
        """desk.html tints an active chip 20% of the category hue into --card and
        keeps --ink text. White on a raw category hue would fail AA, which is why
        the chip tints rather than fills."""
        base = json.loads((ROOT / "ingest" / "store" / "base.json").read_text())
        failures = []
        for cat_id, cat in base["categories"].items():
            colour = cat.get("color")
            if not colour:
                continue
            tint = _mix(colour, self.tok["card"], 20)
            ratio = contrast(self.tok["ink"], tint)
            if ratio < TEXT:
                failures.append(f"{cat_id}: ink on {tint} = {ratio:.2f}:1")
        self.assertEqual([], failures, "\n" + "\n".join(failures))

    def test_type_floor_is_the_smallest_size_on_the_scale(self):
        """--fs-2xs is the documented floor; no --fs-* may be smaller."""
        px = load_px_tokens()
        self.assertEqual("11px", px.get("fs-2xs", ""),
                         "the type floor moved — update docs/DESIGN.md section 2")
        sizes = {k: float(v[:-2]) for k, v in px.items() if k.startswith("fs-")}
        smaller = {k: v for k, v in sizes.items() if v < sizes["fs-2xs"]}
        self.assertEqual({}, smaller, f"type below the 11px floor: {smaller}")


class TestNoRawColourInAppCode(unittest.TestCase):
    """Colour belongs in tokens (or, for categories, in the data store)."""

    # Pages may still carry a favicon data URI; that is markup, not styling.
    PAGES = ["index.html", "desk.html", "memo.html", "performance.html"]

    @staticmethod
    def _declarations_only(text):
        """Strip comments and the favicon URI.

        The rule is about DECLARED colour, not prose. Comments legitimately
        quote hexes — desk.html documents the reference site's #998dff and why
        it was not copied (white on it is 2.9:1) — and a comment cannot paint
        anything, so scanning them produces false failures.
        """
        text = re.sub(r"<link[^>]*rel=\"icon\"[^>]*>", "", text, flags=re.S)
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)     # CSS + JS block
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)    # HTML
        text = re.sub(r"^\s*//.*$", "", text, flags=re.M)     # JS line
        return text

    def test_pages_declare_no_raw_hex(self):
        offenders = {}
        for name in self.PAGES:
            text = self._declarations_only((ROOT / name).read_text())
            found = sorted(set(re.findall(r"#[0-9a-fA-F]{6}", text)))
            if found:
                offenders[name] = found
        self.assertEqual({}, offenders)

    def test_pages_declare_no_raw_px_font_size(self):
        offenders = {}
        for name in self.PAGES + ["vault.html"]:
            text = self._declarations_only((ROOT / name).read_text())
            found = sorted(set(re.findall(r"font-size:\s*([0-9.]+px)", text)))
            if found:
                offenders[name] = found
        self.assertEqual({}, offenders)


if __name__ == "__main__":
    unittest.main()
