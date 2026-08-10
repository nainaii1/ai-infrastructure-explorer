#!/bin/zsh
# Double-click me to check X for new posts RIGHT NOW and send them to Telegram,
# without waiting for the next scheduled run.
#
# Uses the python.org build, not /usr/bin/python3 — Playwright lives there.
cd "$(dirname "$0")"
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 ingest/watcher.py --deliver always
echo ""
echo "Done. Check Telegram for anything new. (This window can be closed.)"
