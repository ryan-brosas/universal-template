<!-- capsule-v2 -->
# Nested-memory LRU re-injection guard — why is dedup keyed on a non-evicting Set and not the read cache?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** keeping AGENT.md injection once-per-session even when the file-state LRU evicts under pressure.

## memoryFilesToAttachments
**Path/Symbol:** `src/utils/attachments.ts:memoryFilesToAttachments` (:1710-1775), `isInstructionsMemoryType` (:1698-1707).
**Signature:** `(memoryFiles: MemoryFileInfo[], toolUseContext, triggerFilePath?) → Attachment[]`.
**Data Shape:** dual dedup structures — `loadedNestedMemoryPaths` (non-evicting Set on toolUseContext) and `readFileState` (100-entry LRU); MemoryFileInfo carries optional `rawContent` + `contentDiffersFromDisk`.

### Decisive source
```ts
// Dedup: loadedNestedMemoryPaths is a non-evicting Set; readFileState
// is a 100-entry LRU that drops entries in busy sessions, so relying
// on it alone re-injects the same AGENT.md on every eviction cycle.
if (toolUseContext.loadedNestedMemoryPaths?.has(memoryFile.path)) continue
if (!toolUseContext.readFileState.has(memoryFile.path)) {
  attachments.push({ type: 'nested_memory', path, content: memoryFile,
                     displayPath: relative(getCwd(), memoryFile.path) })
  toolUseContext.loadedNestedMemoryPaths?.add(memoryFile.path)
  // When the injected content doesn't match disk (stripped HTML comments,
  // stripped frontmatter, truncated MEMORY.md), cache the RAW disk bytes
  // with `isPartialView: true`. Edit/Write see the flag and require a real
  // Read first; getChangedFiles sees real content + undefined offset/limit
  // so mid-session change detection still works.
  toolUseContext.readFileState.set(memoryFile.path, {
    content: memoryFile.contentDiffersFromDisk ? (memoryFile.rawContent ?? memoryFile.content)
                                               : memoryFile.content,
    timestamp: Date.now(), offset: undefined, limit: undefined,
    isPartialView: memoryFile.contentDiffersFromDisk })
```

**Flow:** per injected memory file: check non-evicting Set → check LRU → attach → add to BOTH structures (Set unconditionally; LRU with raw-bytes + `isPartialView` flag when injected content was transformed) → fire-and-forget InstructionsLoaded hook with derived loadReason ('path_glob_match' | 'include' | 'nested_traversal') for instruction types only.
**Invariant:** session-once semantics need storage that never evicts; the eviction-prone cache alone guarantees periodic re-injection loops in busy sessions. When injected ≠ disk bytes, cache RAW disk content and flag the entry partial — otherwise Edit/Write would diff against stripped text and getChangedFiles would emit misleading diffs against a view the model never truly saw.
**Probe:** exported "for testing — regression guard for LRU-eviction re-injection" (:1709-1710); no runner on host (coverage caveat). Deterministic probe: comment block pinned verbatim :1719-1724 and :1737-1749.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "memoryFilesToAttachments loadedNestedMemoryPaths isPartialView rawContent", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the two-tier dedup (permanent set + flagged cache) and raw-bytes-with-flag caching; adapt structure names; omit hook fan-out. Porting trap: using only an LRU for once-per-session injection re-sends AGENT.md on every eviction cycle; caching stripped content as-if-read corrupts later edit/change detection.
