"""Watch a public X timeline and queue new posts for Telegram approval.

Two stages, deliberately split:

  DISCOVERY   a headless browser loads the PUBLIC (logged-out) profile page and
              reads post permalinks. No login, no cookies, no credentials —
              nothing here can get an X account suspended.
  VERIFY      each permalink goes through fetcher.py (fxtwitter) for the
              VERBATIM post text.

The browser only ever supplies a URL. Post text always comes from fxtwitter,
so nothing scraped off a rendered page — and nothing written by a model — can
reach theses.json. A post that fails verification is never queued; it is
reported instead (fail closed).

Nothing is ingested automatically. Posts land in store/pending_posts.json and
are pushed to Telegram with Ingest/Skip buttons; bot.py acts on the tap.

Usage
  python3 watcher.py                 # discover -> verify -> queue -> notify
  python3 watcher.py --dry-run       # discover + verify only, print, touch nothing
  python3 watcher.py --no-notify     # queue but don't send Telegram messages
  python3 watcher.py --since <id>    # override the stored high-water mark
"""

import os
import sys
import json
import time
import argparse
import pathlib
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

import fetcher
from dotenv_util import _load_dotenv
from store_io import (
    load_json_optional,
    load_path_optional,
    save_json,
    now_iso,
    ssl_context,
)

SSL_CTX = ssl_context()

ING = pathlib.Path(__file__).resolve().parent
STORE = ING / "store"
STATE_FILE = STORE / ".watcher_state.json"
PENDING_POSTS = "pending_posts.json"

HANDLE = "aleabitoreddit"
PROFILE_URL = "https://x.com/{handle}"
API_URL = "https://api.telegram.org/bot{token}/{method}"

# The logged-out profile page is HARD-CAPPED at 6 posts (measured 30 Jul 2026:
# the page stops growing at scrollHeight 2844 and ends in a "Sign up / Log in"
# wall). Scrolling cannot get past it, so this is a ceiling, not a tuning knob.
#
# Consequence: the poll interval must be short enough that fewer than 6 posts
# accumulate between runs, or posts are lost with no trace. At the observed
# ~11 posts/day, a 12-hourly poll expects 5-6 — right at the cap. Hence the
# 4-hourly poll (expects ~2) with delivery batched to DELIVERY_HOURS, which
# keeps the operator's requested twice-a-day rhythm without the data loss.
PAGE_CAP = 6
DEFAULT_SCROLLS = 2  # the cap makes more scrolling pointless; 2 confirms the end
SCROLL_PAUSE_MS = 900
PAGE_TIMEOUT_MS = 45000

# Local-time hours at which queued posts are pushed to Telegram. Polling runs
# more often than this; it just stays silent in between.
DELIVERY_HOURS = {0, 12}

# Warn when the timeline has produced nothing for this long. Silence is
# ambiguous — it looks identical whether he stopped posting or X put the
# logged-out view behind a login wall again. Never let that pass unnoticed.
STALE_AFTER_HOURS = 24

# How many runs a post may fail verification before the watcher stops holding
# the high-water mark back for it. See next_watermark().
MAX_VERIFY_ATTEMPTS = 3
ALARM_COOLDOWN_HOURS = 24

MAX_TG_LEN = 3500  # Telegram hard-caps at 4096; leave room for our own chrome


# ----------------------------- pure helpers -----------------------------
# Kept free of I/O so ingest/tests can exercise them without a browser.

def parse_permalink(href):
    """'/handle/status/123' -> ('handle', '123'). Returns (None, None) if not one."""
    if not href:
        return None, None
    path = href.split("?")[0].rstrip("/")
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 3 and parts[1] == "status" and parts[2].isdigit():
        return parts[0], parts[2]
    return None, None


def classify_items(raw_items, handle):
    """Turn raw per-article scrapes into deduped post records.

    raw_items: [{href, datetime, socialContext}] in DOM order.

    Quote-posts render under HIS OWN permalink (the quote is his post), so
    they need no special casing — the quoted tweet is his text plus context.

    Foreign permalinks are the tricky case. They appear for two very different
    reasons: a genuine repost, and a reply by someone ELSE that X renders on
    his profile as conversation context. Observed live: a stranger asking
    "@aleabitoreddit Thought on meta and Microsoft earnings?" shows up exactly
    like a repost would. Ingesting that would file another person's words as
    his thesis — the one failure this pipeline must never have. So a foreign
    permalink is admitted ONLY on a positive repost marker, and dropped
    otherwise. Reposts are rare; misattribution is unacceptable.
    """
    seen = set()
    out = []
    for item in raw_items or []:
        author, post_id = parse_permalink(item.get("href"))
        if not post_id or post_id in seen:
            continue
        seen.add(post_id)
        social = (item.get("socialContext") or "").lower()
        own = author.lower() == handle.lower()
        is_repost = "repost" in social or "retweet" in social
        if not own and not is_repost:
            continue  # someone else's post, shown as thread context — not his
        out.append({
            "id": post_id,
            "url": "https://x.com/{}/status/{}".format(author, post_id),
            "author": author,
            "isRepost": bool(is_repost and not own),
        })
    return out


