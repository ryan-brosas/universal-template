<!-- capsule-v2 -->
# Dual-write mirror — Markdown stays authoritative while every mutation best-effort-syncs the SQLite search index, with observer-based reconciliation

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** When the durable store (Markdown) and the queryable store (SQLite FTS5) must never diverge silently — how do you order the writes, shape the warnings, and guarantee convergence without transactions spanning both?

## registerMemoryTool
**Path/Symbol:** `src/tools/memory-tool.ts:registerMemoryTool` (:227–422); sync helpers `syncAddToSqlite` (:74–112), `syncReplaceToSqlite` (:114–140), `syncRemoveFromSqlite` (:142–166), `syncEvictionsFromSqlite` (:168–191), `reconcileStoreScope` (:193–216); target mapping `sqliteProjectFor`/`sqliteTargetFor` (:61–72); warning plumbing `appendSyncWarning` (:27–36).
**Signature:** registers three action-specific tools (`memory_add`, `memory_replace`, `memory_remove`); returns `(candidate: MemoryStore | null) => void` — a project-store rebinding hook consumed by `index.ts:233`.
**Data Shape:** tool targets `{memory, user, project, failure}` map to SQLite as: `project → (target:"memory", project:<name>)`; everything else → same target, `project: null`; failures additionally format content via `formatFailureMemoryContent`.

### Decisive source
```ts
// ORDER IS THE CONTRACT: Markdown first (throws propagate → tool error),
// SQLite second (all errors become WARNING STRINGS attached to success):
try {
  const result = await store_.add(target, content, signal);      // 1. authoritative write
  if (result.success && !syncHandled) {
    await syncEvictionsFromSqlite(rawTarget, result.evicted_entries, …); // FIFO victims leave index too
    syncWarning = await syncAddToSqlite(rawTarget, content, …);          // 2. mirror write
  }
} catch { /* Markdown failure = real failure */ }

// Mirror failures degrade to a loud, actionable warning on a SUCCESS result:
return "Saved to Markdown, but no matching SQLite memory row was updated. "
     + "Run /memory-sync-markdown if search results look stale.";

// Convergence backstop: after any successful mutation, reconcile the WHOLE scope
if (result.success && !syncHandled && typeof store_.getRawEntriesForSync === "function") {
  const reconciliationWarning = await reconcileStoreScope(
    store_.getRawEntriesForSync(target), rawTarget, dbManager, activeProjectName);
}

// Observer dedupe: stores configured with a mutation observer already reconcile,
// so per-call syncing is skipped for them (WeakSet-guarded attach):
const reconciledStores = new WeakSet<MemoryStore>();
const syncHandled = reconciledStores.has(store_);
```

**Flow:** (1) tool executes the Markdown mutation; (2) unless the store self-reconciles through its mutation observer, the eviction/add/replace/remove mirror calls run; (3) a post-mutation full-scope reconcile sweeps anything point-fixes missed; (4) warnings ride INSIDE the successful result (`warning` + `warnings[]` + appended to `message`) so the model sees success AND staleness risk; (5) `tool_result` events with `details.success === false` are converted to `isError` results.
**Invariant:** NEVER fail a memory write because the SEARCH MIRROR failed — the two-tier contract ("save does NOT silently become SQLite-only" is enforced in reverse: index loss is visible but non-fatal); evictions are mirrored FIRST so a full add cannot leave ghost rows; replace/remove report zero-match distinctly from exceptions because they mean different remediation (resync vs bug). The WeakSet makes observer-mode and manual-mode mutually exclusive per store instance.
**Probe:** `tests/tools/memory-tool.test.ts` — asserts Markdown-first ordering, warning-not-error on mirror failure, eviction cleanup before add-sync, zero-match replace/remove messaging, and observer-attach deduplication. Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "registerMemoryTool syncMemoryEntry reconcileMarkdownMemoryScope removeSyncedMemories", limit: 5 })`

## Verdict
Adopt for any authoritative-store + derived-index pair. Adapt the warning phrasing and repair command name. Extends `sqlite-mirror.md` (which owns row-level identity/reconcile mechanics): THIS capsule owns the call-site choreography, ordering, and warning semantics at the tool boundary.
