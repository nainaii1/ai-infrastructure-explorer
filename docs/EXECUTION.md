# Execution Guide — "Private Coverage" Editorial Upgrade

_Created 2026-07-06 from the approved plan
(`~/.claude/plans/my-friend-build-a-mutable-volcano.md`). This is the to-do doc:
tick boxes as prompts land. One prompt = one Claude Code session = one commit._

**Goal:** bring the app to the quality bar of the reference private research site —
warm serif editorial design, memo-style coverage notes, an Obsidian-style
knowledge Vault (pages + wikilinks + graph view), then minimal performance hooks.
Multi-page vanilla HTML/CSS/JS, no frameworks, still file://-friendly, all data in
`data.js`.

## How to use this doc

1. Work top to bottom — each prompt assumes the previous one landed.
2. Open a fresh Claude Code session per prompt, pick the recommended model/effort,
   and paste the prompt text verbatim.
3. After each session: run the verification checklist, tick the box, commit
   (conventional commits: `feat:` / `refactor:` / `docs:`).
4. Model key — **S5-M / S5-H** = Claude Sonnet 5 medium/high effort (schema
   plumbing, well-specified pages, docs). **Op-M / Op-H** = Opus medium/high
   (design taste, regression-prone refactors, algorithms, research writing).
   Rule of thumb: bump effort one notch whenever a prompt touches `desk.html`.

## Target site map

```
index.html        front page: masthead + "Coverage & market notes" ledger
desk.html         the current Field Guide, moved (Map / Watchlist / Evidence / Brain)
memo.html         memo renderer (?id= / ?ticker=), right-rail TOC
vault.html        knowledge base: ?view=index | ?view=graph | ?page=<slug>
performance.html  Phase 5, minimal; nav-greyed until ≥3 calls
shared/theme.css  design tokens + shared components
shared/common.js  seeding, helpers, nav, wikilink parser
data.js           generated as always; gains memos, vault, later calls
```

## Phase table

| Phase | What ships | Prompts | Status |
|---|---|---|---|
| 0 | This guide | P0 | ✅ 2026-07-06 |
| 1 | Multi-page scaffold + editorial design system | P1–P5 | ✅ 2026-07-08 |
| 2 | Coverage memos (store, memo.html, ledger, skills, seed content) | P6–P10 | ☑ 2026-07-12 |
| 3 | Knowledge Vault (store+sync, index/page views, graph, authoring loop) | P11–P14 | ✅ 2026-07-12 |
| 4 | Cross-linking everywhere | P15 | ✅ |
| 5 | Performance hooks (calls.json + minimal page) | P16 | ✅ 2026-07-12 |
| 6 | "Unpacked" rebrand + focus card + map restructure | U1–U8 | 🚧 U1–U6 done, U7–U8 remain |

## Verification checklist (run after EVERY prompt)

