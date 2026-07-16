#!/bin/zsh
# Double-click me to refresh prices from the Google Sheet and rebuild data.js.
cd "$(dirname "$0")"
/usr/bin/python3 ingest/fetch_prices.py
echo ""
echo "Done. Reload the site to see fresh prices. (This window can be closed.)"
