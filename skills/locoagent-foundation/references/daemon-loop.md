<!-- capsule-v2 -->
# Daemon loop with per-cycle locking — how does a long-running poller stay stoppable within seconds and share the platform between cycles?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does a daemon that runs a workflow every N minutes take a `stop` command promptly, and why does it grab and release the platform lock EVERY cycle?

## Stop-signal polling + lock-between-cycles
**Path/Symbol:** `scripts/workflow-engine.ts`:`daemon` command, `daemonLoop` (`:565-732`).
**Signature:** CLI: `daemon --id <id> [--interval <minutes>]` (default 60; validated positive integer).
**Data Shape:** Daemon marks state with `pid = process.pid`, `mode = 'daemon'` so `summary` can render "Mode: daemon (long-running, polling)"; each cycle still records a full `WorkflowRun` in history.

### Decisive source
```ts
if (platform && !acquireLock(platform, id!)) {
  console.log(`[daemon] Platform "${platform}" busy; skipping cycle ${cycleCount}.`)
} else {
  try {
    // Run the executor asynchronously (spawnSync blocks event loop, breaking setTimeout)
    const proc = Bun.spawn(['bun', 'run', executorPath, '--config', configJson], {...})
    const timeoutId = setTimeout(() => { proc.kill() }, 10 * 60 * 1000)
    execStdout = await new Response(proc.stdout).text()
    execExitCode = await proc.exited
    ...
    const run = finalizeRun(freshState, freshWs, execStdout, execExitCode)
    freshWs.status = 'running'                    // re-mark: finalizeRun set idle
    ;(freshWs as any).pid = process.pid
    ;(freshWs as any).mode = 'daemon'
  } finally { if (platform) releaseLock(platform, id!) }
}
// Wait for interval, checking stop signal every 10 seconds
while (waited < intervalMs) {
  await new Promise(r => setTimeout(r, Math.min(10_000, intervalMs - waited)))
  waited += 10_000
  const checkWs = loadState().workflows[id!]
  if (!checkWs || checkWs.status === 'stopped') { /* cleanup metadata */ return }
}
```

**Flow:** init: refuse if already running, mark running+pid+mode → loop: read state for a stop signal (missing entry counts as stopped) → acquire lock for THIS cycle only (busy ⇒ skip the cycle, don't queue) → spawn executor async (never spawnSync — it blocks the event loop and freezes the timers) with 10-min kill timer → finalize run then restore running/pid/mode → release lock (platform is free while idle) → wait interval in ≤10 s slices, re-reading the stop signal each slice → on exit or crash, always clear pid/mode and fall back to idle.
**Invariant:** The daemon must never hold the platform lock while idle (other workflows/orchestrators may run between cycles), must react to `stop` within one 10-second slice rather than at the next fire, and must clean up daemon metadata on EVERY exit path including fatal errors. Executor success keeps overall status 'running'; only an explicit stop signal ends the loop.
**Probe:** No direct test for the daemon loop (coverage caveat — source-grounded). Deterministic probe: `search_graph --project locoagent --query "daemonLoop"` resolves `locoagent.scripts.workflow-engine.daemonLoop`; `summary` renders mode/pid/logFile from the same state keys.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "daemon interval cycle stop signal workflow", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt per-cycle lock acquisition/release, sliced-interval stop polling, async spawn with kill timer inside a daemon, and metadata cleanup on all exits. Adapt interval default and slice size. Omit nothing from the finally-release rule — holding the lock across the sleep window is the classic porting bug that starves every other workflow.