def newer_than(posts, since_id):
    """Posts with a numerically greater id than since_id, newest first.

    X ids are snowflakes — monotonically increasing — so integer comparison is
    a reliable 'is this new' test with no date parsing.
    """
    if since_id:
        try:
            floor = int(since_id)
        except (TypeError, ValueError):
            floor = 0
    else:
        floor = 0
    fresh = [p for p in posts if int(p["id"]) > floor]
    return sorted(fresh, key=lambda p: int(p["id"]), reverse=True)


def max_id(posts):
    """Highest post id in the list, as a string. None for an empty list."""
    if not posts:
        return None
    return str(max(int(p["id"]) for p in posts))


def next_watermark(found, failed, attempts, max_attempts=MAX_VERIFY_ATTEMPTS):
    """Where lastSeenId may safely advance to, plus who to retry and who to give up on.

    Returns (watermark, retry_ids, gave_up_ids). A None watermark means
    "do not move it at all this run".

    THE BUG THIS EXISTS TO PREVENT (observed live 26 Aug 2026): the mark used
    to advance to the highest id ON THE PAGE regardless of whether each post
    actually made it into the queue. A post that failed fxtwitter verification
    was therefore skipped AND put permanently out of reach on the same run,
    because the next run only looks at posts newer than the mark. Two of his
    posts were lost that way with nothing but a line in a log file.

    So the mark stops BELOW the oldest post still awaiting a retry. That
    trades a stuck mark for a lost post, which is the right way round.

    A post that can never be verified (fxtwitter 500s on some posts
    indefinitely, not just transiently) would otherwise stick the mark
    forever, so each failure is counted and abandoned after max_attempts —
    reported to the operator by url, never dropped in silence.
    """
    retry, gave_up = [], []
    for post in failed or []:
        pid = str(post["id"])
        if attempts.get(pid, 0) + 1 >= max_attempts:
            gave_up.append(pid)
        else:
            retry.append(pid)

    top = max_id(found)
    if retry:
        floor = min(int(pid) for pid in retry)
        below = [int(p["id"]) for p in (found or []) if int(p["id"]) < floor]
        top = str(max(below)) if below else None
    return top, retry, gave_up


def is_stale(state, now=None, hours=STALE_AFTER_HOURS):
    """True when no post has been FOUND for `hours` — i.e. discovery may be broken."""
    stamp = (state or {}).get("lastPostFoundAt")
    if not stamp:
        return False  # never found anything yet; first run shouldn't cry wolf
    now = now or datetime.now(timezone.utc)
    try:
        last = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return (now - last) > timedelta(hours=hours)


def should_alarm(state, now=None, cooldown=ALARM_COOLDOWN_HOURS):
    """Stale AND we haven't already shouted about it recently."""
    if not is_stale(state, now):
        return False
    stamp = (state or {}).get("lastAlarmAt")
    if not stamp:
        return True
    now = now or datetime.now(timezone.utc)
    try:
        last = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return (now - last) > timedelta(hours=cooldown)


def format_post_message(post):
    """The Telegram body for one queued post."""
    head = "🆕 New post from @{}".format(post["author"])
    if post.get("isRepost"):
        head = "🔁 Repost by @{} (originally @{})".format(HANDLE, post["author"])
    when = post.get("postedAt") or "unknown time"
    text = post.get("text") or ""
    if len(text) > MAX_TG_LEN:
        text = text[:MAX_TG_LEN] + "\n… (truncated for this preview; full text is ingested)"
    return "{}\n{}\n\n{}\n\n{}".format(head, when, text, post["url"])


# ----------------------------- discovery -----------------------------

