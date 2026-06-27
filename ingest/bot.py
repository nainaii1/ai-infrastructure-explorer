"""Telegram ingest bot — turns forwarded @aleabitoreddit posts into data.js.

Modes
  python bot.py                      # live: long-poll getUpdates (needs env)
  python bot.py --text "..."         # local: ingest one message (no Telegram)
  python bot.py --text "..." --url https://x.com/u/status/123

Env (see .env.example)
  TELEGRAM_BOT_TOKEN        required for live mode
  ALLOWED_TELEGRAM_USER_ID  required for live mode — ONLY this user is processed

SECURITY
  - Bot token read from env only; never hardcoded.
  - Auth gate: messages from any other Telegram id are ignored.
  - data.js is regenerated via generate_data_js (json.dumps) so post text
    cannot inject code.
"""

import os
import sys
import json
import re
import time
import argparse
import pathlib
import urllib.parse
import urllib.request
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
from datetime import datetime, timezone

import parser as msgparser
import generate_data_js as gen
import fetcher

ING = pathlib.Path(__file__).resolve().parent
STORE = ING / "store"
OFFSET_FILE = STORE / ".bot_offset"
MAX_TEXT_LEN = 4000
API_URL = "https://api.telegram.org/bot{token}/{method}"
_URL_ONLY_RE = re.compile(r"https?://\S+")


def _is_url_only(text):
    """True when the message is essentially just a URL with no meaningful text."""
    stripped = (text or "").strip()
    remainder = _URL_ONLY_RE.sub("", stripped).strip()
    return bool(_URL_ONLY_RE.search(stripped)) and len(remainder) < 10


def _resolve_text(text, posted_at=None):
    """If text is URL-only, fetch tweet content via fxtwitter. Returns (text, posted_at)."""
    if not _is_url_only(text):
        return text, posted_at
    url = _URL_ONLY_RE.search(text).group(0)
    result = fetcher.fetch_tweet(url)
    if result:
        full_text = result["text"] + "\n" + url
        resolved_at = posted_at or result.get("posted_at")
        print("fetcher: resolved tweet text from fxtwitter")
        return full_text, resolved_at
    return text, posted_at  # fall through — ingest will store what it has


def _format_reply(summary):
    if "skipped" in summary:
        reason = summary["skipped"]
        return "⚠️ Skipped: {}{}".format(
            reason, " ({})".format(summary.get("id", "")) if "id" in summary else ""
        )
    tickers = summary.get("tickers") or []
    added = summary.get("added") or []
    queued = summary.get("queued") or []
    lines = ["✅ Ingested from @aleabitoreddit"]
    if tickers:
        lines.append("Tickers: " + ", ".join(tickers))
    if added:
        lines.append("Auto-added: " + ", ".join(added))
    if queued:
        lines.append("Queued for review: " + ", ".join(queued))
    if not tickers and not added:
        lines.append("(no tickers detected — saved as note)")
    return "\n".join(lines)


def _load(name):
    return json.loads((STORE / name).read_text(encoding="utf-8"))


