<!-- capsule-v2 -->
# OpenCode bridge event envelope — how do you normalize a runtime's evolving event wire format into one translation state that keeps text, reasoning, and tool parts well-formed?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The runtime ships several event generations at once — sync-wrapped envelopes, version-suffixed type names, payload under `properties` OR `data`, session ids in four different places, and a quirk where reasoning streams under `field:"text"`. How does one bridge keep every part well-formed across all of them?

## Boundary unwrap + four-shape session filter
**Path/Symbol:** `packages/harness-opencode/src/bridge/opencode-events.ts` — `unwrapOpenCodeEvent` (:70–92), `stripSyncVersion` (:249–251), `getOpenCodeEventSessionId` (:94–108), `emitOpenCodeStreamStart` (:48–68), `emitMissingFinalDelta` (:118–139); `packages/harness-opencode/src/bridge/index.ts` — `consumeEvents` loop (:895–924).
**Signature:** `unwrapOpenCodeEvent(rawEvent: unknown): OpenCodeEvent | undefined`; `getOpenCodeEventSessionId(event: OpenCodeEvent): string | undefined`.
**Data Shape:** normalized event = `{id?, type?, properties?}`; sync wrapper = `{type:'sync', syncEvent:{id, type, data}}`; version suffix = trailing `.\d+` on the type; TranslationState carries per-id delta maps (`textDeltas`, `reasoningDeltas`, `toolInputs`), open-part id sets (`legacyTextPartIds`, `legacyReasoningPartIds`), dedupe sets (`toolCallsEmitted`, `toolResultsEmitted`, `legacyStepFinishPartIds`, `hostToolCallsAuthorized`, `dynamicToolCallIds`), and `messageRoles`.

### Decisive source
```ts
// opencode-events.ts:75–91 — the sync wrapper is unwrapped to its INNER
// identity; malformed envelopes die at the boundary as undefined
if (raw.type === 'sync' && raw.syncEvent) {
  const sync = asOpenCodeObject(raw.syncEvent);
  if (!sync) return undefined;
  return {
    id: String(sync.id ?? raw.id ?? ''),
    type: stripSyncVersion(String(sync.type ?? '')),
    properties: openCodeEventPropertiesFromValue(sync.data) ?? {},
  };
}
return {
  id: typeof raw.id === 'string' ? raw.id : undefined,
  type: typeof raw.type === 'string' ? stripSyncVersion(raw.type) : undefined,
  properties:
    openCodeEventPropertiesFromValue(raw.properties) ??
    openCodeEventPropertiesFromValue(raw.data) ??
    {},
};
```
```ts
// opencode-events.ts:131–138 — end-of-part reconciliation honors the prefix
// contract: only a GROWING final text contributes a tail delta
if (
  !fullText ||
  fullText === emittedText ||
  !fullText.startsWith(emittedText)
) {
  return;
}
emit({ type, id, delta: fullText.slice(emittedText.length) });
```

**Flow:** every raw SSE frame passes `unwrapOpenCodeEvent` (sync unwrap → version-suffix strip → properties-from-properties-??-data; null/array/malformed ⇒ undefined) → the loop drops events whose resolved session id (props.sessionID ?? props.sessionId ?? `session.*`-type ⇒ props.id ?? part.sessionID) differs from this turn's session → permission events are intercepted before translation → everything else enters the translator. Text/reasoning parts open through set-gated `startLegacyPart` (one start per id), accumulate deltas in the state maps, and close on `time.end` (malformed `time` payloads are ignored, not treated as completion). The legacy quirk: OpenCode streams REASONING deltas with `field:"text"` — `emitLegacyPartDelta` checks whether the part id was already announced as a reasoning part and redirects the delta so reasoning never surfaces as text. At part end, `emitMissingFinalDelta` emits the tail only when the final text extends everything already streamed. `stream-start` fires exactly once (latch) on the first assistant message info, carrying `modelId = providerID/modelID` when both are known.
**Invariant:** no consumer-visible part can be opened twice or closed without being opened (set-gated starts + explicit ends); a rewritten (non-prefix) final text never produces a negative or spurious delta; events from other sessions in the same server can never leak into this turn's stream.
**Probe:** `packages/harness-opencode/src/bridge/opencode-events.test.ts` (265L, 10 cases): v2 data-payload unwrap + session id + settlement predicate; sync-wrapper unwrap with `.1` version suffix stripped; malformed envelopes rejected (null/array/non-object syncEvent); legacy part session id; stream-start emitted once with the FIRST assistant model (user role and later assistants ignored) and again without modelId when metadata omits it; missing-final-delta three-way (tail emitted / equal no-op / rewritten no-op); reasoning-under-field:"text" stays reasoning exactly once; plain field:"text" stays text; malformed time not treated as completion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "unwrapOpenCodeEvent getOpenCodeEventSessionId emitMissingFinalDelta emitLegacyPartDelta emitOpenCodeStreamStart", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the boundary-unwrap-then-normalize shape (one function that turns every wire generation into one internal event record, rejecting malformed input at the edge) for any multi-version event feed; adopt the multi-shape session-id walk plus per-turn session filtering when one server multiplexes sessions; adopt prefix-contract tail reconciliation for any runtime that sends both deltas and a final full text; adopt set-gated part opening for idempotent start emission. Adapt the wrapper/suffix shapes and the quirk-routing table to your runtime; omit the messageRoles user-filter unless your runtime echoes user messages back through the same stream. Caveat: the consumeEvents session-filter wiring is deterministic-read-only; the kernel functions it calls are fully test-pinned.
