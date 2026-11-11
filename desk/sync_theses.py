#!/usr/bin/env python3
"""Keep the portfolio dashboard's thesis file in step with the desk's lines.

The dashboard (another project) shows each holding's price lines from its own
theses.json. The desk moves those lines in memos and event updates, so the two
drift apart. This copies ONLY the level numbers the desk has changed:

    buyBelow -> buy_below      addBelow  -> add_below
    stopAbove -> stop_adding_above        trimAbove -> trim_above

Nothing else in the file is touched: no wording, no events, no money. It never
opens portfolio.json.

    python3 desk/sync_theses.py           dry run: print what would change
    python3 desk/sync_theses.py --write   back the file up, then write
"""
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from common import STORE, load_json

THESES = Path(os.path.expanduser("~/Documents/Claude/port_dashboard_2026/theses.json"))
FIELDS = {"buyBelow": "buy_below", "addBelow": "add_below", "stopAbove": "stop_adding_above", "trimAbove": "trim_above"}


def main():
    levels = load_json(STORE / "levels.json", {}).get("levels", {})
    try:
        raw = THESES.read_text(encoding="utf-8")
        T = json.loads(raw)
    except Exception as ex:
        print("theses.json not read ({}); nothing changed".format(ex))
        return 1
    changes = []
    for h in T.get("holdings", []):
        lv = levels.get(h.get("ticker"))
        if not lv or lv.get("action") == "plan" or "levels" not in h:
            continue                                  # the operator's own plans are his to edit
        for k, f in FIELDS.items():
            new, old = lv.get(k), h["levels"].get(f)
            if new is not None and new != old:
                changes.append((h["ticker"], f, old, new))
                h["levels"][f] = new
    if not changes:
        print("theses.json already matches the desk's lines")
        return 0
    for t, f, old, new in changes:
        print("{:8} {:18} {} -> {}".format(t, f, old, new))
    if "--write" not in sys.argv:
        print("\ndry run: {} number(s) would change. Run with --write to apply.".format(len(changes)))
        return 0
    backup = THESES.with_name("theses.json.bak-{}".format(datetime.now().strftime("%Y%m%d-%H%M%S")))
    shutil.copy2(THESES, backup)
    THESES.write_text(json.dumps(T, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote {} number(s); backup at {}".format(len(changes), backup.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
