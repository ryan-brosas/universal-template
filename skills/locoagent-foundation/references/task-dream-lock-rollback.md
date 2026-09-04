<!-- capsule-v2 -->
# Dream task & consolidation-lock rewind — how does a UI-only surfacing task make an invisible subagent killable, and why must killing it rewind a file mtime?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How is the dream (memory-consolidation) agent registered as a task, and what extra side effect does its kill path own?

## Lock mtime IS the lock; kill rewinds it
**Path/Symbol:** `src/tasks/DreamTask/DreamTask.ts` (whole :1-157): state, `registerDreamTask`, `addDreamTurn`, `completeDreamTask`, `failDreamTask`, `DreamTask.kill`.
**Signature:** `registerDreamTask(setAppState, opts: { sessionsReviewing: number; priorMtime: number; abortController: AbortController }): string`.
**Data Shape:** phase is only `'starting'|'updating'` — the prompt has a 4-stage structure but "we don't parse it. Just flip from 'starting' to 'updating' when the first Edit/Write tool_use lands". `filesTouched` documented as INCOMPLETE ("misses any bash-mediated writes... Treat as 'at least these were touched'"). `turns` capped at MAX_TURNS=30 via `slice(-(MAX_TURNS - 1)).concat(turn)`. `priorMtime: number` stashed at registration.

### Decisive source
```ts
async kill(taskId, setAppState) {
  let priorMtime: number | undefined
  updateTaskState<DreamTaskState>(taskId, setAppState, task => {
    if (task.status !== 'running') return task
    task.abortController?.abort()
    priorMtime = task.priorMtime
    return { ...task, status: 'killed', endTime: Date.now(),
             notified: true, abortController: undefined }
  })
  // Rewind the lock mtime so the next session can retry. Same path as the
  // fork-failure catch in autoDream.ts. If updateTaskState was a no-op
  // (already terminal), priorMtime stays undefined and we skip.
  if (priorMtime !== undefined) {
    await rollbackConsolidationLock(priorMtime)
  }
}
```

**Flow:** autoDream forks a consolidation agent and registers this pure-UI task so it appears in the footer pill/Shift+Down dialog ("The dream agent itself is unchanged — this is pure UI surfacing via the existing task registry") → addDreamTurn dedupes touched paths via Set-add filter and skips empty no-op updates entirely → completion/failure set `notified:true` immediately ("dream has no model-facing notification path (it's UI-only), and eviction requires terminal + notified").
**Invariant:** The consolidation lock's freshness is its mtime — a killed dream that leaves a fresh mtime would block future consolidations forever; rollback to the stashed prior mtime makes kill equivalent to never having started. The priorMtime-undefined sentinel doubles as the already-terminal guard. Empty-turn updates must return the SAME reference (render discipline).
**Probe:** `grep -n 'rewind the lock mtime' src/tasks/DreamTask/DreamTask.ts` (:39, call site :150-152) and `grep -n 'eviction requires terminal + notified' src/tasks/DreamTask/DreamTask.ts` (:111) and `grep -n 'but we' src/tasks/DreamTask/DreamTask.ts` (:21, phrase spans two lines).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "registerDreamTask rollbackConsolidationLock", limit: 5 });
```

## Verdict
Adopt the surfacing-only wrapper pattern + lock-rollback-on-kill verbatim. Adapt what "lock" means in your system. Omit turn/touched tracking if your surface needs only a spinner.
