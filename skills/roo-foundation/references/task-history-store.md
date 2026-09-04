<!-- capsule-v2 -->
# Task history store — how do you make per-task JSON files the truth while an index stays fast and multi-instance safe?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How do you combine per-record files, a startup index, cross-process file locking, fs.watch, and periodic reconciliation so no writer combination corrupts or loses task history?

## Files = truth; index = cache; in-process lock + proper-lockfile + reconcile on drift
**Path/Symbol:** `src/core/task-persistence/TaskHistoryStore.ts` (class :44-572; `INDEX_WRITE_DEBOUNCE_MS = 2000` :62; `RECONCILE_INTERVAL_MS = 5min` :65; `initialize()` :80-97 loadIndex→reconcile→watch→periodic; `upsert` :160-188 merge+write+debounce under `withLock`; `reconcile()` :244-300 under lock; `migrateFromGlobalState` :325-368 never-overwrite; `withLock` :538-550; dispose flushes :105-127).
**Signature:** `upsert(item): Promise<HistoryItem[]>`; `delete(taskId)`/`deleteMany(ids)`; `get/getAll/getByWorkspace` served purely from the in-memory Map.
**Data Shape:** `globalStorage/tasks/<taskId>/history_item.json` per record (source of truth) + `tasks/_index.json` `{version: 1, updatedAt, entries: HistoryItem[]}` cache.

### Decisive source
```ts
// upsert merges — delegation fields survive partial updates:
const merged = existing ? { ...existing, ...item } : item
await this.writeTaskFile(merged)      // per-task file via safeWriteJson (proper-lockfile)
this.cache.set(merged.id, merged)
this.scheduleIndexWrite()             // 2s debounce — index lags, files don't
// Reconciliation runs THROUGH the write lock; dir names starting _ or . are not tasks:
const taskDirNames = dirEntries.filter(n => !n.startsWith("_") && !n.startsWith("."))
// disk ⊕ cache both directions: missing-on-disk evicts cache; missing-in-cache adopts disk
```
Cross-instance safety layers: (1) `proper-lockfile` inside safeWriteJson guards single-file writes across processes; (2) in-process `withLock` promise-chain serializes read-modify-write sequences; (3) `fs.watch` on the tasks dir triggers debounced (500ms) reconcile when ANOTHER instance mutates files; (4) periodic 5-minute reconcile covers platforms where fs.watch is unreliable ("fs.watch error → periodic reconciliation serves as the fallback"). Migration from legacy globalState array writes history_item.json ONLY when absent (idempotent, orphaned entries skipped), then writes the index once.
**Flow:** initialize loads index into Map (version-checked, corrupt → empty) → reconcile fixes drift vs directories → watcher + timer keep it fixed → every mutation writes its per-task file immediately, updates the Map, debounces the index; `onWrite` callback fires INSIDE the lock for serialized write-through to legacy globalState during transition; dispose cancels timers, closes watcher, best-effort flushes index synchronously-ish.
**Invariant:** A crash between file write and index write is self-healing (reconcile adopts the file); two instances writing DIFFERENT tasks never conflict; index staleness is bounded by debounce+interval but NEVER causes data loss because files are authoritative; corrupted individual records are skipped, not propagated.
**Probe:** `src/core/task-persistence/__tests__/TaskHistoryStore.spec.ts` (:235 disk-missing-from-index adopted, :253 cache-entry-without-dir evicted, :272 concurrent upserts serialized, :307/:331/:361 migration idempotence + no-overwrite); `TaskHistoryStore.crossInstance.spec.ts` (:56 two instances different tasks, :81 B reconciles A's create, :99 delete detected, :145 concurrent final state correct).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "TaskHistoryStore reconcile scheduleIndexWrite withLock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-layer consistency stack (per-file truth, debounced index, watch-triggered + timed reconciliation, dual locking) as a unit — removing any layer reintroduces the specific race it was added for. Adapt storage paths and the transition-period write-through hook. This is the canonical pattern for any per-record-file + summary-index design.
