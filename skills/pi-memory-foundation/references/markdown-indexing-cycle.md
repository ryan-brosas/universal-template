<!-- capsule-v2 -->
# Markdown-syntax indexing cycle — why must a write be followed by an explicit index refresh before keyword search can find #tags and [[wiki-links]]?

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** After persisting memory that uses markdown organization syntax (`#tag`, `[[link]]`), what has to happen before keyword search reliably retrieves it — and does the search backend have to preserve that syntax rather than strip it?

## Markdown-syntax indexing cycle
**Path/Symbol:** `test/e2e.ts:testTagsInSearch` (:492–519), `runQmdUpdate` (:275–282). Source side: `memory_write` long-term append (cited in write-echo-preview.md) → files on disk; retrieval via `runTool("memory_search", …)` over `index.ts:runQmdSearch` keyword mode (:1291–1325, cited in qmd-search.md).
**Signature:** `testTagsInSearch(): Promise<void>`; `runQmdUpdate(): boolean`; tool params `{ query: string, mode: "keyword" }`.
**Data Shape:** planted entry: `#preference [[editor-choice]] Always use vim for editing (ref: TAG_<epoch>)`. Two probes: query by the tag text (`"#preference"`) and by the wiki-link target text (`"editor-choice"`); both must surface the entry (assertion accepts the unique token OR the distinctive word "vim").

### Decisive source
```ts
// testTagsInSearch (492-519): syntax tokens are search KEYS, not decoration
await runTool("memory_write", {
	target: "long_term",
	content: `#preference [[editor-choice]] Always use vim for editing (ref: ${token}).`,
});
const updated = runQmdUpdate();          // explicit index refresh — NOT optional
assert(updated, "qmd update failed");

const tagResult = await runTool("memory_search", { query: "#preference", mode: "keyword" });
assert(tagText.includes(token) || tagText.toLowerCase().includes("vim"), …);
const linkResult = await runTool("memory_search", { query: "editor-choice", mode: "keyword" });
assert(linkText.includes(token) || linkText.toLowerCase().includes("vim"), …);

// runQmdUpdate (275-282): best-effort sync shell-out with boolean verdict
execSync("qmd update", { stdio: "ignore", timeout: 30_000 }); return true;  // catch → false
```

**Flow:** (1) Start clean: delete MEMORY.md if present. (2) Write one tagged/wiki-linked entry through the production tool. (3) Run `qmd update` explicitly and assert it succeeded — without this step the keyword index may not include the new file yet. (4) Keyword-search by tag text and by wiki-link target; each must return the planted entry. (5) The scenario composes two planes of the in-process harness: mutation (`runTool("memory_write")`) and retrieval (`runTool("memory_search")`), so the whole loop runs without an agent turn.

**Invariant:** markdown syntax must survive into the indexed text (search treats `#tag`/`[[link]]` as ordinary searchable tokens — no stripping layer between write and index); freshly written content is only guaranteed searchable after a successful external index update; update failure is a hard assert inside this scenario even though `runQmdUpdate` itself returns false instead of throwing.

**Probe:** Runner-blocked here (needs `qmd` + collection + `pi` env per Gate-5 rules; recorded in verification.md). Deterministic substitutes EXECUTED pass 4: direct read of :492–519 confirms both assertions and the mandatory `runQmdUpdate()` gate; graph trace shows `runQmdUpdate` has exactly 3 callers (both qmd-gated scenarios + setup); citation census shows zero prior references to `testTagsInSearch`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "testTagsInSearch runQmdUpdate memory_search keyword", limit: 10, fields: ["signature", "name", "file"] });
```
Pass-4 retrieval: `get_code_snippet(pi-memory.test.e2e.runQmdUpdate)` returned the excerpt above; `get_code_snippet(pi-memory.test.e2e.main)` shows this scenario is qmd-gated (tier 2, skipped without backend); `check_index_coverage(test/e2e.ts)` = `no_recorded_issue`.

## Verdict
Adopt the write → EXPLICIT index-refresh → dual-syntax-query verification cycle whenever a port adds an external search index over flat files, and adopt the rule that organization syntax stays plain text end-to-end. Adapt the refresh command and the tag/link grammar to the host. Omit the soft no-tool-call event check from testSelectiveInjection (:481–489) unless the host can observe agent events — pi-memory itself leaves it advisory.
