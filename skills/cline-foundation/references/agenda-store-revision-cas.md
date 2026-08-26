<!-- capsule-v2 -->
# Agenda store revision CAS — two write verbs, one revision counter, DDL-carried invariants

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** how does a single-writer SQLite store make task edits optimistic-CAS-safe while letting lifecycle transitions bypass the edit rules?

## `SqliteAgendaTaskStore.updateTask` vs `updateTaskState` (+ schema)
**Path/Symbol:** `sdk/packages/core/src/tasks/store/sqlite-task-store.ts` — `AgendaTaskRevisionConflictError` :32-39, `updateTask` :413-514, `updateTaskState` :517-577, `createRun` :586-628; `sdk/packages/core/src/tasks/store/task-schema.ts:1-97`.
**Signature:** `updateTask(input: AgendaTaskUpdateInput): AgendaTaskRecord | undefined` / `updateTaskState(taskId, patch: AgendaTaskStatePatch, expectedRevision?: number): AgendaTaskRecord | undefined` / `createRun(input: CreateAgendaTaskRunInput): AgendaTaskRunRecord`.

### Decisive source
```ts
// updateTask — the EDIT verb: bumps revision, revokes approval
if (current.revision !== input.expectedRevision) {
    throw new AgendaTaskRevisionConflictError(current);   // carries current record
}
if (current.status === "in_progress") {
    throw new Error("an in-progress task cannot be edited");
}
const status = current.status === "approved" || current.status === "failed"
    ? "pending_approval" : current.status;
const revision = current.revision + 1;
// UPDATE agenda_tasks SET ... revision = ?, approved_revision = NULL, error = NULL ...
// WHERE task_id = ? AND revision = ?

// updateTaskState — the LIFECYCLE verb: never bumps revision
if (expectedRevision !== undefined && current.revision !== expectedRevision) {
    throw new AgendaTaskRevisionConflictError(current);
}
const status = patch.status ?? current.status;
if (status === "in_progress" && approvedRevision !== current.revision) {
    throw new Error("in-progress task must be approved for its current revision");
}
// UPDATE agenda_tasks SET status/approved_revision/run/session/error/... 
// WHERE task_id = ? AND revision = ?      (revision unchanged)

// createRun — attempt numbering + DB-enforced single active run:
const attempt = maxAttempt + 1;             // UNIQUE(task_id, attempt)
```
```sql
-- task-schema.ts: the invariant carrier
CREATE UNIQUE INDEX agenda_task_runs_one_active_idx
    ON agenda_task_runs(task_id) WHERE status IN ('starting', 'running');
UNIQUE (task_id, attempt);
CHECK ((scope='workspace' AND workspace_root IS NOT NULL)
    OR (scope='global' AND workspace_root IS NULL));
PRAGMA journal_mode = WAL; PRAGMA busy_timeout = 5000; PRAGMA foreign_keys = ON;
```

**Flow:** edits go through `updateTask` (CAS on expectedRevision, revision+1, approval force-cleared, approved/failed demoted to pending_approval); state machine moves (approve, start, complete, fail, cancel, expire, archive) go through `updateTaskState`, which patches columns under a `WHERE revision = current.revision` guard WITHOUT bumping it. Patch columns distinguish null-clears from undefined-preserves (`patch.x === null ⇒ clear; undefined ⇒ keep`). `createRun` numbers attempts via MAX+1 and inserts with status `starting`; a second concurrent starting|running insert violates the partial unique index.
**Invariant:** exactly one counter means "content changed" (revision) and one field means "approved for this content" (approvedRevision); the DB, not the manager, forbids two live runs per task and duplicate spec paths; conflict errors carry the fresh record so callers can retry against reality.
**Probe:** `sqlite-task-store.test.ts` (:56-104) — update at stale expectedRevision throws `AgendaTaskRevisionConflictError`; successful update yields `revision: 2, status: pending_approval`, approval cleared; :211-237 — second `createRun` while first non-terminal throws; after completing run 1, run 2 gets `attempt: 2`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "sqlite agenda task store revision conflict", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.store.sqlite-task-store.SqliteAgendaTaskStore.updateTask" });
```

## Verdict
Adopt the two-verb split (edit = CAS+bump+revoke; transition = guarded patch), null-vs-undefined patch semantics, partial unique index for "one active work item", and attempt numbering via MAX+1 under a UNIQUE constraint. Adapt column sets and CHECK vocabularies to your domain; keep the connection pragmas (WAL/busy_timeout/foreign_keys). Omit better-sqlite3 specifics if your host uses another driver, but keep every invariant as DDL where SQLite can enforce it. Runner caveat: vitest not executable here (no node_modules); evidence = whole direct test read (262 lines, 6 cases) + byte-exact probes.
