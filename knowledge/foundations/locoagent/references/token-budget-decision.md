<!-- capsule-v2 -->
# Token-budget continue/stop decision — how do you decide whether a long agent turn should keep going or stop, using a diminishing-returns heuristic?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a token-budgeted agent turn is near its limit, how does the engine decide to nudge the model to continue vs. force a stop — and what distinguishes "still making progress" from "diminishing returns"?

## BudgetTracker + checkTokenBudget: continuation gating by progress-vs-diminishing-returns
**Path/Symbol:** `src/query/tokenBudget.ts` (whole file :1-93): `createBudgetTracker` (:13-20), `checkTokenBudget` (:45-93), constants `COMPLETION_THRESHOLD = 0.9` (:3) and `DIMINISHING_THRESHOLD = 500` (:4). Consumed by `src/query.ts` `:280` (`createBudgetTracker()` gated on `feature('TOKEN_BUDGET')`) and `:1309` (`checkTokenBudget(...)` in the turn loop).

**Signature:** `createBudgetTracker(): BudgetTracker`; `checkTokenBudget(tracker, agentId: string | undefined, budget: number | null, globalTurnTokens: number): TokenBudgetDecision` where `TokenBudgetDecision = ContinueDecision | StopDecision`.

**Data Shape:** `BudgetTracker = { continuationCount: number; lastDeltaTokens: number; lastGlobalTurnTokens: number; startedAt: number }`. `ContinueDecision = { action:'continue'; nudgeMessage; continuationCount; pct; turnTokens; budget }`. `StopDecision = { action:'stop'; completionEvent: { continuationCount; pct; turnTokens; budget; diminishingReturns: boolean; durationMs } | null }`. `pct = Math.round((turnTokens / budget) * 100)`; `deltaSinceLastCheck = globalTurnTokens - tracker.lastGlobalTurnTokens`.

### Decisive source
```ts
const COMPLETION_THRESHOLD = 0.9
const DIMINISHING_THRESHOLD = 500

export function checkTokenBudget(tracker, agentId, budget, globalTurnTokens): TokenBudgetDecision {
  if (agentId || budget === null || budget <= 0) {
    return { action: 'stop', completionEvent: null }        // no budget → never continue
  }
  const turnTokens = globalTurnTokens
  const pct = Math.round((turnTokens / budget) * 100)
  const deltaSinceLastCheck = globalTurnTokens - tracker.lastGlobalTurnTokens

  const isDiminishing =
    tracker.continuationCount >= 3 &&
    deltaSinceLastCheck < DIMINISHING_THRESHOLD &&
    tracker.lastDeltaTokens < DIMINISHING_THRESHOLD

  if (!isDiminishing && turnTokens < budget * COMPLETION_THRESHOLD) {
    tracker.continuationCount++
    tracker.lastDeltaTokens = deltaSinceLastCheck
    tracker.lastGlobalTurnTokens = globalTurnTokens
    return { action: 'continue', nudgeMessage: getBudgetContinuationMessage(pct, turnTokens, budget),
             continuationCount: tracker.continuationCount, pct, turnTokens, budget }
  }

  if (isDiminishing || tracker.continuationCount > 0) {
    return { action: 'stop', completionEvent: { continuationCount: tracker.continuationCount,
             pct, turnTokens, budget, diminishingReturns: isDiminishing,
             durationMs: Date.now() - tracker.startedAt } }
  }
  return { action: 'stop', completionEvent: null }
}
```

**Flow:** The tracker is created once at turn start (`startedAt` stamps the wall clock; `continuationCount`/`lastDeltaTokens`/`lastGlobalTurnTokens` start at 0). Each pass through the turn loop calls `checkTokenBudget` with the current turn's token output and the resolved budget. If there is no budget (`agentId` set — sub-agent path — or `budget === null/<=0`), it stops immediately with no completion event — never nudges. Otherwise: `pct` = percent of budget consumed; `deltaSinceLastCheck` = how many tokens the model produced since the last check. The model is allowed to continue only while it is NOT diminishing AND under 90% of budget; on continue, the tracker records the delta and bumps the continuation count, and the caller (`src/query.ts:1316-1328`) appends the `nudgeMessage` as a meta user message to push the model onward. Once diminishing (≥3 continuations AND both the current and previous deltas < 500 tokens — i.e. the model is stalling) OR the budget is ≥90% consumed OR a continuation already happened, it stops. If it stops after having made progress, it emits a `completionEvent` (with `diminishingReturns` flag and elapsed `durationMs`); if it never got going, `completionEvent` is null.

**Invariant:** A budgeted turn must never run unbounded: continuation is a *privilege* that requires both (a) real progress (`deltaSinceLastCheck` and the prior delta both ≥ 500 tokens — two consecutive small deltas ⇒ diminishing returns) and (b) headroom (`turnTokens < 0.9 * budget`). The `continuationCount >= 3` gate means the model gets at most a few nudges before the diminishing check engages. The `agentId || budget===null || budget<=0` early return is the safety valve — sub-agent turns and unbudgeted turns are NEVER nudged (a porter who drops this guard would let every turn run past budget). `startedAt` is captured at tracker creation, so `durationMs` measures the whole turn, not the decision loop. The nudge is a *meta* user message (`isMeta: true`), so it does not pollute the visible conversation.

**Probe:** No direct test exists for `src/query/tokenBudget.ts` (coverage caveat — source-grounded). Deterministic probes: grep-pinned constants `COMPLETION_THRESHOLD` :3 / `DIMINISHING_THRESHOLD` :4; the no-budget early return :51-53; the diminishing predicate `continuationCount >= 3 && delta < 500 && lastDelta < 500` :59-62; the continue gate `!isDiminishing && turnTokens < budget * 0.9` :64; `search_graph` resolves `checkTokenBudget` :45-93 / `createBudgetTracker` :13-20 line-exact; `trace_path` `checkTokenBudget` → inbound caller `src/query.ts:1309` (feature-gated `TOKEN_BUDGET`). Port with a unit test asserting: budget `null` ⇒ stop/null; `agentId` set ⇒ stop/null; two consecutive <500 deltas after ≥3 continuations ⇒ stop with `diminishingReturns:true`; small delta under 90% ⇒ continue and nudge count increments.

## Get live surrounding code
**Retrieve:** `codebase-memory-mcp cli search_graph --project locoagent --query "checkTokenBudget" --detail ids`; `codebase-memory-mcp cli get_code_snippet --project locoagent --symbol "checkTokenBudget"`; `codebase-memory-mcp cli trace_path --project locoagent --symbol "checkTokenBudget" --direction inbound`.

**Verdict:** Adopt — the continue/stop decision engine is a portable, reusable contract for any token-budgeted agent loop that must bound a long turn without hard-failing. Adapt the thresholds (90%, 500 tokens, ≥3 continuations) and the nudge-message wording to your budget model.
