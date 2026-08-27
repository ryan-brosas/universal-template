<!-- capsule-v2 -->
# Harness session dual state machine — how do "session ended" and "turn unfinished" stay orthogonal without deadlocking reuse?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** A live agent handle needs both a lifecycle axis (detach/stop/destroy) and a turn-progress axis (idle → running → awaiting-X → suspended). What are the exact gating and cleanup rules so late async callbacks can't corrupt state?

## Two axes, gated entry, turn-scoped cleanup
**Path/Symbol:** `packages/harness/src/agent/harness-agent-session.ts` — states (:45–52), `requirePromptableTurn`/`requireContinuableTurn` (:585–613), `finishTrackedTurn` (:687–695), `endLocalHandle` (:697–704).
**Signature:** `turnState: 'idle'|'running'|'awaiting-approval'|'awaiting-tool-result'|'suspended'`; `sessionState: 'active'|'detached'|'stopped'|'destroyed'`.
**Data Shape:** pendingToolApprovals/pendingToolResults Maps keyed by approvalId/toolCallId; `turnSequence`/`activeTurnSequence` monotonic counter; optional `activePromptControl` keyed by turnId.

### Decisive source
```ts
private requireContinuableTurn(): void {
  if (this.turnState === 'awaiting-approval' || this.turnState === 'awaiting-tool-result'
      || this.turnState === 'suspended') return;
  if (this.turnState === 'running') throw new Error(`... already has a turn in progress.`);
  throw new Error(`... has no unfinished turn to continue.`);
}
...
private finishTrackedTurn(options: { turnId: number }): void {
  if (this.sessionState !== 'active') return;          // late callback after end: no-op
  if (this.activeTurnSequence !== options.turnId) return; // stale turn: no-op
  this.clearActivePromptControl(options.turnId);
  this.pendingToolApprovals.clear();                    // only the CURRENT turn resets pendings
  this.pendingToolResults.clear();
  this.suspendedTurnState = undefined;
  this.turnState = 'idle';
}
```

**Flow:** every entry point calls `requireReusableSession()` (throws unless active) THEN the axis-appropriate gate (`promptTurn`: idle only; `continueTurn`: one of three unfinished states) THEN `startTrackedTurn()`, which bumps the sequence, sets running, and mints a fresh settle-once prompt-control promise. Steering (`experimental_steerTurn`) re-validates FOUR conditions after awaiting the control promise (state, running, not-suspended, same turnId).
**Invariant:** Turn cleanup is turn-scoped AND session-scoped — a finish/fail callback from a superseded or ended session mutates nothing; pending approval/result maps survive across turns ONLY while that specific turn is unfinished.
**Probe:** deterministic probes: `grep -c 'requireContinuableTurn\|requirePromptableTurn' packages/harness/src/agent/harness-agent-session.ts` → `4`; `grep -c 'pendingToolApprovals.clear' packages/harness/src/agent/harness-agent-session.ts` → `1`; direct tests `harness-agent.test.ts:1431` ("continueStream() rejects when there is no unfinished turn"), :2507 ("session.destroy() is idempotent and rejects further turns"), :2690 ("hasUnfinishedTurn() reflects every turn lifecycle state").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "HarnessAgentSession requireContinuableTurn", limit: 4 });
// verified live @9d9a73f — rank#1 requireContinuableTurn :597-613
```

## Verdict
Adopt the two-axis FSM with sequence-keyed, no-op-on-stale callbacks; adapt state names to host vocabulary; omit the steering capability check if the host has no mid-turn injection.