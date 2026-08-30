<!-- capsule-v2 -->
# Task-based tool authoring (`registerToolTask`) — how does a server expose a long-running tool as a pollable task instead of blocking the `tools/call` response?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** What is the exact three-callback shape a server implements for a task-based tool, and which ordering/ownership invariants keep the background run from corrupting the task lifecycle?

## createTask / getTask / getTaskResult over an injected taskStore
**Path/Symbol:** `src/everything/tools/simulate-research-query.ts` (whole file, 345L: schema :13–21; STAGES :24–29; module state map :35–45; background runner `runResearchProcess` :55–160; report generator :165–225; registration + callbacks :236–320; interpretation completer data :325–345). Registered via `server.experimental.tasks.registerToolTask(name, config, { createTask, getTask, getTaskResult })` (:242–318) with `execution: { taskSupport: "required" }` (:251) — the tool can ONLY be invoked as a task. Wired in `tools/index.ts` inside `registerConditionalTools` (NOT the static batch) because it reads live client capabilities at registration time.

**Signature:** `createTask(args, extra) → Promise<CreateTaskResult>`; `getTask(args, extra) → Promise<GetTaskResult>` (delegates to `extra.taskStore.getTask(extra.taskId)`); `getTaskResult(args, extra) → Promise<CallToolResult>`. `extra.taskStore` exposes `createTask({ ttl, pollInterval })`, `updateTaskStatus(taskId, status, message?)`, `storeTaskResult(taskId, "completed"|"failed", result)`, `getTask`, `getTaskResult`. `extra.sendRequest(request, schema)` carries outbound server→client requests.

**Data Shape:** module-level `const researchStates = new Map<string, ResearchState>()` keyed by taskId holds `{ topic, ambiguous, currentStage, clarification?, completed, result? }`; entry deleted only inside `getTaskResult` after the stored result is fetched (:309–317).

### Decisive source
```ts
// tools/simulate-research-query.ts:263-296 — durable-create BEFORE starting work,
// fire-and-forget with a .catch that terminalizes the task on failure
createTask: async (args, extra): Promise<CreateTaskResult> => {
  const validatedArgs = SimulateResearchQuerySchema.parse(args);
  // Create the task in the store
  const task = await extra.taskStore.createTask({ ttl: 300000, pollInterval: 1000 });
  ...
  // Start background research (don't await - runs asynchronously)
  runResearchProcess(task.taskId, validatedArgs, extra.taskStore, extra.sendRequest)
    .catch((error) => {
      console.error(`Research task ${task.taskId} failed:`, error);
      extra.taskStore.updateTaskStatus(task.taskId, "failed", String(error))
        .catch(console.error);
    });
  return { task };
},
```

**Flow:** `tools/call` arrives with task execution requested → `createTask` re-validates args through the zod schema itself (the SDK does not guarantee pre-validation of task-tool args), creates the store record FIRST, seeds the private state map, spawns the runner WITHOUT awaiting, returns `{ task }` → client polls via the SDK's generic `tasks/get` handling (the tool's own `getTask` callback just forwards to the store) → runner walks STAGES, calling `updateTaskStatus(taskId, "working", "<stage>...")` per stage; at stage index 2 it flips status to `"input_required"` BEFORE sending its elicitation, then back to `"working"` after resolution → terminal: `state.completed = true`, result stored via `storeTaskResult(taskId, "completed", result)` → first `tasks/result` fetch deletes the state-map entry.

**Invariants:**
1. **Durable-create-before-respond:** `taskStore.createTask()` MUST complete before `return { task }`; the runner starts only afterwards, so a crash between them leaves no orphan promise claiming a task exists.
2. **Never let a background rejection vanish:** the un-awaited runner gets `.catch(...)` that writes a `"failed"` status — an unhandled rejection would leave the task stuck in `working` until TTL.
3. **Ambiguity degrades by capability, not by error:** `ambiguous: validatedArgs.ambiguous && clientSupportsElicitation` (:275) bakes the capability check into the STATE at creation time, and elicitation failure is caught into a default-interpretation string (:131–138) — the task never fails merely because the user couldn't be asked.
4. **Status transitions bracket the blocked call:** set `input_required` BEFORE awaiting input, restore `working` AFTER — a porter who elicits without flipping status leaves clients polling blind.
5. **State cleanup belongs on the result-read path**, not on completion: completion stores the payload; consumption deletes it.

**Probe:** `src/everything/__tests__/tools.test.ts:1058–1140` — mock `registerToolTask` captures handlers; fake timers drive the staged runner; asserts `sendRequest` called with `expect.objectContaining({ relatedTask: { taskId: 'task-abc' } })` when ambiguous, and completes with `storeTaskResult('task-def', 'completed', …)` without any sendRequest when not ambiguous. Note the test drives `taskHandlers.createTask(args, { taskStore, sendRequest })` DIRECTLY — the handler contract is the surface, not the transport.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "registerToolTask createTask getTask getTaskResult taskStore storeTaskResult", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the three-callback split (create/get/getResult) over an injected store, durable-create-before-spawn, fail-the-task `.catch`, and capability-baked degradation; adapt the store to your persistence layer and the staged-work simulation to your real operation; omit the demo report content and hardcoded 5-minute TTL/poll values (tune per workload). The spec-side twin contract lives in `tasks-extension-lifecycle.md` (five-status machine); this capsule is the SERVER AUTHORING side the reference implementation exercises.
