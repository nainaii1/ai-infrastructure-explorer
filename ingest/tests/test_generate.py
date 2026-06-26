import sys
import re
import json
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import generate_data_js as gen  # noqa: E402


def reparse(js_text):
    m = re.search(r"window\.AIE_DATA\s*=\s*(\{.*\});\s*$", js_text, re.S)
    return json.loads(m.group(1))


class TestBuild(unittest.TestCase):
    def test_core_structure(self):
        d = gen.build_data()
        self.assertEqual(len(d["tickers"]), 16)
        self.assertEqual(len(d["categories"]), 6)
        self.assertTrue(all("layer" in c for c in d["categories"].values()))
        self.assertNotIn("unsorted", d["categories"])  # no unsorted tickers in seed
        self.assertEqual(d["theses"], [])
        self.assertEqual(d["priorities"], [])
        self.assertEqual(d["center"]["title"], "NVIDIA + Hyperscalers")


class TestRenderSafety(unittest.TestCase):
    def test_render_roundtrips(self):
        d = gen.build_data()
        out = gen.render(d)
        self.assertIn("window.AIE_DATA =", out)
        self.assertTrue(out.rstrip().endswith(";"))
        reparse(out)  # must be valid JSON

    def test_injection_is_neutralized(self):
        hostile = '"}; </script><script>alert(1)</script>'
        d = gen.build_data()
        d["theses"] = [{"id": "x_1", "text": hostile, "tickers": []}]
        out = gen.render(d)
        # No raw closing tag can appear in the emitted JS source.
        self.assertNotIn("</script>", out)
        # ...yet the value is preserved exactly after JSON/JS unescaping.
        parsed = reparse(out)
        self.assertEqual(parsed["theses"][0]["text"], hostile)


if __name__ == "__main__":
    unittest.main()
