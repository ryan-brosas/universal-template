<!-- capsule-v2 -->
# Task registry & kill dispatch — how does polymorphic background-task handling survive when only ONE operation is ever called polymorphically?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What does the shared Task interface actually contain, how are task IDs minted, and which implementations are feature-gated out of the registry?

## Kill-only interface over a seven-type union
**Path/Symbol:** `src/Task.ts:79-83` (`Task` type), `src/tasks.ts` (whole :1-39): `getAllTasks`/`getTaskByType`; `src/tasks/types.ts:5-46`: `TaskState` union + `isBackgroundTask`.
**Signature:** `type Task = { name: string; type: TaskType; kill(taskId: string, setAppState: SetAppState): Promise<void> }`; `getTaskByType(type: TaskType): Task | undefined`.
**Data Shape:** `TaskType = 'local_bash'|'local_agent'|'remote_agent'|'in_process_teammate'|'local_workflow'|'monitor_mcp'|'dream'`. Comment records that spawn/render were removed from the interface (#22546) because nothing calls them polymorphically — "All six kill implementations use only setAppState — getAppState/abortController were dead weight." `isBackgroundTask` requires status running/pending AND not (`isBackgrounded === false`) — the `'isBackgrounded' in task` check makes the field optional-by-structural-test for types lacking it.

### Decisive source
```ts
const LocalWorkflowTask: Task | null = feature('WORKFLOW_SCRIPTS')
  ? require('./tasks/LocalWorkflowTask/LocalWorkflowTask.js').LocalWorkflowTask
  : null
const MonitorMcpTask: Task | null = feature('MONITOR_TOOL')
  ? require('./tasks/MonitorMcpTask/MonitorMcpTask.js').MonitorMcpTask
  : null
export function getAllTasks(): Task[] {
  const tasks: Task[] = [LocalShellTask, LocalAgentTask, RemoteAgentTask, DreamTask]
  if (LocalWorkflowTask) tasks.push(LocalWorkflowTask)
  if (MonitorMcpTask) tasks.push(MonitorMcpTask)
  return tasks
}
```

**Flow:** consumers hold heterogeneous `TaskState` in `AppState.tasks` → any stop path resolves `getTaskByType(task.type)` → awaits `kill(taskId, setAppState)` → per-type implementation owns its own teardown.
**Invariant:** The registry must be built INSIDE `getAllTasks()` per call ("inline to avoid circular dependency issues with top-level const") — a module-level array of the four static tasks plus conditionally-required two breaks import cycles. A porter who hoists the registry to a top-level const reintroduces the cycle this shape exists to prevent.
**Probe:** `grep -n "spawn/render were never" src/Task.ts` (:77-78) and `grep -n "feature('WORKFLOW_SCRIPTS')" src/tasks.ts` (:8) and `grep -n "avoid circular dependency" src/tasks.ts` (:18).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getTaskByType getAllTasks", limit: 5 });
```

## Verdict
Adopt the kill-only interface and inline registry construction verbatim — shrinking an interface to its one polymorphic caller is the portable lesson. Adapt the feature-flag mechanism to your host's gating primitive. Omit the specific Bun `feature()` stubs.
