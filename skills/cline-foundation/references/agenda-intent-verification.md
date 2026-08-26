<!-- capsule-v2 -->
# Agenda intent verification — how do you make approval and execution bind to the *current* editable intent, not a stale projection?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** when the source of truth is a user-editable file but approvals live in a database, how does every mutating action re-verify intent synchronously despite debounced file watching?

## Fail-closed reconcile in `refreshAndVerifyTaskIntent`
**Path/Symbol:** `sdk/packages/core/src/tasks/agenda-task-manager.ts:1359-1391` (`AgendaTaskManager.refreshAndVerifyTaskIntent`); signature pair `specSignature`/`taskSignature` :129-176; callers via trace: `approveTask`, `pumpAutomation`, `runTask`.
**Signature:** `private refreshAndVerifyTaskIntent(taskId: string): Promise<AgendaTaskRecord>` — returns the freshly reconciled record or throws; no silent passthrough.
**Data Shape:** signatures are JSON.stringify over the SAME 18 editable fields (type/title/description/instructions/scope/workspaceRoot/cwd/resourcePaths/priority/assignee/modelSelection/mode/systemPrompt/maxIterations/timeoutSeconds/availableAt/expiresAt/automationEligible), with spec side falling back `spec.availableAt ?? current.availableAt`.

### Decisive source
```ts
const known = this.requireTask(taskId);
await this.reconcileScope(known.scope, known.workspaceRoot);  // SYNC reconcile, awaits the
const current = this.requireTask(taskId);                     // scan that the watcher debounce
                                                              // would otherwise delay
if (current.archivedAt) throw new Error(`task ${taskId} no longer has an active task spec`);
if (!current.specPath) throw new Error(`task ${taskId} has no canonical task spec`);
try { parsed = this.fileStoreForTask(current).readSpec(current.specPath); }
catch (error) { throw new Error(`task ${taskId} task spec is unavailable: ...`); }
if (!parsed.ok) throw new Error(`task ${taskId} task spec is invalid: ${parsed.error}`);
if (parsed.spec.taskId !== current.taskId ||
    specSignature(parsed.spec, current) !== taskSignature(current)) {
    throw new Error(`task ${taskId} task spec does not match revision ${current.revision}`);
}
return current;
```

**Flow:** approve/run/pump each call this FIRST → the awaited synchronous `reconcileScope` closes the debounce window (file edits are already folded into SQLite before verification) → archived/missing/unparseable/id-mismatch/signature-mismatch all FAIL CLOSED with distinct messages → only then do revision CAS and status gates run. Any editable-field edit bumps `revision` and revokes approval (`updateTask` forces status back to `pending_approval`, clears `approvedRevision`), so run additionally refuses when `approvedRevision !== revision` ("approval is stale").
**Invariant:** approval is bound to content, not to an id — editing one title byte invalidates the approval AND blocks a running-waiting start; verification reads the FILE, so hand-edits between approve and run are caught even though the watcher fires later.
**Probe:** `agenda-task-manager.test.ts` "binds approval and execution to the current valid Markdown intent" (:185-236): after editing the spec on disk, `approveTask(...pending.revision)` rejects "requested revision is stale", the record shows `revision+1 / pending_approval / edited title`; after approving the NEW revision and corrupting the file, `runTask` rejects "task spec is invalid" and `startSession` is never called (:230-235). Companion: "increments revision and revokes approval when editable fields change" (:160-183).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.agenda-task-manager.AgendaTaskManager.refreshAndVerifyTaskIntent" });
await mcp.codebase_memory.trace_path({ project: "cline", function_name: "cline.sdk.packages.core.src.tasks.agenda-task-manager.AgendaTaskManager.refreshAndVerifyTaskIntent", direction: "inbound", depth: 2 });
```
(Verified this pass: callers_total=3 — exactly approveTask/pumpAutomation/runTask.)

## Verdict
Adopt the sync-reconcile-then-fail-closed ladder whenever approvals outlive an editable artifact, and the paired-field-list signature trick (one field list, two projections) to detect drift without versioning the file format. Adapt which fields are identity vs content. Omit if your intent source is immutable per revision. Runner caveat recorded honestly (no node_modules).
