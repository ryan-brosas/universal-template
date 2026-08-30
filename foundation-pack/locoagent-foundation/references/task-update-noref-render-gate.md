<!-- capsule-v2 -->
# updateTaskState no-op discipline — how does a 25-line state helper keep 18 UI subscribers from re-rendering the world every second?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the reference-equality contract every task-state updater must follow?

## Same-reference return means skip-the-spread
**Path/Symbol:** `src/utils/task/framework.ts:48-72`: `updateTaskState`; consumed by every kill/complete/fail/poll path in `src/tasks/**`.
**Signature:** `updateTaskState<T extends TaskState>(taskId: string, setAppState: SetAppState, updater: (task: T) => T): void`.
**Data Shape:** updater receives the current typed task; returning THE SAME OBJECT REFERENCE signals "nothing changed". Any new object (even field-identical) is treated as a change and re-renders subscribers.

### Decisive source
```ts
setAppState(prev => {
  const task = prev.tasks?.[taskId] as T | undefined
  if (!task) {
    return prev
  }
  const updated = updater(task)
  if (updated === task) {
    // Updater returned the same reference (early-return no-op). Skip the
    // spread so s.tasks subscribers don't re-render on unchanged state.
    return prev
  }
  ...
})
```

**Flow:** RemoteAgentTask's 1s poller leans on this hardest — "No log growth and status unchanged → nothing to report. Return same ref so updateTaskState skips the spread and 18 s.tasks subscribers (REPL, Spinner, PromptInput, ...) don't re-render" (:699-707 of RemoteAgentTask.tsx). Guards that return the untouched task (`if (task.status !== 'running') return task`) are therefore load-bearing performance code, not style.
**Invariant:** NEVER return a fresh object from a guard/no-op branch. A `{...task}` unconditional spread at 1Hz × N tasks re-renders the whole REPL surface every tick; conversely a real transition MUST return a new object or the change silently never lands.
**Probe:** `grep -n "don't re-render on unchanged" src/utils/task/framework.ts` (:60) and `grep -c "18 s.tasks" src/tasks/RemoteAgentTask/RemoteAgentTask.tsx` (1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "updateTaskState", limit: 5 });
```

## Verdict
Adopt the same-reference-means-no-op contract verbatim — it composes with any immutable store. Adapt the generic typing to your state union. Omit nothing; the helper is complete.