def _save(name, data):
    (STORE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bump_version():
    base = _load("base.json")
    version = base["meta"].get("version", "1.0")
    try:
        major, minor = version.split(".")
        base["meta"]["version"] = "{}.{}".format(major, int(minor) + 1)
    except ValueError:
        base["meta"]["version"] = "1.1"
    base["meta"]["lastUpdated"] = _now_iso()
    base["meta"]["source"] = "ingest"
    _save("base.json", base)


def _is_stub(thesis):
    """True when a stored thesis has no real content (URL-only capture)."""
    text = (thesis.get("text") or "").strip()
    return not thesis.get("tickers") and (not text or text.startswith("http"))


def ingest_message(text, source_url="", posted_at=None):
    """Core pipeline: text -> thesis appended, tickers auto-added/queued,
    priorities recomputed, data.js regenerated. Returns a summary dict.
    Shared by live polling and the --text CLI."""
    text, posted_at = _resolve_text(text, posted_at)

    tickers = _load("tickers.json")
    theses = _load("theses.json")
    pending = _load("pending_tickers.json")
    known = [t["ticker"] for t in tickers]

    combined = text if not source_url else (text + " " + source_url)
    thesis, low = msgparser.parse_text(combined[:MAX_TEXT_LEN], known, posted_at=posted_at)

    if not thesis["text"] and not thesis["tickers"]:
        return {"skipped": "empty"}

    existing_idx = next((i for i, t in enumerate(theses) if t["id"] == thesis["id"]), None)
    if existing_idx is not None:
        if _is_stub(theses[existing_idx]):
            theses[existing_idx] = thesis  # replace URL-only stub with real content
        else:
            return {"skipped": "duplicate", "id": thesis["id"]}
    else:
        theses.append(thesis)

    known_upper = {k.upper() for k in known}
    added = []
    for sym in thesis["tickers"]:
        if sym.upper() not in known_upper:
            tickers.append({
                "ticker": sym,
                "company": "",
                "category": "unsorted",
                "market": "",
                "exchange": "",
                "whatTheyDo": "",
                "whyNVDA": "",
                "marketCapTier": "",
                "rating": "watch",
                "sourceTweetUrl": thesis["sourceUrl"],
                "addedDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })
            known_upper.add(sym.upper())
            added.append(sym)

    queued = []
    for cand in low:
        existing = next((p for p in pending if p["candidate"] == cand), None)
        if existing:
            existing["count"] += 1
        else:
            pending.append({
                "candidate": cand,
                "sourceUrl": thesis["sourceUrl"],
                "firstSeen": thesis["ingestedAt"],
                "count": 1,
            })
            queued.append(cand)

    _save("tickers.json", tickers)
    _save("theses.json", theses)
    _save("pending_tickers.json", pending)
    _bump_version()
    gen.write_data_js()

    return {"id": thesis["id"], "tickers": thesis["tickers"], "added": added, "queued": queued}


# --------------------------- live Telegram mode ---------------------------

def _api(token, method, **params):
    url = API_URL.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(url, data=data, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _read_offset():
    try:
        return int(OFFSET_FILE.read_text().strip())
    except (OSError, ValueError):
        return 0


def run_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    allowed = os.environ.get("ALLOWED_TELEGRAM_USER_ID")
    if not token or not allowed:
        sys.exit("ERROR: set TELEGRAM_BOT_TOKEN and ALLOWED_TELEGRAM_USER_ID (see .env.example).")
    allowed = str(allowed)
    print("Bot polling. Only Telegram user id {} is processed. Ctrl-C to stop.".format(allowed))

    offset = _read_offset()
    while True:
        try:
            resp = _api(token, "getUpdates", offset=offset + 1, timeout=50)
        except Exception as exc:  # network hiccup — back off and retry
            print("poll error:", exc)
            time.sleep(5)
            continue
        for upd in resp.get("result", []):
            offset = upd["update_id"]
            OFFSET_FILE.write_text(str(offset))
            msg = upd.get("message") or upd.get("channel_post")
            if not msg:
                continue
            if str((msg.get("from") or {}).get("id", "")) != allowed:
                continue  # auth gate
            text = msg.get("text") or msg.get("caption") or ""
            epoch = msg.get("forward_date") or msg.get("date")
            posted = None
            if epoch:
                posted = datetime.fromtimestamp(int(epoch), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            summary = ingest_message(text, posted_at=posted)
            print("ingested:", summary)
            try:
                _api(token, "sendMessage", chat_id=msg["chat"]["id"],
                     text=_format_reply(summary))
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser(description="Telegram ingest bot for AI Infrastructure Explorer.")
    ap.add_argument("--text", help="Ingest a single message locally (skips Telegram).")
    ap.add_argument("--url", default="", help="Optional source URL for --text mode.")
    ap.add_argument("--posted-at", default=None, help="Optional ISO timestamp for --text mode.")
    args = ap.parse_args()
    if args.text is not None:
        print(json.dumps(ingest_message(args.text, source_url=args.url, posted_at=args.posted_at), indent=2))
    else:
        run_bot()


if __name__ == "__main__":
    main()
