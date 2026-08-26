<!-- capsule-v2 -->
# Stream-object pipeline — how do you turn accumulating text into a monotone partial-object stream with per-strategy validation and consumer-JSON resynthesis?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What is the exact accumulate → parse → validate → dedupe → emit loop, and how do the array/enum strategies reshape deltas?

## The core transform loop
**Path/Symbol:** `packages/ai/src/generate-object/stream-object.ts` transform (:678–757) over `OutputStrategy` (`packages/ai/src/generate-object/output-strategy.ts:16–67`, selector `getOutputStrategy` :403–426).
**Signature:** per text chunk: `accumulatedText += chunk; textDelta += chunk;` → `parsePartialJson(accumulatedText)` → gate on `currentObjectJson !== undefined && !isDeepEqualData(latestObjectJson, currentObjectJson)` → `outputStrategy.validatePartialResult({value, textDelta, latestObject, isFirstDelta, isFinalDelta: parseState === 'successful-parse'})` → on success AND `!isDeepEqualData(latestObject, partial)` emit `{type:'object', object}` then `{type:'text-delta', textDelta}`.
**Data Shape:** strategy returns `ValidationResult<{partial: PARTIAL; textDelta: string}>` — validation may REWRITE the delta (see array below). Unchanged parses are swallowed twice (raw JSON level and validated-partial level).

### Decisive source
```ts
if (
  currentObjectJson !== undefined &&
  !isDeepEqualData(latestObjectJson, currentObjectJson)
) {
  const validationResult = await outputStrategy.validatePartialResult({
    value: currentObjectJson,
    textDelta,
    latestObject,
    isFirstDelta,
    isFinalDelta: parseState === 'successful-parse',
  });
  if (
    validationResult.success &&
    !isDeepEqualData(latestObject, validationResult.value.partial)
  ) {
    ...
    controller.enqueue({ type: 'object', object: latestObject });
    controller.enqueue({ type: 'text-delta', textDelta: validationResult.value.textDelta });
    textDelta = '';
    isFirstDelta = false;
  }
}
```
(stream-object.ts:703–738, verbatim)

**Flow:** text accumulates → partial JSON parsed → raw-level dedupe → strategy validates/reshapes → partial-level dedupe → `{object}` + rewritten `{text-delta}` pair emitted together → on `finish`, any residual `textDelta` flushes FIRST (:754–757) before the finish part resolves result promises.
**Invariant:** (1) DOUBLE dedupe is load-bearing — strategies can collapse distinct raw parses to the same partial (e.g. trailing garbage), so raw-value equality alone would emit duplicate objects. (2) `isFinalDelta = parseState === 'successful-parse'`: repaired (truncated) final parses still count as non-final for grace purposes. (3) Object and its delta text are emitted as an ATOMIC pair so UIs can replay consumer-visible JSON in lockstep with state.

## Array strategy: torn-tail grace + resynthesized consumer JSON
**Path/Symbol:** `output-strategy.ts:166–233` (validatePartialResult), element-stream cursor :265–288.
### Decisive source
```ts
// special treatment for last processed element:
// ignore parse or validation failures, since they indicate that the
// last element is incomplete and should not be included in the result,
// unless it is the final delta
if (i === inputArray.length - 1 && !isFinalDelta) {
  continue;
}
...
let textDelta = '';
if (isFirstDelta) { textDelta += '['; }
if (publishedElementCount > 0) { textDelta += ','; }
textDelta += resultArray
  .slice(publishedElementCount) // only new elements
  .map(element => JSON.stringify(element))
  .join(',');
if (isFinalDelta) { textDelta += ']'; }
```
(:190–225, verbatim)

**Invariant:** the wire carries `{elements:[...]}` but the DELTA text is re-synthesized as a bare `[e1,e2…]` consumer array — brackets/comma placement derive from `isFirstDelta`/`publishedElementCount`/`isFinalDelta`, NOT from the model's text. A porter forwarding raw text chunks leaks envelope braces to consumers. The last element gets parse/validation grace until the final delta because streaming truncates mid-element by construction. Element streams publish via monotonic `publishedElements` cursor — exactly-once delivery even when a later parse revalidates earlier elements.
**Probe:** `stream-object.test.ts` + `__snapshots__/stream-object.test.ts.snap` (delta sequences), `generate-text/output.test.ts:440ff` modern twin (`repaired-parse (returns all but last element)`).

## Enum strategy: prefix-filtered snap
**Path/Symbol:** `output-strategy.ts:357–392`.
### Decisive source
```ts
const possibleEnumValues = enumValues.filter(enumValue =>
  enumValue.startsWith(result),
);
if (value.result.length === 0 || possibleEnumValues.length === 0) {
  return { success: false, error: ... };
}
return {
  success: true,
  value: {
    partial: possibleEnumValues.length > 1 ? result : possibleEnumValues[0],
    textDelta,
  },
};
```
(:370–391, verbatim)

**Invariant:** ambiguous prefixes stay RAW strings; the partial only SNAPS to a full enum value when exactly one option matches. Empty prefix never validates (prevents publishing before any character arrives). Element streams throw `UnsupportedFunctionalityError` in enum mode (:394–399).
**Probe:** `output-strategy.test.ts` suites; behavior mirrored by modern Output.choice (`output.test.ts:618ff` ambiguity cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "validatePartialResult isFinalDelta textDelta", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "ai", name_pattern: "^(objectOutputStrategy|arrayOutputStrategy|enumOutputStrategy|getOutputStrategy)$", detail: "ids" });
```

## Verdict
Adopt double-dedupe accumulation, strategy-owned delta rewriting, torn-tail grace, and prefix-snap enum semantics. Adapt the strategy interface shape (the modern codebase is migrating to the `Output` interface — see `output-interface-vs-strategies.md`). Omit HTTP response plumbing around it. Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2; decisive ranges read at HEAD this session.
