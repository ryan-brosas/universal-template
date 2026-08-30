<!-- capsule-v2 -->
# Subagent failure propagation — how does the Task tool surface a failed child session instead of silently returning partial output?

**Source:** opencode (Slate-licensed monorepo) @ `dev@0352100` (NEW in drift wave 4643e65→0352100, `tool/task.ts` :213-223). **Question:** After awaiting a subagent session, which failure signals must the Task tool check BEFORE returning text to the model?

## The two-check post-await gate
**Path/Symbol:** `packages/opencode/src/tool/task.ts` `TaskTool` execute, after the await of `Session` run (:213-223).
**Signature:** checks on `result.info` (the child's assistant MESSAGE) then `result.parts` (its parts array); both failures `Effect.fail(new Error(...))`.
**Data Shape:** Check 1 — message-level: `result.info.role === "assistant" && result.info.error` ⇒ extract `error.data.message` when it's a string else `error.name`. Check 2 — part-level: `result.parts.findLast(item => item.type === "tool" && item.state.status === "error")` ⇒ use its `state.error`.

### Decisive source
```ts
// task.ts:213-223 — fail LOUDLY with the child's own error text; task_id included for tracing
if (result.info.role === "assistant" && result.info.error) {
  const message =
    "message" in result.info.error.data && typeof result.info.error.data.message === "string"
      ? result.info.error.data.message
      : result.info.error.name
  return yield* Effect.fail(new Error(`Subagent failed (task_id: ${nextSession.id}): ${message}`))
}
const failed = result.parts.findLast((item) => item.type === "tool" && item.state.status === "error")
if (failed?.type === "tool" && failed.state.status === "error") {
  return yield* Effect.fail(new Error(`Subagent failed (task_id: ${nextSession.id}): ${failed.state.error}`))
}
```

**Flow:** parent awaits child completion ⇒ message-error check first (whole-turn abort: overflow, provider death) ⇒ last-errored-tool-part check (child's tool blew up but turn "completed") ⇒ ONLY THEN `findLast(type==="text")` returns the child's final prose. Both failure envelopes carry the CHILD SESSION ID (`task_id:`) so the parent model can reference/retry the specific subagent.
**Invariant:** A subagent whose turn ended in error must NOT hand its partial text back as if it were the deliverable — before this change the parent saw a normal completion and could act on truncated work. Order matters: message-level errors supersede tool-part errors (a dead turn has no trustworthy final text). `findLast` picks the LAST errored tool — the one nearest the end state.
**Probe:** direct test — `packages/opencode/test/tool/task.test.ts` `:287 "execute surfaces child errors with a resumable task_id"` (asserts exact envelope `` `Subagent failed (task_id: ${child?.id}): Network connection lost` `` at :326) and `:330 "execute surfaces terminal child tool errors with a resumable task_id"` (permission-rejection message at :369); source pins:
```bash
grep -n 'Subagent failed (task_id' packages/opencode/src/tool/task.ts
```
expect exactly two hits (:218, :222).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "opencode", pattern: "Subagent failed", limit: 4 });
// rank-1 = packages.opencode.src.tool.task.TaskTool Variable task.ts :81-371 match lines 218;222 —
// the two failure arms themselves (multi-symbol BM25 returns web/share UI noise, not this file)
```

## Verdict
Adopt the post-await two-check failure gate with child-task-id error envelopes; adapt error types to host tool-result schema; omit opencode's agent/permission continuation plumbing.
