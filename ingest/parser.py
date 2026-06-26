"""Parse an incoming post (raw text or Telegram message) into a thesis record
and detect ticker mentions with a confidence split.

No third-party dependencies. The pure functions here are unit-tested in
tests/test_parser.py.

Confidence model:
  high  -> explicit $CASHTAG, or a known symbol mentioned verbatim  (auto-add)
  low   -> bare ALL-CAPS tokens that aren't stopwords/known         (review queue)
"""

import re
import hashlib
from datetime import datetime, timezone

# $AAOI, $SOI.PA, $LPK.DE  (1-5 letters, optional .SUFFIX)
CASHTAG_RE = re.compile(r"\$([A-Za-z]{1,5}(?:\.[A-Za-z]{1,3})?)\b")
URL_RE = re.compile(r"https?://[^\s]+")
STATUS_ID_RE = re.compile(r"(?:twitter\.com|x\.com)/[^/]+/status/(\d+)")
BAREWORD_RE = re.compile(r"\b([A-Z]{2,5})\b")

# Tokens that look like tickers but almost never are — keep junk out of the queue.
STOPWORDS = {
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "NEW",
    "CEO", "CFO", "CTO", "AI", "ML", "GPU", "CPU", "HBM", "CPO", "USA", "US",
    "EU", "UK", "IPO", "ETF", "DC", "PM", "AM", "EPS", "YOY", "QOQ", "ATH",
    "FYI", "IMO", "TLDR", "RT", "USD", "API", "OK", "NO", "ON", "IN", "OF",
    "TO", "IT", "IS", "BE", "SO", "AS", "AT", "OR", "IF", "Q1", "Q2", "Q3",
    "Q4", "H1", "H2", "ROE", "TAM", "SAM", "EOD", "WSB", "DD",
}

CONVICTION_PHRASES = [
    "top pick", "highest conviction", "high conviction", "core position",
    "core holding", "backing up the truck", "loading up", "my biggest",
    "largest position", "favorite", "favourite", "strong conviction", "all in",
]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_urls(text):
    return URL_RE.findall(text or "")


def pick_source_url(urls):
    """Prefer a tweet/status URL; otherwise the first URL found."""
    for u in urls:
        if STATUS_ID_RE.search(u):
            return u
    return urls[0] if urls else ""


def derive_source_id(text, source_url, posted_at):
    """Stable dedupe key: tweet id when available, else a content hash."""
    m = STATUS_ID_RE.search(source_url or "")
    if m:
        return "x_" + m.group(1)
    digest = hashlib.sha1(((text or "") + (posted_at or "")).encode("utf-8")).hexdigest()
    return "h_" + digest[:16]


def detect_tickers(text, known_symbols):
    """Return (high_confidence:set, low_confidence:set)."""
    text = text or ""
    known_upper = {s.upper() for s in known_symbols}
    high, low = set(), set()

    for m in CASHTAG_RE.finditer(text):
        high.add(m.group(1).upper())

    # Known symbols mentioned without a leading '$' (e.g. "AAOI", "TSM").
    for sym in known_upper:
        pattern = r"(?<![A-Za-z0-9$])" + re.escape(sym) + r"(?![A-Za-z0-9])"
        if re.search(pattern, text):
            high.add(sym)

    for m in BAREWORD_RE.finditer(text):
        tok = m.group(1).upper()
        if tok in STOPWORDS or tok in high or tok in known_upper:
            continue
        low.add(tok)

    return high, low


def detect_conviction(text):
    t = (text or "").lower()
    return "high" if any(p in t for p in CONVICTION_PHRASES) else "normal"


def parse_text(text, known_symbols, posted_at=None, author="aleabitoreddit"):
    """Pure: build a thesis dict + sorted low-confidence candidate list."""
    urls = extract_urls(text)
    source_url = pick_source_url(urls)
    posted_at = posted_at or now_iso()
    high, low = detect_tickers(text, known_symbols)
    thesis = {
        "id": derive_source_id(text, source_url, posted_at),
        "source": "x",
        "author": author,
        "sourceUrl": source_url,
        "postedAt": posted_at,
        "ingestedAt": now_iso(),
        "text": (text or "").strip(),
        "tickers": sorted(high),
        "conviction": detect_conviction(text),
        "tags": [],
    }
    return thesis, sorted(low)


def parse_telegram_message(message, known_symbols, author="aleabitoreddit"):
    """Adapt a Telegram message object to parse_text (uses forward_date/date)."""
    text = message.get("text") or message.get("caption") or ""
    epoch = message.get("forward_date") or message.get("date")
    posted_at = None
    if epoch:
        posted_at = datetime.fromtimestamp(int(epoch), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return parse_text(text, known_symbols, posted_at=posted_at, author=author)
