<!-- capsule-v2 -->
# otel attribute sanitizer — why OTel arrays reject mixed types and non-finite numbers, and how to pre-drop them

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai`. **Question:** What does a telemetry layer have to filter from arbitrary JS values before handing them to OpenTelemetry attributes?

## Path/Symbol
`packages/otel/src/sanitize-attribute-value.ts:sanitizeAttributeValue` (:13–47) + `sanitizeAttributes` (:49–61).

**Signature:** `sanitizeAttributeValue(value: AttributeValue): AttributeValue | undefined` — returns a LEGAL OTel value or undefined meaning "drop this key".

**Data Shape:** legal values are string|number|boolean or homogeneous primitive arrays. Everything else (objects, mixed-type arrays, NaN/Infinity, empty arrays, all-invalid arrays) is undefined.

### Decisive source
```ts
  const primitiveTypes = new Set(
    value.filter(isPrimitiveAttributeValue).map(item => typeof item),
  );

  if (primitiveTypes.size !== 1) {
    return undefined;
  }
```
(:24–29; numeric branch :38–44 keeps the array ONLY when `numbers.every(Number.isFinite)`)

**Flow:** scalars pass through unless `!Number.isFinite` (:16–19). Arrays: collect the set of typeof over primitive members — size must be exactly 1 (mixed `'a',1` → drop); then FILTER to that type (silently removing undefined/{} members: `['a',undefined,{},'b'] → ['a','b']`); numbers additionally require ALL finite else whole array drops. Empty array → undefined (no primitives ⇒ size 0 ≠ 1). The map-level wrapper iterates entries and skips any null/undefined-after-sanitize.

**Invariant:** (1) Invalid MEMBERS are filtered out, but invalid WHOLE arrays (wrong mix, non-finite numbers) kill the entire attribute — asymmetric by design and easy to port backwards. (2) The reason these exist: the OTLP exporter serializes an invalid member as `{}` AnyValue and some backends reject/hallucinate the span; the in-repo test documents the wire symptom (`toOtlpAnyValue([undefined])` → `{arrayValue:{values:[{}]}}`, select-attributes.test.ts :82–105). (3) This runs on EVERY attribute incl. literal specs (select-attributes calls it unconditionally), so enrichment callbacks can't inject illegal values either.

**Probe:** `grep -n "primitiveTypes.size !== 1" packages/otel/src/sanitize-attribute-value.ts` → :28. `grep -c "Number.isFinite" packages/otel/src/sanitize-attribute-value.ts` → 2. Direct tests: `sanitize-attribute-value.test.ts` (:15 non-finite scalars dropped, :27 non-finite numeric arrays dropped, :37 invalid entries filtered, :48 mixed types dropped, :60 empty arrays dropped); `select-attributes.test.ts` (:32 "drops invalid array attribute entries" expects `{keep:['stop','length'], input:['input']}`).

**Retrieve:** live-resolved rank-1 @pin:
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "sanitizeAttributeValue primitiveTypes Number.isFinite", limit: 5 });
// → otel sanitizeAttributeValue Function packages/otel/src/sanitize-attribute-value.ts 13-47
```

**Verdict:** ADOPT as-is — this ~60-line kernel prevents a whole class of silent span loss.
