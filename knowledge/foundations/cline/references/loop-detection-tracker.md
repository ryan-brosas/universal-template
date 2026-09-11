<!-- capsule-v2 -->
# Loop detection tracker — soft/hard verdicts over consecutive identical tool calls

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** What is the minimal state machine that catches a model stuck calling the same tool with the same arguments, without false-positives on argument order?

## Canonical-keyed signature; soft fires ONCE at exactly N, hard at >= M
**Path/Symbol:** `sdk/packages/core/src/runtime/safety/loop-detection.ts:20-162` (`LoopDetectionState`, `toolCallSignature`, `checkRepeatedToolCall`, `LoopDetectionTracker`).
**Signature:** `inspect(call: {name, input}) → {kind:"ok"|"soft"|"hard", message?}`; defaults `{softThreshold:3, hardThreshold:5}`.
**Data Shape:** State = `{lastToolName, lastToolSignature, consecutiveIdenticalCount}` — ONE previous call remembered (consecutive run only, not a window).

### Decisive source
```ts
export function toolCallSignature(input: unknown): string {
    if (input == null) return "null";
    if (typeof input === "string") return input;
    ...
    return JSON.stringify(sortKeys(input));   // recursively key-sorted
}
...
return {
    softWarning: state.consecutiveIdenticalCount === config.softThreshold,
    hardEscalation: state.consecutiveIdenticalCount >= config.hardThreshold,
};
```

**Flow:** before each tool executes the runtime feeds the call → identical name+signature increments the run counter else resets to 1 → soft at EXACTLY 3 (`===`, so the notice fires once, not on every subsequent call), hard at ≥5. The runtime wiring (session-runtime-orchestrator.ts:1288-1323): soft ⇒ append a user-role recovery notice ("consider trying a different approach"); hard ⇒ enqueue mistake record with `forceAtLimit:true` whose stop outcome appends the stop message and aborts the active run (`finishReason:"aborted"`). Disabled entirely by `execution.loopDetection === false`; muted while an abort from the tracker chain is already in flight.
**Invariant:** Signatures must be canonically serialized (sorted keys) or `{a:1,b:2}` vs `{b:2,a:1}` reads as different calls and never trips; reset points matter — the orchestrator resets the mistake tracker after successful turns but the loop tracker intentionally persists across turns within a session.
**Probe:** `grep -cF 'softThreshold: 3,' .../loop-detection.ts` → 1; `grep -cF 'state.consecutiveIdenticalCount === config.softThreshold' ...` → 1; `grep -cF 'this.loopTracker.inspect({ name: toolName, input })' .../session-runtime-orchestrator.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "LoopDetectionTracker checkRepeatedToolCall", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verbatim (~160 lines, pure); adapt thresholds via config and message copy; omit the legacy AgentEvent emit channel shape if the host event vocabulary differs. No dedicated unit test file upstream for this port (moved per PLAN.md §3.1) — behavior pinned by orchestrator integration + battery greps executed green.
