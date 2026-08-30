<!-- capsule-v2 -->
# tryReadFile null contract — where does "missing file" become a decision instead of an exception?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** A porter must decide what a failed memory-file read means — crash, log-and-skip, or treated-as-absent — because every downstream behavior (sentinel opt-in, placeholder seeding, state loading) keys off that single answer.

## Total reader (`tryReadFile`)
**Path/Symbol:** `pi-memory.ts:tryReadFile` (:75–81).
**Signature:** `async function tryReadFile(filePath: string): Promise<string | null>`.
**Data Shape:** in: absolute path; out: full UTF-8 text, or `null` for EVERY failure class (ENOENT, EISDIR, EACCES, …). No error typing, no logging, no rethrow.

### Decisive source
```ts
async function tryReadFile(filePath: string): Promise<string | null> {
  try {
    return await fs.readFile(filePath, "utf-8");
  } catch {
    return null;
  }
}
```

**Flow:** readFile → success returns text verbatim → ANY throw collapses to `null` → callers branch on nulliness alone (`if (wsIndex)`, `if (!(await tryReadFile(fp)))`, `stateRaw?.trim() ?? ""`).
**Invariant:** Absence-is-null is the extension's ONLY error boundary for reads. Because the sentinel check (`index.md` at :253–254) and init's create-if-absent seeding both use this same primitive, a port that "improves" it into a throwing or logging reader silently changes three subsystems at once: workspace opt-in would hard-fail outside repos, init would lose idempotence, and interrupt-state loading would crash sessions. Distinguishing ENOENT from EACCES is deliberately NOT modeled — unreadable means absent, which also makes permission problems invisible by design (accept that or widen the contract consciously).
**Probe:** No upstream test suite exists (standing block). Pass-4 executed probe (inline `node -e` replicating :75–81 byte-for-byte on Node v26.7.0, no helper scripts created): missing path ⇒ `null` GREEN; real file ⇒ contents starting `import type` GREEN; directory path (EISDIR swallowed) ⇒ `null` GREEN. Graph evidence: `search_graph "tryReadFile"` rank-1 hit at :75–81; `trace_path inbound` reports callers_total=3 LSP-resolved edges (module/handler/loadLayer) while source-visible call sites are more numerous (sentinel :253, state :262, loadLayer file reads, init guards) — the graph undercounts closures; source wins.
**Adversarial retrieval note:** unlike most seams in this repo, generic phrasing `"missing file error handling absent"` still ranks this function #1 (-12.34) — the seam is robustly retrievable even without exact vocabulary; no RED miss was observed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory-extension", query: "tryReadFile", limit: 5, fields: ["lines"] });
```
(Executed pass 4: single result `pi-memory.tryReadFile Function pi-memory.ts 75-81`; `check_index_coverage("pi-memory.ts")` = `no_recorded_issue`, freshness `metadata_match`.)

## Verdict
Adopt one total reader whose failure mode is "absent", and route EVERY optional-file decision through it so absence semantics live in exactly one place. Adapt by widening the null contract ONLY if the host needs to distinguish not-there from cannot-read (then thread a typed result through sentinel + init + state call sites together). Omit nothing — deleting the choke point scatters try/catch across consumers. Coverage caveat: pinned by executed probe + graph retrieves; no upstream suite.
