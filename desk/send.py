#!/usr/bin/env python3
"""Send a text file (the memo summary or the daily digest) to the operator's
Telegram chat.

    python3 desk/send.py desk/memos/2026-09-24-telegram.txt
"""
import sys

from common import STATE_FILE, Telegram, load_env, load_json


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    env = load_env()
    state = load_json(STATE_FILE, {})
    if not env.get("TELEGRAM_BOT_TOKEN") or not state.get("chatId"):
        print("Telegram is not set up yet (no token in desk/.env, or /start not sent to the bot).")
        return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    Telegram(env["TELEGRAM_BOT_TOKEN"]).send(state["chatId"], text)
    print("sent {} characters".format(len(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
