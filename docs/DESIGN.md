# Design Reference — AI Infrastructure Explorer

> **⚠️ Superseded again (2026-07-08): the v7 "Private Coverage" editorial theme shipped.**
> Design tokens + shared components now live in **`shared/theme.css`** (mirrored
> in `desk.html`'s inline `:root`) — **that file is the source of truth, not this
> doc.** Warm "paper" palette: bg `#faf7f2` / card `#fffdf9` / border `#e6e0d4` /
> text `#33302a` / muted `#8a8375` / ink `#1a1712`. Serif display stack
> `--serif: ui-serif, "New York", Georgia, serif` for the hero, chapter heads,
> and standfirst; Apple system **sans** for body + data-dense surfaces (watchlist
> table, map bands); `--mono` (SF Mono) for tickers, numbers, and small-caps
> labels (uppercase, 0.08em, ~11px). Warm-tinted `--shadow-sm`/`--shadow-lg`;
> `--r-card: 14px`; motion tokens unchanged (`--ease: 240ms`, `--spring`). New
> shared components: top masthead (`AIE.renderNav`), ledger table, chips,
> warm-tinted tier/stance badges (same green/sky/amber/muted hue semantics),
> colophon, and the category-painted gradient border. The dark `#0f1b2e`
> cross-section blueprint + NVIDIA hub are intentional dark accents. Everything
> below (the v6 cleanroom cool `#f5f5f7` palette, and the pre-v6 cream theme) is
> now **historical baseline only** — trust `shared/theme.css` first.

> **⚠️ Superseded (2026-07-03): the v6 "Field Guide" redesign shipped.**
> The app is now one continuous chaptered scroll (hero prologue → 01 Map →
> 02 Watchlist → 03 Evidence → 04 Synthesis) with a floating frosted-glass
> capsule nav (sliding pill + scrollspy; bottom-floating ≤768px).
> Key token changes: bg `#f5f5f7` / border `#e3e3e8` / text `#333336` /
> muted `#86868b` / ink `#1d1d1f`; `--ease: 240ms ease`; `--spring:
> cubic-bezier(.32,.72,.28,1.15)`; `--shadow-sm`/`--shadow-lg`; `--r-card:
> 16px`; Apple system font stack; paper-grain removed. New components: hero
> signal-chain stat nodes (count-up), conviction barbell, "Latest signal"
> card, chapter heads, glossary strip (`AIE_DATA.glossary`), "New this week"
> strip, cross-section heat legend, caveats colophon, scroll reveals
> (`.reveal`/`.in-view`), unified JS-measured max-height drill-down (not
> CSS `grid-template-rows: 0fr->1fr` — that silently collapses to 0 height
> under `overflow`-constrained or flex-column ancestors; fixed 2026-07-03
> alongside capping the Evidence feed to the 10 most recent theses).
> Every "known
> inconsistency" in §7 below was resolved (one `::before` spine everywhere,
> one conviction-badge language, `--line`/`.placeholder-card` deleted,
> documented spine-on-cards/dot-in-table split, watchlist sticky header now
> functional via `max-height`). Sections below describe the **pre-v6 cream
> theme** and remain as the historical baseline; trust `index.html` first.

_Snapshot of the pre-v6 design system, extracted directly from
`index.html`'s `<style>` block and `ingest/store/base.json`.
Baseline dated 2026-07-02._

**Purpose:** this is a *before* baseline, not a proposal. It documents what
exists today so a redesign has an accurate starting point and doesn't
accidentally contradict something intentional. It contains no opinions about
what to change — see "Known inconsistencies" at the end for the one section
that flags things worth a second look.

**How to use this with a design tool/session:** hand this file over as
context alongside `CLAUDE.md`'s hard rules (vanilla HTML/CSS/JS, `file://`-safe,
no CDN fonts/frameworks, 200–300ms transitions, 768px breakpoint — those
constraints don't go away in a redesign unless you explicitly decide to drop
them).

---

## 1. Visual identity, in one paragraph

A light, warm, editorial "research-dossier" aesthetic — cream background,
white cards, hairline borders, dark-slate text — closer to a printed
research note than a typical dark-mode dev-tool dashboard. The one loud
element is a genuine system monospace font used for tickers, data labels,
and mono "eyebrow" captions, which reads as *data* against everything else
reading as *prose*. Category identity (9 colors) is the only chroma in an
otherwise neutral palette, applied consistently as left-edge spines, pill
badges, and hover glows — never as full-color fills.

---

## 2. Color tokens

