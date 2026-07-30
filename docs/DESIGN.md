# Design Reference — AI Infrastructure Explorer

**Current: v9 "soft two-tone" (shipped 2026-07-31).**

`shared/theme.css` is the source of truth. This file describes what is in it.
If the two ever disagree, the CSS is right and this file is stale — fix it.

> **Why this file was rewritten.** The previous version had been "updated" four
> times by stacking a new supersession banner on top of an unchanged body, so it
> ended up describing four different design systems at once and ~78% of it
> documented a theme that no longer existed. Current content had even been
> appended *inside* a section labelled historical. If you need to revise this
> doc, revise the body. Do not add a banner. History lives in §9.

---

## 1. What it looks like, in one paragraph

A soft lavender canvas with white cards floating on it, big near-black display
type, and generous air. One violet accent does the work — links, active states,
the primary button — with a teal secondary reserved for chrome and data marks.
The design language is borrowed from [phantom.com](https://phantom.com) and
[aave.com](https://aave.com), but applied to a dense research tool rather than a
marketing site: reading surfaces get the air and the big numbers, while the
working surfaces (the 11-column watchlist, the supply map, the vault graph) keep
their density because that density is what makes them useful.

The signature component is the **big-number stat block** — a huge figure with a
quiet mono label under it. That is the one idea taken wholesale from Aave.

---

## 2. The accessibility contract

This is not a nice-to-have section; it shaped the palette. Read it before
changing any colour.

1. **Text pairs clear WCAG AA 4.5:1. UI and fill pairs clear 3:1.**
2. **No gradient text, and no white text on the brand gradient.** The gradient
   runs from 6.5:1 at its violet end down to **3.05:1** at its teal end against
   white, so anything relying on it for legibility fails partway along its run.
   `--brand-grad` paints only text-free chrome: the 3px top border, the two 2px
   hub hairlines, and the design-reference swatch. Every CTA is solid violet.
3. **A category colour never carries white text.** The ten category hues are
   3:1 UI colours; white on `accelerators` (`#649d00`) is 3.30:1. Active
   category chips therefore *tint* (20% of the hue into `--card`) and keep
   `--ink` text — measured 12.7–14.1:1 across all ten.
4. **`--fs-2xs` (11px) is the type floor.** Nothing may go smaller.
5. **`--violet-soft` is decorative.** At 3.05:1 it is legal for icons, fills and
   large display type (≥24px bold, where the floor drops to 3:1) and illegal for
   body copy. It appears exactly once as text: the italic phrase in the desk
   hero.
6. **One visible focus ring, site-wide** (`:focus-visible`, 2px `--violet`,
   2px offset), with a white variant on dark stage surfaces.

**This contract is enforced by tests**, not by good intentions.
`ingest/tests/test_contrast.py` reads the shipped `:root` and the category hues
straight from the store, so it fails when a token changes rather than when a
fixture goes stale. It checks all 42 pairs, the ten category hues at the UI
floor, the tinted active-chip case, the 11px type floor, and that no page
declares raw hex or raw px type.

```bash
python3 -m unittest discover -s ingest/tests
```

---

## 3. Tokens

All values below are measured, not eyeballed. Ratios are against `--bg` unless
stated.

### Surfaces

| Token | Value | Role |
|---|---|---|
| `--bg` | `#faf9fe` | Solid canvas / fallback |
| `--canvas-top` / `--canvas-bot` | `#fbfaff` / `#eeeafc` | Body gradient stops, viewport-anchored |
| `--card` | `#ffffff` | Card surface |
| `--paper-sink` | `#f2f0fa` | Recessed rows, hover wash |
| `--paper-tint` | `#f6f4fc` | Zebra, header fill |
| `--border` | `#e6e2f2` | Hairline |
| `--border-strong` | `#d5cfe8` | Emphasised divider |

The canvas gradient is `background-attachment: fixed` so a long page never
drifts past the measured bottom stop. `--canvas-bot` is as deep as it can go
while `--violet`, `--teal` and `--muted` all still clear AA on it
(4.60 / 4.58 / 4.73).

### Type colours

| Token | Value | Contrast |
|---|---|---|
| `--ink` | `#1b1436` | 16.7:1 — display headings |
| `--text` | `#3b3557` | 10.9:1 — body |
| `--muted` | `#6a6484` | 5.3:1 — captions, small-caps labels |

### Brand — a lavender ramp, not one purple

| Token | Value | Contrast | Use |
|---|---|---|---|
| `--violet` | `#6a4ee8` | 5.43:1 on card | Links, small labels, active fills, CTAs |
| `--violet-hi` | `#7c5cf0` | 4.52:1 | Hover |
| `--violet-soft` | `#8775ec` | 3.05:1+ | **Decorative only** — icons, fills, large display |
| `--violet-wash` | `#f0ecfe` | — | Tints, section washes |
| `--teal` | `#0f776f` | ≥4.6:1 everywhere | Secondary accent **when it carries text** |
| `--teal-ui` | `#15a59a` | 3.05:1 | Secondary fills and marks — **never text** |
| `--teal-wash` | `#e2f6f3` | — | Second wash |

The softness comes from atmosphere — the gradient canvas, tinted icons, one
italic phrase — while display type stays near-black. A washed-out purple cannot
carry copy: Phantom's own `#ab9ff2` measures **2.34:1** on white.

`--brand-a` / `--brand-b` / `--brand-grad` / `--brand-ink` are kept as aliases so
existing call sites keep working.

### Semantic

| Pair | Value | Contrast | Meaning |
|---|---|---|---|
| `--sem-act-*` | `#1f6b3d` on `#dcf0e2` | 5.45:1 | act / core |
| `--sem-accumulate-*` | `#2b4fb8` on `#e2e8fc` | 5.90:1 | accumulate |
| `--sem-watch-*` | `#8a5310` on `#fbeed2` | 5.49:1 | watch (displays as "wait") |
| `--sem-pass-*` | `#5f5a76` on `#eae7f2` | 5.36:1 | pass / radar |
| `--pos` / `--neg` | `#1f7a45` / `#b23124` | 5.35 / 6.25:1 | up / down |

`--pos` and `--neg` are defined **once**. Before v9 the app carried two greens
and two reds for the same meaning (`#4d6a2b`/`#a13d2f` on three pages,
`#16a34a`/`#dc2626` on desk.html).

### Dark "stage" surfaces

Used by the map's demand hub, the cross-section chart and the vault graph.
Measured against `--stage`.

| Token | Value | Contrast |
|---|---|---|
| `--stage` / `--stage-hi` | `#0e0a1c` / `#191330` | — |
| `--on-stage` | `#e9e5f6` | 15.8:1 |
| `--on-stage-dim` | `#a9a2c4` | 8.0:1 |
| `--pos-stage` / `--neg-stage` | `#5fd48a` / `#ff9a90` | 10.5 / 9.5:1 |
| `--flat-stage` | `#9c95b8` | 6.9:1 |

### Category hues (data-owned)

Live in `ingest/store/base.json` → `AIE_DATA.categories[id].color`, **never
hardcoded in CSS**. All ten clear the 3:1 UI floor on white:

Photonics `#3b82f6` · Memory `#8b5cf6` · Fabs `#c97c00` · Neoclouds `#16a34a` ·
Materials `#ec6406` · Networking `#0d9488` · Glass `#0284c7` · Robotics
`#e11d48` · Accelerators `#649d00` · Hyperscalers `#6366f1`

Fabs, materials and accelerators were darkened in v9 (from `#e08a00`, `#f97316`,
`#76b900`) because they measured 2.69, 2.80 and 2.41 — under the UI floor.

### Type scale

Nine sizes replace the 30 ad-hoc values the app used before v9.

`--fs-3xl 44` · `--fs-2xl 34` · `--fs-xl 26` · `--fs-lg 20` · `--fs-md 17` ·
`--fs-sm 15` · `--fs-xs 13` · `--fs-2xs 11` (floor) ·
`--fs-stat clamp(38px, 6vw, 64px)`

Families: `--display` (Avenir Next / Futura / SF Pro Display) for headings and
body; `--sans` (Apple system) for data-dense surfaces; `--mono` (SF Mono) for
tickers, numbers and small-caps labels. **No CDN fonts** — every page must open
by double-click under `file://`.

### Spacing, shape, motion

`--s-1 4` · `--s-2 8` · `--s-3 12` · `--s-4 16` · `--s-5 24` · `--s-6 32` ·
`--s-7 48` · `--s-8 72`. Section rhythm is `--s-8`.

`--r-card 28px` · `--r-tile 18px` · `--r-chip 999px`. Shadows are violet-tinted
two-layer (`rgba(27,20,54,…)`).

`--dur 240ms` · `--ease 240ms ease` · `--spring cubic-bezier(.32,.72,.28,1.15)`.
All entrance and decorative motion is gated on `prefers-reduced-motion`.

---

## 4. Shared components (`shared/theme.css`)

Anything used by 2+ pages lives here and is never duplicated (hard rule #3).

| Component | Notes |
|---|---|
| `.gradient-border` | 3px brand band, full width, pure CSS |
| `.aie-nav` / `.aie-masthead` / `.aie-wordmark` / `.aie-nav-links` | Sticky masthead. Links are pills; the active one is a solid violet fill. Built by `AIE.renderNav(activePage)` |
| `.aie-rule-double` | Double hairline under the masthead |
| `.aie-wrap` | 1120px column, `--s-5` gutter |
| `.aie-label` | Uppercase mono small-caps at the 11px floor |
| `.aie-section` / `-head` / `-title` / `-sub` | Section rhythm at `--s-8` |
| **`.aie-stat-grid` / `.aie-stat`** | **The big-number block.** `-value` (tabular figures), `-label`, `-note`, `-icon`. `.aie-stat--lead` tints violet-wash. `.aie-stat-value.is-none` drops to muted text so an absent record never reads as a bad one |
| `.aie-wash` | Soft two-tone pastel panel, used sparingly |
| `.aie-ledger` | Shared table. Roomy rows, violet hover, tabular figures. Stacks on mobile; cells with `data-label` keep their column name |
| `.aie-chip` / `--ticker` / `.is-active` | Pills. Active = solid violet (no data hue). Chips that carry a category hue tint instead — see §2.3 |
| `.aie-badge` + `.aie-tier--*` / `.aie-stance--*` | Tier and stance badges |
| `.th-card` family | The one thesis-card renderer, emitted by `AIE.makeThesisCard`. Spine grows via `transform: scaleX()`, not `width` |
| `.aie-colophon` | Footer |
| `.unf-pill` | Pill button. All that survives of the v7 showcase block |

`AIE.paintGradientBorder()` is a kept-for-boot-order **no-op**.

---

## 5. Page surfaces

| Page | Opens with | Notable |
|---|---|---|
| `desk.html` — **Today** | Hero claim + 3 stat blocks, then a capsule nav (Watchlist · The chain · Themes) | The dense one. 11-column sortable watchlist, pipeline/cross-section map, ticker tiles with expand-in-place, theme digests |
| `index.html` — **Notes** | "Everything I've written up." + 3 stat blocks | The memo ledger with type/call/layer filters |
| `memo.html` | Memo title, live snapshot strip | Right-rail TOC with scrollspy; sources appendix |
| `vault.html` — **Vault** | List or graph | The canvas force-directed graph is a dark-stage island |
| `performance.html` — **Record** | Two ledgers: Calls and Claims | The hit-rate block has three deliberately distinct states — no judged claims / raw counts under threshold / a real percentage. Collapsing them would let an absent record read as a bad one. The untestable share is always rendered |
| `design.html` | Live component gallery | Unlinked from main nav |

Nav labels are **Today · Notes · Vault · Record**. "Coverage" was retired in v9 —
it read as trade jargon and said nothing about what the page held. The internal
page ids are unchanged (`coverage` is still the id for `index.html`), so every
`renderNav()` call site and anchor still works.

---

## 6. Voice

Short, plain, first person. No jargon in any heading, button, column header or
empty state. Analytical prose — memos, calls, digests — is untouched; that is
research, not UI copy.

Retired in v9: "Coverage", "Synthesis", "theses", "verdicts", "conviction tier",
"Signal (Core + Watch)", "Claude's desk view", the `01/02/03` chapter markers.

Vocabulary rule (unchanged, and load-bearing): desk stance `watch` **displays**
as "wait" and user rating `watch` as "following", via `AIE.stanceLabel` /
`AIE.ratingLabel`. The data values stay `watch`. Never render them raw.

---

## 7. Responsive

Breakpoints in use: 420 · 460 · 560 · 640 · 680 · 720 · **768** (the mandated
mobile breakpoint) · 1120 (content column) · 1200 (desk only).

At ≤768px: the ledger stacks and `thead` is hidden; stat blocks go two-up rather
than one-up; the capsule nav becomes a fixed bottom bar with
`env(safe-area-inset-bottom)`; section rhythm relaxes from `--s-8` to `--s-7`.

---

## 8. Open items

1. **`vault.html` still declares raw px type and hex.** It is excluded from the
   `test_pages_declare_no_raw_hex` list because its graph reads colours through
   `token(name, fallback)`. Worth revisiting when the canvas is repainted.
2. **The vault graph canvas does not follow the theme.** Every node, edge and
   label colour is a baked literal, and type colours are read **once** at render
   time via `getComputedStyle`. Its stale fallbacks were refreshed in v9, but a
   real repaint is a separate job.
3. **Layout computed in JS.** These break if the surrounding CSS changes:
   `insertDetailAfterRow()` reads `offsetTop` to find grid row boundaries
   (`desk.html`); `AIE.setDrilldownOpen` measures `scrollHeight` once and only
   re-measures on `resize` (no `ResizeObserver`); the capsule pill is positioned
   from `offsetWidth`/`offsetLeft`; scrollspy uses tuned magic numbers
   (`innerHeight * 0.45`, `rootMargin: "-72px 0px -75% 0px"`) paired with
   hardcoded `scroll-margin-top` values.
4. **`.mc-bars` height coupling.** `desk.html` sets bar height from a JS literal
   (`170`) that must stay in sync with the CSS `190px`.
5. **`--spring` overshoots** (`cubic-bezier(.32,.72,.28,1.15)`). Deliberate, and
   close to what both reference sites do, but design linters flag it as dated.
   Worth a decision rather than a drift.
6. **`max-height` drill-downs** are flagged by linters as layout animation. They
   are deliberate: the CSS-only `grid-template-rows: 0fr→1fr` alternative
   silently resolves to 0 height inside `overflow`-constrained or flex-column
   ancestors. Do not "fix" them.
7. **No dark mode.** A deliberate v9 decision, not an oversight.

---

## 9. History

- **v9 "soft two-tone"** (2026-07-31) — this document. Lavender canvas, violet +
  teal, first real type and spacing scales, the stat block, plain-English voice,
  "Coverage" retired.
- **v8 "analysis tool, not product"** (2026-07-18) — removed the Evidence
  chapter, the Focus card and all hero art.
- **v7 "Unpacked"** (2026-07-15) — cool neutral-grey canvas, blue→violet
  gradient used sparingly, true-black stage surfaces. Multi-page split, coverage
  memos, vault, performance.
- **v7 "Private Coverage"** (2026-07-08) — warm editorial "paper" theme; the
  single-page app became a multi-page site with `shared/theme.css`.
- **v6 "Field Guide"** (2026-07-03) — tabs dissolved into one chaptered scroll;
  cool cleanroom palette; the JS-measured drill-down replaced the CSS grid trick.
- **Pre-v6** — cream "research dossier" theme, four tabs.

## 10. Viewing it

No build step. Every page must work by double-click:

```bash
open index.html
```

The Fetch-prices button needs `http://`:

```bash
python3 ingest/serve.py
```
