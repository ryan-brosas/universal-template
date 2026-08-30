<!-- capsule-v2 -->
# Ingest provenance pinning — how does a note pin its target so a later session re-finds the exact code without re-cloning?

**Source:** user-authored ingest notes over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/notes`; Codebase Memory `inspo-notes`. **Question:** What must a capture note pin — path, license, graph identity, symbol ranges, tests — so retrieval works months later against an indexed graph instead of a fresh clone?

## Provenance header + evidence pins
**Path/Symbol:** provenance banner = note line 3 (`growchief-cdpDetectionPass.md:3`, `browser-harness-get_ws_url.md:3`, `browser-use-BrowserSession.connect.md:3`); evidence pins = section 6 of every note.
**Signature:** `Provenance: <absolute repo path>, <license>, indexed <project> (<N> nodes / <M> edges, <mode>, <date>). Graph: <symbol> at <file>:<lines>. Tests: <test-path>.`
**Data Shape:** absolute filesystem path (never a bare repo name), SPDX license name, the codebase-memory project name + size/mode/date snapshot, the pinned symbol with file+line range, and where the direct tests live.

### Decisive source
```markdown
Provenance: `/mnt/hdd/utopia/inspo/growchief`, AGPL-3.0, indexed `growchief`
(2558 nodes / 7075 edges). `shared/server/bots/cdp.detection.pass.ts:3-33`.
**Inspect only — do not copy.**
```
(`notes/growchief-cdpDetectionPass.md:3-4`)

Compare `browser-harness-get_ws_url.md:3`:
```markdown
Provenance: `/mnt/hdd/utopia/inspo/browser-harness`, MIT, indexed project
`browser-harness` (2641 nodes / 4650 edges, fast, 2026-08-21).
Graph: `get_ws_url` at `src/browser_harness/daemon.py:211-289`.
Tests: `tests/unit/test_daemon.py`.
```

**Flow:** clone/index once → stamp every note with absolute path + license + graph project + node/edge counts + symbol@lines + test path → later sessions go straight to `search_graph`/`get_code_snippet` on the named project instead of re-cloning → re-run `index_status` before trusting node/edge counts, because they are a point-in-time snapshot.
**Invariant:** a note without an absolute path or without line-range pins is not done; counts are explicitly historical (2641 vs the live 2669 for browser-harness) and must be revalidated via `index_status --verbose`, never trusted as current state.
**Probe:** deterministic probe: `grep -c 'indexed' notes/browser-harness-get_ws_url.md` ≥ 1 AND `grep -cE ':[0-9]+-[0-9]+' notes/browser-harness-get_ws_url.md` = 2 (range pins exist).

> **ERRATUM (docs-knowledge pass 9 probe-liveness audit, 2026-08-24):** the original second assertion (`≥ 5`) was mis-derived at authoring ([DONE:324]-class defect, caught by first full byte-exact execution of this leaf's probes) and is replaced by assertions matching the note's actual pin grammar — the note carries TWO range pins (`src/browser_harness/daemon.py:211-289` in provenance header AND evidence section) plus NINE single-line pins. Repaired probe (both green live): `grep -cE ':[0-9]+-[0-9]+' …` = **2** AND `grep -cF 'daemon.py:76' …` = **1** (representative of nine single-line pins: daemon.py `:76/:98/:115/:190/:358`, helpers.py `:53/:328/:137`, admin.py `:340` — each grep -cF verified = 1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "inspo-notes", pattern: "Provenance", limit: 10 });
// resolves inspo-notes.<note> Module nodes - provenance banner @ note line 3
// (EXECUTED 2026-08-24 docs-knowledge pass 9: 4 result; search_graph query/name_pattern forms return 0
//  on this doc-shaped graph — Section nodes are tokenless/filtered; search_code is the working primitive)
```

## Verdict
Adopt the provenance-header format verbatim for any new capture note; adapt the graph-stat fields to whatever the indexer exposes; omit re-cloning behavior entirely — the whole point of the pin is that the indexed project is the durable access path.
