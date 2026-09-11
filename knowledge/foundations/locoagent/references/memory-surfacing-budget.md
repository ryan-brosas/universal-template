<!-- capsule-v2 -->
# Memory surfacing budget ladder — how does bounded injection stay bounded across lines, bytes, turns, and whole sessions?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** the three-tier cap arithmetic that stops memory surfacing from eating the context window.

## readMemoriesForSurfacing + budget constants
**Path/Symbol:** `src/utils/attachments.ts:MAX_MEMORY_LINES/MAX_MEMORY_BYTES/RELEVANT_MEMORIES_CONFIG` (:269-289), `readMemoriesForSurfacing` (:2279-2321), `collectSurfacedMemories` (:2251-2266), `memoryHeader` (:2327-2332), `getRelevantMemoryAttachments` slice (:2231-2234).
**Signature:** `readMemoriesForSurfacing(selected: {path, mtimeMs}[], signal?) → {path, content, mtimeMs, header, limit?}[]`; `collectSurfacedMemories(messages) → {paths: Set, totalBytes}`.
**Data Shape:** caps — 200 lines/file, 4096 bytes/file, 5 files/turn, 60KB/session (`MAX_SESSION_BYTES: 60 * 1024`).

### Decisive source
```ts
// Line cap alone doesn't bound size (200 × 500-char lines = 100KB). The
// surfacer injects up to 5 files per turn via <system-reminder>, bypassing
// the per-message tool-result budget, so a tight per-file byte cap keeps
// aggregate injection bounded (5 × 4KB = 20KB/turn). ...
// MAX_SESSION_BYTES comment: "~26K tokens/session observed in prod. Cap the
// cumulative bytes ... Budget is ~3 full injections; after that the
// most-relevant memories are already in context. Scanning messages (rather
// than tracking in toolUseContext) means compact naturally resets the
// counter — old attachments are gone from context, so re-surfacing is valid."
```

**Flow:** selector picks candidates → `readFileInRange(path, 0, 200, 4096, signal, { truncateOnByteLimit: true })` → truncated reads get an appended note telling the model to FileRead the full path → header computed ONCE here → per-turn `.slice(0, 5)` after dedup vs readFileState + alreadySurfaced → session gate compares `collectSurfacedMemories(messages).totalBytes >= 60KB` BEFORE prefetching.
**Invariant:** truncation surfaces partial content WITH A POINTER, never silently drops a file the ranker chose ("frontmatter + opening context is usually what matters"); the session counter lives IN THE TRANSCRIPT so compaction resets it by construction — no external state to invalidate; `limit` threads into readFileState writes so change-detection skips partial views. Line cap without byte cap is no cap at all (200×500-char lines = 100KB).
**Probe:** no upstream test (coverage caveat); constants pinned verbatim :269-289. Deterministic probe: `grep -n "truncateOnByteLimit" src/utils/attachments.ts src/utils/fsOperations.ts 2>/dev/null | head`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "readMemoriesForSurfacing MAX_SESSION_BYTES truncateOnByteLimit relevant memories", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the line+byte+session triple-cap with pointer-noting truncation and transcript-resident counters; adapt thresholds to your injection channel; omit memdir ranking internals. Porting trap: implementing only the line cap leaves a 100KB-per-file hole; tracking the session budget in mutable app state breaks its automatic compact-reset property.