### Structural (CSS custom properties, `index.html` `:root`)
| Token | Value | Used for |
|---|---|---|
| `--bg` | `#faf8f3` (warm cream) | Page background |
| `--card` | `#ffffff` | Card/panel surfaces |
| `--border` | `#e7e3da` (soft warm gray) | Hairline borders, dividers |
| `--text` | `#1e293b` (dark slate) | Body text |
| `--muted` | `#64748b` | Secondary text, labels, captions |
| `--line` | `#d8d3c8` | Declared but not referenced elsewhere in the current CSS — see "Known inconsistencies" |
| `--ink` | `#0f172a` (near-black) | High-contrast type: active tab underline, big numbers, hub band background |
| `--ease` | `250ms ease` | All transitions (within the 200–300ms rule) |
| `--mono` | `"SF Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, "Cascadia Code", "Roboto Mono", monospace` | All data/ticker/label typography — genuine system stack, no CDN |

Body font: `Inter, system-ui, sans-serif` (declared on `html, body`; Inter
itself isn't bundled — falls back to `system-ui` under `file://`, so in
practice most users see their OS system font, not actual Inter).

A faint inline-SVG noise texture (`body::before`, 3.5% opacity) sits behind
all content for paper-like atmosphere — no network request, `file://`-safe.

### Category palette (9, from `ingest/store/base.json` → `AIE_DATA.categories[id].color`)
Never hardcoded in CSS — every category-colored element reads `--accent`
from an inline style set by JS. This is the **only** source of chroma in the app.

| Category | Color | Flow zone |
|---|---|---|
| Photonics | `#3b82f6` | Supply |
| AI Memory | `#8b5cf6` | Supply |
| Glass Substrates | `#0ea5e9` | Supply |
| Materials & Packaging | `#f97316` | Supply |
| Fabs & Foundries | `#f59e0b` | Chip |
| Accelerators | `#76b900` | Chip |
| Networking | `#14b8a6` | Chip |
| Neoclouds | `#22c55e` | Demand |
| Robotics | `#e11d48` | Demand |
| *Unsorted (triage)* | `#94a3b8` | *(no zone — muted footer)* |

Accent colors are almost never used at full saturation on large areas —
the dominant pattern is `color-mix(in srgb, var(--accent) N%, <base>)` to
tint a background/border/text against `--card`, `--bg`, `white`, or `black`,
typically at 5–16% for fills and 45–75% for text/icons. This keeps every
category consistent in *weight* even though hues differ.

### Semantic colors (hardcoded, not tokenized — only place raw hex appears outside category colors)
| Value | Used for |
|---|---|
| `#16a34a` / `#dcfce7` | Positive: watchlist gains (`.wl-pos`), high-conviction thesis border, high-conviction badge |
| `#dc2626` | Negative: watchlist losses (`.wl-neg`) |
| `#fef3c7` / `#b45309` | Medium-conviction brain-digest badge (amber) |
| `#f59e0b` (12–40% mix) | Watchlist "prices are stale" hint banner |

---

## 3. Typography scale

No `<h1>`–`<h6>` hierarchy is used consistently — sizes are set per-component.
Full inventory, largest to smallest:

| Size | Weight | Where | Font |
|---|---|---|---|
| 27px | 700 | `.tk-ticker` — the ticker symbol on a card. The single largest, most distinctive type moment in the app. | mono |
| 22px | 700 | `.brand h1` / `.brand-bolt` — app title + ⚡ | system |
| 18px | 600 | `.placeholder-card h2` *(currently unused — see §7)* | system |
| 16px | 600 | `.th-empty-title`, `.bd-title` (brain digest theme name) | system |
| 15px | 600–700 | `.map-header h2`, `.layer-title` | system |
| 14px | 500 | `.tab-btn`, `.placeholder-card p` | system |
| 13.5px | — | `.th-text`, `.bd-narrative` — thesis/digest body prose | system |
| 13px | 400–700 | `.tk-company`, `.tk-body dd`, `.wl-table` base, `.bd-points li` | system |
| 12.5px | — | `.layer-desc`, `.wl-hint` | system |
| 12px | 500 | `.tk-company` variants, `.bd-sub`, `.ps-chip` | system / mono |
| 11px | 400–700 | `.layer-index`, `.layer-count`, `.tk-badge`, `.th-date`, `.th-source`, `.cards-ledger` | mono |
| 10–10.5px | 700 | Uppercase mono "eyebrow" labels: `.ledger-eyebrow`, `.zone-label`, `.tk-tier-label`, `.th-conviction`, `.bd-conviction`, `.priority-strip .ps-label`, `.wl-table thead th` | mono |
| 9.5px | 700 | `.layer-detail-label` ("What to watch") | mono |
| 8px | — | Zone-divider `▲` flow-direction marker | — |

