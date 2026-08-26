<!-- capsule-v2 -->
# Ask inputs normalization — how does a user-input picker tool survive malformed model arguments and pause the turn?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How do you clamp an LLM's freeform form-building call into a strict UI contract, and what happens to the turn after the picker is shown?

## Per-kind clamps + defaults injection + exception-based pause
**Path/Symbol:** `backend/src/lib/chat/tools/toolDispatcher.ts:85` (`cleanAskInputString`), `:90-182` (`normalizeAskInputsEvent`); pause class `streaming.ts:164` (`AssistantStreamAskInputsPause`), thrown at :565-567; response parser `contextBuilders.ts:395` (`parseAskInputsResponsePayload`). Direct tests: `src/__tests__/integration/chat.routes.test.ts` (ask_inputs flows).
**Signature:** `normalizeAskInputsEvent(args) -> AskInputsEvent`; items ≤12, ids ≤80 chars (synthesized `"<kind>-<index+1>"` when blank), questions ≤500, options ≤8 with values ≤500, text answers ≤5,000 (`MAX_ASK_INPUT_TEXT_LENGTH`), choice answers ≤1,000.
**Data Shape:** three item kinds — choice `{options[], allow_other(default TRUE), other_label(default "Other")}`, text `{question}`, documents `{document_types[] ≤8}` — plus optional `response_prefix` ≤200.

### Decisive source
```ts
const options = rawOptions.map(parse).filter(Boolean).slice(0, 8);
const normalizedOptions = options.length > 0 ? options : [{ value: "Continue" }]; // never render an empty picker
…
if (askInputsEvents.length > 0) {
    throw new AssistantStreamAskInputsPause();   // AFTER events emitted+persisted
    // "Stop this assistant turn here so the model does not add redundant prose
    //  telling the user to answer the picker or attach documents."
}
```

**Flow:** model emits ask_inputs → args normalized per-kind with defaults injected for missing question/label/other → event written to SSE AND persisted into `events` → pause exception unwinds to runLLMStream's catch which treats it as SUCCESS-shaped termination (no error event) → client renders picker → POST ask-input response is parsed/clamped by `parseAskInputsResponsePayload` (skipped flags honored; empty answers without skipped ⇒ row dropped) → appended onto the last REAL assistant message via the reservation-skipping append.
**Invariant:** A picker with zero items or zero options must never reach the UI; normalization guarantees shape rather than rejecting. The pause is an exception ONLY as control flow — it must fire after persistence so the turn's history already contains the question.
**Probe:** `grep -c 'AssistantStreamAskInputsPause' src/lib/chat/streaming.ts` → 4; `grep -c '{ value: "Continue" }' src/lib/chat/tools/toolDispatcher.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "ask_inputs normalizeAskInputsEvent AssistantStreamAskInputsPause", limit: 10 });
```

## Verdict
Adopt clamp-with-default normalization + persist-then-pause control flow + strict response parsing as portable contracts; adapt kind taxonomy/limits to your UI.