# NOTE: X's current profile markup renders NO <time> elements, so the obvious
# "the link wrapping the timestamp is the permalink" trick does not work here.
# The first /handle/status/<id> href inside an <article> is the item's own
# permalink; any later ones belong to an embedded quoted post, which we do not
# want as a separate thesis (it would be misattributed to him). Hence [0] only.
# Exact post times come from fxtwitter at the verify step, so losing <time>
# costs us nothing.
_EXTRACT_JS = """
() => {
  const re = /^\\/[^/]+\\/status\\/\\d+$/;
  return [...document.querySelectorAll('article')].map(a => {
    const main = [...a.querySelectorAll('a')]
      .map(x => x.getAttribute('href'))
      .find(h => h && re.test(h.split('?')[0]));
    const sc = a.querySelector('[data-testid="socialContext"]');
    return { href: main || null, socialContext: sc ? sc.innerText : '' };
  }).filter(x => x.href);
}
"""


def _launch_browser(pw, headless):
    """Launch the browser X will actually serve.

    Verified 27 Aug 2026: X answers Playwright's BUNDLED Chromium with a bare
    HTTP 403 and an empty body — no login wall, no markup change, just a
    fingerprint block at the edge. Real Google Chrome (channel="chrome") from
    the same machine, same IP, same user agent, headless, gets 200 and renders
    the timeline. So the browser build is the thing that matters here, not the
    headless flag and not the UA string.

    Bundled Chromium stays as the fallback so a machine without Chrome still
    runs (and fails with the usual plain-English discovery error) rather than
    crashing on launch.
    """
    try:
        return pw.chromium.launch(headless=headless, channel="chrome")
    except Exception as exc:
        print("watcher: Google Chrome unavailable ({}), falling back to "
              "bundled Chromium — X currently blocks it.".format(exc))
        return pw.chromium.launch(headless=headless)


