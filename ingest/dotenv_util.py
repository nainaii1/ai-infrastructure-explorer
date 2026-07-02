"""Tiny stdlib-only .env loader shared by synthesize.py and fetch_prices.py.

Kept as a standalone leaf module (no other ingest/*.py imports) so scripts
that need it don't pull in synthesize.py's `anthropic` dependency just to
read an API key from ingest/.env.
"""

import os
import pathlib

ING = pathlib.Path(__file__).resolve().parent


def _parse_dotenv(text):
    """Parse KEY=VALUE lines into a dict: skip blanks/comments, keep '=' in values,
    strip at most one matched surrounding quote pair. Pure/testable."""
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]  # only a matched surrounding pair, not unmatched inner quotes
        if key:
            out[key] = val
    return out


def _load_dotenv():
    """Best-effort: load ingest/.env into os.environ for keys NOT already set, so
    `python3 ingest/<script>.py` works right after you edit .env (no shell
    sourcing needed). Existing/exported env vars always win; missing file is fine.
    """
    path = ING / ".env"
    if not path.exists():
        return
    try:
        env = _parse_dotenv(path.read_text(encoding="utf-8"))
    except OSError:
        return
    for key, val in env.items():
        if key not in os.environ:
            os.environ[key] = val
