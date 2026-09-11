<!-- capsule-v2 -->
# Task fanout — preserve order, release only acquired permits, steer before stopping

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory project `oh-my-pi`. **Path:** `packages/coding-agent/src/task/{index,executor}.ts`. **Question:** How does a task fanout remain deterministic under cancellation and runaway subagents?

## Source contract
**Path/Symbol:** `TaskTool.#runSyncSpawns` (1319+), `runSubagent` (executor.ts 2470s+; follow-up turn runner at 2536), `#getSpawnSemaphore`/`#releaseSpawnSemaphore` (638).
**Signature:** sync fanout returns an array in input order; subagent runner yields requests, usage, abort state, and salvage text.
**Data Shape:** spawn index, session semaphore, all-settled payloads, request budget, last assistant activity.

### Decisive source
```ts
// Every release funnels through here: the flag flips before the
// release so no path — acquire-time abort, executor failure, or a
// future refactor that reorders the branches — can return a permit
// twice. Releasing a permit this job never acquired would steal one
// from a running job and let a later spawn start past task.maxConcurrency.
const releasePermit = () => {
  if (!semaphoreHeld) return;
  semaphoreHeld = false;
  this.#releaseSpawnSemaphore();
};
try { await semaphore.acquire(runSignal); semaphoreHeld = true; }
catch { /* acquire-time abort falls through to the same settle path */ }
if (!semaphoreHeld || runSignal.aborted) {
  releasePermit(); progress.status = "aborted"; onSettled?.(true);
  throw new Error("Aborted before execution");
}
```

**Flow:** allocate stable spawn positions → acquire session permit (abort-aware acquire) → run each child → convert rejected work to an INDEXED result → merge in original order → steer once at soft budget → force-stop at the hard ceiling (1.5×) → salvage partial output. Acquire-time aborts still fire progress + `onSettled` so batch aggregate state never sticks at "running".

**Invariant:** a cancelled queued child NEVER releases a permit it did not acquire (single funnel + flag-before-release); partial work reports last useful activity rather than pretending success.

**Probe:** direct `test/task/task-spawn.test.ts:151–275` proves queue cancellation has no permit leak; `test/task/task-guards.test.ts:171–315` proves one soft notice then 1.5× hard stop and partial-output salvage.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "TaskTool executeSyncFanout runSubagent request budget", limit: 16, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.task.TaskTool" });
```

## Verdict
Adopt ordered fanout with indexed settled results, flag-guarded single-funnel permit release, and soft-then-hard budgets with salvage; adapt concurrency limits and budget multipliers to host policy; omit the IRC/hub follow-up surface unless porting the whole subagent manager.
