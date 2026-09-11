<!-- capsule-v2 -->
# extractReasoningMiddleware — how do you convert XML-tagged reasoning in a token stream into first-class reasoning parts without emitting tags or wedging on split chunks?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** How does a stream transform buffer across deltas to detect `<tag>...</tag>` boundaries, and what state must reset per text block?

## extractReasoningMiddleware (wrapGenerate + wrapStream)
**Path/Symbol:** `packages/ai/src/middleware/extract-reasoning-middleware.ts:extractReasoningMiddleware` (:17–250; wrapGenerate :31–80, wrapStream :82–248); helpers `createIdMap` (`util/create-id-map.ts`), `getPotentialStartIndex` (`util/get-potential-start-index.ts`).
**Signature:** `function extractReasoningMiddleware({ tagName: string, separator = '\n', startWithReasoning = false }): LanguageModelMiddleware`.
**Data Shape:** Per text-part-id extraction state `{ isFirstReasoning, isFirstText, afterSwitch, isReasoning, buffer, idCounter, textId }` held in an id map. Emitted reasoning ids are synthesized `reasoning-${idCounter}`; the original text id is preserved for text deltas. wrapGenerate path: one regex pass `${openingTag}(.*?)${closingTag}` with `gs` flags over each text part.

### Decisive source
```ts
// Per-delta loop (:188-242):
do {
  const nextTag = activeExtraction.isReasoning ? closingTag : openingTag;
  const startIndex = getPotentialStartIndex(activeExtraction.buffer, nextTag);
  if (startIndex == null) { publish(activeExtraction.buffer); activeExtraction.buffer=''; break; }
  publish(activeExtraction.buffer.slice(0, startIndex));
  const foundFullMatch = startIndex + nextTag.length <= activeExtraction.buffer.length;
  if (foundFullMatch) {
    activeExtraction.buffer = activeExtraction.buffer.slice(startIndex + nextTag.length);
    if (activeExtraction.isReasoning) {
      // Emit reasoning-start for empty reasoning blocks (no delta was published).
      if (activeExtraction.isFirstReasoning)
        controller.enqueue({ type: 'reasoning-start', id: `reasoning-${activeExtraction.idCounter}` });
      controller.enqueue({ type: 'reasoning-end', id: `reasoning-${activeExtraction.idCounter++}` });
    }
    activeExtraction.isReasoning = !activeExtraction.isReasoning;
    activeExtraction.afterSwitch = true;
  } else {
    activeExtraction.buffer = activeExtraction.buffer.slice(startIndex); // hold partial tag
    break;
  }
} while (true);
// text-start HOLD so reasoning-start precedes it (:107-117, issue #7774):
if (chunk.type === 'text-start') { delayedTextStart = chunk; return; }
```

**Flow:** wrapStream pipes the provider stream through a TransformStream keyed by chunk id → every `text-delta` appends to that id's buffer → loop publishes safe prefixes, toggles mode at full tag matches, and HOLDS a potential partial tag tail in the buffer until more deltas arrive → `publish()` inserts `separator` after mode switches (not before the first segment) and flushes `delayedTextStart` right before the first text delta. wrapGenerate handles the non-stream case with matchAll + reverse splice-out of matches.
**Invariant:** A tag can straddle any number of chunks — never publish a buffer suffix that could be a tag prefix (`getPotentialStartIndex`). Every emitted `reasoning-start` gets exactly one matching `reasoning-end`, including EMPTY `<think></think>` blocks. State lives per text-part id and must not read inherited map properties (test :289 "should not read Object.prototype for missing text part ids").
**Probe:** `packages/ai/src/middleware/extract-reasoning-middleware.test.ts` — basic extraction :66, no-text case :105, multiple/split/single-chunk-multi tags :145/:336/:490, startWithReasoning both modes :186/:795, empty tags :1185, prototype-safety :289.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "extractReasoningMiddleware", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the per-id buffering state machine with partial-tag holding and empty-block start/end synthesis. Adapt tag syntax (XML vs channel markers), separator policy, and id scheme to host; omit wrapGenerate if your host is stream-only. Coverage caveat: best-effort index; excerpts read directly at HEAD.
