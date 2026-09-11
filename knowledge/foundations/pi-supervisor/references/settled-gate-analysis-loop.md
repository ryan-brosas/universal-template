<!-- capsule-v2 -->
# Settled-gate analysis loop — why agent_settled is the only trusted checkpoint and what happens on steer/done there

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** At which lifecycle point may the supervisor trust that the conversation snapshot is final enough to steer or declare done, and what must happen in each outcome branch?

## agent_settled checkpoint fan-out
**Path/Symbol:** `src/index.ts:default` (`pi.on('agent_settled', ...)` at :232-327).
**Signature:** `async (_event, ctx: ExtensionContext) => Promise<void>` registered inside the extension default export.
**Data Shape:** Reads full branch messages via `extractMessages(ctx)`; consumes `state.getState()!` (non-null asserted after `isActive()` gate); decision is `{ action: 'continue'|'steer'|'done', message?, reasoning, confidence, asi? }`.

### Decisive source
```ts
pi.on('agent_settled', async (_event, ctx) => {
    currentCtx = ctx;
    if (!state.isActive()) return;
    const inputEpochAtStart = userInputEpoch;
    ...
    const decision = await analyze(
      ctx,
      state.getState()!,
      true /* fully settled checkpoint */,
      ...
    );
    // A real user prompt supersedes a decision computed from the preceding
    // settled snapshot. Do not race that prompt or steer from stale context.
    if (userInputEpoch !== inputEpochAtStart) { ...return; }
    if (decision.action === 'steer' && decision.message) {
      state.incrementIdleSteers();
      state.addIntervention({ message: decision.message, reasoning: decision.reasoning, timestamp: Date.now(), asi: decision.asi });
      ...
      pi.sendUserMessage(decision.message, { deliverAs: 'followUp' });
    } else if (decision.action === 'done') {
      state.resetIdleSteers();
      state.resetReframeTier();
      updateUI(ctx, widgetState, state.getState(), { type: 'done' });
      state.stop();
      disposeSession();
```

**Flow:** gate on active → record input epoch → wait out child subagents → check ineffective pattern → escalate tier if detected and tier < 4 → analyze with `agentIsIdle=true` → epoch recheck → branch: steer = increment idleSteers + persist intervention + UI + `sendUserMessage(deliverAs:'followUp')`; done = reset counters + show done + stop + dispose; continue = back to watching.
**Invariant:** `agent_settled` fires only after auto-retries, overflow-compaction recovery, and queued follow-ups are all complete — steering from any earlier event races an unfinished run. Steer messages are recorded as interventions BEFORE being sent so a crash mid-send still leaves the audit trail. `done` always resets BOTH idleSteers and reframeTier and disposes the supervisor session.
**Probe:** `grep -c "deliverAs: 'followUp'" src/index.ts` → 4 (three kickstart sends at :116/:453/:500 share the value with the settled-steer send; mid-run steer alone uses `'steer'`). Direct test: `tests/ephemeral-supervision.test.ts` pins session-load/compaction arms; `tests/supervise-command.test.ts:186` "when agent is idle" pins kickstart behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "agent_settled userInputEpoch stale decision race", limit: 10 });
```

## Verdict
Adopt the settled-checkpoint rule (analyze only when the host guarantees quiescence; re-check user-input staleness AFTER paying for analysis). Adapt event names and message-delivery channels to your host. Omit pi's specific `willRetry` compaction-retry semantics unless your host has the same retry-then-resume behavior (see compaction-survival capsule).
