<!-- capsule-v2 -->
# Agenda spec reconciliation — who wins when a user edits the Markdown on disk: the file, the database, or neither?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** how do you reconcile a directory of user-editable intent files against DB-projected tasks without ever losing identity or resurrecting terminal state?

## Disk-wins-with-ranks reconciliation in `reconcileFileStore`
**Path/Symbol:** `sdk/packages/core/src/tasks/agenda-task-manager.ts:987-1145` (`reconcileFileStore`, callers=3 via reconcileScope/ensureScope/start); watcher root `resolveWatchRoot` :1432-1443 with in-source rationale :1424-1431.
**Signature:** `private async reconcileFileStore(fileStore: AgendaTaskSpecFileStore): Promise<void>` — one pass per scope: import/merge seen files, then archive unseen paths.
**Data Shape:** iterates `fileStore.listSpecs()` results `{specPath, ok, spec?, error?}`; DB side keyed by `specPath` (UNIQUE) and `taskId`; FILE_RECONCILER_ACTOR = `{kind:"system", id:"file_reconciler"}`.

### Decisive source
```ts
if (!spec.taskId) {                                   // mint id INTO the file, CAS-guarded
    spec = fileStore.writeSpec({ ...spec, taskId: createSessionId("task_") },
        { specPath: spec.specPath, expectedContentHash: spec.contentHash });
}
if (existingByPath && spec.taskId && spec.taskId !== existingByPath.taskId) {
    // taskId immutability: rewrite the EDITED file back to the DB-owned id
    spec = fileStore.writeSpec({ ...spec, taskId: existingByPath.taskId },
        { specPath: spec.specPath, expectedContentHash: spec.contentHash });
}
if (existingById?.specPath && existingById.specPath !== spec.specPath) continue;  // id owned elsewhere → skip
if (specSignature(spec, existing) === taskSignature(existing)) continue;         // no-op
if (existing.status === "in_progress") continue;    // defer edit until run end
if (["completed","cancelled","expired"].includes(existing.status)) {
    fileStore.writeSpec(existing, { ... });          // TERMINAL: DB outranks disk — rewrite file to DB truth
    continue;
}
await this.updateTask(specUpdate(spec, existing));   // non-terminal: disk wins
```

**Flow:** invalid parses log-and-continue (never abort the walk) → unseen paths at the end: `in_progress` runs are cancelled first ("Task spec was deleted."), completed/expired keep status, everything else archives as cancelled with `approvedRevision/currentRunId` cleared and `task.deleted` published → ends with `queueAutomation()` so newly imported work can start.
**Invariant:** taskId is minted once and immutable — an edited file's foreign id is rewritten back (test-pinned "replacement_id" case); archived tasks restore on re-appearance (deleted-before-start ⇒ `pending_approval`, else prior status); terminal tasks are protected BOTH from DB edits ("cannot be edited from completed") and from raw-file corruption (file gets repaired from DB). The fs.watch root uses `realpathSync.native` because unresolved Windows 8.3 short paths (e.g. `C:\Users\RUNNER~1`) abort libuv's fs-event loop entirely — documented in-source: going WITHOUT the watcher beats crashing the process (:1424-1431).
**Probe:** `agenda-task-manager.test.ts`: "imports and reconciles user-edited Markdown specs" (:499-553) pins revision bump on edit AND `getTask("replacement_id")` undefined + file rewritten back to `task_from_file`; "isolates stale hand-authored specs during startup reconciliation" (:579-607) pins expired+valid coexistence through `manager.start()`; "preserves terminal tasks and last-known-good state across raw edits" (:887-921) pins completed task surviving `writeFileSync(specPath, "not valid task Markdown")`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.agenda-task-manager.AgendaTaskManager.reconcileFileStore" });
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.agenda-task-manager.AgendaTaskManager.resolveWatchRoot" });
```

## Verdict
Adopt the rank table (no-op < defer-in-progress < disk-wins < terminal-repairs-file) for any dual-homed file/DB projection, plus mint-id-into-artifact for identity bootstrap. Adapt statuses and the actor marker. Keep the realpathSync.native watcher rule verbatim if you watch user paths cross-platform. Runner caveat recorded honestly (no node_modules).
