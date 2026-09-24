#!/usr/bin/env python3
"""The collector. Runs every six hours on its own (launchd) and does two things:

1. Reads each analyst's public X timeline (desk/analysts.json) through the
   free fxtwitter API and saves any new posts.
2. Picks up whatever the operator forwarded to the Telegram bot since the last
   run (links, pasted text, screenshots; subscriber-only posts and replies
   included) and saves those too, replying "saved" to each.

Nothing is judged here. Posts land verbatim in desk/store/posts/; the memo run
decides what matters. The collector starts, works, and exits: there is no
long-running bot to crash.

    python3 desk/collect.py            normal run
    python3 desk/collect.py --days 14  backfill further on a first run
"""
import argparse
import re
import sys
from datetime import datetime, timedelta, timezone

from common import (MEDIA_DIR, POSTS_DIR, STATE_FILE, DESK, Telegram,
                    get_json, load_env, load_json, now_iso, save_json)

TIMELINE = "https://api.fxtwitter.com/2/profile/{h}/statuses"
STATUS = "https://api.fxtwitter.com/{u}/status/{i}"
STATUS_RE = re.compile(r"(?:twitter\.com|x\.com|fxtwitter\.com|fixupx\.com)/([A-Za-z0-9_]+)/status/(\d+)")
MAX_PAGES = 6
FAIL_ALERT_AFTER = 2      # consecutive failed runs (~12 hours) before a Telegram alert
SEEN_CAP = 20000


# ---------------------------------------------------------------- shaping

def _iso(ts):
    try:
        return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def _media(t):
    m = t.get("media") or {}
    return [x.get("url") for x in (m.get("all") or m.get("photos") or []) if x.get("url")]


def shape(t, via, handle=None):
    """One fxtwitter status (timeline or single-status format) -> our record."""
    author = (t.get("author") or {}).get("screen_name")
    rep = t.get("replying_to")
    reply_to = None
    if isinstance(rep, dict):
        reply_to = {"author": rep.get("screen_name"), "url": rep.get("url")}
    elif rep:
        st = t.get("replying_to_status")
        reply_to = {"author": rep, "url": "https://x.com/{}/status/{}".format(rep, st) if st else None}
    q = t.get("quote")
    quote = None
    if q:
        quote = {"author": (q.get("author") or {}).get("screen_name"),
                 "url": q.get("url"), "text": (q.get("text") or "").strip()}
    reposted_by = (t.get("reposted_by") or {}).get("screen_name")
    return {
        "id": str(t.get("id")),
        "url": t.get("url") or "https://x.com/{}/status/{}".format(author, t.get("id")),
        "author": author,
        "repostedBy": reposted_by if reposted_by and reposted_by != author else None,
        "postedAt": _iso(t.get("created_timestamp")),
        "text": (t.get("text") or "").strip(),
        "quote": quote,
        "replyTo": reply_to,
        "media": _media(t),
        "via": via,
        "kind": "post",
        "paid": False,
        "collectedAt": now_iso(),
    }


def fetch_status(user, sid):
    """Single post via fxtwitter, or None if it can't be read (deleted,
    protected, or subscriber-only)."""
    try:
        d = get_json(STATUS.format(u=user, i=sid))
    except Exception as e:
        print("  fxtwitter failed for {}/{}: {}".format(user, sid, e))
        return None
    t = d.get("tweet")
    if d.get("code") != 200 or not t or not (t.get("text") or t.get("media")):
        return None
    return t


def attach_parent(rec):
    """A reply is useless without what it replies to. Pull the parent's text
    when it is someone else's post (self-threads are collected anyway)."""
    rt = rec.get("replyTo")
    if not rt or not rt.get("url") or rt.get("author") == rec.get("author"):
        return rec
    m = STATUS_RE.search(rt["url"])
    if m:
        p = fetch_status(m.group(1), m.group(2))
        if p:
            rt["text"] = (p.get("text") or "").strip()
    return rec


# ---------------------------------------------------------------- store

def save_posts(recs, state):
    """Append new records to the month file of their post date. Dedupe on id."""
    seen = set(state.get("seen", []))
    by_month = {}
    added = []
    for r in recs:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        month = (r.get("postedAt") or r["collectedAt"])[:7]
        by_month.setdefault(month, []).append(r)
        added.append(r)
    for month, items in by_month.items():
        path = POSTS_DIR / "posts-{}.json".format(month)
        cur = load_json(path, [])
        cur.extend(items)
        cur.sort(key=lambda x: x.get("postedAt") or x["collectedAt"])
        save_json(path, cur)
    state["seen"] = list(seen)[-SEEN_CAP:]
    return added


