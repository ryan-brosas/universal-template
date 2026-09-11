<!-- capsule-v2 -->
# killTask & agent-exit orphan sweep — what must a synchronous process-kill state transition clean up, and why do killed bash tasks swallow their own notification?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the full teardown set for a killed shell task, and how do background processes get prevented from outliving their spawning subagent?

## Null the three runtime handles, pre-set notified, purge the dead agent's queue
**Path/Symbol:** `src/tasks/LocalShellTask/killShellTasks.ts:16-46`: `killTask`; :53-76: `killShellTasksForAgent`.
**Signature:** `killTask(taskId: string, setAppState: SetAppStateFn): void`; `killShellTasksForAgent(agentId: AgentId, getAppState, setAppState): void`.
**Data Shape:** LocalShellTaskState runtime handles = `shellCommand` / `unregisterCleanup` / `cleanupTimeoutId`. Killed result: `status:'killed', notified:true, shellCommand:null, unregisterCleanup:undefined, cleanupTimeoutId:undefined, endTime`.

### Decisive source
```ts
task.unregisterCleanup?.()
if (task.cleanupTimeoutId) {
  clearTimeout(task.cleanupTimeoutId)
}
return { ...task, status: 'killed', notified: true, shellCommand: null,
         unregisterCleanup: undefined, cleanupTimeoutId: undefined,
         endTime: Date.now() }
...
// Purge any queued notifications addressed to this agent — its query loop
// has exited and won't drain them. killTask fires 'killed' notifications
// asynchronously; drop the ones already queued and any that land later sit
// harmlessly (no consumer matches a dead agentId).
dequeueAllMatching(cmd => cmd.agentId === agentId)
```

**Flow:** killTask kills+cleans the ShellCommand inside try/catch (logError — a throw must not skip the state transition), unregisters cleanup, clears any pending cleanup timer, transitions synchronously, then fire-and-forget `evictTaskOutput`. `killShellTasksForAgent` runs from runAgent.ts's finally block so "background processes don't outlive the agent that started them (prevents 10-day fake-logs.sh zombies)" — sweeps AppState for running shell tasks with that agentId and kills each.
**Invariant:** Pre-setting `notified:true` in the kill transition is what suppresses the later "exit code 137" completion notification (stopTask.ts :67 documents this as deliberate noise suppression — unlike AGENT tasks, whose AbortError notification carries extractPartialResult payload). The queue purge must happen even though notifications fire async — a dead agent's queue is never drained again.
**Probe:** `grep -n "10-day fake-logs.sh zombies" src/tasks/LocalShellTask/killShellTasks.ts` (:52) and `grep -n "exit code 137" src/tasks/stopTask.ts` (:67) and `grep -n "dequeueAllMatching(cmd => cmd.agentId === agentId)" src/tasks/LocalShellTask/killShellTasks.ts` (:75).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "killShellTasksForAgent", limit: 5 });
```

## Verdict
Adopt the teardown checklist (handles → timers → status → output eviction → queue purge) verbatim. Adapt which handles your process wrapper owns. Omit nothing — the finally-block orphan sweep is the whole point.
