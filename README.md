# AI Infrastructure Explorer

A one-page field guide to the AI hardware supply chain: who sits in which layer,
what constrains each layer right now, the storylines that explain the tape, and
a dated, sourced log of what has changed.

Open `index.html` by double-clicking it. No server, no build, no dependencies.

## What it is

Three views over one dataset:

- **Map.** Eleven layers from the buyers of compute at the top (labs,
  hyperscalers, neoclouds) down through accelerators, systems, networking,
  optics, memory, foundry, equipment, materials and power. Each layer states its
  current constraint and what to watch. Click a company for its dossier: what it
  does, why it matters in the chain, the bull and bear case, what would change
  the picture, and every sourced fact on file.
- **Narratives.** The nine storylines (the memory squeeze, the laser shortage,
  who is paying for the buildout, and so on), each with the case, the counter,
  and the signposts that would settle it.
- **Timeline.** Dated developments, newest first, every one with a source link.
  Filter by narrative or search a ticker. Future dates show as upcoming.

Every company and narrative has a link (`index.html#c/NVDA`,
`index.html#n/memory-squeeze`) so a note can point at it.

## Files

```
index.html   the page
style.css    the styles
app.js       the rendering and routing
data.js      THE PRODUCT: layers, companies, narratives, developments
check.py     validates data.js (run before committing)
CLAUDE.md    how to maintain it
```

That is the whole thing.

## How to update it

`data.js` is a hand-edited file. It is `window.DATA = { ... }` around a JSON
object, so keep it valid JSON: double quotes, no trailing commas.

- **Something happened.** Add an entry to `developments` with an ISO `date`, a
  one-line `title`, a two-sentence `summary`, the `companies` it touches, the
  `narratives` it bears on, a `sourceType` (`filing`, `company`, `press`,
  `analyst`) and the `source` URL. If it changes a company's picture, update
  that company's `bull`, `bear` or `watch` text and add the number to its
  `facts`.
- **A new company matters.** Add it to `companies` with its `layer`. Include it
  only if it sits on a constraint; the map is a guide, not a census.
- **A storyline changes shape.** Edit the narrative's `status`
  (`building`, `consensus`, `contested`, `fading`), its `case` or `counter`.
- **A layer's constraint moves.** Edit `constraint` and `watch` on the layer.

Then run:

```bash
python3 check.py
```

It parses the file, checks every reference resolves, that every fact and
development has a source URL, and prints an inventory. Bump `meta.updated`.

Rules: no number without a source, no development without a date, no company
without a reason to be on the map.

## What it deliberately does not do

No live prices, no scoring, no tiers, no bots, no scrapers, no agents, no
database. Prices are one click away in any broker and go stale the moment they
are stored; scoring posting frequency measures the poster, not the chain. The
value here is the curated, sourced structure, and that is maintained by reading
and writing, not by pipelines.
