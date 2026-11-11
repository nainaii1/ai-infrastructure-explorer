#!/usr/bin/env python3
"""Bundle the collected posts for a window into one compact reading file for
the memo or the digest: grouped by analyst, oldest first, noise fields dropped.

    python3 desk/prep.py --since 2026-09-17            -> desk/store/reading.md
    python3 desk/prep.py --hours 24                    last 24 hours
"""
import argparse
import glob
import re
from datetime import datetime, timedelta, timezone

from common import DESK, POSTS_DIR, ROOT, STORE, load_json

OUT = DESK / "store" / "reading.md"


def load_window(since):
    posts = []
    for f in sorted(glob.glob(str(POSTS_DIR / "posts-*.json"))):
        for p in load_json(f, []):
            stamp = p.get("postedAt") or p["collectedAt"]
            if stamp >= since:
                posts.append(p)
    return posts


SIGNAL = re.compile(r"\$[A-Za-z]{1,6}\b|\d")      # a ticker or any number
CASHTAG = re.compile(r"\$([A-Za-z]{1,6}|\d{4,6})\b")


def trim(posts):
    """Cut the reading load without touching the store (since 11 Nov 2026):
    a reply under 80 characters with no ticker and no number is chatter, and a
    post several analysts reposted is read once, with the others named."""
    out, dropped, seen = [], 0, {}
    for p in posts:
        text = p.get("text") or ""
        if p.get("replyTo") and not p.get("repostedBy") and not p.get("paid") and len(text) < 80 and not SIGNAL.search(text) \
                and not p.get("media"):
            dropped += 1
            continue
        if p.get("repostedBy"):
            first = seen.get(p.get("url"))
            if first is not None:
                first.setdefault("alsoBy", []).append(p["repostedBy"])
                dropped += 1
                continue
            seen[p.get("url")] = p
        out.append(p)
    return out, dropped


def my_names():
    """Tickers the operator holds, plans or hunts: their posts are read first."""
    book = load_json(STORE / "book.json", {})
    names = {t for ts in (book.get("sleeves") or {}).values() for t in ts} | set(book.get("plans") or {})
    brain = load_json(STORE / "brain.json", {})
    names |= {h.get("ticker") for h in brain.get("hunt") or []}
    return {n.split(".")[0].upper() for n in names if n}


def fmt(p):
    who = "@{}".format(p.get("author") or "?")
    if p.get("repostedBy"):
        who = "REPOST of {}".format(who)
        if p.get("alsoBy"):
            who += " (also reposted by {})".format(", ".join("@" + h for h in p["alsoBy"]))
    tags = []
    if p.get("paid"):
        tags.append("PAID/forwarded")
    if p.get("kind") != "post":
        tags.append(p["kind"].upper())
    head = "- [{}] {} {}{}".format((p.get("postedAt") or p["collectedAt"])[:16].replace("T", " "),
                                   who, p.get("url") or "(no link)",
                                   " [" + ", ".join(tags) + "]" if tags else "")
    text = (p.get("text") or "")
    cap = 600 if p.get("repostedBy") or p.get("replyTo") else 3000   # reposts and replies are context, not the main case
    if len(text) > cap:
        text = text[:cap] + " [...]"
    lines = [head, "  " + text.replace("\n", "\n  ")]
    rt = p.get("replyTo")
    if rt and rt.get("text"):
        lines.append("  > replying to @{}: {}".format(rt.get("author"), rt["text"][:500].replace("\n", " ")))
    q = p.get("quote")
    if q and q.get("text"):
        lines.append("  > quoting @{}: {}".format(q.get("author"), q["text"][:500].replace("\n", " ")))
    for m in p.get("media") or []:
        if not str(m).startswith("http"):
            lines.append("  [screenshot file: {}]".format(m))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="ISO date or timestamp")
    ap.add_argument("--hours", type=int)
    args = ap.parse_args()
    if args.hours:
        since = (datetime.now(timezone.utc) - timedelta(hours=args.hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif args.since:
        since = args.since
    else:
        ap.error("give --since or --hours")

    posts, dropped = trim(load_window(since))
    mine = my_names()
    roster = [a["handle"] for a in load_json(DESK / "analysts.json", {"analysts": []})["analysts"]]
    groups = {}
    for p in posts:
        key = p.get("repostedBy") or p.get("author") or "forwarded"
        if p.get("via") == "telegram":
            key = "Forwarded to the bot"
        groups.setdefault(key, []).append(p)

    order = ["Forwarded to the bot"] + roster + sorted(k for k in groups if k not in roster and k != "Forwarded to the bot")
    out = ["# Posts since {} ({} to read; {} short replies and repeat reposts left out)\n".format(since, len(posts), dropped)]
    first = [p for p in posts if not p.get("repostedBy") and not p.get("replyTo")
             and {x.upper() for x in CASHTAG.findall(p.get("text") or "")} & mine]
    if first:
        out.append("\n## On your names first ({}): {}\n".format(len(first), ", ".join(sorted(mine))))
        out.append("These posts name a holding, a plan or a hunt-list name. They appear again under their analyst below.\n")
        out.extend("- [{}] @{} {}: {}".format((p.get("postedAt") or p["collectedAt"])[:10], p.get("author"), p.get("url"),
                                             (p.get("text") or "")[:220].replace("\n", " ")) for p in
                   sorted(first, key=lambda x: x.get("postedAt") or x["collectedAt"]))
    for k in order:
        if k in groups:
            items = sorted(groups[k], key=lambda x: x.get("postedAt") or x["collectedAt"])
            out.append("\n## {} ({})\n".format(k if k.startswith("Forwarded") else "@" + k, len(items)))
            out.extend(fmt(p) for p in items)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("{} posts -> {} ({} KB); {} left out".format(len(posts), OUT.relative_to(ROOT), OUT.stat().st_size // 1024, dropped))


if __name__ == "__main__":
    main()
