<!-- capsule-v2 -->
# Streaming tool executor — how do tools run while the response is still streaming, safely?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How are tool_use blocks executed as they arrive mid-stream while keeping result order, sibling-error blast radius, and interrupt semantics correct?

## StreamingToolExecutor
**Path/Symbol:** `src/services/tools/StreamingToolExecutor.ts` — class `StreamingToolExecutor` (:40-519): `addTool` (:76-124), `canExecuteTool` (:129-135), `processQueue` (:140-151), `executeTool` (:265-405), `getCompletedResults` (:412-440 sync generator), `getRemainingResults` (:453-490 async generator), `discard` (:69-71), `markToolUseAsComplete` (:521-530). Status FSM: `queued|executing|completed|yielded` (:19).
**Signature:** `addTool(block, assistantMessage)` called once per parsed tool_use block DURING streaming; consumers drain via sync `getCompletedResults()` between chunks and await `getRemainingResults()` after stream end.
**Data Shape:** Per-tool TrackedTool holds its own results buffer + pendingProgress queue; results yield in RECEIPT order, not completion order — a later fast tool never overtakes an earlier serial tool.

### Decisive source
```ts
// :45-48 two-controller abort topology
// Child of toolUseContext.abortController. Fires when a Bash tool errors
// so sibling subprocesses die immediately instead of running to completion.
// Aborting this does NOT abort the parent — query.ts won't end the turn.
private siblingAbortController: AbortController
// :355-363 Bash-only sibling kill
if (isErrorResult) {
  thisToolErrored = true
  // Only Bash errors cancel siblings. Bash commands often have implicit
  // dependency chains (e.g. mkdir fails → subsequent commands pointless).
  // Read/WebFetch/etc are independent — one failure shouldn't nuke the rest.
  if (tool.block.name === BASH_TOOL_NAME) {
    this.hasErrored = true
    this.siblingAbortController.abort('sibling_error')
  }
}
// :304-318 child→parent bubble-back EXCEPT for sibling_error/interrupt/discard
toolAbortController.signal.addEventListener('abort', () => {
  if (signal.reason !== 'sibling_error' && !parent.aborted && !this.discarded) {
    this.toolUseContext.abortController.abort(toolAbortController.signal.reason)
  }
}, { once: true })
```

**Flow:** addTool resolves concurrency safety ONCE at enqueue (schema-parse failure or predicate throw ⇒ `false` = serial-conservative) → processQueue starts queued tools whenever executing-set is empty or all-executing ∧ candidate are concurrency-safe; a NON-safe tool BLOCKS the scan (order barrier) → each executeTool wraps runToolUse with its own child controller (of the executor's sibling controller) → mid-flight abort checks inject synthetic error tool_results with THREE distinct reasons: `user_interrupted` (REJECT_MESSAGE + memory-correction hint; respects per-tool `interruptBehavior()` — 'block' tools return null = keep running on plain interrupts), `sibling_error` ("Cancelled: parallel tool call <desc> errored", skipped for the tool that itself errored via thisToolErrored flag), `streaming_fallback` (post-discard) → results marked yielded exactly once by the draining generators → contextModifiers applied only for SERIAL tools inline; concurrent-tool modifiers unsupported (in-source NOTE).

**Invariant:** (1) Bash is the ONLY error that kills siblings — implicit dependency chains justify it; independent read tools fail in isolation. (2) Child-abort bubble-back is asymmetric BY DESIGN: sibling_error and discarded-fallback aborts stay local (the turn continues), any other reason (e.g., permission-dialog cancelAndAbort #21056) MUST reach the parent or the turn hangs. (3) Unknown tool names complete instantly with an error tool_result (never stall the queue). (4) discard() flips a flag consulted lazily — queued tools synthesize errors when they start; running ones see 'streaming_fallback' on next update; getCompletedResults returns nothing after discard (query.ts recreates a fresh executor instead). (5) hasUnfinishedTools counts everything not-yet-yielded, so getRemainingResults terminates only after ALL results (synthetic included) have been handed over.

**Probe:** coverage caveat — no upstream tests. Deterministic pins: `grep -n "Only Bash errors cancel siblings" src/services/tools/StreamingToolExecutor.ts` (:356); `grep -n "does NOT abort the parent" src/services/tools/StreamingToolExecutor.ts` (:47); `grep -n "#21056 regression" src/services/tools/StreamingToolExecutor.ts` (:300); graph resolves `src.services.tools.StreamingToolExecutor.StreamingToolExecutor` (sole class node).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "StreamingToolExecutor sibling abort concurrency queued", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt receipt-order buffering, the Bash-only sibling-kill scope, the three-reason synthetic-result taxonomy, and the asymmetric child-abort bubble; adapt interruptBehavior per tool to host needs; omit the concurrent-contextModifier gap only if you also forbid modifiers on parallel tools. Porting trap: killing all siblings on ANY error turns independent reads into collateral cancellations; bubbling sibling_error up to the query controller ends the whole turn.
