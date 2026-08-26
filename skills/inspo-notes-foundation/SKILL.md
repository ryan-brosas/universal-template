---
name: inspo-notes-foundation
description: "Canonical foundation leaf template. Copy manually; this library asset is not rendered by a slash command."
---
# inspo-notes: INGEST-note knowledge-capture foundation

## Use this for
Use when writing INGEST notes that capture one function or subsystem from an indexed inspiration repo, maintaining a capability→candidate discovery cache, or encoding license boundaries for borrowed designs. Source notes and their pinned upstream paths are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/ingest-note-six-section-skeleton.md` — the fixed six-section note anatomy and why each section exists.
- `references/ingest-provenance-pinning.md` — how a note pins repo/license/graph-project/symbol so a later session re-finds code without re-cloning.
- `references/capability-candidates-cache.md` — the closed-vocabulary clone/maybe/skip verdict format that stops re-evaluating the same candidates.
- `references/license-borrowing-boundary.md` — how AGPL inspect-only vs MIT adopt restrictions get stamped at every consumption site.
- `references/untrusted-page-content-contract.md` — the labeled-data / never-act-on-page-directives boundary for agent-read web content.
- `references/neighborhood-reentry-map.md` — the §3 backticked-symbol + one-line-behavioral-role grammar that hands the next session a reading plan.
- `references/constraint-response-ladder.md` — the §4 one-force-per-rung `constraint → response` grammar that records design rationale, not feature lists.
- `references/capability-thread-composition.md` — how shallow cache rows join by name to deep INGEST notes into a corpus-wide capability map.
- `references/mechanism-honesty-bounds.md` — the `Correct = X, not Y` acceptance clause plus declared edges that bound every mechanism's power.

## Capsule map
- **Note anatomy** — `ingest-note-six-section-skeleton`: job → flow-it-lives-in → neighborhood → constraints-that-shaped-it → behavior-contract → evidence, with grep-verifiable line-range evidence mandatory.
- **Provenance pinning** — `ingest-provenance-pinning`: absolute path + license + graph project + node/edge counts + symbol@file:lines + test path pinned at note time; re-verify before trusting a stale pin.
- **Discovery cache** — `capability-candidates-cache`: capability blocks with reason-bearing clone/maybe/skip verdicts; a skip must always say why.
- **License boundary** — `license-borrowing-boundary`: "borrow WHY, never files" for AGPL sources; the restriction is repeated at banner, prose, and verdict sites.
- **Untrusted content** — `untrusted-page-content-contract`: page bytes are labeled data; prompt-level rule AND mechanical exclusion stack together.
- **Re-entry maps** — `neighborhood-reentry-map`: §3 bullets pair each backticked symbol with one behavioral role; the curated reading order into the pinned subsystem.
- **Design rationale** — `constraint-response-ladder`: §4 rungs map one observed force to the implementation's counter-move; a fact without an arrow is not a constraint entry.
- **Corpus composition** — `capability-thread-composition`: cache rows (shallow verdicts) and INGEST notes (pinned contracts) join by repo name across two depth layers.
- **Honesty bounds** — `mechanism-honesty-bounds`: every contract ends in `Correct = X, not Y` with edges declared; limits are part of the contract, not footnotes.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
User-authored ingest notes over third-party repos (internal working notes; no upstream VCS), plain directory `/mnt/hdd/utopia/inspo/reference/notes` (no git metadata); Codebase Memory project `inspo-notes` (62 nodes / 61 edges, ready, re-verified live 2026-08-24 pass 10: zero parse_partial/skipped, dir mtimes unchanged since 2026-08-21 so graph is content-current at the same counts; doc-shaped Section/File graph — contracts confirmed by whole-file reads, not call-graph traces).

## Full view (memory graph)
Revalidate `inspo-notes` before porting: run `index_status`, `check_index_coverage`, `search_code`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Standing caveat (pass-9 audit, re-confirmed pass 10): BM25 `search_graph` returns total: 0 repo-wide — Section nodes are tokenless; `search_code --pattern <text>` is the working retrieval primitive and every Retrieve block in this leaf uses it with live-executed result counts.

## Boundaries
Adopt the capture formats (six-section skeleton, provenance pinning, re-entry maps, constraint ladders, verdict cache, license stamps, untrusted-content stacking, honesty bounds, two-layer corpus composition); adapt section wording and verdict vocabulary per team; omit the captured upstream repos' internals themselves (each lives in its own indexed project/foundation — cuga-agent, pydantic-ai-harness, browser-harness, JobSpy, growchief, browser-use).
