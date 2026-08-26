<!-- capsule-v2 -->
# stopTask dispatch & typed stop errors — what does the shared stop entrypoint guarantee, and which notifications does it suppress vs preserve?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do TaskStopTool and the SDK stop_task control request share one stop path, and what are its failure modes?

## Validate → type-dispatch kill → selective suppression
**Path/Symbol:** `src/tasks/stopTask.ts` (whole :1-100): `StopTaskError`, `stopTask`.
**Signature:** `stopTask(taskId: string, context: StopTaskContext): Promise<StopTaskResult>` where result = `{ taskId, taskType, command: string | undefined }`; throws `StopTaskError(message, code)` with code ∈ `'not_found'|'not_running'|'unsupported_type'`.
**Data Shape:** context = `{ getAppState, setAppState }` only — stop needs no abortController of its own because each task's kill owns its own.

### Decisive source
```ts
const taskImpl = getTaskByType(task.type)
if (!taskImpl) {
  throw new StopTaskError(`Unsupported task type: ${task.type}`, 'unsupported_type')
}
await taskImpl.kill(taskId, setAppState)
// Bash: suppress the "exit code 137" notification (noise). Agent tasks: don't
// suppress — the AbortError catch sends a notification carrying
// extractPartialResult(agentMessages), which is the payload not noise.
if (isLocalShellTask(task)) {
  ...set notified:true...          // suppress XML completion notification
  if (suppressed) {
    emitTaskTerminatedSdk(taskId, 'stopped', {...})  // but close SDK bookend
  }
}
```

**Flow:** look up id → not found / not running (status !== 'running') / unknown type each throw a DISTINCTLY-CODED error so callers can map to user-facing messages → dispatch through the registry (`getTaskByType`) so every task type is stoppable through one door → shell-only post-kill suppression with direct SDK bookend emit ("Suppressing the XML notification also suppresses print.ts's parsed task_notification SDK event").
**Invariant:** The three failure codes are exhaustive and thrown BEFORE any state mutation. Suppression policy is per-type, not global: killing a bash task silences noise, killing an agent preserves its partial-result notification. The returned `command` field is the raw command for shells but `task.description` for everything else — consumers rendering "stopped X" must not assume it's always a command string.
**Probe:** `grep -n 'not_running' src/tasks/stopTask.ts` (:13) and `grep -n 'payload not noise' src/tasks/stopTask.ts` (:69) and `grep -n 'task.command : task.description' src/tasks/stopTask.ts` (:97).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "StopTaskError", limit: 5 });
```

## Verdict
Adopt the typed-error + registry-dispatch shape verbatim. Adapt error codes to your API surface. Omit SDK bookend re-emit if you have no event stream.
