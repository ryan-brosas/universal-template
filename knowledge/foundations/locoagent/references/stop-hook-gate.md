<!-- capsule-v2 -->
# Stop-hook terminal gate — how can a hook force the agent to keep working, and what runs before/after the hook itself?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the exact contract for hooks that block turn completion (vs. prevent continuation), and which side-effects are ordered around them?

## handleStopHooks
**Path/Symbol:** `src/query/stopHooks.ts:handleStopHooks` (:65-473); consumers src/query.ts:1267-1306; executor `src/utils/hooks.ts:executeStopHooks`.
**Signature:** `async function* handleStopHooks(messagesForQuery, assistantMessages, systemPrompt, userContext, systemContext, toolUseContext, querySource, stopHookActive?): AsyncGenerator<StreamEvent|RequestStartEvent|Message|Tombstone|ToolUseSummaryMessage, StopHookResult>` where `StopHookResult = { blockingErrors: Message[]; preventContinuation: boolean }`.
**Data Shape:** hook results stream as progress messages (`toolUseID`, `HookProgress.data.command`) and attachments typed `hook_success | hook_non_blocking_error | hook_error_during_execution`; a blocking error becomes an `isMeta` user message built from `getStopHookMessage(result.blockingError)`.

### Decisive source
```ts
if (result.blockingError) {
  const userMessage = createUserMessage({ content: getStopHookMessage(result.blockingError), isMeta: true })
  blockingErrors.push(userMessage); yield userMessage
}
// ...in query.ts:
if (stopHookResult.blockingErrors.length > 0) {
  const next: State = {
    messages: [...messagesForQuery, ...assistantMessages, ...stopHookResult.blockingErrors],
    /* ... */ stopHookActive: true,
    maxOutputTokensRecoveryCount: 0,
    hasAttemptedReactiveCompact,   // PRESERVED — see invariant 3
    transition: { reason: 'stop_hook_blocking' },
  }; state = next; continue
}
```

**Flow:** save cache-safe params snapshot FIRST for main-thread sources only (`repl_main_thread`/`sdk` — consumed by REPL `/btw` and SDK side_question regardless of prompt-suggestion settings :70-77) → job classifier (TEMPLATES): awaited under a 60s `.unref()` timer race so state.json lands before the turn returns ("otherwise `claude list` shows stale state") → bare-mode skips background bookkeeping (prompt suggestion, memory extraction, auto-dream) → CHICAGO_MCP computer-use cleanup MAIN THREAD ONLY ("a subagent's stopHooks releasing it leaves the main thread's cleanup seeing isLockHeldLocally()===false" :159-163) → executeStopHooks consumed streaming → per-hook duration matched by `command + first unassigned entry` because "Hooks run in parallel" (:242-253) → summary system message if any hooks ran + error notification with transcript shortcut → THEN teammate ladder: TaskCompleted hooks for each in-progress task owned by this teammate, then TeammateIdle hooks, each with the SAME blocking/prevent contract and its own toolUseID from progress messages. Abort during any hook ⇒ return `{blockingErrors: [], preventContinuation: true}` after yielding an interruption message.
**Invariant:** (1) `stopHookActive: true` on the retry State is what makes the NEXT round's hook invocation receive `stopHookActive ?? false` — the re-entrancy one-shot sentinel; (2) `hasAttemptedReactiveCompact` must be preserved across the blocking retry (resetting it caused a documented thousands-of-API-calls infinite loop, :1292-1297); (3) hook EXECUTION errors are caught at the boundary and downgraded to a user-visible warning system message with `{blockingErrors:[], preventContinuation:false}` (:456-472) — a crashing hook never blocks or crashes the turn; (4) blockingErrors are appended AFTER assistantMessages in next State's messages (API ordering: tool_results then user turns).
**Probe:** coverage caveat (no upstream tests for this file). Deterministic probes: `grep -n "preventContinuation\|blockingError" src/query/stopHooks.ts | wc -l` → ~20 sites across both ladders; `grep -n "unref()" src/query/stopHooks.ts` pins the 60s classifier race (:127-131); `sed -n '159,163p' src/query/stopHooks.ts` verbatim main-thread-only rationale.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "handleStopHooks blockingErrors", limit: 5, fields: ["signature","name","file"] });
// → locoagent.src.query.stopHooks.handleStopHooks Function src/query/stopHooks.ts 65-473 (only hit)
```

## Verdict
Adopt the two-outcome hook contract (block-with-feedback vs. prevent-and-stop) and the crash-downgrade boundary; adapt which background bookkeeping surrounds hooks; omit the teammate/task ladder unless you have multi-agent task ownership. Porting trap: treating a thrown hook error as a blocking error lets a broken hook hold the agent hostage; forgetting `stopHookActive` re-entry marking lets the same hook loop forever.
