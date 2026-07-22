#!/bin/zsh
# Double-click me — one menu for everything the desk's backend does.
# (The app itself needs nothing: just open desk.html in a browser.)
cd "$(dirname "$0")"

ENV_FILE="ingest/.env"

load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a; . "./$ENV_FILE"; set +a
  else
    echo "⚠️  $ENV_FILE not found — bot/synthesize need it (see ingest/.env.example)."
  fi
}

echo "AI Infrastructure Explorer — backend"
echo ""
echo "  1) Start the capture bot   (forward posts on Telegram; keep this window open)"
echo "  2) Refresh prices          (Google Sheet → store/prices.json → data.js)"
echo "  3) Serve the app           (http://localhost:8765 — enables the Fetch-prices button)"
echo "  4) Status                  (bot running? prices as-of? tickers awaiting triage?)"
echo ""
printf "Pick 1-4: "
read -r choice

case "$choice" in
  1)
    load_env
    echo ""
    echo "Bot starting. It only runs while this window stays open."
    echo "Stop it with Ctrl+C or by closing the window."
    echo ""
    /usr/bin/python3 ingest/bot.py
    ;;
  2)
    /usr/bin/python3 ingest/fetch_prices.py
    echo ""
    echo "Done. Reload the site to see fresh prices."
    ;;
  3)
    echo ""
    echo "Server starting at http://localhost:8765 — it runs while this window stays open."
    ( sleep 1 && open "http://localhost:8765/desk.html" ) &
    /usr/bin/python3 ingest/serve.py
    ;;
  4)
    echo ""
    if pgrep -f "python3 ingest/bot.py" > /dev/null 2>&1; then
      echo "Bot:      RUNNING"
    else
      echo "Bot:      not running (option 1 starts it)"
    fi
    /usr/bin/python3 - <<'PY'
import json, pathlib
store = pathlib.Path("ingest/store")
try:
    prices = json.loads((store / "prices.json").read_text())
    as_of = sorted(v.get("asOf", "") for v in prices.get("prices", prices).values() if isinstance(v, dict))
    print("Prices:   as of", (as_of[-1][:10] if as_of and as_of[-1] else "unknown"))
except Exception:
    print("Prices:   no prices.json yet (option 2 fetches them)")
try:
    tickers = json.loads((store / "tickers.json").read_text())
    unsorted_n = sum(1 for t in tickers if t.get("category") == "unsorted")
except Exception:
    unsorted_n = 0
try:
    pending = json.loads((store / "pending_tickers.json").read_text())
    pending_n = len(pending if isinstance(pending, list) else pending.get("pending") or [])
except Exception:
    pending_n = 0
print(f"Triage:   {unsorted_n} unsorted ticker(s), {pending_n} pending candidate(s)")
print("          (both are handled in the weekly review)")
PY
    echo ""
    echo "(This window can be closed.)"
    ;;
  *)
    echo "No such option — run me again and pick 1-4."
    ;;
esac
