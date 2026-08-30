<!-- capsule-v2 -->
# Tool-call cleanup ladder — how do half-finished tool parts get closed when the stream dies mid-call?

**Source:** opencode (Slate-licensed monorepo) @ `dev@0352100`; Codebase Memory `opencode`. **Question:** When the LLM stream aborts or fails between tool-input-start and tool-result, what exact terminal state must every in-flight part reach?

## Cleanup ordering
**Path/Symbol:** `packages/opencode/src/session/processor.ts` `cleanup` (:539-597); support: `readToolCall` :129-142 (deletes registry entry when its part vanished), `settleToolCall` :123-127 (Deferred.succeed + Effect.ignore), `failToolCall` :186-205.
**Signature:** `cleanup(): Effect<void>` — runs via `Effect.ensuring(cleanup())` after EVERY process attempt (success, failure, retry exhaustion, interrupt).
**Data Shape:** iterates `ctx.toolcalls` values; each pending Deferred gets a 250ms bounded await (`Effect.timeout("250 millis")` + ignore), then any STILL-registered call has its part forced to `{status:"error", error:"Tool execution aborted", metadata:{...meta, interrupted:true}}`.

### Decisive source
```ts
// processor.ts:571-594 — grace-await THEN force-close; interrupted flag rides metadata
yield* Effect.forEach(
  Object.values(ctx.toolcalls),
  (call) => Deferred.await(call.done).pipe(Effect.timeout("250 millis"), Effect.ignore),
  { concurrency: "unbounded" },
)
for (const toolCallID of Object.keys(ctx.toolcalls)) {
  const match = yield* readToolCall(toolCallID)
  if (!match) continue
  ...
  state: {
    ...part.state,
    status: "error",
    error: "Tool execution aborted",
    metadata: { ...metadata, interrupted: true },
    time: { start: ..., end },
  },
}
```

**Flow:** snapshot patch flush FIRST (any un-flushed file changes become a patch part :540-553), then open text part gets end-timestamped and persisted, then reasoning parts end-stamped + map cleared, then the tool ladder above, finally `assistantMessage.time.completed = Date.now()` + message update (:595-596). The 250ms grace exists because tool executions settle their own Deferreds concurrently — a just-finishing tool wins the race and completes normally; only stragglers are force-closed as aborted. `readToolCall` returning undefined (part deleted elsewhere) removes the registry entry instead of writing.
**Invariant:** A completed tool part is NEVER overwritten by cleanup — `failToolCall`/the loop only touch parts still in `ctx.toolcalls`, and `completeToolCall` settles+removes the entry on success (:160-184). Force-closed parts must carry `interrupted:true` in metadata so downstream UI can distinguish abort from genuine tool error. Every exit path funnels through `ensuring(cleanup)`; adding an early return inside `process` that skips it strands running parts forever.
**Probe:** direct pins (execute from repo root):
```bash
grep -n 'interrupted: true' packages/opencode/src/session/processor.ts
grep -n 'Tool execution aborted' packages/opencode/src/session/processor.ts
```
expect one hit each (:589, :588).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "cleanup toolcalls Deferred timeout ensuring", limit: 6 });
```

## Verdict
Adopt the settle-then-force-close ladder with bounded grace and the interrupted-metadata marker; adapt timing constants and part schema to host; omit the snapshot-patch coupling if the host has no shadow-git.