- [ ] `python3 -m unittest discover -s ingest/tests` passes
- [ ] Every page opens by double-click (file://) AND via `python3 ingest/serve.py`
- [ ] Browser console clean; nav links resolve both ways (relative hrefs only)
- [ ] 768px mobile pass on touched pages
- [ ] Unknown `?ticker=` / `?page=` shows a graceful empty state (where applicable)
- [ ] If seeding/version changed: clear `aie_*` localStorage → reload → re-seeds

---

## Phase 1 — Editorial foundation

### ✅ P1 · Op-M — shared/theme.css

> Read CLAUDE.md and docs/EXECUTION.md (Phase 1). Create `shared/theme.css`: the
> new editorial design-token set — warm paper bg `#faf7f2`, card `#fffdf9`, border
> `#e6e0d4`, ink `#1a1712`, muted `#8a8375`; display serif stack
> `ui-serif, "New York", Georgia, serif`; keep the existing `--mono` stack for
> uppercase small-caps labels (0.08em tracking, 11px). Build shared components:
> top nav bar (serif wordmark left, `PRIVATE COVERAGE · NOT ADVICE` small-caps,
> page links Coverage / Desk / Vault / Graph / Performance-greyed), double
> hairline rule under the masthead, ledger table styles, chips, tier/stance badges
> (warm-tinted fills, same hue semantics), footer colophon, and the 3px gradient
> top border (category colors still come from data.js at runtime — do not hardcode
> them). Motion tokens unchanged (200–300ms, spring, reduced-motion gating).
> Include a commented static HTML snippet at the bottom of the file for visual QA.
> Do NOT touch index.html yet. Commit as `feat: editorial design tokens + shared components (theme.css)`.

### ✅ P2 · Op-H — split & wire desk.html (highest regression risk)

> Read CLAUDE.md and docs/EXECUTION.md. `git mv index.html desk.html`. Create
> `shared/common.js` exposing a global `AIE` namespace: move from the inline app
> script the localStorage seeding block (keys stay `aie_*`), `setDrilldownOpen()`,
> date/percent formatters, and category-color helpers; add `AIE.renderNav(activePage)`
> (renders the theme.css top nav) and a stub `AIE.linkForTicker(sym)` returning
> `desk.html#watchlist` for now. Wire `<link href="shared/theme.css">` and
> `<script src="shared/common.js">` (after data.js) into desk.html; delete the
> moved code from its inline script; keep the capsule chapter nav working under
> the new top nav. Verify via file://: all chapters render, all three drill-downs
> animate, watchlist sorting/filters work, both map views work, scrollspy works,
> mobile 768px OK. Commit as `refactor: multi-page split — field guide moves to desk.html, shared assets extracted`.

### ✅ P3 · Op-M — retokenize desk.html to the editorial theme

> Read CLAUDE.md, docs/DESIGN.md, and shared/theme.css. Restyle desk.html to the
> warm editorial theme by changing CSS custom-property values and hero/chapter-head
> typography to the serif display stack — do NOT rewrite selectors or renderer JS.
> Restyle the capsule nav warm (frosted paper instead of cool glass). Category
> colors keep coming from `AIE_DATA.categories[id].color`. Data-dense surfaces
> (watchlist table, map bands) keep the system sans body. Manual QA: map pipeline
> + cross-section, click-to-filter + layer detail drill-down, watchlist sort/tier
> chips/Desk column, Evidence cap + drill-down, Brain sources drill-down, hero
> count-up, reduced-motion, 768px. Commit as `feat: editorial retheme of the field guide (desk.html)`.

### ✅ P4 · S5-H — new index.html front page

> Read CLAUDE.md, shared/theme.css, shared/common.js. Create the new `index.html`
> editorial front page: masthead (wordmark + PRIVATE COVERAGE), a serif standfirst
> paragraph describing the desk (source it from AIE_DATA meta/counts, not
> hardcoded copy where data exists), a latest-desk meta strip (desk.meta.reviewedAt,
> verdict count, thesis count), links into desk.html chapters, and a reserved
> empty-state section for the coverage ledger: "Coverage notes begin with the next
> weekly review." Body text serif ~17px/1.65. Uses theme.css + common.js — no
> duplicated CSS/JS. Commit as `feat: editorial front page (coverage index shell)`.

### ✅ P5 · S5-M — docs sync

> Update CLAUDE.md for the multi-page architecture: rewrite hard rule #3 (app code
> = page files + exactly shared/theme.css + shared/common.js; anything used by 2+
> pages goes in shared, never duplicated), extend rule #2 (all memo/vault data
> rides inside data.js, fetch still banned), update Current status, Design system
> (editorial theme supersedes cleanroom), File structure, and note the Signal
> Digest spec is superseded by the memo feature. Update docs/DESIGN.md (new
> tokens; archive cleanroom section), docs/ROADMAP.md (phase table pointer to
> docs/EXECUTION.md), README.md (site map). Commit as `docs: bring docs current with multi-page editorial architecture`.

## Phase 2 — Coverage memos

### ☑ P6 · S5-M — memos.json plumbing

> Read CLAUDE.md and docs/EXECUTION.md (memos.json schema below). Create
> `ingest/store/memos.json` with meta (schemaVersion 1, updatedAt, author
> "claude-desk", disclaimer) and empty `memos: []`. In
> `ingest/generate_data_js.py`, load it with the same optional-load pattern used
> for glossary and pass through as the `memos` key. Add unittest cases to
> ingest/tests: file absent → `memos` key present as `{}`; file present →
> passthrough intact. Regenerate data.js. Commit as `feat: memos store + data.js passthrough`.
>
> Memo record schema: `{ id: "m_<ticker>_<yyyy>w<ww>", ticker, kind:
> "coverage"|"update"|"exit-note", title, dek, publishedAt, updatedAt, rating
> (MUST equal current desk stance: act|accumulate|watch|pass), sections:
> [{heading, body}] (ordered, drives TOC), sourceThesisIds: [], basedOnVerdict:
> bool }`. Bodies are plain paragraphs on `\n\n` supporting `**bold**`, `$TICK`,
> `[[wikilink]]` only.

