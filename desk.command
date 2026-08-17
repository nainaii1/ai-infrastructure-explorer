#!/bin/zsh
# Double-click me — one menu for everything the desk's backend does.
# (The app itself needs nothing: just open desk.html in a browser.)
cd "$(dirname "$0")"

ENV_FILE="ingest/.env"
BOT_LABEL="com.aie.bot"

load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a; . "./$ENV_FILE"; set +a
  else
    echo "⚠️  $ENV_FILE not found — bot/synthesize need it (see ingest/.env.example)."
  fi
}

# Since 8 Aug 2026 the bot normally runs as a launchd background service
# (com.aie.bot), not started by hand. `launchctl list <label>` exits 0 only
# if that service is loaded — this is the authoritative check, distinct from
# whether it's currently mid-restart (PID shows "-" briefly either way).
bot_agent_loaded() {
  launchctl list "$BOT_LABEL" >/dev/null 2>&1
}

bot_agent_pid() {
  launchctl list | awk -v l="$BOT_LABEL" '$3==l{print $1}'
}

echo "AI Infrastructure Explorer — backend"
echo ""
echo "  1) Bot check / restart     (it normally runs by itself in the background)"
echo "  2) Refresh prices          (Google Sheet → store/prices.json → data.js)"
echo "  3) Serve the app           (http://localhost:8765 — enables the Fetch-prices button)"
echo "  4) Status                  (bot running? prices as-of? tickers awaiting triage?)"
echo ""
printf "Pick 1-4: "
read -r choice

case "$choice" in
  1)
    if bot_agent_loaded; then
      pid="$(bot_agent_pid)"
      echo ""
      if [[ "$pid" =~ ^[0-9]+$ ]]; then
        echo "The bot is already running in the background (pid $pid) — it starts"
        echo "itself at login and keeps itself running, so there's nothing to do."
      else
        echo "The bot's background service is installed but not currently running"
        echo "(check the log: ~/Library/Logs/aie-bot.log)."
      fi
      echo ""
      echo "Not receiving replies? A restart usually fixes it — it picks up any"
      echo "code changes and clears a stuck connection."
      printf "Restart it now? [y/N] "
      read -r ans
      if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
        launchctl kickstart -k "gui/$(id -u)/$BOT_LABEL"
        echo "Restarted. Give it a few seconds, then try forwarding a post again."
      else
        echo "Left it as-is."
      fi
    else
      load_env
      echo ""
      echo "No background bot service is installed — running it here instead."
      echo "It only runs while this window stays open. Stop it with Ctrl+C."
      echo "(To make it always-on instead, see docs/GUIDE.md, section 2, Step 4.)"
      echo ""
      /usr/bin/python3 ingest/bot.py
    fi
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
    if bot_agent_loaded; then
      pid="$(bot_agent_pid)"
      if [[ "$pid" =~ ^[0-9]+$ ]]; then
        echo "Bot:      RUNNING (background service, pid $pid)"
      else
        echo "Bot:      background service installed, not currently running"
        echo "          — check ~/Library/Logs/aie-bot.log (option 1 can restart it)"
      fi
    elif pgrep -f "python3 ingest/bot.py" > /dev/null 2>&1; then
      echo "Bot:      RUNNING (started manually, this session only)"
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
