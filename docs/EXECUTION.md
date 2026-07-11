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
| 3 | Knowledge Vault (store+sync, index/page views, graph, authoring loop) | P11–P14 | 🚧 P11–P13 done |
| 4 | Cross-linking everywhere | P15 | ☐ |
| 5 | Performance hooks (calls.json + minimal page) | P16 | ☐ |

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

### ☐ P14 · Op-M — vault authoring loop + first enrichment

> Create `.claude/skills/vault-note/SKILL.md` — `/vault-note SLUG` enriches one
> vault page's `note` (plain prose, 1–3 paragraphs, dense with `[[wikilinks]]` to
> related pages; never touch `auto.*`), stamps noteUpdatedAt, regens data.js.
> Add a weekly-review step: enrich pages touched by tier or stance changes.
> Then do the first enrichment pass: all 10 theme pages + top 5 ticker pages.
> Commit as `feat: vault authoring skill + first enrichment pass`.

## Phase 4 — Cross-linking

### ☐ P15 · S5-H — link everything

> Upgrade `AIE.linkForTicker(sym)` in common.js: memo exists → memo.html; else
> vault page exists → vault.html?page=…; else desk.html#watchlist. Apply it to
> every ticker chip site-wide: thesis cards (Evidence + memo appendix), brain
> digest ticker lists, watchlist rows (row click), map layer detail panels, vault
> side panel/pages. Watchlist gains a "Note" column (memo link + date) for
> covered names. Coverage ledger gains theme (category) filter chips. Commit as
> `feat: site-wide ticker cross-linking`.

## Phase 5 — Performance hooks

### ☐ P16 · S5-H — calls.json + minimal performance page

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

_When all boxes are ticked: final pass — README screenshots, GitHub Pages check
(case-sensitive paths!), and a `/weekly-review` run to exercise the whole loop._
