<!-- capsule-v2 -->
# codebase_search tool plane — how does the RAG search result reach BOTH the UI and the model, and who owns the gates?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** When porting a semantic-code-search tool over an existing index service, which layer throws, which layer soft-fails, and why does one search produce two different renderings?

## CodebaseSearchTool.execute — three-layer gate ladder + dual emission
**Path/Symbol:** `src/core/tools/CodebaseSearchTool.ts:CodebaseSearchTool.execute` (21–129); knobs from `src/services/code-index/config-manager.ts` (`currentSearchMinScore` :525–535, `currentSearchMaxResults` :541–543); soft/loud split at `src/services/code-index/manager.ts:searchIndex` (335–341) vs `src/services/code-index/search-service.ts:searchIndex` (27–64).
**Signature:** `async execute(params: { query: string; path?: string }, task: Task, callbacks: ToolCallbacks): Promise<void>`.
**Data Shape:** input = free-text query + optional directory prefix; output = ONE `say("codebase_search_result", JSON)` UI event plus ONE plain-text `pushToolResult`; failures are strings via handleError/toolDenied, never throws.

### Decisive source
```ts
if (!manager.isFeatureEnabled) {
    throw new Error("Code Indexing is disabled in the settings.")
}
if (!manager.isFeatureConfigured) {
    throw new Error("Code Indexing is not configured (Missing OpenAI Key or Qdrant URL).")
}
const searchResults: VectorStoreSearchResult[] = await manager.searchIndex(query, directoryPrefix)
// ...
searchResults.forEach((result) => {
    if (!result.payload) return                    // silently dropped
    if (!("filePath" in result.payload)) return    // silently dropped
    const relativePath = vscode.workspace.asRelativePath(result.payload.filePath, false)
    jsonResult.results.push({ filePath: relativePath, score: result.score,
        startLine: result.payload.startLine, endLine: result.payload.endLine,
        codeChunk: result.payload.codeChunk.trim() })
})
const payload = { tool: "codebaseSearch", content: jsonResult }
await task.say("codebase_search_result", JSON.stringify(payload))
// ...then a separate plain-text rendering for pushToolResult
```

**Flow:** resolve workspace (`task.cwd || getWorkspacePath()`, error-as-content if none) → missing `query` increments `consecutiveMistakeCount`, sets `didToolFailInCurrentTurn`, pushes `sayAndCreateMissingParamError` text (Task.ts :1824–1832) → approval ask `{tool:"codebaseSearch", query, path, isOutsideWorkspace:false}` (denial ⇒ toolDenied) → reset mistake count → tool-level loud pre-checks → `manager.searchIndex` → shape results → dual emit.
**Invariant:** (1) The three gate layers DISAGREE on failure mode BY DESIGN — tool throws loud distinct messages ("disabled in the settings" vs "not configured (Missing OpenAI Key or Qdrant URL)"), manager returns `[]` when disabled but `assertInitialized()` otherwise, service throws on state ∉ {Indexed, Indexing} and flips Error-state (see search-gating-state). A porter collapsing them into one guard loses the telemetry distinction between "off", "unconfigured", and "not ready". (2) Result shaping is LOSSY toward the model: entries without payload/filePath vanish silently (no warning), chunks are trimmed, paths become workspace-relative — while the UI JSON carries the same shaped data, so UI and model can never disagree. (3) NO cap lives in the tool: `minScore` = user setting → model-specific threshold (`EMBEDDING_MODEL_PROFILES`) → `DEFAULT_SEARCH_MIN_SCORE`; `maxResults` = user setting ?? `DEFAULT_MAX_SEARCH_RESULTS` (spec-pinned config-manager.spec.ts:796–1018). (4) Empty results push a plain sentence, not an error — a miss is a successful search.
**Probe:** runner BLOCKED (no node_modules/vitest; NO direct spec exists for CodebaseSearchTool at pin — glob over src/** found only the tool file). Deterministic source pins from repo root: `grep -c 'Code Indexing is not configured' src/core/tools/CodebaseSearchTool.ts` → 1; `grep -c 'codebase_search_result' src/core/tools/CodebaseSearchTool.ts` → 1; `grep -c 'return \[\]' src/services/code-index/manager.ts` → 1; `grep -c 'DEFAULT_MAX_SEARCH_RESULTS' src/services/code-index/config-manager.ts` → ≥2.
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "Roo-Code", qualified_name: "Roo-Code.src.core.tools.CodebaseSearchTool.CodebaseSearchTool.execute" });
```

## Verdict
Adopt the loud-tool/soft-manager/state-gated-service three-layer split, silent payload-less filtering before shaping, relative-path+trim normalization feeding ONE shared JSON that renders twice (structured for UI, prose blocks for model), and config-owned score/result knobs instead of tool-local constants. Adapt the VS Code asRelativePath call and the exact error copy. Omit the extension-context/providerRef plumbing. Coverage caveat: no direct spec at pin; behavior pinned by whole-file source read + byte-exact greps + live snippet retrieval.
