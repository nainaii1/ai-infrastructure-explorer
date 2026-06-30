# Telegram Bot Setup

➡️ **Moved.** Telegram setup, daily usage, and troubleshooting now live in the
single operating guide so there's one source of truth:

**[docs/GUIDE.md → "The Telegram bot"](GUIDE.md#2-the-telegram-bot-capture-new-ideas)**

Quick reminder of the thing people miss most: the bot is **not** a cloud service —
it only replies while `python3 ingest/bot.py` is running in a terminal on your Mac.

> ⚠️ Never paste your real `TELEGRAM_BOT_TOKEN` into this file (or any file under
> `docs/`) — it's tracked by git and would be published. Your token belongs only
> in `ingest/.env`, which is gitignored.
