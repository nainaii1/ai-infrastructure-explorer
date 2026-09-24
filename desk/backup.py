#!/usr/bin/env python3
"""Nightly backup of the private desk data to a PRIVATE GitHub repo.

The main repo is public, so desk/store/ and desk/memos/ are gitignored there.
This copies them into a separate local clone of nainaii1/ai-desk-private and
pushes. Runs from launchd (com.aie.desk-backup) every night; safe to run by
hand any time. Refuses to push if the target repo is not private.

    python3 desk/backup.py
"""
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from common import DESK, STATE_FILE, Telegram, load_env, load_json

REPO = "nainaii1/ai-desk-private"
CLONE = Path.home() / "Documents" / "Claude" / "ai-desk-private-backup"
COPY = ["store", "memos", "analysts.json"]
SKIP = {"reading.md", "digest.txt"}     # scratch files, rebuilt on every run


def run(*cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def gh(*args):
    return run("/opt/homebrew/bin/gh" if Path("/opt/homebrew/bin/gh").exists() else "gh", *args)


def main():
    if gh("repo", "view", REPO, "--json", "visibility", "-q", ".visibility") != "PRIVATE":
        raise SystemExit("Refusing to back up: {} is not private.".format(REPO))
    if not (CLONE / ".git").exists():
        CLONE.parent.mkdir(parents=True, exist_ok=True)
        gh("repo", "clone", REPO, str(CLONE))

    for name in COPY:
        src, dst = DESK / name, CLONE / name
        if dst.exists():
            shutil.rmtree(dst) if dst.is_dir() else dst.unlink()
        if src.is_dir():
            shutil.copytree(src, dst, ignore=lambda d, files: [f for f in files if f in SKIP or f.endswith(".tmp")])
        elif src.exists():
            shutil.copy2(src, dst)

    readme = CLONE / "README.md"
    if not readme.exists():
        readme.write_text("# AI desk: private backup\n\nNightly copy of `desk/store/` and `desk/memos/` "
                          "from ai-supply-desk. Private on purpose: it holds forwarded subscriber posts. "
                          "Never make this repo public.\n", encoding="utf-8")

    run("git", "add", "-A", cwd=CLONE)
    if not run("git", "status", "--porcelain", cwd=CLONE):
        print("backup: nothing changed")
        return 0
    run("git", "commit", "-q", "-m", "backup: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")), cwd=CLONE)
    run("git", "push", "-q", "origin", "HEAD", cwd=CLONE)
    print("backup: pushed to", REPO)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                       # tell the operator; don't fail silently
        print("backup FAILED:", e)
        env, state = load_env(), load_json(STATE_FILE, {})
        if env.get("TELEGRAM_BOT_TOKEN") and state.get("chatId"):
            try:
                Telegram(env["TELEGRAM_BOT_TOKEN"]).send(state["chatId"], "Desk backup failed: {}".format(e))
            except Exception:
                pass
        sys.exit(1)