# ---------------------------------------------------------------- timelines

def collect_timeline(handle, cutoff, seen):
    """New posts from one public timeline, newest first, back to `cutoff` or
    the first page that holds nothing new."""
    out, cursor = [], None
    for _ in range(MAX_PAGES):
        url = TIMELINE.format(h=handle) + ("?cursor=" + cursor if cursor else "")
        d = get_json(url)
        if d.get("code") != 200:
            raise RuntimeError("fxtwitter answered {} {}".format(d.get("code"), d.get("message")))
        fresh = 0
        for t in d.get("results") or []:
            rec = shape(t, "timeline", handle)
            if not rec["postedAt"] or rec["postedAt"] < cutoff or rec["id"] in seen:
                continue          # old, pinned, or already stored
            fresh += 1
            out.append(attach_parent(rec))
        cursor = (d.get("cursor") or {}).get("bottom")
        if not fresh or not cursor:
            break
    return out


# ---------------------------------------------------------------- telegram inbox

def _urls(msg):
    text = (msg.get("text") or msg.get("caption") or "")
    ents = (msg.get("entities") or []) + (msg.get("caption_entities") or [])
    extra = " ".join(e.get("url", "") for e in ents if e.get("type") == "text_link")
    return STATUS_RE.findall(text + " " + extra), text


def handle_message(msg, uid, tg, state):
    """Turn one forwarded Telegram message into records. Returns (recs, reply)."""
    pairs, text = _urls(msg)
    base = {"via": "telegram", "collectedAt": now_iso(), "quote": None, "replyTo": None,
            "repostedBy": None, "media": [], "paid": False}

    if msg.get("photo"):
        big = max(msg["photo"], key=lambda p: p.get("file_size", 0))
        dest = MEDIA_DIR / "tg-{}.jpg".format(uid)
        tg.download(big["file_id"], dest)
        m = re.search(r"@([A-Za-z0-9_]+)", text)
        author = pairs[0][0] if pairs else (m.group(1) if m else None)
        url = "https://x.com/{}/status/{}".format(*pairs[0]) if pairs else None
        rec = dict(base, id="tg-{}".format(uid), url=url, author=author,
                   postedAt=None, text=STATUS_RE.sub("", text).strip(), kind="screenshot", paid=True,
                   media=[str(dest.relative_to(DESK.parent))])
        return [rec], "Saved screenshot{}. I'll read it at the next memo.".format(
            " of @" + author + "'s post" if author else "")

    if not pairs:
        if not text.strip():
            return [], None
        rec = dict(base, id="tg-{}".format(uid), url=None, author=None, postedAt=None,
                   text=text.strip(), kind="note", paid=True)
        return [rec], "Saved as a note."

    recs, lines = [], []
    leftover = STATUS_RE.sub("", text)
    leftover = re.sub(r"https?://\S*", "", leftover).strip()
    for user, sid in pairs:
        t = fetch_status(user, sid)
        if t:
            rec = attach_parent(shape(t, "telegram"))
            recs.append(rec)
            lines.append("Saved @{}: {}".format(rec["author"], rec["text"][:70].replace("\n", " ")))
        elif len(leftover) > 20:
            recs.append(dict(base, id=sid, url="https://x.com/{}/status/{}".format(user, sid),
                             author=user, postedAt=None, text=leftover, kind="post", paid=True))
            lines.append("Saved @{} (subscriber post, using the text you pasted).".format(user))
        else:
            lines.append("Couldn't read @{}'s post; it's probably subscriber-only. "
                         "Send the link again with the text pasted under it, or a screenshot.".format(user))
    return recs, "\n".join(lines)


PAIR_WINDOW = 120   # seconds: a link and the text/screenshot sent with it


def _is_bare_link(msg):
    pairs, text = _urls(msg)
    rest = re.sub(r"https?://\S*", "", STATUS_RE.sub("", text)).strip()
    return bool(pairs) and len(rest) <= 20 and not msg.get("photo")


