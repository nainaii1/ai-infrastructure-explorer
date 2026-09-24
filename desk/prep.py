#!/usr/bin/env python3
"""Bundle the collected posts for a window into one compact reading file for
the memo or the digest: grouped by analyst, oldest first, noise fields dropped.

    python3 desk/prep.py --since 2026-09-17            -> desk/store/reading.md
    python3 desk/prep.py --hours 24                    last 24 hours
"""
import argparse
import glob
from datetime import datetime, timedelta, timezone

from common import DESK, POSTS_DIR, ROOT, load_json

OUT = DESK / "store" / "reading.md"


def load_window(since):
    posts = []
    for f in sorted(glob.glob(str(POSTS_DIR / "posts-*.json"))):
        for p in load_json(f, []):
            stamp = p.get("postedAt") or p["collectedAt"]
            if stamp >= since:
                posts.append(p)
    return posts


def fmt(p):
    who = "@{}".format(p.get("author") or "?")
    if p.get("repostedBy"):
        who = "REPOST of {}".format(who)
    tags = []
    if p.get("paid"):
        tags.append("PAID/forwarded")
    if p.get("kind") != "post":
        tags.append(p["kind"].upper())
    head = "- [{}] {} {}{}".format((p.get("postedAt") or p["collectedAt"])[:16].replace("T", " "),
                                   who, p.get("url") or "(no link)",
                                   " [" + ", ".join(tags) + "]" if tags else "")
    text = (p.get("text") or "")
    cap = 600 if p.get("repostedBy") else 3000   # reposts are context, not the analyst's own view
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

    posts = load_window(since)
    roster = [a["handle"] for a in load_json(DESK / "analysts.json", {"analysts": []})["analysts"]]
    groups = {}
    for p in posts:
        key = p.get("repostedBy") or p.get("author") or "forwarded"
        if p.get("via") == "telegram":
            key = "Forwarded to the bot"
        groups.setdefault(key, []).append(p)

    order = ["Forwarded to the bot"] + roster + sorted(k for k in groups if k not in roster and k != "Forwarded to the bot")
    out = ["# Posts since {} ({} total)\n".format(since, len(posts))]
    for k in order:
        if k in groups:
            items = sorted(groups[k], key=lambda x: x.get("postedAt") or x["collectedAt"])
            out.append("\n## {} ({})\n".format(k if k.startswith("Forwarded") else "@" + k, len(items)))
            out.extend(fmt(p) for p in items)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("{} posts -> {} ({} KB)".format(len(posts), OUT.relative_to(ROOT), OUT.stat().st_size // 1024))


if __name__ == "__main__":
    main()