**Pattern:** body/prose text uses the system sans stack; anything that is
*data* (tickers, counts, dates, badges, uppercase eyebrow labels) uses
`--mono`. This split is the main typographic device in the app — worth
preserving deliberately in any redesign rather than treating as incidental.

Uppercase mono eyebrows consistently use `letter-spacing: 0.06em–0.18em`
(tighter for larger labels, looser for the smallest ones).

---

## 4. Spacing & shape scale

**Border radius** (used consistently, not ad hoc):
- `4px` — small chip/tag backgrounds (`.wl-hint code`)
- `6px` — `.layer-index` badge, `.wl-rating` select, `.th-ticker` chip
- `8px` — buttons (`.map-show-all`, `.wl-fetch`), `.wl-hint` banner
- `12px` — **the dominant card radius**: every card/panel (`.layer-band`,
  `.tk-card`, `.placeholder-card`, `.priority-strip`, `.cards-empty`,
  `.th-card`, `.bd-card`, `.wl-table-wrap`)
- `999px` (pill) — all badges/chips/toggles (`.tk-badge`, `.ps-chip`,
  `.th-conviction`, `.bd-conviction`, `.bd-toggle`)

**Left-edge accent spine** (the app's signature micro-pattern): a 4px
solid-color bar on the left edge of a card, using `::before` with
`position: absolute`, widening to 7px on hover/active via a `width`
transition. Appears on `.layer-band`, `.tk-card`; a variant using
`border-left` (not an absolutely-positioned pseudo-element) appears on
`.th-card` and `.bd-card`. Two different CSS techniques for the same visual
idea — see §7.

**Gaps:** tight (4–9px) for badge/icon clusters and inline metadata; medium
(12–20px) for card internals and grid gutters (`.card-grid` gap is 18px);
loose (28–40px) between major sections (`.cards-section` margin-top 40px,
28px on mobile).

**Card padding:** consistently close to `18–20px` vertical, `18–24px`
horizontal, with **more padding on the left than the right** on cards that
carry the accent spine (e.g. `.tk-card`: `20px 20px 18px 24px`) — the extra
left padding keeps text clear of the spine.

---

## 5. Motion

- Single easing token for everything: `--ease: 250ms ease` (mid-point of the
  200–300ms rule in `CLAUDE.md`).
- Hover/active transitions are always on `transform`, `box-shadow`,
  `border-color`, `background`, or pseudo-element `width` — never on
  layout-affecting properties.
- Ticker cards have a one-time entrance animation on render: `tk-rise`
  (fade + 10px translateY, 320ms ease, **staggered per card via an inline
  `animation-delay`** set in JS). Respects `prefers-reduced-motion: reduce`
  (animation disabled, cards render at full opacity immediately) — the only
  place in the app with an explicit reduced-motion fallback.
- Tab switching is a simple opacity fade (`.tab-panel` → `.tab-panel.active`),
  not a transform/slide.
- The Brain tab's "sources" drill-down (`.bd-sources`) toggles with plain
  `display: none/block` — no transition, unlike the map's `.layer-detail`
  (which animates `max-height`/`opacity`/`margin-top`). Inconsistent; see §7.

---

## 6. Component inventory

### Header / nav
- `.gradient-border` — fixed 3px bar across the full viewport width, top.
  Background is a `linear-gradient` painted by JS at runtime from the live
  category color list (left→right), not CSS — so it auto-updates if
  categories change. Fallback color is `--border` until JS runs.
- ⚡ favicon — inline SVG data URI, no external request.
- `.brand` — bolt glyph + `<h1>` title + muted subtitle, inline on desktop,
  stacked on mobile (`flex-direction: column` at ≤768px).
- `nav.tabs` / `.tab-btn` — underline-style tabs, active state = dark
  (`--ink`) text + 2px bottom border, muted otherwise. Horizontally
  scrollable with no visible scrollbar styling on mobile.

### Tab 1 — Supply Chain Map
- `.map-intro` — single-line "how to read this map" copy, muted, capped at
  `72ch` (the only explicit measure/line-length constraint in the app).
- `.layer-stack` — vertical flow pipeline (not the SVG arc map described in
  earlier drafts of `CLAUDE.md` — that was superseded). A `::before` on the
  stack itself paints a 2px vertical "flow rail" in the left gutter, using a
  `linear-gradient` from faint (bottom) to stronger (top) `--ink` — visually
  "flows up into NVIDIA."
- `.zone-divider` — labeled hairline break between flow zones (Demand / Chip
  / Supply), with a small `▲` marker sitting on the rail. A muted variant
  (`--muted` suffix) is used for the "Triage" footer zone and suppresses the
  `▲` marker (empty `content`).
- `.layer-band` — the core interactive card. States: default, `:hover`
  (translateX 2px, accent-tinted border/background/shadow, spine widens to
  7px), `.is-active` (stronger accent tint + shadow, spine stays at 7px),
  `:focus-visible` (2px muted outline). A non-interactive `.layer-hub`
  variant (dark `--ink` background, white text, `cursor: default`, no hover
  transform) represents the "NVIDIA + Hyperscalers" demand hub, pinned above
  the pipeline.
- `.layer-detail` — collapsible "what to watch" panel inside an active band;
  animates open via `max-height`/`opacity`/`margin-top`.
- On mobile (≤768px): `.layer-band` wraps (`flex-wrap: wrap`), the ticker
  count drops below the title block with a `52px` left margin to align under
  the text (not the badge).

### Tab 1 — Ticker cards (Section B)
- `.cards-ledger` — hairline-underlined header: mono uppercase "Holdings"
  eyebrow + right-aligned scope text (e.g. "Photonics · 6 companies").
- `.card-grid` — CSS grid, `repeat(4, 1fr)` desktop → `repeat(2, 1fr)` at
  ≤1024px → single column at ≤768px.
- `.tk-card` — accent spine (see §4), staggered rise-in animation, hover
  lift (`translateY(-3px)` + shadow + spine widen). Internal structure:
  - `.tk-head` — big mono ticker (27px) + muted company name.
  - `.tk-badges` — category pill (tinted fill), market pill (flag + exchange,
    outlined/neutral), and a right-aligned 4-segment "meter" (`.tk-meter`,
    4× 4×11px bars) for market-cap tier (Mega=4 lit, Small=1 lit) instead of
    a text label alone.
  - `.tk-body` — `dt`/`dd` label-value rows ("What they do:", "Why NVDA
    needs them:"), separated by a hairline top-border on repeat rows.
  - Optional `.tk-prio` badge when the ticker has ingest-derived priority.
- `.cards-empty` — dashed border, accent-tinted (falls back to `--muted` if
  no category is selected), used for zero-ticker categories (e.g. Networking
  had 0 tickers historically — still a valid state to design for).
- `.priority-strip` — "mentioned by @aleabitoreddit" chip row above the
  ledger; each `.ps-chip` is a pill with rank, symbol (mono, bold), and
  mention-count meta, on a `--bg`-colored (not `--card`) background so it
  reads slightly recessed against the section.

### Tab 2 — Watchlist
- `.wl-header` — ledger label + right-aligned actions (as-of timestamp +
  fetch button).
- `.wl-fetch` — the app's one solid-fill button: `--ink` background, white
  text, `border-radius: 8px`, opacity-fade on hover/disabled (this is the
  only button style that doesn't use the outline/ghost pattern everything
  else uses).
- `.wl-hint` — amber-tinted banner (`color-mix` with the one hardcoded
  `#f59e0b`) for a "prices are stale, use the local server" notice.
- `.wl-table` — sticky header (`position: sticky; top: 0`), numeric columns
  right-aligned + mono, sortable column headers with a `.arrow` indicator,
  row hover tinted by that row's category `--accent` at 6%. Category shown
  as a colored dot (`.wl-dot`, 9px circle) + label, not a pill (only place
  category identity uses a dot instead of a pill/spine).
- `.wl-rating` — a plain `<select>`-style control, not custom-styled beyond
  border/radius/padding.

### Tab 3 — Thesis
- `.th-card` — `border-left: 4px solid var(--border)`, turned green
  (`#16a34a`) for high-conviction posts. **Uses `border-left`, not the
  `::before` spine technique** used elsewhere (see §7).
- `.th-card-meta` — date (mono, muted) + conviction pill + right-aligned
  source link.
- `.th-conviction` — pill badge, two states: `.high` (green) and `.normal`
  (neutral gray) — no "medium"/"low" distinction at the thesis level
  (unlike Brain digests, which have three).
- `.th-text` — `white-space: pre-wrap` body text (preserves the author's own
  line breaks from the source post).
- `.th-tickers` — chips colored per-ticker via an inline `--t-color` custom
  property (falls back to `#94a3b8` if the ticker has no resolvable category).
- `.th-empty` — centered empty state for when no theses are ingested yet.

### Tab 4 — Brain
- `.bd-card` — same `border-left` accent pattern as `.th-card` (accent color
  here, not a fixed border color).
- `.bd-conviction` — three states: `.high` (green), `.medium` (amber —
  the one place amber is used), `.low` (neutral gray).
- `.bd-narrative` — `pre-wrap` prose, same treatment as thesis text.
- `.bd-points` — plain `<ul>`, default disc markers, no custom bullet styling.
- `.bd-toggle` — ghost/outline pill button ("Show sources"), the pattern
  used everywhere except `.wl-fetch`.
- `.bd-sources` — drill-down list of the source thesis cards, reusing
  `.th-card` in a compact/`--bg`-tinted variant (`.th-card-compact`).

---

## 7. Known inconsistencies (worth a decision, not a bug report)

A redesign is a natural point to either deliberately keep or resolve these —
flagging them so they're a choice, not an oversight:

1. **Two different "accent spine" techniques.** `.layer-band`/`.tk-card` use
   an absolutely-positioned `::before` (lets the spine animate its `width`
   independently on hover). `.th-card`/`.bd-card` use plain `border-left`
   (simpler, but can't do the width-grow hover effect). If spine-grow-on-hover
   is a signature interaction worth keeping, Thesis/Brain cards are currently
   missing it.
2. **One solid-fill button vs. everywhere-else outline buttons.** `.wl-fetch`
   is the only `--ink`-filled button in the app; `.map-show-all` and
   `.bd-toggle` are outlined/ghost. Intentional (it's the one true
   call-to-action: "Fetch prices") or accidental drift — worth confirming.
3. **`--line` token is declared but unused.** Defined in `:root` as "default
   (unhovered) map connector line," a leftover from an earlier SVG-map
   design. Dead token.
4. **`.placeholder-card` CSS is dead.** Built for the original "Coming soon"
   states of Tabs 2–3 (v1); all four tabs now have real content, and nothing
   in the current JS assigns this class. Safe to remove, or repurpose for a
   future empty/loading state.
5. **Conviction vocabularies don't match across tabs.** Thesis conviction is
   binary (`high` / `normal`); Brain digest conviction is three-way (`high` /
   `medium` / `low`). Both represent "how confident is this," so the visual
   language (and possibly the underlying enum) could unify.
6. **Category identity renders three different ways**: a left-edge spine
   (cards/layers), a tinted pill (badges), and a plain colored dot
   (Watchlist only). Consider whether Watchlist should match the pill/spine
   pattern or if the dot is deliberately more compact for a dense table row.
7. **Drill-down animation is inconsistent.** The map's `.layer-detail` panel
   animates open (`max-height`/`opacity`); the Brain tab's `.bd-sources`
   drill-down snaps open with `display: none/block`. Same interaction
   ("reveal more detail on demand"), two different feels.
8. **Body font `Inter` isn't actually bundled.** `font-family: Inter,
   system-ui, sans-serif` — since there's no CDN/local font file (by design,
   per the offline-first rule), everyone effectively sees `system-ui`. Not a
   bug, but worth knowing before assuming "Inter" describes what people see.

---

## 8. Responsive behavior

Single breakpoint system, mobile-first isn't used — desktop is the base,
overrides cascade down:
- `≤1024px` — ticker card grid drops from 4 → 2 columns.
- `≤768px` (the `CLAUDE.md`-mandated breakpoint) — app padding tightens
  (24px→16px sides), brand stacks vertically, tab nav becomes horizontally
  scrollable, card grid drops to 1 column, layer bands wrap and re-align
  their count, section top-margins shrink (40px→28px).
- No tablet-specific tier beyond the 1024px grid change; no distinct
  large-desktop tier (max content width is a flat `1200px` centered
  container at every size above 768px).

---

## 9. Viewing it live for reference

There's no build step. To look at the current app while redesigning:
```bash
open index.html                    # or double-click it — works fully offline
```
Yahoo price fetching needs `http://` (not `file://`); if that matters for
what you're looking at:
```bash
python3 ingest/serve.py            # then open http://localhost:8765/
```

Note: no fresh screenshots are embedded in this doc (the browser automation
tool wasn't available when this was written). `docs/images/thesis-tab.jpeg`
predates the map redesign and no longer reflects the current UI — worth
re-capturing per-tab screenshots before/during a redesign session for visual
comparison alongside this token reference.
