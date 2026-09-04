<!-- capsule-v2 -->
# Prompt task dispatch — how do subtask parts and compaction tasks hijack the turn loop?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How does the loop execute a queued subtask as a synthetic Task-tool call, and what state transitions must a porter preserve on failure/interrupt?

## Subtask as first-class loop step
**Path/Symbol:** `packages/opencode/src/session/prompt.ts` (`handleSubtask`, lines 255–449; dispatch :1142–1147).
**Signature:** `handleSubtask({task, model, lastUser, sessionID, session, msgs})` — `task` is a `SessionV1.SubtaskPart` popped from `MessageV2.latest(msgs).tasks`.
**Data Shape:** Creates a real assistant message (`agent: task.agent`, zeroed tokens/cost) + a REAL `tool` part for `TaskTool.id` with `callID: ulid()` and status "running"; `taskArgs = {prompt, description, subagent_type, command}`; executes through the genuine `taskTool.execute(...)` with `extra: {bypassAgentCheck: true, promptOps}` and per-task `AbortController`; permission asks merge `Permission.merge(taskAgent.permission, session.permission ?? [])`.

### Decisive source
```ts
// prompt.ts:350-380 — failure is DATA on the tool part, never a loop crash
.pipe(
  Effect.catchCause((cause) => {
    const defect = Cause.squash(cause)
    error = defect instanceof Error ? defect : new Error(String(defect))
    return Effect.logError("subtask execution failed", { error, ... })
  }),
  Effect.onInterrupt(() => Effect.gen(function* () {
    taskAbort.abort()
    assistantMessage.finish = "tool-calls"          // interrupted child still yields control back
    assistantMessage.time.completed = Date.now()
    yield* sessions.updateMessage(assistantMessage)
    if (part.state.status === "running") { /* mark part status:"error", error:"Cancelled", keep metadata */ }
  })),
)
```

**Flow:** resolve optional per-task model override → mint assistant message + running Task tool-part → fire plugin hooks `tool.execute.before/after` → missing agent ⇒ typed NamedError listing available agents (published to `Session.Event.Error` too) → run taskTool → on result: completed part carries `{title, metadata, output, attachments}` (attachments get fresh PartIDs); on no-result: error part keeps prior metadata — `metadata: part.state.status === "pending" ? undefined : part.state.metadata` so a mid-run failure PRESERVES sessionId/model provenance while a never-started one drops it → if `task.command`, append a synthetic user message "Summarize the task tool output above and continue with your task." → `continue` loop.
**Invariant:** The subtask is represented in the transcript as an ordinary Task tool call — UI, permissions, and history replay all see the same shape. Interrupt must still finalize the assistant message (`finish: "tool-calls"`) or the parent session hangs busy. Failed subtasks degrade to error-string tool results that the model can read.
**Probe:** `packages/opencode/test/session/prompt.test.ts:920` "failed subtask preserves metadata on error tool state" (missing-model child ⇒ `state.metadata.sessionId/model` defined + "Tool execution failed"); `:1018` "running subtask preserves metadata after tool-call transition" (polls running part for metadata.sessionId then cancels); `:964` "subtask child inherits parent session external_directory allow".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", qn_pattern: "packages.opencode.src.session.prompt", limit: 20, detail: "ids" });
await mcp.codebase_memory.search_graph({ project: "opencode", query: "subtask agent child task", limit: 10 });
```

## Verdict
Adopt the transcript-shaped subtask representation, error-as-data part states, and the interrupt finalizer; adapt the Effect interruption semantics to host cancellation; omit the specific TaskTool wiring (covered by task-tool.md).
