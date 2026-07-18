"""Fetch tweet content from a public x.com URL using the fxtwitter API.

No auth, no API key, no pip install. Falls back gracefully — callers should
handle None returns and prompt the user to paste the text manually.

fxtwitter API: https://api.fxtwitter.com/{username}/status/{tweet_id}
"""

import json
import re
import urllib.request
from datetime import datetime, timezone

from store_io import ssl_context

_SSL_CTX = ssl_context()  # verified — bot.py no longer disables checks globally

_STATUS_RE = re.compile(r"(?:twitter\.com|x\.com)/([^/?#\s]+)/status/(\d+)")
_FXTWITTER = "https://api.fxtwitter.com/{username}/status/{tweet_id}"


def extract_tweet_id(url):
    m = _STATUS_RE.search(url or "")
    if m:
        return m.group(1), m.group(2)
    return None, None


def fetch_tweet(url):
    """Fetch tweet metadata via fxtwitter.

    Returns dict {text, posted_at, author} on success, None on failure.
    posted_at is ISO-8601 UTC string or None.
    """
    username, tweet_id = extract_tweet_id(url)
    if not tweet_id:
        return None

    api_url = _FXTWITTER.format(username=username, tweet_id=tweet_id)
    try:
        with urllib.request.urlopen(api_url, timeout=10, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print("fetcher: fxtwitter request failed:", exc)
        return None

    tweet = data.get("tweet")
    if not tweet or data.get("code") != 200:
        print("fetcher: fxtwitter returned no tweet:", data.get("message"))
        return None

    text = tweet.get("text", "").strip()
    if not text:
        return None

    posted_at = None
    ts = tweet.get("created_timestamp")
    if ts:
        try:
            posted_at = datetime.fromtimestamp(int(ts), timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        except Exception:
            pass

    author = (tweet.get("author") or {}).get("screen_name") or username

    return {"text": text, "posted_at": posted_at, "author": author}
