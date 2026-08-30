<!-- capsule-v2 -->
# Workflow lifecycle state machine — how do external processes start, stop, and monitor long-running pipelines through one shared JSON state file?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does an agent (or any caller) drive background workflows through idle→running→idle/stopped states without corrupting state when a stop signal races execution?

## Lifecycle transitions around prepareRun/finalizeRun
**Path/Symbol:** `scripts/workflow-engine.ts`:`prepareRun`, `finalizeRun`, `executeWorkflow` (`:183-247`, `:269-316`).
**Signature:** `prepareRun(id): { def, ws, state, executorPath, configJson }`; `finalizeRun(state, ws, stdout, exitCode, stderr?): WorkflowRun`.
**Data Shape:** `StateFile { version: 1, workflows: Record<id, WorkflowState> }`; `WorkflowState { status: 'idle'|'running'|'stopped', lastRun: WorkflowRun|null, runCount, history: WorkflowRun[] }`; `WorkflowRun { startedAt, finishedAt, status: 'success'|'failed'|'partial', stepsCompleted, stepsTotal, error?, output? }`. History hard-trimmed to last 30 runs (`ws.history.length > 30 → slice(-30)`).

### Decisive source
```ts
// finalizeRun — result classification from the executor's LAST stdout line
let output: Record<string, unknown> = {}
if (stdout) {
  try {
    const lines = stdout.trim().split('\n')
    const lastLine = lines[lines.length - 1]!
    output = JSON.parse(lastLine)          // machine contract: one JSON result line
  } catch (_) {
    output = { rawOutput: stdout.slice(-500) }
  }
}
...
run.status = 'success'
if (exitCode !== 0) {
  run.status = 'failed'
  run.error = stderr?.slice(-300) || `exit code ${exitCode}`
} else if (run.stepsCompleted < run.stepsTotal) {
  run.status = 'partial'                   // partial completion is its own status
}
ws.status = 'idle'; ws.lastRun = run; ws.runCount++; ws.history.push(run)
```

**Flow:** `prepareRun` rejects a second start when `status === 'running'`, flips idle→running and persists BEFORE spawning → executor spawned with `--config <json>` and a 10-minute kill timer → after exit, the engine RE-LOADS state from disk (`freshState`) because `stop` may have flipped status during the run → `finalizeRun` classifies the run and appends history → `reset` is the only path from `stopped` back to `idle`.
**Invariant:** Every mutation of a workflow entry inside `orchestrate` is wrapped in an in-process `withStateMutex` promise chain because `saveState` rewrites the WHOLE file — two interleaved load-modify-save sequences would clobber sibling entries. After a spawn, always re-read state from disk instead of reusing the pre-spawn object. Cross-process races are handled by the platform lock (see `platform-lock.md`), not this mutex.
**Probe:** No direct bun:test exists for the engine CLI (coverage caveat — claims are source-grounded). Deterministic probe: `search_graph --project locoagent --name-pattern "^(prepareRun|finalizeRun|executeWorkflow)$"` resolves all three with these exact line ranges; `workflows/state.json` consumers (`checkWorkflowStopped` in each executor) pin the same schema.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "finalizeRun workflow state", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the idle/running/stopped state machine, the last-stdout-line JSON result contract, success/failed/partial classification, history cap at 30, and the in-process state mutex for whole-file rewrites. Adapt paths, timeouts (10 min here), and command surface to the host. Omit the Bun-specific spawn calls if porting off Bun; keep the re-read-before-finalize rule regardless.
