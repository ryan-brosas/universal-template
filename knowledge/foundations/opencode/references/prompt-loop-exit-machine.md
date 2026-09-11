<!-- capsule-v2 -->
# Prompt turn-loop exit machine — when does the agent loop stop instead of calling the LLM again?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** What exact predicate ends a prompt run's while(true) loop, and which tool states are deliberately excluded from keeping it alive?

## Loop-exit gate with orphan carve-outs
**Path/Symbol:** `packages/opencode/src/session/prompt.ts` (`runLoop`, lines 1081–1341; exit gate :1100–1130; `isOrphanedInterruptedTool` :96–100).
**Signature:** `runLoop(sessionID): Effect<SessionV1.WithParts>` — internal body of `loop()` behind `state.ensureRunning`.
**Data Shape:** Per iteration: reload full history via `MessageV2.filterCompactedEffect`, destructure `MessageV2.latest(msgs)` into `{user, assistant, finished, tasks}`; `tasks` is the pending subtask/compaction queue popped each step. Exit needs FOUR things true at once: `lastAssistant.finish` set, finish ∉ {"tool-calls"}, `hasToolCalls === false`, and `lastAssistant.parentID === lastUser.id`.

### Decisive source
```ts
// prompt.ts:96-99 — cleanup()-marked aborts are NOT pending work
function isOrphanedInterruptedTool(part: SessionV1.ToolPart) {
  return part.state.status === "error" && part.state.metadata?.interrupted === true
}
// prompt.ts:1103-1116 — "stop" does NOT mean done if real tool calls exist
const hasToolCalls =
  lastAssistantMsg?.parts.some(
    (part) => part.type === "tool" && !part.metadata?.providerExecuted && !isOrphanedInterruptedTool(part),
  ) ?? false
if (
  lastAssistant?.finish &&
  !["tool-calls", "unknown"].includes(lastAssistant.finish) &&   // "unknown" added @0352100
  !hasToolCalls &&
  lastAssistant.parentID === lastUser.id
) { /* log orphan warning, break */ }
```

PASS-5 DRIFT NOTE (@0352100): the finish exclusion set grew from `["tool-calls"]` to `["tool-calls", "unknown"]` (prompt.ts :1113, mirrored at :1295) — a truncated/network-errored stream records finish `"unknown"`, and ending the turn on it would strand the conversation; paired with the new network_error→ResponseStreamError conversion (see network-error-finish-conversion.md).

**Flow:** reload messages → find latest assistant → compute `hasToolCalls` excluding `providerExecuted` parts AND interrupted orphans → if finish is terminal AND no live tool calls AND assistant belongs to the latest user message: warn about any orphan and `break` → else step++, pop task (subtask → `handleSubtask`, compaction → process), check overflow auto-compaction, build assistant shell, call LLM via processor.
**Invariant:** Some providers emit `finish: "stop"` even when tool calls are present — the loop MUST keep running so tool results go back to the model; only interrupted-orphan tool parts (`metadata.interrupted === true`) may be ignored, never retried as an assistant prefill. A porter who exits on "stop" unconditionally strands every tool call after a stop-finish.
**Probe:** `packages/opencode/test/session/prompt.test.ts:892` "loop continues when finish is stop but assistant has tool parts" (2 LLM calls, second text wins); `:503` "loop exits without an LLM request for interrupted orphan tool calls" (`llm.hits` length 0); `:2222` "does not loop empty assistant turns for a simple reply" (exactly 1 call).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "structured output tool schema", limit: 5 });
// file-scope sweep of the whole service:
await mcp.codebase_memory.search_graph({ project: "opencode", qn_pattern: "packages.opencode.src.session.prompt", limit: 20, detail: "ids" });
```

## Verdict
Adopt the four-clause exit predicate and both exclusion classes (`providerExecuted`, interrupted orphans); adapt the Effect/fiber wrapper to host runtime; omit the v1 event bridge details. Tests pin all three behaviors directly at HEAD.