### ☑ P7 · Op-M — memo.html renderer

> Read CLAUDE.md, docs/EXECUTION.md, shared/theme.css, shared/common.js. Build
> `memo.html`: reads `?id=` or `?ticker=` (newest memo for ticker) via
> URLSearchParams. Render: top nav, title/dek/rating badge/published+updated
> dates, an auto snapshot strip pulled live from the ticker record (price, tier,
> category chip, desk stance — never hand-written), the ordered sections with
> anchored headings, a sticky right-rail table of contents with
> IntersectionObserver scrollspy (≤768px: collapses to a top "Contents"
> drill-down via setDrilldownOpen), a sources appendix rendering real thesis
> cards from sourceThesisIds (move/reuse a shared `makeThesisCard` in common.js),
> a prior-memos-for-this-ticker list, disclaimer footer. Body renderer supports
> `**bold**`, `$TICK` chips (via AIE.linkForTicker), and `[[slug]]` wikilinks
> pointing to `vault.html?page=slug` (fine that vault doesn't exist yet). Unknown
> ticker/id → graceful empty state. Serif body 17px/1.65. Commit as `feat: memo page with right-rail TOC and sources appendix`.

### ☑ P8 · S5-H — coverage ledger on index.html

> Read index.html, shared/theme.css. Replace the reserved empty-state with the
> coverage ledger: one row per memo (date · ticker chip · kind chip · title ·
> rating badge), newest first, row links to memo.html?id=…; filter chips for kind
> and rating; entry count ("N entries"); tickers with a desk verdict but no memo
> render as muted "verdict only" rows linking to desk.html#watchlist. Empty-state
> stays when memos is empty. Commit as `feat: coverage & market notes ledger`.

### ☑ P9 · S5-M — authoring skills

> Extend `.claude/skills/weekly-review/SKILL.md` with step 4b: after updating
> verdicts, write/refresh memos in ingest/store/memos.json for Core names whose
> stance changed or that gained ≥3 new theses; memo rating MUST equal the desk
> stance; sections follow Snapshot / Thesis / Why own it / Risks / Bottom line;
> cite sourceThesisIds; then regen data.js + bump base.json version. Also create
> `.claude/skills/coverage-note/SKILL.md` — `/coverage-note TICKER` authors or
> updates one memo using the same rules. Commit as `docs: memo authoring added to weekly review + /coverage-note skill`.

### ☑ P10 · Op-H — seed the first memos (research writing)

> Author memos for the top 3–5 Core names by priority score: read their theses,
> brain digest, and desk verdict; write full memos (Snapshot / Thesis / Why own
> it / Risks / Bottom line) in ingest/store/memos.json per the skill rules, with
> sourceThesisIds cited and rating matching stance. Regen data.js, bump base.json
> meta.version, verify index ledger + memo pages render. Commit as `feat: first coverage memos for top Core names`.

## Phase 3 — Knowledge Vault

### ☑ P11 · S5-H — vault.json + vault_sync.py (2026-07-12)

> Read CLAUDE.md and docs/EXECUTION.md (vault schema below). Create
> `ingest/store/vault.json` and `ingest/vault_sync.py`: idempotent upsert of one
> page per Core+Watch ticker, per category (theme), per glossary term (concept),
> plus the person page (@aleabitoreddit). Each page: `slug` (kebab-case), `type`
> (ticker|theme|person|event|concept), `title`, `auto` (machine-owned: refs =
> structural links like ticker→theme, stats = tier/mentions/lastMentioned),
> `note` (Claude-owned prose, "" until enriched — sync must NEVER modify it),
> `noteUpdatedAt`. Event pages are never auto-created, only synced. Recompute
> meta pageCount/linkCount (auto.refs ∪ wikilinks parsed from notes). Hook
> vault_sync into the generate_data_js.py flow and pass `vault` through to
> data.js. Unit tests: idempotency, note preservation, counts. Regen. Commit as
> `feat: knowledge vault store + structural sync`.

### ☑ P12 · Op-M — vault.html index + page views (2026-07-12)

> Read CLAUDE.md, shared/*, docs/EXECUTION.md. Build `vault.html` with
> `?view=index` (default): "N pages · M links" serif header, type filter chips,
> rows showing title + stub/enriched badge + last-updated; and `?page=slug`:
> title, type chip, auto-stats strip (live from ticker/theme data), note prose
> with clickable `[[wikilinks]]`, auto sections for linked memos, cited theses,
> and computed backlinks ("What links here"). Put the wikilink parser in
> common.js and make memo.html reuse it. Unknown slug → empty state. Commit as
> `feat: vault index + page views with wikilinks and backlinks`.

### ☑ P13 · Op-H — vault graph view (hardest algorithmic task) (2026-07-12)

> Read vault.html and docs/EXECUTION.md graph spec. Add `?view=graph`: canvas 2D
> force-directed layout, hand-written physics, no libraries. O(n²) pair repulsion
> (≤300 nodes), spring attraction along edges (rest length 60–90px by node type),
> mild centering gravity, damping ~0.85 with a cooling alpha that restarts on
> drag/filter. Deterministic init: positions hashed from slug, theme nodes
> pre-placed on a ring. Node colors: theme = its data.js category color; ticker /
> person / event / concept = theme.css tokens. Interactions: hover highlights the
> node + 1-hop edges and dims the rest; click opens a side panel (title, stats,
> "Open page →", "Open memo →" when one exists); drag pins a node; legend by
> type; devicePixelRatio scaling; pause the loop when settled or tab hidden;
> prefers-reduced-motion → settle ~300 iterations synchronously and draw static.
> Mobile ≤768px: side panel becomes a bottom sheet; +/− zoom and reset buttons.
> Un-grey the "Graph" nav link. Commit as `feat: vault knowledge graph (canvas force layout)`.

### ☑ P14 · Op-M — vault authoring loop + first enrichment (2026-07-12)

> Create `.claude/skills/vault-note/SKILL.md` — `/vault-note SLUG` enriches one
> vault page's `note` (plain prose, 1–3 paragraphs, dense with `[[wikilinks]]` to
> related pages; never touch `auto.*`), stamps noteUpdatedAt, regens data.js.
> Add a weekly-review step: enrich pages touched by tier or stance changes.
> Then do the first enrichment pass: all 10 theme pages + top 5 ticker pages.
> Commit as `feat: vault authoring skill + first enrichment pass`.

## Phase 4 — Cross-linking

### ✅ P15 · S5-H — link everything (2026-07-12)

> Upgrade `AIE.linkForTicker(sym)` in common.js: memo exists → memo.html; else
> vault page exists → vault.html?page=…; else desk.html#watchlist. Apply it to
> every ticker chip site-wide: thesis cards (Evidence + memo appendix), brain
> digest ticker lists, watchlist rows (row click), map layer detail panels, vault
> side panel/pages. Watchlist gains a "Note" column (memo link + date) for
> covered names. Coverage ledger gains theme (category) filter chips. Commit as
> `feat: site-wide ticker cross-linking`.

**Shipped (commit `feat: site-wide ticker cross-linking`):**
`AIE.linkForTicker(sym)` now returns, in order, `memo.html?ticker=SYM` (a
coverage memo exists) → `vault.html?page=<slug>` (a `type:"ticker"` vault page
exists) → `desk.html#chapter-watchlist`. Applied to: thesis-card ticker chips
(shared `makeThesisCard`, so Evidence feed + memo appendix + **vault cited-thesis
cards** all inherit it), brain-digest ticker lists, ticker-card headers (the map's
per-category cards), and the watchlist (symbol is a link + whole-row click, both
guarded so the rating `<select>` and in-row links still work). Watchlist added a
**Note** column linking the newest memo with its date. Coverage ledger added a
**Theme** filter group (distinct ticker categories, ordered by value-chain layer)
that narrows both memo rows and verdict-only stubs. Vault graph side panel already
linked page + memo, so it was left as-is. `.th-ticker` / `.tk-ticker` / `.wl-sym`
gained link (hover) styling. No `data.js` regen — code-only change.

## Phase 5 — Performance hooks

### ☑ P16 · S5-H — calls.json + minimal performance page (2026-07-12)

> Read docs/EXECUTION.md. Create `ingest/store/calls.json` (meta + calls: id,
> ticker, kind new-position|add-on-dip|trim|exit, calledAt, entryPrice,
> entryCurrency, stanceAtCall, memoId, thesisIds, closedAt, exitPrice, outcome
> open|win|loss|wash, benchmark {symbol "SMH", priceAtCall}) + generate_data_js
> passthrough + tests. Extend weekly-review SKILL.md: stamp a call (entry price
> from prices.json) ONLY for future discrete events — verdict newly flipping to
> act/accumulate, a declared dip-buy, or an exit; explicitly no retro-fitting.
> Build minimal `performance.html`: ledger table (date, ticker, kind, entry,
> latest from prices, return %, vs-SMH), disclaimer. Nav link stays greyed until
> ≥3 calls exist (render-time check). Commit as `feat: calls ledger schema + minimal performance page`.

---

## Phase 6 — "Unpacked" rebrand + focus card + map restructure

_Added 2026-07-13 from the approved plan
(`~/.claude/plans/this-section-on-01-robust-liskov.md`). Three workstreams:
(a) rebrand every page to a Samsung Galaxy Unpacked aesthetic — cool
neutral-grey canvas, near-black bold geometric sans display type, ONE
blue→violet gradient accent used sparingly, white large-radius cards, pill
controls, true-black "event stage" dark surfaces; (b) a desk-authored weekly
**Focus card** ("the headline") leading index + desk hero, demoting raw tweets
to Evidence; (c) Chapter 01 restructure — 49 tall cards become compact tiles
with expand-in-place, line-art category icons, animated flow arrows._

Model key addition — **F5-M / F5-H** = Claude Fable 5 medium/high effort
(design taste on new components). Op/S5 as before. Same rule of thumb: bump
one notch when a prompt touches `desk.html`.

### Token spec (the U2 payload — later prompts reference this table)

| Token | New value |
|---|---|
| `--bg` / `--card` / `--border` | `#f4f5f7` / `#ffffff` / `#e2e5ea` |
| `--ink` / `--text` / `--muted` | `#0b0d12` / `#2a2e35` / `#7c828c` |
| `--paper-sink` / `--paper-tint` | `#eceef1` / `#f0f2f5` (names kept — pages consume them) |
| `--stage` / `--stage-hi` (new) | `#0a0a0c` / `#16161a` — replaces hardcoded `#0f1b2e` (desk.html cross-section + color-mix; vault.html graph bg) |
| `--brand-a` / `--brand-b` | `#2b6bf3` / `#7a3bf0` |
| `--brand-grad` / `--brand-ink` (new) | `linear-gradient(100deg, var(--brand-a), var(--brand-b))` / `#3d55f2` (solid fallback) |
| `--display` (new) | `"Avenir Next", "Futura", -apple-system, "SF Pro Display", "Segoe UI", system-ui, sans-serif` · weight 700 / -0.02em tracking at use sites |
| `--serif` | transitional alias `var(--display)` in U2; per-page rename in U4; alias deleted in U8 |
| `--r-card` / `--r-tile` (new) / `--r-chip` | `20px` / `14px` / `999px` |
| `--shadow-sm` / `--shadow-lg` | cool-tinted `rgba(15,23,42,…)` soft / deep pairs |
| `--sem-act-*` | `#def0dd` / `#256b39` |
| `--sem-accumulate-*` | `#dce9f9` / `#1f5fa8` |
| `--sem-watch-*` | `#fbeecb` / `#8c5c0a` |
| `--sem-pass-*` | `#e8eaee` / `#7c828c` |
| Motion | `--dur/--ease/--spring` unchanged (hard rule #5); add `@keyframes aie-flow` dash-scroll (ambient; the existing reduced-motion gate kills it) |

The 3px gradient top border becomes the **brand gradient** (pure CSS);
`AIE.paintGradientBorder()` becomes a kept-for-boot-order no-op. Category
colors keep their data-viz job (bands/tiles/chips/graph) — never the chrome.

### ☑ U1 · S5-M — this guide (2026-07-13)

> Append Phase 6 to docs/EXECUTION.md: token spec table, focus-card design,
> prompts U2–U8 with model+effort, loop commands for the difficult steps.
> Commit as `docs: unpacked rebrand execution guide`.

### ☑ U2 · F5-M — brand tokens (2026-07-13) ⚠️ CHECKPOINT: eyeball all 5 pages before U3

> Read CLAUDE.md and docs/EXECUTION.md Phase 6 (token spec). In
> `shared/theme.css`: rewrite `:root` per the token table (add `--display`,
> alias `--serif: var(--display)`, `--stage`/`--stage-hi`, `--brand-*`,
> `--r-tile`; recalibrate `--sem-*`); set `.gradient-border { background:
> var(--brand-grad); }`; add `@keyframes aie-flow { to { stroke-dashoffset:
> -12; } }`; sweep any warm literals in shared components (grep
> `rgba(60, 48, 30` and the old warm hexes). In `desk.html`: **DELETE the
> duplicate `:root` block (~lines 26–48)** — it is a strict subset that
> silently overrides theme.css; swap `#0f1b2e` → `var(--stage)` (the
> `.map-cross` rule ~line 475 and inside the `color-mix()` string ~line 1865).
> In `vault.html`: the two graph-stage hexes (~line 158) → `var(--stage-hi)` /
> `var(--stage)`. In `shared/common.js`: make `paintGradientBorder` a no-op
> (KEEP the export — every page calls it at boot). Verify: unit tests green;
> all 5 pages via file:// — cool canvas, display type flipped via the alias,
> gradient border, badges legible on bg/card/zebra/stage, vault graph node
> colors flow (runtime getComputedStyle), reduced-motion pass, 375/768px.
> Commit as `feat: unpacked design tokens`.

_Shipped 2026-07-13 (`0fdf102`). One extra beyond the prompt: `desk.html` also
carried a **page-local `.gradient-border` rule** (not just the `:root` block)
that overrode theme.css — deleted it too, else the desk border stayed a grey
hairline. Also swept `desk.html`'s hardcoded warm tier/stance badge hexes to the
`--sem-*` tokens so the checkpoint didn't render stale badges. 101 unit tests
green; all 5 pages verified via the local server._

### ☑ U3 · S5-M — category palette recalibration (2026-07-13)

> Read docs/EXECUTION.md Phase 6. In `ingest/store/base.json`, deepen the
> light/acid category hues for the cool canvas — fabs `#f59e0b`→`#e08a00`,
> neoclouds `#22c55e`→`#16a34a`, glass `#0ea5e9`→`#0284c7`; keep accelerators
> `#76b900` (NVIDIA-green is semantic); judge the rest against `#f4f5f7`.
> Small recognizable moves only. Regen via `python3
> ingest/generate_data_js.py` (never hand-edit data.js; expect vault.json
> churn). Verify hues flow to layer bands, cross-section bars, chips, and the
> vault graph theme nodes. Commit as `feat: cooler category palette`.

_Shipped 2026-07-13 (`a6dd0c8`). Four hues moved: the three mandated (fabs,
neoclouds, glass) plus **networking `#14b8a6`→`#0d9488`** as the "judge the
rest" call — the one remaining acid teal that washed out on the near-white
canvas. Photonics/memory/materials/robotics/hyperscalers kept (enough weight
already); accelerators kept (semantic). The regen churned **priority scores**,
not `vault.json` (the scorer's recency weighting recomputes vs today's date);
tier counts unchanged, so nothing re-tiered. Verified hues flow to bands,
cross-section bars, and vault graph nodes._

### ☑ U4 · Op-H — per-page polish (2026-07-13)

> Read CLAUDE.md + docs/EXECUTION.md Phase 6. Across all 5 pages: replace
> `var(--serif)` → `var(--display)` (~29 uses) adding weight-700 /
> -0.02em tracking at display sites; pill-ify toggles/buttons/filter chips
> (`--r-chip`, active state = brand-gradient fill + white text); at most ONE
> gradient text moment per page (`color: var(--brand-ink)` fallback BEFORE the
> background-clip declarations); sweep page-local warm literals (grep
> `#faf7f2|#fffdf9|#e6e0d4|#f2ede4|#f6f1e8|rgba(60, 48, 30`); desk.html dark
> surfaces (cross-section, NVIDIA hub) restyled on `var(--stage)` with a
> brand-gradient hairline top edge; muted text on stage ≥ 4.5:1 (use
> `#9aa1ac`+). Full interactive click-through per page (map filter, watchlist
> sort, evidence + brain drill-downs, memo scrollspy, vault graph drag, ledger
> filters). Commit as `feat: unpacked page pass`.
>
> **Then run:** `/loop open each page (index, desk, memo?ticker=SIVE, vault,
> vault?view=graph, performance) on the local server; check console clean, no
> warm-color remnants, no 375px overflow, reduced-motion inert; fix what
> fails; stop when a full pass is clean`

_Shipped 2026-07-13 (`dfe9fd5`). All 23 page `var(--serif)` → `var(--display)`;
weight 700 / -0.02em at display sites. ONE gradient-text moment on each
front-of-house page (index + desk hero headlines) via a `.grad` span with a
solid `--brand-ink` fallback before the background-clip declarations — memo /
vault / performance kept solid ink (reading surfaces). Pills: `.aie-chip`
active state moved to the brand gradient in `shared/theme.css` (shared, so every
filter toggle inherits it); desk `.vt-btn`, tier/`.filter-chip` **neutral**
fallback, and the capsule pill all go brand-gradient — **category filter chips
keep their `--chip-accent` data-viz color** (rule #4). desk dark surfaces
(NVIDIA hub + cross-section) rebuilt on `var(--stage)` with a 2px
brand-gradient hairline top edge; the two sub-4.5:1 stage greys lifted to
`#9aa1ac`. Warm remnants beyond the grep list also swept: the capsule
frosted-paper (`rgba(255,253,249…)` / `rgba(74,60,40…)`) → cool white, the amber
`.wl-hint` → `--brand-ink`, and every warm off-white / blueprint-navy literal in
the **vault graph** overlays + canvas draw code → cool slate/white. Verified on
the local server across all 6 surfaces (console clean, no warm remnants, no
375px overflow, display type + gradient active states + stage hairlines, and
map filter / view toggle / watchlist sort / evidence+brain drill-downs / vault
type filter / graph render all working); 101 unit tests green. reduced-motion
gating untouched, so preserved by construction._

### ☑ U5 · S5-H — Focus card ("the headline") (2026-07-14)

> Read CLAUDE.md + docs/EXECUTION.md Phase 6. Every financial terminal leads
> with a headline; this site leads with raw tweets. (1) `ingest/store/
> verdicts.json` gains `meta.focus = { headline, dek, updatedAt, tickers[] }`
> — seed it from the 2026-07-12 review (the washout-resolves / CEO-insider-
> buying story). (2) `.claude/skills/weekly-review/SKILL.md` gains a step:
> author the week's headline — short, declarative, desk voice, one story only.
> (3) `index.html`: full-width Focus card directly under the masthead, before
> the standfirst — brand-gradient hairline, mono `FOCUS · <date>` eyebrow,
> display-type headline (~34px), one-line dek, ticker chips via
> `AIE.linkForTicker`. (4) `desk.html` hero: the Focus headline replaces
> "Latest signal" as the lead card; the raw latest-tweet card demotes to a
> compact secondary slot linking into Chapter 03. Graceful absence: no
> `meta.focus` → both surfaces render exactly as today. Regen; verify both
> surfaces + the absent-key empty state in a sandbox copy. Commit as
> `feat: weekly focus headline card`.

_Shipped 2026-07-14. Seeded `meta.focus` from the SIVE insider-buying /
Nvidia-denial story in the 2026-07-12 verdict (tickers SIVE, LITE — the
channel-check thread ties both). Since `verdicts.json` already passes
through whole in `generate_data_js.py`, no pipeline code changed. One
addition beyond the prompt's letter: the renderer (`AIE.renderFocusCard`)
and its look (`.aie-focus` family) landed in `shared/common.js` /
`shared/theme.css` rather than being written twice — hard rule #3 requires
anything used by 2+ pages to live in shared, and this component is used by
both index.html and desk.html identically (pages only add their own
margin/placement CSS around it). `desk.html`'s demoted "Latest signal" slot
keeps `makeThesisCard(..., {compact:true})` and wraps its eyebrow in a link
to `#chapter-thesis`. Verified: both pages render live, the `meta.focus`
absent-state collapses cleanly with no layout gap (tested in-browser via
`AIE.renderFocusCard(mount, null)`), 375px mobile clean on both pages, no
console errors, 106 unit tests green._

### ✅ U6 · Op-M — category icons in data

> Read CLAUDE.md + docs/EXECUTION.md Phase 6. (1) In `ingest/store/base.json`
> add 12 hand-drawn line-art icons as inner-SVG strings (no `<svg>` wrapper):
> `categories[<id>].icon` for all 10 + `center.icon` + `unsortedCategory.icon`
> — viewBox `0 0 24 24`, `fill="none" stroke="currentColor" stroke-width="1.5"
> stroke-linecap="round" stroke-linejoin="round"`; motifs: photonics=light
> beam, memory=stacked chips, fabs=wafer, neoclouds=cloud+rack,
> materials=layered substrate, networking=switch fabric, glass=pane,
> robotics=arm, accelerators=GPU die, hyperscalers=server towers. (2) In
> `ingest/generate_data_js.py` add `_validate_icon(markup)` called from
> `build_data()`: allowlist elements path|circle|line|rect|polyline|ellipse
> and geometry/stroke attributes only; reject `on*=`, `script`, `href`,
> `<svg` → ValueError. (3) Tests in `ingest/tests/test_generate.py`: valid
> icon passes, `onload=` rejected, `<script>` rejected, missing icon
> tolerated (optional field). (4) `shared/common.js`: `AIE.iconSVG(markup,
> color, size)` — builds the `<svg viewBox="0 0 24 24" aria-hidden="true">`
> wrapper via innerHTML of the validated store markup, tinted through
> currentColor. (5) Wire into `makeLayerBand()` so pipeline bands + hub show
> icons immediately. Regen; grep data.js for `<path`. Commit as
> `feat: category icons in base.json`.

### ☐ U7 · F5-H — Chapter 01 restructure (hardest; desk.html only)

> Read CLAUDE.md + docs/EXECUTION.md Phase 6. In `desk.html`: (1) split
> `makeCard()` into `makeTile(ticker)` — compact ~90–110px: `AIE.iconSVG`
> category icon, mono ticker, one-line company, tier + stance micro-badges,
> `sparkSVG(t, 56, 20)` — and `makeCardDetail(ticker)` (the existing
> badges/prose/verdict markup, unchanged). (2) `#cardGrid` →
> `repeat(auto-fill, minmax(168px, 1fr))`, tiles on `--r-tile` (49 cards →
> ~7 tile rows). (3) Expand-in-place: clicking a tile inserts a
> `grid-column: 1 / -1` detail row right after the clicked tile's row,
> animated with `AIE.setDrilldownOpen` (NOT grid-template-rows 0fr→1fr — the
> documented v6 bug); one open at a time; Esc/re-click closes;
> `aria-expanded` + Enter/Space keyboard (mirror the `appendLayerBand`
> pattern). (4) Chapter reorder to cut scroll: head → map → priority strip
> merged into the holdings ledger row as a horizontal chip scroller → tile
> grid → glossary behind a drill-down. `renderCards()` tier/radar/filter
> logic stays verbatim; `revealify` still staggers tiles. (5) Animate
> `makeFlowArrow()` dashes with the U2 `aie-flow` keyframes. Commit as
> `feat: map tiles + expand-in-place`.
>
> **Then run:** `/loop on desk.html: click every layer band + cross bar
> (filter scopes tiles), toggle radar (counts correct), expand/collapse tiles
> incl. after a filter change and a window resize, keyboard Enter/Esc, 375px
> + 768px, reduced-motion; fix regressions; stop when a full checklist pass
> is clean twice in a row`

### ☐ U8 · S5-M — docs + alias cleanup

> Update CLAUDE.md (Design system section → Unpacked tokens; rule #4's
> gradient-border sentence — the border is now brand chrome, category colors
> stay data; Map rendering section → tiles + expand-in-place), rewrite
> docs/DESIGN.md's token reference, add a ROADMAP.md status entry. Delete the
> `--serif` alias from shared/theme.css — `grep -rn 'var(--serif)' *.html
> shared/` must return nothing. Tick the Phase 6 boxes. Commit as
> `docs: unpacked design system current`.

---

_When all boxes are ticked: final pass — README screenshots, GitHub Pages check
(case-sensitive paths!), and a `/weekly-review` run to exercise the whole loop._
