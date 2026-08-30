<!-- capsule-v2 -->
# Auto-compaction activation — when and how does a product session actually fire compaction, retry an overflow, and avoid re-firing on stale usage?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** Where is the kernel's `shouldCompact/compact()` actually wired at runtime, and what gate ladder prevents both missed compaction and infinite re-compaction?

## Session-level trigger plane (dynamic wiring the graph cannot see)
**Path/Symbol:** `packages/coding-agent/src/core/agent-session.ts:AgentSession._checkCompaction` (:2050-2154) → `AgentSession._runAutoCompaction` (:2166-2348). Inbound callers (trace): `_checkCompaction` ← `{prompt, _handlePostAgentRun}`; `_runAutoCompaction` ← `_checkCompaction`.
**Signature:** `_checkCompaction(assistantMessage, skipAbortedCheck = true): Promise<boolean>` — the boolean drives whether the post-run loop calls `agent.continue()`.
**Data Shape:** inputs: last assistant message (usage, stopReason, provider/model, timestamp), model contextWindow/maxTokens, compaction settings; outputs: fired? + continuation hint.

### Decisive source
```ts
// stale-fire guard: pre-compaction assistant messages never re-trigger
const compactionEntry = getLatestCompactionEntry(this.sessionManager.getBranch());
const assistantIsFromBeforeCompaction =
    compactionEntry !== null && assistantMessage.timestamp <= new Date(compactionEntry.timestamp).getTime();
if (assistantIsFromBeforeCompaction) return false;
// Case 1/2: overflow or recoverable truncation → compact, retry ONCE
if (this._overflowRecoveryAttempted) { /* emit failure */ return false; }
this._overflowRecoveryAttempted = true;
...messages.pop-if-assistant...
return await this._runAutoCompaction("overflow", willRetry);
// Case 3: threshold with zero/error-usage fallback estimate
const directContextTokens = assistantMessage.usage ? calculateContextTokens(assistantMessage.usage) : 0;
if (assistantMessage.stopReason === "error" || directContextTokens === 0) { contextTokens = estimateContextTokens(messages).tokens; }
if (shouldCompact(contextTokens, contextWindow, settings)) return await this._runAutoCompaction("threshold", false);
```

**Flow:** enabled? → not aborted? → same-model guard for overflow errors (a small old model's overflow must not compact for a switched larger model) → stale-timestamp guard → overflow/recoverable-length branch (compact-and-retry once, latch `_overflowRecoveryAttempted`, drop failed assistant from agent state but keep it in session history) → threshold branch (usage-backed tokens, else message-size estimate) → `_runAutoCompaction` runs extension interception (`session_before_compact` cancel/replace), default summarizer, appends compaction entry, rebuilds agent state, strips a trailing error/length message before continuing.
**Invariant:** after any compaction, no pre-compaction usage or error may re-fire it (timestamp guards in BOTH branches); overflow recovery retries exactly once; the return value only asks for `continue()` when the turn was interrupted (`willRetry`) or messages are queued.
**Probe:** `packages/coding-agent/test/suite/regressions/8328-zero-usage-auto-compaction.test.ts` spies on `_runAutoCompaction`: zero-usage + big user message ⇒ called once with `("threshold", false)`; short context ⇒ not called. BLOCKED live this pass: the suite transitively imports `ai/src/models.generated.ts` (gitignored generated catalogs); behavior confirmed by direct read of test + source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", query: "auto compaction session run trigger threshold context window reserve", limit: 15 });
// executed live this pass: ranked _runAutoCompaction :2166-2348 (#1); search_graph name_pattern ".*_checkCompaction"
// located :2050-2154; trace_path inbound confirmed dynamic activation {prompt, _handlePostAgentRun} — closing the
// leaf's recorded "zero inbound CALLS edges" blind spot.
```

## Verdict
Adopt the gate ladder (enabled/aborted/same-model/stale-guard/retry-once-latch/estimate-fallback) as the activation contract around any compaction kernel. Adapt settings plumbing to your host. Omit extension event names verbatim. Coverage: `no_recorded_issue` ×2 cited paths at generation 2026-08-24T16:11:21Z.
