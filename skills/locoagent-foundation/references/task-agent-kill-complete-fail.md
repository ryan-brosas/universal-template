<!-- capsule-v2 -->
# Agent-task kill/complete/fail & eviction grace — what do all three terminal transitions share, and why does retain block eviction?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the common terminal-transition shape for local_agent tasks and how does the panel-grace period interact with user-held views?

## Shared teardown set; evictAfter = retain ? undefined : now + 30s
**Path/Symbol:** `src/tasks/LocalAgentTask/LocalAgentTask.tsx:281-303`: `killAsyncAgent`; :412-432: `completeAgentTask`; :437-456: `failAgentTask`; :309-315 `killAllRunningAgentTasks`; :322-332 `markAgentsNotified`.
**Signature:** `killAsyncAgent(taskId: string, setAppState: SetAppState): void` (also the Task.kill impl); cleanup registered at spawn via `registerCleanup(async () => killAsyncAgent(agentId, setAppState))`.
**Data Shape:** every transition: guard running → `task.unregisterCleanup?.()` → new object with `status`, `endTime: Date.now()`, `abortController: undefined`, `unregisterCleanup: undefined`, `selectedAgent: undefined`. Terminal ones add `evictAfter: task.retain ? undefined : Date.now() + PANEL_GRACE_MS`.

### Decisive source
```ts
export function killAsyncAgent(taskId, setAppState): void {
  let killed = false;
  updateTaskState<LocalAgentTaskState>(taskId, setAppState, task => {
    if (task.status !== 'running') { return task; }
    killed = true;
    task.abortController?.abort();
    task.unregisterCleanup?.();
    return { ...task, status: 'killed', endTime: Date.now(),
      evictAfter: task.retain ? undefined : Date.now() + PANEL_GRACE_MS,
      abortController: undefined, unregisterCleanup: undefined,
      selectedAgent: undefined };
  });
  if (killed) { void evictTaskOutput(taskId); }
}
```

**Flow:** AgentTool completes → `completeAgentTask(result)` keys off `result.agentId` (taskId === agentId for this type) → notification is NOT sent here ("sent by AgentTool via enqueueAgentNotification"). Kill aborts the controller; the AbortError catch in the runner sends the notification carrying `extractPartialResult(agentMessages)` — deliberately NOT suppressed because it carries payload. `retain:true` (user viewing the transcript) makes evictAfter undefined = never auto-evict; framework's evict gate reads `(evictAfter ?? Infinity) > Date.now()`.
**Invariant:** The killed flag must be captured inside the updater so output eviction fires only on a real transition. Dropping `selectedAgent` on terminal prevents a stale agent-definition reference from pinning memory after death. Bulk paths (`killAllRunningAgentTasks`, `markAgentsNotified`) exist precisely because aggregate notifications replace per-agent ones.
**Probe:** `grep -n "evictAfter: task.retain ? undefined" src/tasks/LocalAgentTask/LocalAgentTask.tsx` (:294/:424/:448) and `grep -cn "sent by AgentTool via enqueueAgentNotification" src/tasks/LocalAgentTask/LocalAgentTask.tsx` (2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "killAsyncAgent completeAgentTask", limit: 5 });
```

## Verdict
Adopt the shared terminal shape + retain-grace interaction verbatim. Adapt PANEL_GRACE_MS to your UI dwell time. Omit SDK summary emission unless you carry the progress-summary service.