def discover(handle=HANDLE, scrolls=DEFAULT_SCROLLS, headless=True):
    """Load the public profile page and return classified post records.

    Raises RuntimeError with a plain-English cause on failure — a login wall,
    a timeout, or an empty render all mean 'discovery is broken', and the
    caller must surface that rather than treat it as 'no new posts'.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is not installed. Run: pip3 install playwright "
            "&& python3 -m playwright install chromium"
        )

    raw = []
    with sync_playwright() as pw:
        browser = _launch_browser(pw, headless)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 1600},
            user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
        )
        page = ctx.new_page()
        try:
            resp = page.goto(PROFILE_URL.format(handle=handle),
                             timeout=PAGE_TIMEOUT_MS,
                             wait_until="domcontentloaded")
            if resp is not None and resp.status == 403:
                raise RuntimeError(
                    "X refused the page outright (HTTP 403, empty body) — "
                    "this browser build is fingerprint-blocked, NOT a markup "
                    "change or a login wall. Install/repair Google Chrome so "
                    "_launch_browser can use channel='chrome'."
                )
            try:
                page.wait_for_selector("article", timeout=PAGE_TIMEOUT_MS)
            except Exception:
                body = (page.inner_text("body") or "")[:400]
                if "sign in" in body.lower() or "log in" in body.lower():
                    raise RuntimeError(
                        "X is showing a login wall for the logged-out profile "
                        "view — the free discovery route is closed. "
                        "See docs/WATCHER.md 'When it breaks'."
                    )
                raise RuntimeError(
                    "No posts rendered on the profile page. X markup may have "
                    "changed. Page began: {!r}".format(body[:200])
                )
            # X VIRTUALIZES the timeline: articles scrolled past are removed
            # from the DOM, so a single evaluate() after scrolling returns only
            # what is on screen NOW. Harvest after every scroll and accumulate,
            # or scrolling gains nothing at all.
            raw = list(page.evaluate(_EXTRACT_JS))
            for _ in range(max(0, scrolls)):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(SCROLL_PAUSE_MS)
                raw.extend(page.evaluate(_EXTRACT_JS))
        finally:
            ctx.close()
            browser.close()

    posts = classify_items(raw, handle)
    if not posts:
        raise RuntimeError("Profile page rendered but yielded no permalinks.")
    return posts


# ----------------------------- verification -----------------------------

def verify_post(post, handle=HANDLE):
    """Attach VERBATIM text via fxtwitter. Returns None when unverifiable.

    This is the firewall: a post we cannot confirm against X's own content
    API never enters the queue, and therefore can never be ingested.

    It is also the second authorship check. classify_items() decides from the
    rendered page; here we ask X itself who wrote it. A post claiming to be his
    that fxtwitter attributes to someone else is rejected outright — that
    mismatch means the permalink and the article got crossed, and the safe
    response to "these two sources disagree about authorship" is to drop it.
    """
    data = fetcher.fetch_tweet(post["url"])
    if not data or not (data.get("text") or "").strip():
        return None
    real_author = (data.get("author") or "").lower()
    if not post.get("isRepost") and real_author and real_author != handle.lower():
        print("watcher: authorship mismatch on {} — page said {}, X says {}. Dropped."
              .format(post["url"], post["author"], data.get("author")))
        return None
    out = dict(post)
    out["text"] = data["text"].strip()
    out["postedAt"] = data.get("posted_at") or data.get("postedAt")
    out["verifiedAuthor"] = data.get("author")
    return out


# ----------------------------- state + queue -----------------------------

def load_state():
    return load_path_optional(STATE_FILE, {})


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def load_pending():
    return load_json_optional(PENDING_POSTS, [])


def save_pending(items):
    save_json(PENDING_POSTS, items)


def queue_posts(posts):
    """Append posts to the approval queue, skipping ones already there."""
    pending = load_pending()
    have = {p["id"] for p in pending}
    added = []
    for p in posts:
        if p["id"] in have:
            continue
        rec = dict(p)
        rec["status"] = "pending"
        rec["queuedAt"] = now_iso()
        rec["notifiedAt"] = None
        pending.append(rec)
        added.append(rec)
    if added:
        save_pending(pending)
    return added


def undelivered():
    """Queued posts still awaiting their Telegram message."""
    return [p for p in load_pending()
            if p.get("status") == "pending" and not p.get("notifiedAt")]


def mark_delivered(ids):
    pending = load_pending()
    stamp = now_iso()
    for p in pending:
        if p["id"] in ids:
            p["notifiedAt"] = stamp
    save_pending(pending)


def is_delivery_time(now=None, hours=DELIVERY_HOURS):
    """True inside a delivery hour, in LOCAL time (the operator is in MYT)."""
    now = now or datetime.now()
    return now.hour in hours


# ----------------------------- telegram -----------------------------

def _api(token, method, **params):
    url = API_URL.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(url, data=data, timeout=60, context=SSL_CTX) as resp:
        return json.loads(resp.read().decode())


def _keyboard(post_id):
    return json.dumps({"inline_keyboard": [[
        {"text": "✅ Ingest", "callback_data": "ok:{}".format(post_id)},
        {"text": "❌ Skip", "callback_data": "no:{}".format(post_id)},
    ]]})


def notify(token, chat_id, post):
    return _api(token, "sendMessage", chat_id=chat_id,
                text=format_post_message(post),
                reply_markup=_keyboard(post["id"]),
                disable_web_page_preview="true")


def alert(token, chat_id, text):
    return _api(token, "sendMessage", chat_id=chat_id, text=text)


# ----------------------------- the run -----------------------------

def run(scrolls=DEFAULT_SCROLLS, dry_run=False, notify_enabled=True, since=None,
        headless=True, deliver="auto"):
    _load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("ALLOWED_TELEGRAM_USER_ID")
    state = load_state()
    since_id = since or state.get("lastSeenId")

    try:
        found = discover(scrolls=scrolls, headless=headless)
    except RuntimeError as exc:
        print("watcher: DISCOVERY FAILED:", exc)
        if notify_enabled and token and chat_id and not dry_run:
            try:
                alert(token, chat_id, "⚠️ X watcher could not read the timeline.\n\n{}"
                                      "\n\nNothing was lost — it will retry on the next "
                                      "run. Forward posts manually meanwhile.".format(exc))
            except Exception:
                pass
        state["lastRunAt"] = now_iso()
        state["lastError"] = str(exc)
        if not dry_run:
            save_state(state)
        return 1

    fresh = newer_than(found, since_id)
    print("watcher: {} posts on page, {} newer than {}".format(
        len(found), len(fresh), since_id or "(nothing seen yet)"))

    verified, failed = [], []
    for p in fresh:
        v = verify_post(p)
        (verified if v else failed).append(v or p)
        time.sleep(0.4)  # be gentle with fxtwitter

    if failed:
        print("watcher: {} post(s) could not be verified and were NOT queued:".format(len(failed)))
        for p in failed:
            print("   ", p["url"])

    if dry_run:
        for p in verified:
            print("\n--- {} {} ---".format(p["id"], p.get("postedAt")))
            print((p.get("text") or "")[:300])
        print("\nwatcher: dry run — nothing queued, nothing saved.")
        return 0

    added = queue_posts(verified)
    print("watcher: queued {} new post(s)".format(len(added)))

    # The page only ever shows PAGE_CAP posts. Hitting that ceiling means the
    # timeline was full and older posts had already scrolled out of reach —
    # we cannot know how many. Say so loudly: a silent gap is exactly the
    # failure this whole design is trying to avoid.
    overflowed = len(fresh) >= PAGE_CAP and since_id
    if overflowed:
        print("watcher: OVERFLOW — page was full ({} posts); some may have been missed."
              .format(PAGE_CAP))

    deliver_now = deliver == "always" or (deliver == "auto" and is_delivery_time())
    queue = undelivered()
    sent = 0
    if notify_enabled and queue and deliver_now:
        if not token or not chat_id:
            print("watcher: TELEGRAM_BOT_TOKEN / ALLOWED_TELEGRAM_USER_ID not set "
                  "— queued but not sent.")
        else:
            if overflowed:
                try:
                    alert(token, chat_id,
                          "⚠️ The X page was full ({} posts) this run, so older posts "
                          "may have scrolled out of reach before I saw them. Worth a "
                          "quick look at x.com/{} for anything between these.".format(
                              PAGE_CAP, HANDLE))
                except Exception:
                    pass
            done = []
            for p in sorted(queue, key=lambda x: int(x["id"])):  # oldest first reads better
                try:
                    notify(token, chat_id, p)
                    done.append(p["id"])
                    sent += 1
                except Exception as exc:
                    print("watcher: send failed for {}: {}".format(p["id"], exc))
            if done:
                mark_delivered(set(done))
    elif queue:
        print("watcher: {} post(s) waiting — next delivery at {} local.".format(
            len(queue), "/".join("{:02d}:00".format(h) for h in sorted(DELIVERY_HOURS))))
    print("watcher: sent {} message(s)".format(sent))

    now = datetime.now(timezone.utc)
    state["lastRunAt"] = now_iso()
    state.pop("lastError", None)

    # Advance the high-water mark only as far as verification actually got.
    # See next_watermark() for the loss this guards against.
    attempts = dict(state.get("verifyAttempts") or {})
    top, retry_ids, gave_up = next_watermark(found, failed, attempts)
    for pid in retry_ids:
        attempts[pid] = attempts.get(pid, 0) + 1
    for pid in gave_up:
        attempts.pop(pid, None)
    for p_ok in verified:
        attempts.pop(str(p_ok["id"]), None)
    state["verifyAttempts"] = attempts

    if retry_ids:
        print("watcher: holding the mark at {} — {} post(s) await a retry.".format(
            top or "(unmoved)", len(retry_ids)))
    if gave_up:
        urls = ["https://x.com/{}/status/{}".format(HANDLE, pid) for pid in gave_up]
        print("watcher: GIVING UP after {} attempts on:".format(MAX_VERIFY_ATTEMPTS))
        for u in urls:
            print("   ", u)
        if notify_enabled and token and chat_id:
            try:
                alert(token, chat_id,
                      "⚠️ Could not verify {} post(s) after {} tries — they will NOT "
                      "be queued and I am moving past them. Forward manually if you "
                      "want them:\n\n{}".format(
                          len(urls), MAX_VERIFY_ATTEMPTS, "\n".join(urls)))
            except Exception:
                pass

    if top:
        state["lastSeenId"] = top
    if fresh:
        state["lastPostFoundAt"] = now_iso()

    if should_alarm(state, now):
        msg = ("⚠️ No new posts from @{} in over {}h.\n\nThis is usually just a "
               "quiet spell, but it can also mean X closed the logged-out view "
               "and the watcher is blind. Worth a manual check of "
               "x.com/{}.".format(HANDLE, STALE_AFTER_HOURS, HANDLE))
        print("watcher:", msg.replace("\n", " "))
        if notify_enabled and token and chat_id:
            try:
                alert(token, chat_id, msg)
                state["lastAlarmAt"] = now_iso()
            except Exception:
                pass

    save_state(state)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Watch an X timeline; queue posts for approval.")
    ap.add_argument("--scrolls", type=int, default=DEFAULT_SCROLLS,
                    help="How far to scroll the profile page (default {}).".format(DEFAULT_SCROLLS))
    ap.add_argument("--dry-run", action="store_true",
                    help="Discover + verify only. Prints results, writes nothing.")
    ap.add_argument("--no-notify", action="store_true", help="Queue without sending Telegram messages.")
    ap.add_argument("--since", default=None, help="Override the stored last-seen post id.")
    ap.add_argument("--headed", action="store_true", help="Show the browser (debugging).")
    ap.add_argument("--deliver", choices=["auto", "always", "never"], default="auto",
                    help="auto = send only during delivery hours (default); "
                         "always = send now; never = queue silently.")
    args = ap.parse_args()
    sys.exit(run(scrolls=args.scrolls, dry_run=args.dry_run,
                 notify_enabled=not args.no_notify, since=args.since,
                 headless=not args.headed, deliver=args.deliver))


if __name__ == "__main__":
    main()
