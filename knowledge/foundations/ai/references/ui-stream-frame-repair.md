<!-- capsule-v2 -->
# UI-message stream frame repair — how does a durable shared stream survive duplicated or orphaned part chunks?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** Retries and reconnects interleave duplicate chunks on one shared stream, and `processUIMessageStream` fatals on a delta whose part was never started — what normalizer makes the stream safe?

## Per-family, per-step framing state machine
**Path/Symbol:** `packages/workflow/src/normalize-ui-message-stream.ts:normalizeUIMessageStreamParts` (:110–174) with `repairPart` (:27–58) and `PartFrameState {open, ended}`.
**Signature:** `(source: AsyncIterable<UIMessageChunk>) => AsyncGenerator<UIMessageChunk>`; state reset on BOTH `reset-step` and `finish-step`.
**Data Shape:** Two independent frame states (`text`, `reasoning`), each holding open/ended id sets scoped to the CURRENT step.

### Decisive source
```ts
if (kind === 'start') {
  if (state.open.has(id) || state.ended.has(id)) return;  // drop replayed start
  state.open.add(id); yield chunk; return;
}
if (state.ended.has(id)) return;                          // drop re-delivered tail
if (!state.open.has(id)) {                                // synthesize missing start
  state.open.add(id); yield { type: startType, id } as UIMessageChunk;
}
if (kind === 'end') { state.open.delete(id); state.ended.add(id); }
yield chunk;
```
Scope note (deliberate): `tool-input-delta` raises the same class of fatal error, but tool parts are LEFT UNTOUCHED — the consumer never resets its tool-call map on finish-step and tool-call ids are unique, so the step-boundary id-reuse trap doesn't apply to them.

**Flow:** chunk in → per-family machine → well-formed streams pass unchanged; duplicates dropped (start for open-or-ended id; delta/end after end); orphans healed by synthesizing the missing `*-start`; both step-boundary chunk types clear both families' open+ended sets because that is EXACTLY where the consumer clears its active-part maps (multi-step turns legitimately reuse id "0").
**Invariant:** Repair only FRAMING, never content — worst case degrades to "text begins slightly into the step" or "a duplicated tail is dropped" instead of a dead turn (`Received text-delta for missing text part …`). Reset must mirror the CONSUMER's reset points, not the producer's.
**Probe:** deterministic probes: `grep -c "\.clear()" packages/workflow/src/normalize-ui-message-stream.ts` → `8` (2 chunk types × 2 families × open+ended). Direct tests: `to-ui-message-chunk.test.ts:201` drives `normalizeUIMessageStreamParts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "normalizeUIMessageStreamParts repairPart", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: repairPart :27-58 + normalizeUIMessageStreamParts :110-174, total:2 exact
```

## Verdict
Adopt the two-set per-family machine with consumer-mirrored resets and the tool-family exclusion rationale; adapt synthesized-start chunk shape to your protocol version; do NOT extend to tool parts without first reproducing an actual orphaning mode there.
