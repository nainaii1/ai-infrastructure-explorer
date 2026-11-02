#!/usr/bin/env python3
"""One-file copy of the page (guide + desk) for the operator's phone.

Inlines style.css, data.js, desk.js and app.js into a single HTML file that
is published as a PRIVATE claude.ai artifact after each weekly memo (see the
weekly-memo skill). It holds holdings and levels, so it is written to
desk/store/ (gitignored) and must never be committed or made public.

    python3 desk/build.py && python3 desk/snapshot.py
"""
import re
import sys

from common import ROOT, STORE

OUT = STORE / "snapshot" / "desk.html"


def themed(css):
    """The artifact viewer sets data-theme on the root, so each dark token
    block must also answer an explicit light or dark choice."""
    def fix(m):
        body = m.group(1).strip().rstrip(";")
        return ('@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ {0}; color-scheme: dark; }} }}\n'
                ':root[data-theme="dark"] {{ {0}; color-scheme: dark; }}').format(body)
    return re.sub(r"@media \(prefers-color-scheme: dark\) \{\s*:root \{([^}]*)\}\s*\}", fix, css)


def script(path):
    return "<script>\n" + path.read_text(encoding="utf-8").replace("</", "<\\/") + "\n</script>"


def main():
    if not (ROOT / "desk.js").exists():
        print("no desk.js: run desk/build.py first")
        return 1
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    body = page[page.index("<body>") + 6:page.index("</body>")]
    body = re.sub(r'<script src="[^"]+"></script>\s*', "", body)
    out = "\n".join([
        "<title>AI Supply Desk</title>",
        "<style>\n" + themed((ROOT / "style.css").read_text(encoding="utf-8")) + "\n</style>",
        body.strip(),
        script(ROOT / "data.js"), script(ROOT / "desk.js"), script(ROOT / "app.js"),
    ])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out, encoding="utf-8")
    print("wrote {} ({:,} bytes)".format(OUT.relative_to(ROOT), len(out.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
