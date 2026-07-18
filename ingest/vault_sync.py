"""Knowledge Vault structural sync.

Builds one Obsidian-style page per Core+Watch ticker, per category (theme),
per glossary term (concept), plus one person page for the analyst
(@aleabitoreddit). Each page has two halves:

  auto   — machine-owned. Recomputed from the store on every sync:
             refs  = structural links (ticker->theme, theme->tickers, ...)
             stats = tier / mentions / lastMentioned and friends
  note   — Claude-owned prose. Empty ("") until enriched by /vault-note.
           **The sync must NEVER touch an existing note.**

The sync is idempotent: given the same store it returns byte-identical
`pages`, and it only bumps meta.syncedAt when the pages actually changed
(so a no-op sync doesn't churn data.js). Event pages are never auto-created
— they are only carried forward if an operator adds them by hand.

Pure/testable core (`build_vault`) + thin store I/O wrapper (`sync`).
"""

import json
import pathlib
import re
from datetime import datetime, timezone

import scorer

ING = pathlib.Path(__file__).resolve().parent
STORE = ING / "store"
VAULT_PATH = STORE / "vault.json"

PERSON_HANDLE = "@aleabitoreddit"
PERSON_SLUG = "aleabitoreddit"
SCHEMA_VERSION = 1

# Only Core and Watch names earn a ticker page — radar one-off name-drops don't.
TICKER_TIERS = ("core", "watch")

# Deterministic page order → byte-stable output for idempotency.
TYPE_ORDER = {"theme": 0, "ticker": 1, "person": 2, "concept": 3, "event": 4}

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def slugify(s):
    """Match memo.html's slug(): lowercase, non-alphanumerics -> single hyphen.

    Keeping this identical is what makes `[[wikilinks]]` in memos and notes
    resolve to the right vault page.
    """
    out = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    return out or "page"


def _wikilink_slugs(note):
    """Slugs referenced by [[wikilinks]] inside a note body ("" -> none)."""
    if not note:
        return []
    return [slugify(m.group(1).strip()) for m in WIKILINK_RE.finditer(note)]


def _blank_note_fields():
    return {"note": "", "noteUpdatedAt": None}


from store_io import load_path_optional as _load_optional  # noqa: E402


def _desired_pages(tickers, priorities, categories, glossary):
    """Compute the auto-owned page set (no notes) from the store.

    Returns a list of dicts each with slug/type/title/auto — note fields are
    merged in later so existing prose is preserved.
    """
    prio_by_sym = {p["ticker"]: p for p in priorities}
    tiers = scorer.assign_tiers([t["ticker"] for t in tickers], priorities)

    # theme pages (real categories only — never the "unsorted" triage bucket)
    theme_slugs = {cid: slugify(cid) for cid in categories}
    members = {cid: [] for cid in categories}  # category id -> [ticker slugs]
    tier_counts = {cid: {"core": 0, "watch": 0} for cid in categories}

    pages = []

    # ticker pages (Core + Watch), and collect theme membership as we go
    for t in tickers:
        sym = t["ticker"]
        tier = tiers.get(sym, "radar")
        if tier not in TICKER_TIERS:
            continue
        cat = t.get("category")
        refs = [PERSON_SLUG]
        if cat in theme_slugs:
            refs.insert(0, theme_slugs[cat])
            members[cat].append(slugify(sym))
            tier_counts[cat][tier] += 1
        p = prio_by_sym.get(sym, {})
        stats = {
            "tier": tier,
            "mentions": p.get("mentions", 0),
            "lastMentioned": p.get("lastMentioned"),
            "category": cat,
            "market": t.get("market"),
            "marketCapTier": t.get("marketCapTier"),
            "company": t.get("company", ""),
        }
        title = "{} · {}".format(sym, t["company"]) if t.get("company") else sym
        pages.append({
            "slug": slugify(sym),
            "type": "ticker",
            "title": title,
            "auto": {"refs": refs, "stats": stats},
        })

    # theme pages
    for cid, cat in categories.items():
        member_slugs = sorted(set(members[cid]))
        pages.append({
            "slug": theme_slugs[cid],
            "type": "theme",
            "title": cat.get("label", cid),
            "auto": {
                "refs": member_slugs,
                "stats": {
                    "label": cat.get("label", cid),
                    "flowRole": cat.get("flowRole"),
                    "memberCount": len(member_slugs),
                    "coreCount": tier_counts[cid]["core"],
                    "watchCount": tier_counts[cid]["watch"],
                },
            },
        })

    # person page (the analyst) — hubs into every theme
    pages.append({
        "slug": PERSON_SLUG,
        "type": "person",
        "title": PERSON_HANDLE,
        "auto": {
            "refs": sorted(theme_slugs.values()),
            "stats": {
                "handle": PERSON_HANDLE,
                "themesCovered": len(theme_slugs),
            },
        },
    })

    # concept pages (glossary terms)
    for g in glossary:
        term = g.get("term")
        if not term:
            continue
        pages.append({
            "slug": slugify(term),
            "type": "concept",
            "title": term,
            "auto": {"refs": [], "stats": {"definition": g.get("def", "")}},
        })

    return pages


