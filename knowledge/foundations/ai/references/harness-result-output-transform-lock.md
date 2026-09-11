<!-- capsule-v2 -->
# Harness output transform lock — how do partial structured-output parses ride a text stream without leaking parses for the wrong text part?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Your result stream must publish `partialOutputStream` values parsed from streaming text — how do you pick WHICH text id carries parses, when do you republish, and what happens to buffered text at step boundaries?

## First-text-chunk-id lock + stringify-compare change gate + boundary flush

**Path/Symbol:** `packages/harness/src/agent/internal/harness-stream-text-result.ts` — `createOutputTransformStream` (:844–939), `publishTextChunk` (:859–875); consumer getters `partialOutputStream` (:673–688), `elementStream` (:690–700), `output` (:702–716). Twin of ai-core's enriched-stream-publisher (packages/ai) with DIFFERENT flush boundaries.
**Signature:** `createOutputTransformStream(output): TransformStream<TextStreamPart, {part, partialOutput}>`; `output.parsePartialOutput({text}) → {partial} | undefined`.
**Data Shape:** envelope `{ part: TextStreamPart, partialOutput: InferStreamOutput | undefined }`; accumulators `firstTextChunkId`, `text` (whole), `textChunk` (unpublished tail), `lastPublishedValue`.

### Decisive source
```ts
// :892–897 — ONLY the first text id ever seen is the parse carrier; others pass unenriched
if (firstTextChunkId == null) firstTextChunkId = chunk.id;
else if (chunk.id !== firstTextChunkId) {
  controller.enqueue({ part: chunk, partialOutput: undefined }); return;
}
...
// :912–936 — accumulate, parse, and republish ONLY on stringified CHANGE
text += chunk.text; textChunk += chunk.text;
const result = await output.parsePartialOutput({ text });
if (result === undefined) return;                       // parser not ready yet
const currentValue = typeof result.partial === 'string'
  ? result.partial : JSON.stringify(result.partial);
if (currentValue !== lastPublishedValue) {
  publishTextChunk({ controller, partialOutput: result.partial });  // re-emits BUFFERED tail as one delta
  lastPublishedValue = currentValue;
}
// :879–881 + :904–909 — pending buffer flushes at finish-step AND text-end (harness-specific boundaries)
```

**Flow:** with an output spec the constructor pipes baseStream through this transform instead of the pass-through wrapper; every emitted part becomes an `{part, partialOutput}` envelope; `partialOutputStream` strips null envelopes; empty deltas that carry only providerMetadata still pass through (:916–919); `elementStream` throws `notSupportedYet` unless the spec supplies a transform, and `output` parses complete text once via `parseCompleteOutput` on finalStep.
**Invariant:** Parses attach to exactly ONE text part identity per turn — a second text id (e.g. a tool's echo) can never poison partial state; consumers observe monotone parse progress because unchanged parses never re-publish; no text is dropped — unpublished tails flush at semantic boundaries.
**Probe:** deterministic content probes at pin: :853–857 accumulator declarations, :879 finish-step flush guard, :930 change gate (all read-verified byte-exact); graph line-pins from live BM25 (`createOutputTransformStream :844–939`, `publishTextChunk :859–875`). No dedicated class test exists (coverage caveat recorded in ai-work/research.md pass 19).
**Retrieve:** `search_graph { project:"ai", query:"harness stream text result turn telemetry" }` → `HarnessStreamTextResult.partialOutputStream :673–688` + `createOutputTransformStream :844–939` + `.transform :878–937` ranked on harness-stream-text-result.ts (verified live @pin).

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ai", qualified_name: "ai.packages.harness.src.agent.internal.harness-stream-text-result.createOutputTransformStream" });
```

## Verdict
Adopt the id-lock + change-gate pattern for any streamed-parse surface; adapt flush boundaries to your protocol (harness flushes at finish-step/text-end where ai-core publishes on the enriched pipeline); keep the envelope so one stream serves both raw and parsed consumers.
