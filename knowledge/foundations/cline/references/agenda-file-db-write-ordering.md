<!-- capsule-v2 -->
# Agenda file/DB write ordering — which side do you write first, and how does each ordering compensate its own failure?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** when a task's truth spans a Markdown file and a SQLite row with a revision counter, in what order do you write them so any crash leaves detectable, reconcilable state?

## `createTask` (DB-first) vs `updateTask` (file-first), each self-compensating
**Path/Symbol:** `sdk/packages/core/src/tasks/agenda-task-manager.ts` — `createTask` :353-396, `updateTask` :448-567 (decisive :451-535).
**Signature:** `createTask(input): Promise<AgendaTaskRecord>` / `updateTask(input: AgendaTaskUpdateInput): Promise<AgendaTaskRecord>`.

### Decisive source
```ts
// CREATE: DB row first, createOnly spec second, row deleted on failure
const task = this.store.createTask({ ...normalizedInput, taskId, specPath });
try {
    fileStore.writeSpec({ ...normalizedInput, taskId }, { specPath, createOnly: true });
} catch (error) {
    this.store.deleteTask(taskId);
    throw error;
}

// UPDATE: probe conflict via the store itself for the canonical error + fresh record:
if (current.revision !== input.expectedRevision) {
    // Let the store produce its canonical conflict error and current record.
    this.store.updateTask(input);          // deliberately invoked to throw
}
...
if (input.updatedBy.id !== FILE_RECONCILER_ACTOR.id &&
    specSignature(source.spec, current) !== taskSignature(current)) {
    throw new Error(`task spec changed outside the manager; reconcile task ${current.taskId} and retry`);
}
expectedContentHash = source.contentHash;  // CAS pin = bytes the editor agreed to
spec = targetStore.writeSpec(normalizedDesired, { specPath, expectedContentHash, createOnly: !staysInSameStore });
updated = this.store.updateTask(normalizedInput);   // only now bump revision
```
```ts
// compensation on update failure: restore old bytes using the NEW hash as expectation
if (spec && staysInSameStore && current.specPath) {
    targetStore.writeSpec(current, { specPath: current.specPath, expectedContentHash: spec.contentHash });
} else if (spec) {
    targetStore.deleteSpec(targetSpecPath, { expectedContentHash: spec.contentHash });
}
```

**Flow:** create validates everything first (future expiry, location normalization, no taskId/specPath collision), inserts the row, then writes the spec createOnly — if the write fails the row is deleted, so validation failures leave zero artifacts. Update refuses edits from in_progress/completed/cancelled/expired, verifies the on-disk spec still matches the manager's last-known signature (skipped for the FILE_RECONCILER actor, which is the reconciler writing back disk truth), stages the new file guarded by the old contentHash, and only then bumps the DB revision; failure restores the previous bytes (using the new spec's contentHash as the expected value) or deletes a just-created file.
**Invariant:** crash windows are always "old-file+old-row" or "new-file+old-row" — both states are detected by the next reconciliation/signature check; never "half-merged". Create-side validation precedes all persistence; update-side conflict detection reuses the store's canonical error instead of duplicating message logic.
**Probe:** `agenda-task-manager.test.ts` "does not leave a task spec behind when task validation fails" (:475-497) — impossible time window ⇒ rejects "availableAt must be before expiresAt", `listSpecPaths()` empty, `getTask` undefined; "preserves terminal tasks and last-known-good state across raw edits" (:887-921) pins edit-refusal from completed ("cannot be edited from completed") and that writing garbage over a completed task's spec cannot corrupt it.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "createTask writeSpec deleteTask agenda manager", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.agenda-task-manager.AgendaTaskManager.updateTask" });
```

## Verdict
Adopt the asymmetric pair: brand-new entities = authority-first with delete-compensation (cheap because nothing user-visible exists yet); edits to user-editable truth = file-first with content-hash CAS and restore-compensation (because users watch the file). Adapt which side is "authority" for your host. Omit the FILE_RECONCILER actor bypass unless you have an automated reconciler with equal write rights. Runner caveat: vitest not executable here (no node_modules); evidence = direct test reads (:475-497, :887-921) + byte-exact probes.
