<!-- capsule-v2 -->
# Cross-turn tool-use summaries — how does a ~1s side-model summary ride along with a 5-30s main stream without blocking anything?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How is an auxiliary model call overlapped with the turn so its output lands one iteration later, and what are the abort/subagent rules?

## pendingToolUseSummary promise relay
**Path/Symbol:** `src/query.ts` State field (:211), generation (:1411-1482), settlement (:1054-1060); generator `src/services/toolUseSummary/toolUseSummaryGenerator.ts:generateToolUseSummary`.
**Signature:** `nextPendingToolUseSummary = generateToolUseSummary({tools: toolInfoForSummary, signal, isNonInteractiveSession, lastAssistantText}).then(s => s ? createToolUseSummaryMessage(s, toolUseIds) : null).catch(() => null)` — stored on State, `await`ed at the TOP of the NEXT iteration.
**Data Shape:** per-tool info `{ name, input, output }` where output is found by scanning `toolResults` for the matching `tool_use_id`; result message carries all `toolUseIds`.

### Decisive source
```ts
// Yield tool use summary from previous turn — haiku (~1s) resolved during
// model streaming (5-30s)
if (pendingToolUseSummary) {
  const summary = await pendingToolUseSummary   // usually already resolved
  if (summary) { yield summary }
}
// ... after tools run, fire for the NEXT round without awaiting:
if (config.gates.emitToolUseSummaries && toolUseBlocks.length > 0 &&
    !toolUseContext.abortController.signal.aborted &&
    !toolUseContext.agentId /* subagents don't surface in mobile UI */) {
  nextPendingToolUseSummary = generateToolUseSummary({...}).catch(() => null)
}
```

**Flow:** tools finish → IF gate on AND there were tool blocks AND not aborted AND NOT a subagent → kick off the Haiku summary WITHOUT awaiting → store the promise in State → next iteration yields it just before deciding follow-up (by then the main stream consumed most of the wall-clock window). Gate source is env `CLAUDE_CODE_EMIT_TOOL_USE_SUMMARIES` snapshotted into `QueryConfig.gates` at turn start (config.ts :26-28).
**Invariant:** (1) `.catch(() => null)` — summary failure must NEVER fail the turn; (2) never start one when aborted or for subagents; (3) exactly-one-in-flight via State handoff — no accumulation across rounds; (4) the await point is BEFORE the `!needsFollowUp` branch so the summary still lands on terminal iterations... note the settlement sits AFTER the aborted-streaming early-return (:1015-1052), so an aborted turn silently drops the pending promise (acceptable: UI-only artifact).
**Probe:** coverage caveat (no upstream tests). Deterministic probes: `grep -n "pendingToolUseSummary" src/query.ts` → 5 sites (:211, :277, :1055-1059, :1159/1215/1242 resets, :1412-1481, :1722); every recovery continue-site sets it to `undefined` (dropping a stale cross-model summary is correct — it describes the discarded attempt).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "generateToolUseSummary", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the fire-carry-yield-later pattern for any cheap auxiliary inference; adapt the trigger conditions; omit the mobile-UI rationale if N/A. Porting trap: awaiting at generation time adds its latency to the critical path; yielding at the START of the next stream instead loses ordering vs. the new response's first tokens.
