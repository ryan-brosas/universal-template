<!-- capsule-v2 -->
# Settled-checkpoint steering — where do the two steering paths differ, and what races must be lost on purpose?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** When analysis finishes AFTER a new user prompt arrived, why must the fresh decision be discarded?

## agent_settled handler (`src/index.ts:232-327`)
**Path/Symbol:** `src/index.ts` `pi.on('agent_settled')` (:232-327); `userInputEpoch` counter :82-91; race check :292-298.
**Signature:** event handler; epoch = integer incremented on every interactive/rpc `input` and `before_agent_start`.
**Data Shape:** Decision delivery channel differs by path: mid-run steer uses `{deliverAs:'steer'}`, settled steer uses `{deliverAs:'followUp'}`.

### Decisive source
```ts
pi.on('input', e => { if (e.source === 'interactive' || e.source === 'rpc') userInputEpoch++; });
pi.on('before_agent_start', () => { userInputEpoch++; });

pi.on('agent_settled', async (_e, ctx) => {
  const inputEpochAtStart = userInputEpoch;      // snapshot BEFORE slow LLM call
  ...
  const decision = await analyze(ctx, state.getState()!, true, ineffectivePattern,
    undefined, streamingDelta => updateUI(... thinking ...));
  // A real user prompt supersedes a decision computed from the preceding
  // settled snapshot. Do not race that prompt or steer from stale context.
  if (userInputEpoch !== inputEpochAtStart) {
    updateUI(...watching...); return;            // DROP the decision entirely
  }
  if (decision.action === 'steer' && decision.message) {
    state.incrementIdleSteers();
    state.addIntervention({...});
    pi.sendUserMessage(decision.message, { deliverAs: 'followUp' });   // queued as user
  } else if (decision.action === 'done') {
    state.resetIdleSteers(); state.resetReframeTier();
    updateUI(...done...); state.stop(); disposeSession();              // stop AFTER showing done
  }
});
```

**Flow:** settle → subagent check FIRST (`checkChildPiProcesses`; wait 2s-poll/120s-cap then proceed with warning) → detectIneffectivePattern → escalate tier if detected & <4 → analyze with live thinking stream to widget → EPOCH RACE GATE → steer/done/watching branches. Mid-run path (`turn_end`, :201-226) is the same analyze but delivers via `'steer'` (immediate injection) and only at confidence ≥0.85.
**Invariant:** (1) The epoch race gate is unconditional — even a 'done' computed against stale context is discarded; user input always wins. (2) Steers are logged as interventions BEFORE sending, so pattern detection sees them even if delivery fails. (3) `done` resets idleSteers + reframeTier THEN stops — order matters because persist-on-stop would otherwise journal stale counters. (4) Subagent liveness gates the whole checkpoint: supervising while children run would judge incomplete work.
**Probe:** `tests/supervise-command.test.ts` kickstart idle/busy/append/edge suites (:120-362); epoch mechanism `src/index.ts:82-91` pinned by `grep -c "userInputEpoch++" src/index.ts` = 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "userInputEpoch inputEpochAtStart agent_settled deliverAs", limit: 8 });
```

## Verdict
Adopt epoch-style staleness gate for any async judge whose decision lands after arbitrary wall-time. Adapt delivery channels ('steer' vs 'followUp') to your host's message API. Omit subagent process-scraping if your host has no child processes.
