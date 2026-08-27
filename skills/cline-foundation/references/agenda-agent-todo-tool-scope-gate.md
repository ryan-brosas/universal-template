<!-- capsule-v2 -->
# agenda-agent-todo-tool-scope-gate — how does an agent-facing tool expose a reduced verb set under session-derived authority?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How do you let an LLM agent create/update/list/get durable tasks while making cancellation, approval, and cross-workspace access UNREPRESENTABLE at the schema layer?

## Session defaults are the authority; scope checked on payload AND on every fetched row; expected_revision demanded after the scope gate
**Path/Symbol:** `sdk/packages/core/src/tasks/agenda-task-tool.ts` (`executeTodoTaskOperation` :186-329; `assertRequestedScope` :165-183; `assertSessionScope` :145-163; `TodoTaskInputSchema` :47-73; `captureTodoTaskMutation` :97-110).
**Signature:** `executeTodoTaskOperation(options, rawInput: unknown, context): Promise<TodoTaskResult>` — result union `{ok:true, task?|tasks?}` | `{ok:false, error:{code, message}}`.
**Data Shape:** Zod schema admits ONLY `operation: create|update|list|get` — cancel/run/approve are unrepresentable (not merely forbidden). Scope authority = `resolveSessionDefaults(sessionId)`: a workspaceRoot ⇒ workspace session, else global. Telemetry only for MUTATING_OPERATIONS {create, update}, `tool: "tasks.todo.<op>"`, success flag set after the awaited manager call / false in catch.

### Decisive source
```ts
const sessionScope = assertRequestedScope(input, defaults);   // payload can't override
case "update": {
	const taskId = requiredString(input.task_id, "task_id");
	assertSessionScope(await options.manager.getTask(taskId), defaults);  // fetched-row check FIRST…
	if (!input.expected_revision) {
		throw new Error("expected_revision is required for update");      // …then CAS demand
	}
// assertSessionScope: !task → "task does not exist" (existence-hiding);
// workspace session requires task.scope==="workspace" && resolve-equal workspaceRoot;
// global session rejects any non-global task.
```

**Flow:** zod safeParse (fail ⇒ `invalid_task_input` with first issue message) ⇒ require context.sessionId ("tasks requires a Hub session") ⇒ require resolvable session defaults ⇒ `assertRequestedScope` (rejects input.scope mismatch and any workspace_root that isn't resolve-equal to the session root BEFORE any manager call) ⇒ per-op: create forces scope/workspaceRoot from defaults (cwd only in workspace scope; modelSelection falls back to the session default); update fetch→scope-check→expected_revision; list filters pinned to sessionScope+root; get fetch→scope-check ⇒ all throws caught into `task_operation_failed`.
**Invariant:** The tool layer is a second authority boundary in front of the manager: even a hostile or confused agent payload cannot widen scope beyond the calling session, cannot name a privileged operation, and cannot mutate without an optimistic-concurrency revision.
**Probe:** `grep -cF 'expected_revision is required for update' sdk/packages/core/src/tasks/agenda-task-tool.ts` → 1 (:258). Test pins (`agenda-task-tool.test.ts`, 3 cases read whole): "cannot inspect another scope or request cancellation" — `{operation:"cancel"}` ⇒ `{ok:false, error:{code:"invalid_task_input"}}` and `manager.cancelTask` NEVER called (:155,:156); "pins list and create operations to the current session workspace" — escaped workspace_root ⇒ `task_operation_failed` with exactly one listTasks call; "captures usage telemetry for durable mutations".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.agenda-task-tool.executeTodoTaskOperation" });
// observed: Function lines 186-329 verbatim, byte-equal to the checkout whole-read
```

## Verdict
Adopt schema-level verb reduction, session-defaults-derived authority with double-sided scope checks (payload + fetched rows), existence-hiding errors, revision demands placed AFTER authorization, and mutation-only telemetry. Adapt verb sets and actor identity. Omit Cline's agenda manager. Coverage: no_recorded_issue both paths @ gen 2026-08-24T16:12:41Z; suite read whole; runner-BLOCKED honestly.
