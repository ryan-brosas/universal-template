<!-- capsule-v2 -->
# Output specification — how do you turn one `output` argument into a provider responseFormat, a complete-parse, and a partial/element stream without leaking the wire envelope?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** When porting typed structured output over plain-text model responses, what envelope does each mode impose on the provider and why must the porter keep it invisible?

## Output factory family (`text` / `object` / `array` / `choice` / `json`)
**Path/Symbol:** `packages/ai/src/generate-text/output.ts:object|array|choice|json|text` (interface :22–58; object :93–185; array :197–382; choice :394–522; json :533–603).
**Signature:** `function array<ELEMENT>({ element: FlexibleSchema<ELEMENT>, name?, description? }): Output<Array<ELEMENT>, Array<ELEMENT>, ELEMENT>` (same shape for the others; every factory returns the 4-method `Output` interface).
**Data Shape:** The `Output` interface = `{ name, responseFormat: PromiseLike<responseFormat>, parseCompleteOutput({text}, ctx), parsePartialOutput({text}): {partial} | undefined, createElementStreamTransform(): TransformStream | undefined }`. `parseCompleteOutput` failures throw `NoObjectGeneratedError` carrying text + response + usage + finishReason context.

### Decisive source
```ts
// array.responseFormat (:220-247): wrap element schema into an OBJECT envelope
const {
  $schema: _$schema,
  definitions,
  $defs,
  ...itemSchema
} = jsonSchema as JSONSchema7 & { $defs?: JSONSchema7['definitions'] };
return {
  type: 'json' as const,
  schema: {
    $schema: 'http://json-schema.org/draft-07/schema#',
    ...(definitions != null && { definitions }),
    ...($defs != null && { $defs }),
    type: 'object',
    properties: { elements: { type: 'array', items: itemSchema } },
    required: ['elements'],
    additionalProperties: false,
  },
  ...
};
// array.parsePartialOutput (:338-341): drop the LAST element on repaired parse
const rawElements =
  result.state === 'repaired-parse' && outerValue.elements.length > 0
    ? outerValue.elements.slice(0, -1)
    : outerValue.elements;
// createElementStreamTransform (:360-380): publish-once cursor
let publishedElements = 0;
// for (; publishedElements < partialOutput.length; publishedElements++) controller.enqueue(...)
```
Complete parse (:249–313) requires an object with an `elements` array, then validates EACH element against the original element schema. `choice.partial` (:503–513) returns the exact value on successful parse but on repaired parse only when exactly ONE option prefix-matches (ambiguity → undefined).

**Flow:** responseFormat promised to the model call (`await output?.responseFormat` at generate-text.ts:1018) → complete path parses JSON → unwraps envelope → validates per element → returns bare `Array<ELEMENT>`; partial path repairs truncated JSON → drops last (possibly torn) element on repaired-parse → validates elements individually, skipping invalid ones silently; element stream enqueues each newly completed element exactly once via the monotonic `publishedElements` cursor.
**Invariant:** The `{elements}` object envelope exists ONLY on the wire; user-facing values are always bare arrays. Root `$defs`/`definitions` must be hoisted to the wrapper or root-relative `$ref`s inside items dangle. On repaired (truncated) partial parses the final element is incomplete by construction — emitting it surfaces garbage.
**Probe:** `packages/ai/src/generate-text/output.test.ts` — responseFormat envelope (:240ff), parseCompleteOutput incl. transform-validated elements (:369/:409), `repaired-parse (returns all but last element)` (:450); orchestrator gating "output should be undefined when finish reason is tool-calls" (generate-text.test.ts :8044 area).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "output array object choice json specification", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the interface shape (one spec → responseFormat + complete/partial/element parsing) and the array envelope with defs hoisting plus repaired-partial last-element drop. Adapt envelope key names and error taxonomy to host; omit choice-prefix disambiguation if you have no streaming enum need. Coverage caveat: best-effort index; all excerpts read directly at HEAD.
