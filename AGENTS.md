# AGENTS.md — AI Infrastructure Explorer

**Read [CLAUDE.md](CLAUDE.md) — it is the single agent-facing engineering
guide for this repo.** This file exists only so tools that look for an
AGENTS.md find the pointer.

Quick orientation (details and hard rules all live in CLAUDE.md):

- Multi-page offline app: `desk.html` (the working desk — map, watchlist,
  evidence, synthesis), `index.html` (Coverage — memo ledger), `memo.html`,
  `vault.html` (list + graph views), `performance.html`, `design.html`.
  All render from the generated `data.js`; shared code in `shared/`.
- Backend: stdlib Python in `ingest/` writing `ingest/store/*.json`, funneled
  through `ingest/generate_data_js.py` (the only producer of `data.js`).
- Weekly workflow: the `.claude/skills/weekly-review` skill (run in a Claude
  Code session). Never hand-edit `data.js`; secrets live only in gitignored
  `ingest/.env`.

An earlier version of this file described the retired v6 single-page app and
a Codex-based process — that content was removed 18 Jul 2026 because it had
drifted from reality. Git history has it if ever needed.
