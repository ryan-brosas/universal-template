<!-- capsule-v2 -->
# Selective injection kill switch — why does PI_MEMORY_NO_SEARCH only work in per-turn mode?

**Source:** pi-memory (MIT) `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory` (full mode 380n/941e @2026-08-22T23:46:09Z). **Question:** How do you let an eval (or user) turn OFF retrieval injection — and what snapshot-mode interaction silently defeats such a switch?

## Selective injection kill switch
**Path/Symbol:** `index.ts` default export → `pi.on("before_agent_start")` (:1540–1583), kill-switch branch :1547; consumer `searchRelevantMemories` (:1193–1237).
**Signature:** `const skipSearch = process.env.PI_MEMORY_NO_SEARCH === "1"; const searchResults = skipSearch ? "" : await searchRelevantMemories(event.prompt ?? "");`
**Data Shape:** env flag read per turn, exact string `"1"`; empty-string search result ⇒ context built without the search section. `searchRelevantMemories` itself is fail-open: no qmd / blank prompt / control-char-only query / missing collection / 3s race timeout / any throw ⇒ `""`.

### Decisive source
```ts
// index.ts:1545-1549 — the guard lives INSIDE the mode === "per-turn" branch
if (mode === "per-turn") {
  const skipSearch = process.env.PI_MEMORY_NO_SEARCH === "1";
  const searchResults = skipSearch ? "" : await searchRelevantMemories(event.prompt ?? "");
  memoryContext = buildMemoryContext(searchResults);
} else {
  // stable-snapshot branch: NO skipSearch check — the cached snapshot is served as-is
```

**Flow:** per-turn mode rebuilds context each turn and honors the kill switch; stable mode (`PI_MEMORY_SNAPSHOT=stable`, the default) serves the byte-stable cached snapshot where the flag is never consulted. The e2e/eval harnesses rely on the per-turn path: `test/e2e.ts:testSelectiveInjection` (:452–490) proves a related prompt surfaces a freshly written memory WITHOUT instructing the model to search (soft-checking that `memory_search` was not called); `test/eval-recall.ts` Mode B sets the flag to isolate injection from baseline.
**Invariant:** an injection kill switch is only meaningful in the regime that re-resolves retrieval per turn. If you port the stable snapshot, your kill switch must either force a per-turn rebuild or be documented as snapshot-mode-dependent — otherwise arm B of any A/B eval measures the same injected bytes as arm A and the delta is fake.
**Probe:** `test/e2e.ts:testSelectiveInjection` (:452–490) — live tier, runner-blocked here (needs pi+qmd); unit tier for the hook shape EXECUTED pass 1 (`bun test` 182/182). Flag semantics pinned by source :1547.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "before_agent_start PI_MEMORY_NO_SEARCH searchRelevantMemories getSnapshotMode", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the env kill switch pattern with its fail-open search wrapper for any retrieval-injection pipeline. Adapt the trigger (env vs config) to your host. Omit nothing on the invariant: check which serving mode bypasses the switch before trusting it in experiments.
---
