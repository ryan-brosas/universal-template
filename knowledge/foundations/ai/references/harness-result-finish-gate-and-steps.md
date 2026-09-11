<!-- capsule-v2 -->
# Harness finish gate & step ledger — when is a terminal `finish` a contract violation, and how do per-step results aggregate into turn-level answers?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** A foreign runtime's stream ends — how do you decide whether its buffered tail is data or a protocol bug, and what exactly do `result.text/steps/usage/toolCalls` return?

## Unclosed-step-content gate + flatMap aggregation over stepsBuffer

**Path/Symbol:** `packages/harness/src/agent/internal/harness-stream-text-result.ts` — `finishStep` (:252–316), `finish` (:332–485), aggregate fields (:162–168).
**Signature:** `finishStep({ finishReason: LanguageModelV4FinishReason /* {unified,raw} */, usage, providerMetadata, warnings }): StepResult`; `finish(input?: { finishReason, totalUsage, providerMetadata }): Promise<void>`.
**Data Shape:** `stepsBuffer: StepResult[]` grows per finish-step; `accumulatedUsage` via `addLanguageModelUsage`; `finalFinishReason/finalRawFinishReason/finalProviderMetadata` = LAST step's values; `aggregateWarnings: CallWarning[]`.

### Decisive source
```ts
// :339–351 — terminal finish with buffered content = adapter protocol violation, NOT data
if (this.currentStepContent.length > 0) {
  this.fail(new Error(
    'HarnessAgent: received terminal finish with unclosed step content. ' +
    'Harness adapters must emit `finish-step` before `finish`.'));
  return;
}
...
// :388 + :398 + :459–463 — turn-level answers are flatMaps over per-step results
const aggregatedContent = this.stepsBuffer.flatMap(s => s.content);
this._text.resolve(finalStep.text);            // FINAL step only, not the concatenation
this._toolCalls.resolve(this.stepsBuffer.flatMap(s => s.toolCalls));
this._usage.resolve(this.accumulatedUsage);    // additive across steps
this._warnings.resolve(this.aggregateWarnings.length > 0 ? this.aggregateWarnings : undefined);
// :362–386 — zero-step turn still resolves finalStep as a synthesized empty DefaultStepResult
```

**Flow:** each adapter `finish-step` → finishStep builds one `DefaultStepResult` from currentStepContent (V4 `{unified,raw}` reason and nested usage normalized at this boundary), pushes to stepsBuffer, emits the `finish-step` part, accumulates usage, advances stepNumber; terminal `finish` gates on empty buffer, then resolves all 22 promises (text = FINAL step's text; content/toolCalls/toolResults/files/sources = cross-step flatMaps) and enqueues the `finish` part before closing.
**Invariant:** A terminal finish never flushes un-captured content — buffered tail means the adapter skipped a semantic boundary and the whole turn FAILS (error part + rejected promises). Empty terminal turns are legal: steps=[], text=''. Last-step-wins for finishReason/providerMetadata; additive-only for usage.
**Probe:** deterministic direct tests in run-prompt.test.ts: :703–731 ("fails when terminal finish receives unclosed step content" — error message match `/unclosed step content/`, `result.steps` rejects), :670–701 (mid-step stream close without suspension fails too), :733–752 ("allows an empty terminal turn" — `steps` resolves [] and `text` resolves ''), :754+ ("evaluates stop conditions only after real finish-step events"). All read-verified @pin.
**Retrieve:** `search_graph { project:"ai", query:"harness stream text result turn telemetry" }` → `HarnessStreamTextResult.finishStep :252–316` and `.finish :332–485` ranked on file harness-stream-text-result.ts (verified live @pin); `get_code_snippet qualified_name=…HarnessStreamTextResult.finish` returned :332–485 byte-matching the checkout read.

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ai", qualified_name: "ai.packages.harness.src.agent.internal.harness-stream-text-result.HarnessStreamTextResult.finishStep" });
```

## Verdict
Adopt the gate (treat boundary-less tails as protocol errors, not data) and the flatMap-per-family aggregation shape; adapt which families concatenate vs take-final to your result semantics; keep text = FINAL step because consumers expect the model's last answer, not transcript.
