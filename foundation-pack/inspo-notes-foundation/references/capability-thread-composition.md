<!-- capsule-v2 -->
# Capability-thread composition — how do INGEST notes + candidates cache compose into one corpus-wide capability map?

**Source:** user-authored ingest notes over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/notes`; Codebase Memory `inspo-notes`. **Question:** How is the note corpus organized so separate single-function captures still answer a product-level capability question ("how do we delegate to a real browser?") without any single file containing it?

## Two-layer corpus: cache rows → deep notes
**Path/Symbol:** `candidates.md:3` (capability block 1, S3 sidecar), `candidates.md:8` (block 2, policy-governed loop), `candidates.md:13` (block 3, CDP-first lead collection); thread members = `pydantic-ai-harness-BrowserUse.md` + `browser-use-BrowserSession.connect.md` + `browser-harness-get_ws_url.md` (+ growchief/jobspy as boundary analogs).
**Signature:** cache row: `- <owner>/<repo> | use case: <why relevant> | verdict: <clone|maybe|skip> (<reason>) | link: <url>`; deep note: `# INGEST — <repo> · target: <symbol>`; the join key is the repo identity — a `verdict: clone` row predicts a same-named deep note exists or should.
**Data Shape:** three capabilities over seven files; the browser-delegation capability threads FOUR notes at different depths (host-tool contract pah / session connect bu / daemon attach bh / detection pass gc); cross-references are by NAME not link — "already cloned+indexed; ingest from graph" in candidates.md points at the indexed graph projects, and notes never hyperlink each other.

### Decisive source
```markdown
## Capability: S3 sidecar — Pydantic AI host delegating to a Browser Use specialist
over existing Chrome CDP (domain-limited, structured output, behind an adapter)
- pydantic/pydantic-ai-harness | use case: demonstrates the authoritative BrowserUse
  capability ... | verdict: clone | ...
```
(`notes/candidates.md:3-4`)

joined across files by name:
```markdown
# INGEST — pydantic-ai-harness  ·  target: BrowserUse capability (`browse_web`)
```
(`notes/pydantic-ai-harness-BrowserUse.md:1`, plus `# INGEST — browser-use/browser-use` and
`# INGEST — browser-use/browser-harness` siblings; grep -il 'browser-harness' hits exactly
{its own note, candidates.md})

**Flow:** discovery starts in candidates.md (shallow, verdict-per-repo) → a `clone` verdict authorizes deep capture → the resulting INGEST note pins symbol-level provenance into its own file while the cache row stays unchanged → later sessions answer a capability question by reading the cache block for orientation then descending into each threaded note for the porting-grade detail → new candidates land as cache rows first; only cloned ones earn notes.
**Invariant:** the two layers stay consistent through the name join — a deep note without any candidates row means an off-cache capture (acceptable, but the row should be backfilled), and a `clone` verdict with no note means claimed-but-not-captured. Depth is deliberately asymmetric inside one capability (a host-side tool contract and a websocket-resolution edge case are BOTH legitimate captures) because the unit of capture is "one function's contract", not "one repo".
**Probe:** deterministic probes (notes dir): `grep -c '^## Capability:' notes/candidates.md` = **3**; `grep -c '# INGEST' notes/candidates.md` = **0** (cache holds zero deep notes — layer separation); `grep -il 'CDP' *.md | wc -l` = **6** (six of seven files carry the browser-delegation thread vocabulary); `grep -c '# INGEST' notes/pydantic-ai-harness-BrowserUse.md` = **1**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "inspo-notes", pattern: "Capability: policy-governed", limit: 5 });
// EXECUTED 2026-08-24 inspo-notes pass 10: results: 1 — Section node
// inspo-notes.candidates.Capability:-policy-governed-agent-execution-loop-(propose-→-approve-→...)
// @ candidates.md:8-9, i.e. the graph itself indexes capability blocks as retrievable units;
// the second composition probe pattern:"not a lead CSV" resolves the growchief flow Section
// @ cdp.detection.pass note lines 8-9 (capability outcome sentence), results: 1.
```

## Verdict
Adopt the cache-rows-shallow + deep-notes-pinned two-layer corpus shape for any growing capture library; adapt the verdict vocabulary to your team's rules but keep the name-based join so layers stay greppable without links; omit per-note back-links and indexes — the corpus stays flat on purpose, because the retrieval path is grep/graph on names, not navigation.