def _is_companion(msg):
    pairs, text = _urls(msg)
    return not pairs and (msg.get("photo") or len(text.strip()) > 20)


def pair_messages(updates):
    """Sharing from the X app often sends the link and the pasted text (or a
    screenshot) as two Telegram messages. Join a bare link with the text or
    photo sent right before or after it, so the post keeps its author and URL."""
    msgs = [u for u in updates if u.get("message")]
    used, out = set(), []
    for i, u in enumerate(msgs):
        if i in used:
            continue
        m = u["message"]
        if _is_bare_link(m):
            for j in (i + 1, i - 1):
                if 0 <= j < len(msgs) and j not in used:
                    n = msgs[j]["message"]
                    if (n.get("from") or {}).get("id") == (m.get("from") or {}).get("id") \
                            and abs(n.get("date", 0) - m.get("date", 0)) <= PAIR_WINDOW and _is_companion(n):
                        merged = dict(n)
                        key = "caption" if n.get("photo") else "text"
                        merged[key] = (m.get("text") or "") + "\n" + (n.get(key) or "")
                        merged["message_id"] = m.get("message_id")
                        used.update({i, j})
                        if j == i - 1:
                            out = [x for x in out if x is not msgs[j]]
                        out.append(dict(msgs[j] if j > i else u, message=merged))
                        break
            else:
                out.append(u)
            continue
        out.append(u)
    return out


def collect_telegram(tg, state):
    recs = []
    offset = state.get("tgOffset")
    updates = tg.call("getUpdates", offset=offset, timeout=0, allowed_updates=["message"])
    if updates:
        state["tgOffset"] = updates[-1]["update_id"] + 1
    for u in pair_messages(updates):
        msg = u.get("message")
        if not msg:
            continue
        sender = (msg.get("from") or {}).get("id")
        chat = msg["chat"]["id"]
        if state.get("ownerId") is None:
            if (msg.get("text") or "").startswith("/start"):
                state["ownerId"], state["chatId"] = sender, chat
                tg.send(chat, "Linked. Forward me X posts, subscriber posts with the text pasted, "
                              "replies, or screenshots. I pick them up every six hours; replies come back when they are saved.")
            continue
        if sender != state["ownerId"]:
            continue              # only the operator can feed the desk
        try:
            new, reply = handle_message(msg, u["update_id"], tg, state)
        except Exception as e:
            new, reply = [], "Something went wrong saving that: {}".format(e)
        recs.extend(new)
        if reply:
            tg.send(chat, reply, reply_to=msg.get("message_id"))
    return recs


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3,
                    help="how far back to read a timeline (first run uses 14)")
    ap.add_argument("--no-telegram", action="store_true")
    args = ap.parse_args()

    state = load_json(STATE_FILE, {})
    first_run = not state.get("seen")
    days = max(args.days, 14 if first_run else 0)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen = set(state.get("seen", []))
    fails = state.setdefault("failures", {})
    roster = load_json(DESK / "analysts.json", {"analysts": []})["analysts"]

    env = load_env()
    tg = Telegram(env["TELEGRAM_BOT_TOKEN"]) if env.get("TELEGRAM_BOT_TOKEN") else None

    collected, problems = [], []
    for a in roster:
        h = a["handle"]
        try:
            got = collect_timeline(h, cutoff, seen)
            collected.extend(got)
            fails[h] = 0
            print("@{}: {} new".format(h, len(got)))
        except Exception as e:
            fails[h] = fails.get(h, 0) + 1
            print("@{}: FAILED ({}), {} in a row".format(h, e, fails[h]))
            if fails[h] == FAIL_ALERT_AFTER:
                problems.append("@{} has failed {} runs in a row: {}".format(h, fails[h], e))

    if tg and not args.no_telegram:
        try:
            got = collect_telegram(tg, state)
            collected.extend(got)
            print("telegram: {} saved".format(len(got)))
        except Exception as e:
            print("telegram: FAILED ({})".format(e))

    added = save_posts(collected, state)
    state["lastRun"] = now_iso()
    state["lastAdded"] = len(added)
    save_json(STATE_FILE, state)
    print("saved {} new post(s)".format(len(added)))

    if problems and tg and state.get("chatId"):
        tg.send(state["chatId"], "Desk collector problem:\n" + "\n".join(problems) +
                "\nX may have changed something. Ask Claude to look at desk/collect.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
