<!-- capsule-v2 -->
# registerTask resume-merge — how does re-registering a task preserve UI-held state without double-emitting task_started?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** When a backgrounded agent is resumed/replaced, which fields survive and when does the SDK bookend fire?

## Replacement detection via pre-state capture, SDK event only on first registration
**Path/Symbol:** `src/utils/task/framework.ts:77-117`: `registerTask`.
**Signature:** `registerTask(task: TaskState, setAppState: SetAppState): void`.
**Data Shape:** merges incoming task over any existing entry with the SAME id; carries forward five UI-held fields from the existing entry when it has `retain` (the LocalAgentTaskState discriminator): retain / startTime / messages / diskLoaded / pendingMessages.

### Decisive source
```ts
let isReplacement = false
setAppState(prev => {
  const existing = prev.tasks[task.id]
  isReplacement = existing !== undefined
  // Carry forward UI-held state on re-register (resumeAgentBackground
  // replaces the task; user's retain shouldn't reset)...
  const merged =
    existing && 'retain' in existing
      ? { ...task, retain: existing.retain, startTime: existing.startTime,
          messages: existing.messages, diskLoaded: existing.diskLoaded,
          pendingMessages: existing.pendingMessages }
      : task
  return { ...prev, tasks: { ...prev.tasks, [task.id]: merged } }
})
// Replacement (resume) — not a new start. Skip to avoid double-emit.
if (isReplacement) return
enqueueSdkEvent({ type: 'system', subtype: 'task_started', ... })
```

**Flow:** spawn/resume calls registerTask → if an entry existed, its user-held view state is grafted onto the fresh runtime state → `task_started` SDK event fires ONLY for genuinely new tasks so consumers see exactly one start bookend per lifecycle.
**Invariant:** The replacement flag must be captured INSIDE the updater (pre-write state), not read after — reading post-state would make every registration look like a replacement. And the merge predicate is `'retain' in existing` (field presence), not a type check, because framework.ts deliberately does not import the concrete task types.
**Probe:** `grep -n "not a new start" src/utils/task/framework.ts` (:101) and `grep -n "'retain' in existing" src/utils/task/framework.ts` (:88) and `grep -n "user's just-appended prompt" src/utils/task/framework.ts` (:86).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "registerTask", limit: 5 });
```

## Verdict
Adopt the merge-field list + single-bookend rule verbatim. Adapt which fields are "UI-held" to your client. Omit the workflowName/prompt extra fields unless you carry that taxonomy.
