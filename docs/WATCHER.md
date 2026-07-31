# The X Watcher — automatic post discovery

Built 30 Jul 2026. Replaces "open X and forward anything interesting" with
"tap ✅ twice a day."

**Cost: nothing.** No API key, no account, no subscription.

---

## 1. What it does, in plain English

Every 4 hours a small program opens `x.com/aleabitoreddit` in an invisible
browser, notes the links of any posts it hasn't seen before, and fetches each
post's real text.

It does **not** ingest anything on its own. New posts wait in a queue. Twice a
day — **midnight and noon, your time** — they arrive in Telegram, one message
per post, each with two buttons:

```
🆕 New post from @aleabitoreddit
2026-07-30T06:52:06Z

Just some interesting takeaways from $FORM earnings call on CPO:
…

https://x.com/aleabitoreddit/status/2082720873908494456

        [ ✅ Ingest ]   [ ❌ Skip ]
```

Tap **✅ Ingest** → exactly what forwarding a post does today: thesis saved,
tickers detected, `data.js` rebuilt. The message rewrites itself into the usual
confirmation.

Tap **❌ Skip** → gone, and it won't be offered again.

Nothing enters your data without a tap. Your judgement is still the filter —
you just stop doing the hunting.

---

## 2. Daily use

**There is nothing to run.** The schedule is installed and running.

The only requirement: **the bot must be running for the buttons to work.**

```bash
cd /Users/mikembp/Documents/Claude/ai-supply-desk && python3 ingest/bot.py
```

If the bot is off when you tap, Telegram holds the tap for **24 hours** and it
will be processed as soon as the bot is running again. After 24 hours the tap
is lost — but the post stays in the queue, so nothing is destroyed (see §5).

### Check right now instead of waiting

Double-click **`check-x-now.command`** in the project folder. It checks
immediately and sends anything new to Telegram regardless of the hour.

---

## 3. Why it's built this way

Three design decisions worth knowing, because they're what keep your data
trustworthy.

### The browser never supplies text — only links

The invisible browser reads *permalinks* and nothing else. Every post's actual
words come from **fxtwitter** (`ingest/fetcher.py`), the same service you
already use when forwarding a link.

This is deliberate. A post that can't be confirmed through fxtwitter is
**never queued** — it's reported to you instead. Nothing scraped off a rendered
page, and nothing written by an AI model, can reach `theses.json`. Everything in
your store is verbatim from X.

### Other people's posts are filtered out

X shows replies from strangers on his profile when he's in the thread. During
testing, this appeared:

> `/stockprodigyman/status/…` — "@aleabitoreddit @LeaderInvests Thought on meta
> and Microsoft earnings?"

That's someone asking *him* a question. Ingesting it would file another
person's words as his thesis. So posts under someone else's name are dropped
unless X explicitly marks them as a repost. **Quote-posts are unaffected** — a
quote is his own post and comes through normally.

Genuine reposts do come through, labelled 🔁, and are filed under the original
author's name rather than his.

### It tells you when it's blind

If X ever puts the logged-out view behind a login wall, discovery breaks — and
a broken watcher looks *exactly* like a quiet week. So if nothing is found for
24 hours, it messages you. Silence is never treated as good news.

---

## 4. The one real limitation

**The public page shows at most 6 posts.** Measured, not guessed: the page
stops loading at the same point every time and ends in a "Sign up / Log in"
wall. Scrolling cannot get past it.

That's why it polls every 4 hours rather than every 12. At his rate (~11
posts/day) a 12-hour gap expects 5–6 posts — right at the ceiling, so a busy
day would push older posts out of reach before they were ever seen. Four-hourly
polling expects about 2, with plenty of headroom.

**You still only get notified twice a day.** The extra checks are silent; they
just make sure nothing is missed between them.

If the ceiling is ever hit anyway, you get a warning naming the risk, rather
than a silent gap:

> ⚠️ The X page was full (6 posts) this run, so older posts may have scrolled
> out of reach before I saw them.

---

## 5. When something looks wrong

**"I'm not getting messages."**
Check the log first:

```bash
tail -30 ~/Library/Logs/aie-watch-x.log
```

- `queued 0 new post(s)` → working fine, he simply hasn't posted.
- `DISCOVERY FAILED` → the message says why. A login wall means the free route
  has closed; see below.
- Nothing at all → the schedule isn't running. Check with
  `launchctl list | grep watch-x`, and reinstall with
  `launchctl load ~/Library/LaunchAgents/com.aie.watch-x.plist`.
- Also: **your Mac must be awake** at the scheduled time. If it was asleep, the
  run is skipped — but the next one catches up on everything missed.

**"I tapped ✅ and nothing happened."**
The bot wasn't running. Start it, and if it's been under 24 hours the tap will
process by itself. If longer, re-send the queue:

```bash
python3 ingest/watcher.py --deliver always
```

**"The bot warns that data.js wasn't updated."**
Same as always: restart the bot so it picks up current code. This happens
whenever `ingest/` files change while the bot is running.

**"X closed the logged-out view."**
Then this approach is finished and the fallbacks cost money — Apify at roughly
$0.14/month, or Grok's X Search via OpenRouter at about $0.30/month. Both were
priced during the build. Say the word and they can be swapped in; the queue,
the buttons and the verification firewall all stay the same.

### Running it by hand

```bash
python3 ingest/watcher.py --dry-run        # look, change nothing
python3 ingest/watcher.py --deliver always # check + send now
python3 ingest/watcher.py --no-notify      # queue silently
python3 ingest/watcher.py --headed         # watch the browser work (debugging)
```

---

## 6. Files

| File | What it is |
|---|---|
| `ingest/watcher.py` | The watcher — discovery, verification, queue, notify |
| `ingest/store/pending_posts.json` | The approval queue and its history |
| `ingest/store/.watcher_state.json` | Last post seen (gitignored) |
| `com.aie.watch-x.plist` | The 4-hourly schedule |
| `check-x-now.command` | Double-click to check immediately |
| `~/Library/Logs/aie-watch-x.log` | Every run's output |

Nothing is ever deleted from `pending_posts.json` — skipped posts stay with
`status: "skipped"`, so you can always see what was offered and declined.

### A note on the interpreter

The schedule calls
`/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` by full path,
**not** `/usr/bin/python3` like the price refresh does. Playwright is installed
only in the python.org build, and scheduled jobs don't use your shell's PATH.
If you ever reinstall Python, update that path in the plist.
