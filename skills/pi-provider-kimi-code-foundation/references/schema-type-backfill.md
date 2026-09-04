<!-- capsule-v2 -->
# JSON Schema type back-fill — how do you make a strict server-side schema validator accept typeless JSON Schemas from arbitrary tools?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** MCP/agent tool definitions frequently emit property schemas without `type`, and Moonshot's validator rejects them — which nodes may be back-filled and which must be left alone?

## JSON Schema type back-fill
**Path/Symbol:** `src/payload.ts:288-418`; entry `normalizeJsonSchemaPropertyTypes` 361-378 + `recurseJsonSchemaPropertyTypes` 380-408; dispatchers `normalizeOpenAIToolSchemas` 410-418 (OpenAI path only). Header comment: "mirrors kosong's ensure_property_types".
**Signature:** `(node: unknown): void` — mutates schemas in place, adding `node.type`.
**Data Shape:** walks `function.parameters` of every payload tool; recursion covers `properties` values, `items` (object or tuple array), `additionalProperties`, and the three branch arrays `anyOf`/`oneOf`/`allOf`.

### Decisive source
```ts
// -----------------------------------------------------------------------------
// JSON Schema property-type normalizer (mirrors kosong's ensure_property_types).
// Moonshot's tool schema validator rejects property schemas that omit `type`;
// this walks the schema and back-fills a type from `enum` / `const` / nested
// structure hints, defaulting to "string" when nothing else applies.
// -----------------------------------------------------------------------------
if (
  node.type === undefined &&
  !Object.keys(node).some((key) => JSON_SCHEMA_COMBINATOR_KEYS.has(key))
) {
  if (Array.isArray(node.enum) && node.enum.length > 0) {
    node.type = inferJsonSchemaTypeFromValues(node.enum);
  } else if ("const" in node) {
    node.type = inferJsonSchemaTypeFromValues([node.const]);
  } else {
    node.type = inferJsonSchemaTypeFromStructure(node);
  }
}
```
```ts
function inferJsonSchemaTypeFromStructure(node: JsonRecord): string {
  if (hasAnyKey(node, JSON_SCHEMA_OBJECT_KEYS)) return "object";
  if (hasAnyKey(node, JSON_SCHEMA_ARRAY_KEYS)) return "array";
  if (hasAnyKey(node, JSON_SCHEMA_STRING_KEYS)) return "string";
  if (hasAnyKey(node, JSON_SCHEMA_NUMERIC_KEYS)) return "number";
  return "string";
}
```

**Flow:** for each reachable node lacking `type`: skip entirely when any combinator key (`anyOf|oneOf|allOf|not|if|then|else|$ref`) is present (the server resolves those; guessing would be wrong); else infer from non-empty `enum` values → from `const` → from keyword-set membership (object keys incl. properties/required; array keys incl. items/prefixItems; string keys incl. pattern/format; numeric keys) → default `"string"`. Mixed enum sets collapse: integer+number ⇒ "number", anything heterogeneous ⇒ "string". Recursion then continues into structural children regardless.
**Invariant:** Never overwrite an explicit `type`; never annotate combinator-keyed nodes; back-fill is additive-only so the transform is idempotent across repeated requests.

**Probe:** `tests/payload.test.ts:206` ("fills missing OpenAI tool parameter schema types") plus the type-inference matrix exercised through `applyKimiPayloadMutations` fixtures.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "normalizeJsonSchemaPropertyTypes inferJsonSchemaTypeFromStructure", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the guard-first back-fill: combinator-keyed and already-typed nodes untouched, inference ladder enum→const→keyword-sets→string. Adapt keyword sets to your validator's actual rejections. Omit the OpenAI-path gating if your host normalizes both protocols' tool arrays uniformly. No coverage caveat at this pin.
