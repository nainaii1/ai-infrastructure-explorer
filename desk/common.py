"""Shared plumbing for the desk: paths, JSON files, secrets, HTTP, Telegram.

Standard library only. Nothing here decides anything; it just moves bytes.
"""
import json
import os
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DESK = Path(__file__).resolve().parent
ROOT = DESK.parent
STORE = DESK / "store"
POSTS_DIR = STORE / "posts"      # posts-YYYY-MM.json, one file per month
MEDIA_DIR = STORE / "media"      # screenshots forwarded to the bot
PRICES_DIR = STORE / "prices"    # one snapshot per memo run
STATE_FILE = STORE / "state.json"
ENV_FILE = DESK / ".env"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- files

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def save_json(path, data):
    """Write atomically so a crash mid-write never leaves half a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_env():
    """Read desk/.env (KEY=value lines). Real environment variables win."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("TELEGRAM_BOT_TOKEN",):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


# ---------------------------------------------------------------- http

def _ssl_context():
    """python.org's macOS Python ships without a CA store; use the system one.
    Certificate checks stay on."""
    for ca in (ssl.get_default_verify_paths().cafile, "/etc/ssl/cert.pem"):
        if ca and os.path.exists(ca):
            return ssl.create_default_context(cafile=ca)
    return ssl.create_default_context()


SSL_CTX = _ssl_context()


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        return r.read()


def get_json(url, timeout=20):
    return json.loads(http_get(url, timeout).decode("utf-8"))


# ---------------------------------------------------------------- telegram

class Telegram:
    def __init__(self, token):
        self.token = token

    def call(self, method, **params):
        url = "https://api.telegram.org/bot{}/{}".format(self.token, method)
        data = urllib.parse.urlencode(
            {k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
             for k, v in params.items() if v is not None}).encode()
        req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=40, context=SSL_CTX) as r:
            out = json.loads(r.read().decode("utf-8"))
        if not out.get("ok"):
            raise RuntimeError("Telegram {} failed: {}".format(method, out))
        return out["result"]

    def send(self, chat_id, text, reply_to=None):
        """Plain text (no markup to escape). Long text is split on line breaks
        into Telegram's 4096-character limit."""
        limit, chunks, cur = 3900, [], ""
        for line in text.splitlines(keepends=True):
            if len(cur) + len(line) > limit and cur:
                chunks.append(cur)
                cur = ""
            while len(line) > limit:          # a single monster line
                chunks.append(line[:limit])
                line = line[limit:]
            cur += line
        if cur.strip():
            chunks.append(cur)
        for i, c in enumerate(chunks):
            self.call("sendMessage", chat_id=chat_id, text=c,
                      reply_to_message_id=reply_to if i == 0 else None,
                      disable_web_page_preview="true")

    def download(self, file_id, dest):
        info = self.call("getFile", file_id=file_id)
        url = "https://api.telegram.org/file/bot{}/{}".format(self.token, info["file_path"])
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(http_get(url, timeout=60))
        return dest
