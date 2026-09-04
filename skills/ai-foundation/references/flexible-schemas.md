<!-- capsule-v2 -->
# asSchema — how do you normalize Zod v3, Zod v4, Standard Schema, raw JSON Schema, and lazy factories into ONE Schema interface with deferred JSON-Schema conversion?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9` (package `@ai-sdk/provider-utils`); Codebase Memory project `ai`. **Question:** What does the unified schema facade promise, which branches convert eagerly vs lazily, and why is reference inlining the default?

## asSchema + zodSchema dispatch
**Path/Symbol:** `packages/provider-utils/src/schema.ts:asSchema` (:142–158), `zodSchema` (:275–292), `zod3Schema` (:200–230), `zod4Schema` (:232–266), `jsonSchema` (:105–129), type `FlexibleSchema` (:82–86).
**Signature:** `function asSchema<OBJECT>(schema: FlexibleSchema<OBJECT> | undefined): Schema<OBJECT>`; `function zodSchema(zodSchema, { useReferences? }): Schema<OBJECT>`.
**Data Shape:** `Schema<OBJECT> = { [schemaSymbol]: true, _type, validate?: (value) => ValidationResult | PromiseLike<...>, jsonSchema: JSONSchema7 | PromiseLike<JSONSchema7> }` — validation and wire-schema are SEPARATE capabilities. `FlexibleSchema = Schema | LazySchema (callable) | ZodSchema (z3|z4) | StandardSchema`. Undefined → empty strict object schema (`additionalProperties:false`). Detection: `'_zod' in zodSchema` ⇒ zod4.

### Decisive source
```ts
export function asSchema(schema) {
  return schema == null
    ? jsonSchema({ type:'object', properties:{}, additionalProperties:false })
    : isSchema(schema)            // symbol-marked custom Schema
      ? schema
      : '~standard' in schema     // Standard Schema branch
        ? schema['~standard'].vendor === 'zod'
          ? zodSchema(schema)
          : standardSchema(schema)   // requires '~standard'.jsonSchema converter
        : schema();                  // LazySchema: call the factory
}
// zod4 path (:247-256): DEFERRED conversion + additionalProperties normalization
return jsonSchema(
  () => addAdditionalPropertiesToJsonSchema(
    toJSONSchema(zodSchema, { target:'draft-7', io:'input', reused: useReferences ? 'ref' : 'inline' })),
  { validate: async value => { const r = await safeParseAsync(zodSchema, value); ... } },
);
// zod3 path (:215-220): $refStrategy 'none' by default
() => zod3ToJsonSchema(zodSchema, { $refStrategy: useReferences ? 'root' : 'none' })
```

**Flow:** Callers accept `FlexibleSchema` at the public surface → `asSchema` normalizes once → downstream code reads `.jsonSchema` (lazily materialized + cached via closure in `jsonSchema()`) for providers and `.validate` for outputs/inputs. Standard Schema validation maps issues into `TypeValidationError`; JSON-Schema-only vendors throw on conversion rather than degrading.
**Invariant:** JSON-Schema generation must stay lazy ("defer json schema creation to avoid unnecessary computation when only validation is needed") — eager conversion would tax every startup. Validation always uses the ORIGINAL validator (zod parse / standard validate), never the converted JSON Schema, so transforms and refinements survive. Reference inlining defaults ON (`reused:'inline'` / `$refStrategy:'none'`) because some providers reject `$ref`s (google/openapi); recursive schemas must opt into references explicitly.
**Probe:** `packages/provider-utils/src/schema.test.ts` — undefined→empty object schema (:7), zod4 conversion incl. optional/enum/nullable/literal (:44–194), "duplicate referenced schemas (and not use references) by default" (:117) vs `useReferences:true` recursive `z.lazy` (:133/:150), transform io:input (:194), output validation with transform (:234), StandardSchema describe (:262).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "asSchema zodSchema flexible schema", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the two-capability Schema interface (jsonSchema + validate), lazy conversion with caching, original-validator validation, and inline-by-default reference policy. Adapt the vendor-detection hack (`'_zod' in`) to host schema libraries; omit zod3 support if your host is v4-only. Coverage caveat: provider-utils index.ts has a parse_partial flag at line 131 (unrelated range); schema.ts itself verified clean.
