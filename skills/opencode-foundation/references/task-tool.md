<!-- capsule-v2 -->
# Task tool — subagent delegation with background mode

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a coding agent spawn a subagent (foreground or background) without the caller duplicating its work?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/task.ts` (360 lines): `id = "task"` (:24), `Parameters` (:44-47), `execute`; `deriveSubagentSessionPermission` (`agent/subagent-permissions`).
**Signature:** `execute({description, prompt, subagent_type, task_id?, background?})` — `background=true` launches the subagent asynchronously and returns immediately; otherwise awaits and returns the result.
**Data Shape:** `Parameters = {description: string (3-5 words), prompt: string, subagent_type: string, task_id?: string, background?: boolean}`; background-mode output tells the caller NOT to sleep/poll/duplicate the task.

### Decisive source
```ts
// background mode: launches the subagent asynchronously and returns immediately
"Background mode: background=true launches the subagent asynchronously and returns immediately."
"DO NOT sleep, poll for progress, ask the task for status, or duplicate this task's work — avoid working with the same files or topics it is using."
"Work on non-overlapping tasks, or briefly tell the user what you launched and end your response."
```

**Flow:** caller provides a short description + prompt + subagent type; the task tool spawns a subagent session (with derived permissions). Foreground awaits the result; background returns immediately and notifies on completion. The background-mode output explicitly instructs the caller to work on non-overlapping tasks.
**Invariant:** background tasks notify on completion automatically; the caller must not duplicate the task's work or poll for status.
**Probe:** `packages/opencode/test/tool/task.test.ts` (foreground returns the subagent result; background returns immediately and notifies; subagent permissions derived correctly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "TaskTool task subagent background prompt subagent_type", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the subagent-delegation tool with foreground/background modes and explicit non-overlap guidance; adapt the subagent type registry and permission derivation to host; omit the Effect service wiring unless the target uses Effect.
