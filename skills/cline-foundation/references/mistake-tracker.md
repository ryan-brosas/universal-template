<!-- capsule-v2 -->
# Mistake tracker — consecutive-failure budget with overridable limit decision

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** How does a runtime bound repeated failures (api errors, bad tool calls) while still letting the host decide "stop vs continue with guidance"?

## Counter with forceAtLimit jump; telemetry fires BEFORE the decision resolves
**Path/Symbol:** `sdk/packages/core/src/runtime/safety/mistake-tracker.ts:80-159` (`MistakeTracker.record`) + `:165-223` (pure helpers).
**Signature:** `record({iteration, reason:"api_error"|"invalid_tool_call"|"tool_execution_failed", details?, forceAtLimit?}) → {action:"continue", guidance?} | {action:"stop", message, reason?}`.
**Data Shape:** `maxConsecutiveMistakes` from config (`!max || next < max` ⇒ max=0/undefined means NEVER stop). Optional `onLimitReached(ctx)` returns a decision; optional `onLimitTelemetry(ctx)` is observability-only.

### Decisive source
```ts
const next = input.forceAtLimit && max ? max : this.consecutiveMistakes + 1;
...
this.options.onLimitTelemetry?.(limitContext);   // exactly once per hit,
                                                 // BEFORE the decision
...
try {
    return await callback(input);
} catch (error) {
    return {
        action: "stop",
        reason: error instanceof Error ? error.message : `maximum consecutive mistakes reached (${input.maxConsecutiveMistakes})`,
    };
}
```

**Flow:** every mistake emits a recoverable error event + warn log FIRST → at limit: telemetry hook fires unconditionally → decision resolved from callback or default stop ("maximum consecutive mistakes reached (N)") → a THROWN callback error also becomes stop (host bugs can't loop the run) → "continue" resets the counter to 0 and appends trimmed guidance as a recovery notice; "stop" builds the deterministic message: `Stopped after X/Y consecutive mistakes (reason) at iteration N. Error: … Decision: … Session state was preserved. Send a new prompt to resume from the latest state.` The orchestrator serializes record calls onto a promise chain (`activeTrackerWork`) because its event stream is sync but record is async, and a stop appends the message then aborts the active runtime.
**Invariant:** Counter reset happens ONLY on an explicit continue decision (and after successful turns in the orchestrator) — never on read; `forceAtLimit:true` jumps straight to max (used by hard loop-detection escalation so one pathological tool pattern consumes the whole budget at once); telemetry-before-decision guarantees the event even when onLimitReached throws.
**Probe:** `grep -cF 'input.forceAtLimit && max ? max : this.consecutiveMistakes + 1' .../mistake-tracker.ts` → 1; `grep -cF 'onLimitTelemetry?.(limitContext)' ...` → 1; `grep -cF 'maximum consecutive mistakes reached' ...` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "MistakeTracker record forceAtLimit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the counter semantics, throw-becomes-stop rule, and telemetry ordering; adapt reason enum and stop-message copy to host vocabulary; omit agentId/conversationId getter plumbing if hosts pass identity differently. Runner blocked honestly; battery greps green.
