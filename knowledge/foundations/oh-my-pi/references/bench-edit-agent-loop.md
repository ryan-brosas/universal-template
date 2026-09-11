<!-- capsule-v2 -->
# Edit-benchmark agent loop — fixture isolation, event-driven verification, and per-run artifact capture

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you run one benchmarked agent turn-loop against an isolated fixture workspace — driving either in-process or RPC clients through one interface — and capture everything needed to score it?

## BenchmarkClient facade + env save/restore + JSONL event log + success composition
**Path/Symbol:** `packages/metaharness/adapters/edit/runner.ts` — `BenchmarkClient` (56-78), `runSingleTask` (1061-1492), `runConcurrentBenchmarkRun`+worker pool in `runBenchmark` (1906-2211), conversation dumps `writeConversationDump` (161-181).
**Signature:** `interface BenchmarkClient { start(); prompt(text); followUp(text); getSessionStats(); getLastAssistantText(); getMessages(); getState(); abort?(); dispose(); }`; `runSingleTask(task, runIndex, config, cwd, expectedDir, shared?): Promise<TaskRunResult>`.
**Data Shape:** per-run scratch dir under `runs/rb-<rand>/`; per-run JSONL log (`meta`, `prompt`, tool events, `stats before/after`, `response`, `result`); success = `verificationPassed && (!mustUseEditTool || editSucceeded) && (!mustUseReadTool || readUsed)`; session identity = deterministic `reb_<hash>` over provider/model/task/system/initial-prompt (provider-side caching keyed consistently across runs).

### Decisive source
```ts
const previousEnv = {
    PI_EDIT_VARIANT: process.env.PI_EDIT_VARIANT,
    PI_EDIT_FUZZY: process.env.PI_EDIT_FUZZY,
    ...
};
try { /* set PI_* knobs, start client, attempt loop */ }
finally {
    const restoreEnvKey = (key) => {
        const value = previousEnv[key];
        if (value === undefined) delete process.env[key];   // undefined ⇒ DELETE, not "undefined" string
        else process.env[key] = value;
    };
    restoreEnvKey("PI_EDIT_VARIANT"); ...
}
```
```ts
// Each worker takes one task at a time and launches all N runs for that
// task concurrently. The best run is chosen later via summarizeTaskRuns;
// taskConcurrency caps the number of in-flight tasks (not runs).
const worker = async (): Promise<void> => { while (true) { const task = taskQueue.shift(); if (!task) return; await runTaskAllRuns(task); } };
```

**Flow:** copy task fixtures into a fresh scratch dir → save the process env keys the config will set → apply edit-variant/fuzzy knobs + strict mode → construct ONE of two clients behind the same interface (`InProcessClient` by default with discovered shared infra — auth storage/LSP warm pools; or CLI `RpcClient` subprocess) → attempt loop (see retry-ladder capsule): deliver prompt/followUp, collect events, classify tool calls into stats/failure records, verify against expected fixtures (auto-format first when configured), break on verified match → snapshot the conversation (messages + system prompt + model + tools) and write a markdown dump next to copied artifacts → ALWAYS dispose client and restore env (undefined-sensitivity!) → worker-pool scheduling shuffles tasks once, caps concurrent TASKS, fans each task's N runs concurrently, and rebuilds a live result snapshot after every completion.
**Invariant:** parallel runs must be isolated (fresh fixture dir + unique provider-session identity only where inputs are identical) and the parent's environment must emerge untouched regardless of failure path — restoring `undefined` as deletion is the detail porters get wrong; every completed run appends its full event trail before any scoring reads it.
**Probe:** `packages/metaharness/adapters/edit/runner.test.ts:63-108` pins mid-flight snapshotting (`summarizes completed runs without requiring every scheduled run to finish`) and report-before-any-completion; `:361-410` pins the conversation-dump artifact layout (`task_weird/run-1.md` + artifacts dir copy).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "runSingleTask BenchmarkClient InProcessClient RpcClient writeConversationDump worker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any agent-evaluation harness: single client facade over in-process/subprocess modes, fixture-per-run isolation, env save/restore with undefined-aware deletion, JSONL evidence logs, live-rebuildable summaries. Adapt the knob names and client construction to your agent SDK; omit OMP-specific tool gating. Snapshot semantics and artifact layout directly test-pinned.
