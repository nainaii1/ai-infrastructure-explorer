#!/usr/bin/env python3
"""Validate data.js. Run before committing: python3 check.py

Checks that the file parses as JSON after the `window.DATA =` prefix, that every
reference (layer, company, narrative) resolves, that dates are ISO, that every
development and fact carries a source URL, and prints a short inventory.
Exit code 1 on any error so it can gate a commit.
"""
import json, re, sys
from datetime import date
from pathlib import Path

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PERIOD = re.compile(r"^(Q[1-4]|FQ[1-4]|H[12])\s(FY)?\d{2,4}$|^FY\d{2,4}$")
STAGES = {"demand", "compute", "supply"}
STATUSES = {"consensus", "building", "contested", "fading"}
SOURCE_TYPES = {"filing", "company", "press", "analyst"}


def load(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    start = raw.index("{")
    end = raw.rindex("}")
    return json.loads(raw[start:end + 1])


def main() -> int:
    path = Path(__file__).with_name("data.js")
    try:
        d = load(path)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"ERROR: data.js does not parse as JSON: {e}")
        return 1

    errors, warnings = [], []
    layers = {l["id"] for l in d["layers"]}
    tickers = [c["ticker"] for c in d["companies"]]
    narrs = {n["id"] for n in d["narratives"]}

    if len(set(tickers)) != len(tickers):
        errors.append("duplicate tickers: " + ", ".join(t for t in set(tickers) if tickers.count(t) > 1))
    if len(layers) != len(d["layers"]):
        errors.append("duplicate layer ids")
    if len(narrs) != len(d["narratives"]):
        errors.append("duplicate narrative ids")

    for l in d["layers"]:
        if l["stage"] not in STAGES:
            errors.append(f"layer {l['id']}: stage {l['stage']!r} not in {sorted(STAGES)}")
        for k in ("name", "summary", "constraint", "watch"):
            if not l.get(k):
                errors.append(f"layer {l['id']}: missing {k}")

    for c in d["companies"]:
        t = c["ticker"]
        if c["layer"] not in layers:
            errors.append(f"{t}: unknown layer {c['layer']!r}")
        for k in ("name", "what", "role", "bull", "bear", "watch", "hq"):
            if not c.get(k):
                errors.append(f"{t}: missing {k}")
        if "listed" not in c:
            errors.append(f"{t}: missing listed flag")
        for f in c.get("facts", []):
            if not f.get("source", "").startswith("http"):
                errors.append(f"{t}: fact without a source URL: {f.get('text', '')[:60]}")
            a = f.get("asOf", "")
            if not (ISO.match(a) or PERIOD.match(a)):
                errors.append(f"{t}: fact asOf {a!r} is neither ISO date nor a period like 'Q2 2026'")
        if not c.get("facts"):
            warnings.append(f"{t}: no sourced facts yet")

    for n in d["narratives"]:
        if n["status"] not in STATUSES:
            errors.append(f"narrative {n['id']}: status {n['status']!r} not in {sorted(STATUSES)}")
        for t in n["companies"]:
            if t not in tickers:
                errors.append(f"narrative {n['id']}: unknown company {t}")
        if not n.get("signposts"):
            errors.append(f"narrative {n['id']}: no signposts")

    seen = set()
    for dev in d["developments"]:
        key = (dev["date"], dev["title"])
        if key in seen:
            errors.append(f"duplicate development: {key}")
        seen.add(key)
        if not ISO.match(dev["date"]):
            errors.append(f"development {dev['title'][:50]!r}: date {dev['date']!r} not ISO")
        if not dev.get("source", "").startswith("http"):
            errors.append(f"development {dev['title'][:50]!r}: no source URL")
        if dev.get("sourceType") not in SOURCE_TYPES:
            errors.append(f"development {dev['title'][:50]!r}: sourceType {dev.get('sourceType')!r} not in {sorted(SOURCE_TYPES)}")
        for t in dev["companies"]:
            if t not in tickers:
                errors.append(f"development {dev['title'][:50]!r}: unknown company {t}")
        for n in dev["narratives"]:
            if n not in narrs:
                errors.append(f"development {dev['title'][:50]!r}: unknown narrative {n}")

    if not ISO.match(d["meta"]["updated"]):
        errors.append("meta.updated is not an ISO date")

    for w in warnings:
        print("warn:", w)
    for e in errors:
        print("ERROR:", e)

    by_layer = {l["id"]: sum(1 for c in d["companies"] if c["layer"] == l["id"]) for l in d["layers"]}
    latest = max(dev["date"] for dev in d["developments"] if dev["date"] <= date.today().isoformat())
    print(f"\n{len(d['companies'])} companies across {len(d['layers'])} layers "
          f"({', '.join(f'{k} {v}' for k, v in by_layer.items())})")
    print(f"{len(d['narratives'])} narratives, {len(d['developments'])} developments, latest dated {latest}, "
          f"{sum(len(c.get('facts', [])) for c in d['companies'])} sourced facts")
    print(f"{len(warnings)} warnings, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