def _count_links(pages):
    """Distinct directed edges = union of auto.refs and note wikilinks.

    Only edges whose target is an existing page are counted (dangling
    wikilinks to not-yet-created pages don't inflate the number).
    """
    valid = {p["slug"] for p in pages}
    edges = set()
    for p in pages:
        src = p["slug"]
        targets = list(p.get("auto", {}).get("refs", [])) + _wikilink_slugs(p.get("note", ""))
        for tgt in targets:
            if tgt in valid and tgt != src:
                edges.add((src, tgt))
    return len(edges)


def build_vault(existing, tickers, priorities, categories, glossary, now=None):
    """Pure builder: merge the desired auto page set over existing pages.

    - preserves every existing `note` / `noteUpdatedAt` (never modified here)
    - carries forward event pages and any enriched (non-empty-note) orphans
    - recomputes meta.pageCount / meta.linkCount
    - only advances meta.syncedAt when the page set actually changed
    """
    now = now or datetime.now(timezone.utc)
    old_pages = (existing or {}).get("pages", []) or []
    old_by_slug = {p["slug"]: p for p in old_pages}

    desired = _desired_pages(tickers, priorities, categories, glossary)
    desired_slugs = {p["slug"] for p in desired}

    pages = []
    for p in desired:
        prev = old_by_slug.get(p["slug"])
        if prev is not None:
            p = dict(p)
            p["note"] = prev.get("note", "")
            p["noteUpdatedAt"] = prev.get("noteUpdatedAt")
        else:
            p = dict(p, **_blank_note_fields())
        pages.append(p)

    # Carry forward pages that fall outside the auto set but must survive:
    # hand-added event pages, and enriched orphans (don't destroy prose).
    for prev in old_pages:
        if prev["slug"] in desired_slugs:
            continue
        if prev.get("type") == "event" or prev.get("note"):
            carried = dict(prev)
            carried.setdefault("note", "")
            carried.setdefault("noteUpdatedAt", None)
            pages.append(carried)

    pages.sort(key=lambda p: (TYPE_ORDER.get(p["type"], 99), p["slug"]))

    # Idempotency: keep the previous timestamp when nothing changed.
    changed = pages != old_pages
    old_meta = (existing or {}).get("meta", {})
    synced_at = now.strftime("%Y-%m-%dT%H:%M:%SZ") if changed else old_meta.get("syncedAt")

    return {
        "meta": {
            "schemaVersion": SCHEMA_VERSION,
            "syncedAt": synced_at,
            "pageCount": len(pages),
            "linkCount": _count_links(pages),
        },
        "pages": pages,
    }


def sync(store=STORE, now=None, write=True):
    """Load the store, rebuild the vault, write it back (if changed), return it."""
    store = pathlib.Path(store)
    tickers = json.loads((store / "tickers.json").read_text(encoding="utf-8"))
    theses = json.loads((store / "theses.json").read_text(encoding="utf-8"))
    base = json.loads((store / "base.json").read_text(encoding="utf-8"))
    existing = _load_optional(store / "vault.json", {})

    # Same symbol canonicalization as generate_data_js (aliases merge,
    # theme tags drop) so vault tiers match the app's tiers.
    canonical_theses = scorer.canonicalize_theses(
        theses, base.get("tickerAliases"), base.get("themeTags"))
    priorities = scorer.compute_priorities(canonical_theses)
    vault = build_vault(
        existing,
        tickers,
        priorities,
        base.get("categories", {}),
        base.get("glossary", []),
        now=now,
    )

    if write:
        (store / "vault.json").write_text(
            json.dumps(vault, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
        )
    return vault


if __name__ == "__main__":
    v = sync()
    print("Synced vault: {} pages, {} links".format(
        v["meta"]["pageCount"], v["meta"]["linkCount"]))
