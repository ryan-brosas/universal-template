<!-- capsule-v2 -->
# Query-loop state machine — how does one `while(true)` generator replace recursion while surviving aborts, fallbacks, and 7 continue sites?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does the agent turn loop carry mutable cross-iteration state through recovery paths without losing invariants — and what must a porter replicate about its generator-based structure?

## queryLoop + State struct
**Path/Symbol:** `src/query.ts:queryLoop` (:241-1729), public wrapper `query` (:219-239); `type State` (:204-217).
**Signature:** `async function* queryLoop(params: QueryParams, consumedCommandUuids: string[]): AsyncGenerator<StreamEvent|RequestStartEvent|Message|TombstoneMessage|ToolUseSummaryMessage, Terminal>`; exported `query()` wraps it and fires `notifyCommandLifecycle(uuid,'completed')` for every drained queued command ONLY on normal return (:229-238).
**Data Shape:** `State = { messages; toolUseContext; autoCompactTracking; maxOutputTokensRecoveryCount; hasAttemptedReactiveCompact; maxOutputTokensOverride; pendingToolUseSummary; stopHookActive; turnCount; transition?: Continue }`. Loop-local (NOT on State): `taskBudgetRemaining`, `budgetTracker`, `config = buildQueryConfig()`, `using pendingMemoryPrefetch`. The outer `while(true)` destructures `state` at the top of each iteration so reads stay bare-name; every continue site writes a WHOLE new `state = {...}` object instead of 9 separate assignments.

### Decisive source
```ts
// Mutable cross-iteration state ... Continue sites write `state = { ... }`
// instead of 9 separate assignments.
let state: State = { messages: params.messages, /* ..., */ turnCount: 1,
                     maxOutputTokensRecoveryCount: 0,
                     hasAttemptedReactiveCompact: false }
const config = buildQueryConfig()          // snapshot ONCE per turn
using pendingMemoryPrefetch = startRelevantMemoryPrefetch(   // once per TURN
  state.messages, state.toolUseContext)     // prompt invariant across iterations
while (true) { /* destructure state → ... → state = next; continue */ }
```

**Flow:** per iteration: yield `stream_request_start` → increment `queryTracking.depth` (chainId stable, depth+1 per iteration :347-355) → context-reduction ladder (`applyToolResultBudget` BEFORE microcompact because cached MC matches by tool_use_id only :369-394 → HISTORY_SNIP snip → microcompact → CONTEXT_COLLAPSE projection BEFORE autocompact so collapse getting under threshold keeps granular context :428-447) → autocompact → blocking-limit preempt check (skipped when compaction JUST succeeded, for compact/session_memory fork agents that would deadlock, or when reactive-compact/collapse owns recovery :615-648) → stream from model with withheld-error filtering → post-stream recovery ladder → if no tool_use blocks: stop-hook/budget terminal path; else run tools → drain attachments → build next State → loop.
**Invariant:** (1) `feature()` gates must stay INLINE at guarded blocks (bun tree-shaking constraint — config.ts comment: "Intentionally excludes feature() gates"); (2) env/statsig gates ARE snapshotted once into `QueryConfig` because CACHED_MAY_BE_STALE may flip mid-stream — withhold and recover must see the SAME value (media gate hoisted to `mediaRecoveryEnabled` :626-627 "withhold-without-recover would eat the message"); (3) memory prefetch starts once per user turn, NOT per iteration ("per-iteration firing would ask sideQuery the same question N times"); (4) every continue site must reset exactly the counters its path needs — the normal tool-round site resets `maxOutputTokensRecoveryCount: 0, hasAttemptedReactiveCompact: false` (:1720-1721) but the stop-hook-blocking site PRESERVES `hasAttemptedReactiveCompact` (:1292-1297 "Resetting to false here caused an infinite loop: compact → still too long → error → stop hook blocking → … burning thousands of API calls").
**Probe:** no upstream test file covers query.ts directly (repo `tests/` = shell scripts only; coverage caveat). Deterministic probes: `grep -n "reason:" src/query.ts | grep -o "'[a-z_]*'" | sort -u` → ≥13 terminal/transition reasons incl. `'blocking_limit','image_error','model_error','aborted_streaming','aborted_tools','stop_hook_prevented','hook_stopped','max_turns','prompt_too_long','collapse_drain_retry','reactive_compact_retry','max_output_tokens_escalate','token_budget_continuation','next_turn'`; `grep -c "state = next" src/query.ts` → 7.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "queryLoop state transition", limit: 5, fields: ["signature","name","file"] });
// → locoagent.src.query.queryLoop Function src/query.ts 241-1729 (rank #1)
```

## Verdict
Adopt the whole-State-struct continue pattern, the once-per-turn vs per-iteration split for prefetch/config, and the preserve-vs-reset discipline on recovery guards; adapt the specific feature gates and analytics; omit ANT-only telemetry strings. Porting trap: converting this to plain recursion loses the `yield*` delegation contract that lets stopHooks stream progress messages through the same generator; another trap is resetting `hasAttemptedReactiveCompact` at the stop-hook site (documented infinite API-burn loop).
