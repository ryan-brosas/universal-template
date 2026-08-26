<!-- capsule-v2 -->
# Harness stream abort-vs-error settle — how does a user stop become an `abort` part while every other failure stays an `error`, without the consumer ever seeing both?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** An emit-callback adapter and a pull-based consumer disagree about failure shape — where do you convert rejection into an event, and how do you guarantee exactly ONE terminal part?

## Emit→pull bridge + single-terminal settle
**Path/Symbol:** `packages/harness/src/agent/internal/to-harness-stream.ts` — `toHarnessStream` (:32–75); `packages/harness/src/agent/internal/run-prompt.ts` — `settleFailure` (:148–172), error branch ordering (:709–730), suspend drain (:1024–1048).
**Signature:** `toHarnessStream({ invoke(emit): PromiseLike<PromptControl> }): { stream, control }`; `settleFailure(err)`.
**Data Shape:** bridge converts `control.done` rejection into a FINAL `{type:'error', error}` CHUNK then closes normally; closed-flag makes enqueue/close idempotent.

### Decisive source
```ts
// to-harness-stream.ts:24 — rejection becomes a discriminated-union EVENT, not a stream error
Promise.resolve(control.done).then(
  () => safeClose(),
  (err) => { safeEnqueue({ type: 'error', error: err }); safeClose(); },
).catch(() => {});
...
// run-prompt.ts: settle BEFORE translate-and-forward, or consumers see TWO terminal parts
if (value.type === 'error' && displayValue.type === 'error') {
  await waitForOutstandingHostToolExecutions();
  await telemetry.error(value.error);          // raw error (absolute paths) for diagnostics
  logBridgeError({ ... });
  settleFailure(displayValue.error);           // workDir-stripped error for the consumer
  return;
}
...
const settleFailure = (err: unknown) => {
  if (!input.isTurnSuspending?.()) input.onTurnFailed?.();   // suspension is NOT a failure
  if (input.abortSignal?.aborted) { result.abort({ error: err, ... }); return; }  // user stop ⇒ abort part
  result.fail(err);
};
```

**Flow:** adapter emits into the bridge → reader loop translates and forwards ASAP; on stream `error` events the loop settles FIRST and returns so the translated error part never also reaches the consumer; at drain time a suspending turn discards partial step content (`discardCurrentStepContent`) instead of fabricating a StepResult without finish-step.
**Invariant:** Exactly one terminal outcome per turn — abort (caller signal), fail (real error), or finish (finalFinish) — and an adapter rejection surfaces as an ordinary event chunk so iteration needs no try/catch. Display projections (stripWorkDir) are display-only; telemetry/diagnostics keep RAW errors for debuggability.
**Probe:** deterministic probes: `grep -c 'safeEnqueue' packages/harness/src/agent/internal/to-harness-stream.ts` → `3`; direct tests `to-harness-stream.test.ts:92–118` ("enqueues an error part and closes the stream when done rejects"), `harness-agent.test.ts:1087` ("settles an aborted turn with an abort part..."), :1055 ("keeps a turn unfinished when suspension closes its stream mid-step"). Companion capsule: harness-builtin-replay-split.md owns the replay-set invariant in this same file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "settleFailure", limit: 3 });
await mcp.codebase_memory.search_graph({ project: "ai", query: "toHarnessStream", limit: 3 });
// both verified live @9d9a73f — rank#1 line-exact (:158-172 / :32-75)
```

## Verdict
Adopt reject→event-chunk bridging and the pre-forward settle ordering; adapt terminal-part names to host's stream union; omit the suspension discard branch if host turns cannot be sliced.