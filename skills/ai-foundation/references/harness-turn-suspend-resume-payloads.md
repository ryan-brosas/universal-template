<!-- capsule-v2 -->
# Harness suspend/resume payloads — how does an unfinished turn cross a process boundary without losing pending approvals or tool results?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** What exact envelope, validation, and nesting rules make a mid-turn suspension serializable — and why must resume-session state never carry pendings at top level?

## continue-turn payload + nested continuation under resume-session
**Path/Symbol:** `packages/harness/src/agent/harness-agent-session.ts` — `addPendingToolState` (:521–539), `suspendCurrentTurn` (:541–557), `toResumeStateWithContinuation` (:572–583); `packages/harness/src/agent/internal/lifecycle-state-validation.ts` :16–108; derivation of initial turnState in `harness-agent.ts` :456–467.
**Signature:** `suspendTurn(): Promise<HarnessAgentContinueTurnState>`; `validateLifecycleStateData({harness, state, expectedType}): Promise<STATE>`.
**Data Shape:** `{ type: 'continue-turn'|'resume-session', harnessId, specificationVersion: 'harness-v1', data (adapter-specific, schema-validated), pendingToolApprovals?, pendingToolResults?, continueFrom? }`.

### Decisive source
```ts
// lifecycle-state-validation.ts — the invariant that forces nesting
if (state.type === 'resume-session' && 'pendingToolApprovals' in state && state.pendingToolApprovals !== undefined) {
  throw new HarnessError({ message:
    'Resume session state cannot contain pending tool approvals; unfinished turns must be stored as `continueFrom`.' });
}
...
// session: idempotent suspension + pendings ride the CONTINUE payload
this.suspendedTurnState ??= (async () => {
  const raw = await options.session.doSuspendTurn();
  const validated = await validateLifecycleStateData({ harness: this.harness, state: raw, expectedType: 'continue-turn' });
  return this.addPendingToolState(validated);
})();
...
// harness-agent.ts createSession: resumed sessions re-derive WHERE they paused
turnState: effectiveContinueFrom == null ? 'idle'
  : effectiveContinueFrom.pendingToolApprovals != null && effectiveContinueFrom.pendingToolApprovals.length > 0
    ? 'awaiting-approval'
    : effectiveContinueFrom.pendingToolResults != null && effectiveContinueFrom.pendingToolResults.length > 0
      ? 'awaiting-tool-result'
      : 'suspended',
```

**Flow:** detach/stop with a non-idle turn call `suspendCurrentTurn`, wrap its validated continue-turn payload as `resumeSession.continueFrom` (`toResumeStateWithContinuation`), and end the local handle; the NEXT process passes `createSession({ sessionId, resumeFrom })`, whose validation recursively validates the nested continueFrom and whose turnState ladder restores exactly where the runtime paused.
**Invariant:** Suspension is idempotent per turn (`??=` promise memoization — stop() during an in-flight suspendTurn shares one payload); pendings live ONLY on continue-turn envelopes; every crossing validates type + specificationVersion + harnessId + optional adapter schema BEFORE the payload reaches the adapter.
**Probe:** deterministic probes: `grep -c 'suspendedTurnState ??=' packages/harness/src/agent/harness-agent-session.ts` → `1`; `grep -c 'must be stored as' packages/harness/src/agent/internal/lifecycle-state-validation.ts` → `2`; direct tests `harness-agent.test.ts:1265–1371` ("serializes and resumes a client-side tool result pause" — asserts `continueFrom.pendingToolResults` equals the recorded call), :1948/:1965 (reject resume-state with top-level pendings).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "validateLifecycleStateData", limit: 3 });
// verified live @9d9a73f — rank#1 :16-108; suspendCurrentTurn :541-557 total:1
```

## Verdict
Adopt the two-envelope model (continue-turn carries pendings; resume-session nests it) with recursive validation; adapt the schema-validation call to host's validator; omit Codex/Pi-specific `data` shapes.