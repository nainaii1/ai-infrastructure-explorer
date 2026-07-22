"""Shared store I/O + SSL helpers for the ingest scripts.

One home for the helpers that were previously copy-pasted across bot.py,
fetch_prices.py, review.py, synthesize.py, generate_data_js.py and
vault_sync.py (extracted 18 Jul 2026). Stdlib-only.
"""

import os
import ssl
import json
import pathlib
from datetime import datetime, timezone

ING = pathlib.Path(__file__).resolve().parent
STORE = ING / "store"


def load_json(name):
    """Read store/<name> as JSON (raises on missing/invalid — loud by design)."""
    return json.loads((STORE / name).read_text(encoding="utf-8"))


def load_json_optional(name, default):
    """Read store/<name>, returning `default` when missing or unparseable."""
    return load_path_optional(STORE / name, default)


def load_path_optional(path, default):
    """Read an arbitrary path as JSON, returning `default` when missing/invalid."""
    path = pathlib.Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return default


def save_json(name, data, trailing_newline=False):
    """Write store/<name> as pretty JSON (ensure_ascii=False, indent=2)."""
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if trailing_newline:
        text += "\n"
    (STORE / name).write_text(text, encoding="utf-8")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ssl_context():
    """A verifying SSL context backed by a real CA bundle. Some Python builds
    (notably python.org macOS) ship without a configured store, so fall back to
    the system bundle / certifi. Verification stays ON in every case."""
    candidates = [ssl.get_default_verify_paths().cafile, "/etc/ssl/cert.pem"]
    try:
        import certifi
        candidates.append(certifi.where())
    except Exception:
        pass
    for ca in candidates:
        if ca and os.path.exists(ca):
            try:
                return ssl.create_default_context(cafile=ca)
            except Exception:
                continue
    return ssl.create_default_context()
