<!-- capsule-v2 -->
# Markdown memory store — §-delimited entries, metadata comments, atomic conflict-safe writes

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an agent persist token-aware Markdown memory (MEMORY.md/USER.md/failures.md) so entries carry invisible timestamps, stay within a char budget, survive external editors without clobbering, and render as a frozen system-prompt snapshot?

## MemoryStore
**Path/Symbol:** `src/store/memory-store.ts:MemoryStore` (class, 52–1068); key methods `add` (152–230), `applyMutationPlan` (327–411), `replace` (413–459), `remove` (461–487), `loadFromDisk` (130–148), `formatForSystemPrompt` (491–511), `saveToDisk` (791–890), `runTargetMutation` (744–783).
**Signature:** `new MemoryStore(config: MemoryConfig)`; `add(target: 'memory'|'user'|'failure', content: string, signal?) → Promise<MemoryResult>`; `applyMutationPlan(target, operations[], {requireShrink?}) → Promise<MemoryResult>`.
**Data Shape:** entries are `string[]` joined by `ENTRY_DELIMITER` (`§`). Each entry is `text <!-- created=YYYY-MM-DD, last=YYYY-MM-DD[, project64=<base64url>] -->`. `MemoryResult = { success, target, usage: "pct% — cur/limit chars", entry_count, message?, evicted_entries?, evicted_count?, matches? }`. Targets: memory/user/failure; failures get `memoryCharLimit*2` space.

### Decisive source
```ts
// encodeEntry (memory-store.ts:550-555): metadata as an invisible HTML comment
private encodeEntry(text, created, lastReferenced, project?) {
  const projectMetadata = project?.trim()
    ? `, project64=${Buffer.from(project.trim(), "utf-8").toString("base64url")}` : "";
  return `${text} <!-- created=${created}, last=${lastReferenced}${projectMetadata} -->`;
}

// decodeEntry (561-573): regex; legacy entries without metadata default to today
const match = raw.match(/^(.*?)\s*<!--\s*created=([^,]+),\s*last=([^,>]+)(?:,\s*project64=([A-Za-z0-9_-]+))?\s*-->\s*$/);
// project decoded via Buffer.from(match[4], "base64url").toString("utf-8")

// _add (189-230): dedupe on stripped text (+ project for failures), then budget check
const newTotal = [...entries, encoded].join(ENTRY_DELIMITER).length;
if (newTotal > limit) {
  if (strategy === "fifo-evict") return this.fifoEvictAndAdd(...); // shift() oldest
  return this.memoryFullError(target, content.length);
}

// runTargetMutation (744-783): mutation lock + external-write conflict retry
return withMarkdownMutationLock(storagePath, async () => {
  for (let attempt = 0; ; attempt++) {
    const result = await mutation();
    // after publish, re-read; if fingerprint changed → ExternalMemoryWriteConflict → retry
    if (state.fingerprint !== expectedFingerprint) throw new ExternalMemoryWriteConflict();
    return await this.finalizeTargetMutation(target, storagePath, result);
  }
});

// saveToDisk (791-890): temp file in same dir, then link/rename + fingerprint verify
// missing → fs.link(tmp, file); existing → rename(file, recoveryPath), verify, fs.link(tmp, file)
// rollback via restoreDisplacedFile / rollbackPublishedFile on any EEXIST/conflict
```

**Flow:** (1) `loadFromDisk` reads each target file, splits on `§`, dedupes preserving order, fingerprints each file, and builds a frozen `snapshot` (memory+user stripped of metadata). (2) Every mutation runs under `withMarkdownMutationLock` (per-file atomic lock). (3) `_add` scans content, dedupes, encodes metadata, checks the char budget (fifo-evict or reject/auto-consolidate), writes atomically. (4) `saveToDisk` uses temp-file + `fs.link`/`fs.rename` with fingerprint verification and rollback so an external editor's concurrent write is never silently overwritten. (5) `formatForSystemPrompt` renders the frozen snapshot fenced in `<memory-context>…</memory-context>` plus recent failure memories.

**Invariant:** an entry's visible text is stable while its timestamps live in an invisible HTML comment; a write that races an external editor refuses (ExternalMemoryWriteConflict) and retries against disk truth rather than clobbering; the system-prompt snapshot is frozen at load so mid-session adds never mutate the injected block.

**Probe:** `tests/store/memory-store.test.ts` — `add` persists + returns usage stats (:134), `no-ops on duplicate` (:153), `evicts oldest entries in file order when fifo-evict` (:208), `returns frozen snapshot — add after load does not change it` (:679), `injects recent failure memories by default` (:705), `file content is correct after write (read back and check)` (:792). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "MemoryStore add applyMutationPlan saveToDisk encodeEntry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the §-delimited Markdown store, the metadata-comment encoding, the char-budget FIFO eviction, the atomic temp+link/rename write with fingerprint verification, the external-write conflict retry, and the frozen system-prompt snapshot. Adapt the entry delimiter, file names, char limits, and the exact metadata-comment regex to the host. Omit the auto-consolidation subprocess and the Pi extension mutation-observer wiring unless a target needs them.
