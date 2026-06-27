# Telegram Bot Setup Guide

This guide walks you through the one-time setup to connect the ingest pipeline
to your Telegram account. Takes about 5 minutes.

---

## What you're setting up

A private Telegram bot that only you can talk to. When you forward a post from
@aleabitoreddit into it, the bot captures the thesis, extracts tickers, and
rewrites `data.js` automatically. No third-party service, no subscription — just
the free Telegram Bot API and the Python script that's already on your machine.

---

## Step 1 — Create the bot with BotFather

1. Open Telegram and search for **@BotFather** (the official blue-check bot).
2. Send it the message: `/newbot`
3. It will ask for a name — type anything, e.g. `AI Supply Desk`
4. It will ask for a username — must end in `bot`, e.g. `aisupplydesk_bot`
5. BotFather replies with a **token** that looks like:
   ```
   1234567890:AAE-abc123XYZ_something_long_here
   ```
   Copy this — you'll need it in Step 3. Keep it private (treat it like a password).

---

## Step 2 — Find your Telegram user ID

1. Search for **@userinfobot** in Telegram.
2. Send it any message (even just `/start`).
3. It replies with your numeric **Id**, e.g. `987654321`

Copy that number.

---

## Step 3 — Add the credentials to `.env`

Open the file `ingest/.env` in any text editor. It already exists (created from
`.env.example`). Fill in the two values:

```
TELEGRAM_BOT_TOKEN=1234567890:AAE-abc123XYZ_something_long_here
ALLOWED_TELEGRAM_USER_ID=987654321
```

Replace the examples with your actual token and ID.

> This file is gitignored — it will never be committed or pushed to GitHub.

---

## Step 4 — Run the bot

In your terminal, from the project root:

```bash
set -a; . ./ingest/.env; set +a
python3 ingest/bot.py
```

You should see:
```
Bot listening... (allowed user: 987654321)
```

Leave the terminal open. The bot is now waiting for messages.

---

## Step 5 — Test it

1. In Telegram, search for the username you created (e.g. `@aisupplydesk_bot`).
2. Send a message or forward a post from @aleabitoreddit.
3. The bot replies with a summary like:
   ```
   ✅ Ingested h_abc123
   Tickers: AAOI, COHR, LITE
   Added: POET
   Queued: NPO
   ```
4. Check `data.js` — it updated automatically.
5. Refresh the app to see the new thesis and updated priority tags.

---

## Day-to-day usage

**Forwarding a post:** In Telegram, open a post by @aleabitoreddit, tap the
forward icon, and select your bot. Done.

**Pasting text:** You can also paste the text directly into the bot chat.
Include the `x.com/...` URL so the thesis is linked to its source:
```
$AAOI is my top pick for 1.6T optical https://x.com/aleabitoreddit/status/1234
```

**Weekly prices (separate from the bot):**
```bash
python3 ingest/serve.py    # then open http://localhost:8765/ → Watchlist → Fetch prices
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Bot doesn't reply | Wrong token or user ID | Re-check `ingest/.env`; restart `bot.py` |
| "Not authorized" in logs | Message from the wrong Telegram account | Send from the account whose ID is in `.env` |
| Bot replies but `data.js` unchanged | Python error in the pipeline | Check the terminal — errors print there |
| Bot stops after a while | Terminal session ended | Restart `python3 ingest/bot.py` |

---

## Stopping the bot

Press **Ctrl-C** in the terminal. Data is safe — store JSON files are written
before each `data.js` regeneration.

---

## Security reminder

- The `TELEGRAM_BOT_TOKEN` is a secret. Don't share it, don't paste it into
  chat, and don't commit it.
- The bot silently ignores any Telegram user ID other than yours.
- You can revoke a compromised token at any time: message @BotFather → `/revoke`
