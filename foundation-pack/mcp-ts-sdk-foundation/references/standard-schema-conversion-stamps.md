<!-- capsule-v2 -->
# Standard Schema conversion & the provably-object stamp — how does a vendor-agnostic schema become a wire-legal MCP tool schema without lying about its root type?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How should `registerTool`/`registerPrompt` convert any Standard Schema (Zod v4, Valibot, ArkType) to JSON Schema, and when may a typeless root be stamped `type:'object'`?

## Conversion ladder
**Path/Symbol:** `packages/core-internal/src/util/standardSchema.ts`: vendored Standard-Schema interfaces (:13-139), guards `isStandardJSONSchema`/`isStandardSchema` (:143-163), `JSON_SCHEMA_CONVERSION_TARGET = 'draft-2020-12'` (:170), `standardSchemaToJsonSchema(schema, io)` (:183-235), `isProvablyObjectShapedRoot` (:244-260), format-pattern trust rule (:336-341), `promptArgumentsFromStandardSchema` (:345-357).
**Signature:** `standardSchemaToJsonSchema(schema: StandardJSONSchemaV1, io: 'input' | 'output' = 'input'): Record<string, unknown>`.
**Data Shape:** input schemas MUST be object-rooted (explicit non-object ⇒ throw); output roots may be anything (SEP-2106); zod 4.0–4.1 lacks `~standard.jsonSchema` ⇒ one-time-warned fallback to bundled `z.toJSONSchema`; zod 3 (`_def`, no `_zod`) ⇒ clear upgrade error.

### Decisive source
```ts
// :213-234 the io split
if (io === 'output') {
    // SEP-2106: outputSchema may have any JSON Schema root. An explicit `type` … is returned as-is.
    if (result.type !== undefined) return result;
    return isProvablyObjectShapedRoot(result) ? { type: 'object', ...result } : result;
}
if (result.type !== undefined && result.type !== 'object') {
    throw new Error(`MCP tool and prompt schemas must describe objects (got type: ${…}). …`);
}
return { type: 'object', ...result };
```
```ts
// :244-251 provable object shape = keywords at root, or EVERY composition member provably object
if ('properties' in schema || 'patternProperties' in schema || 'additionalProperties' in schema || 'required' in schema) return true;
// oneOf/anyOf/allOf: members.every(m => m.type === 'object' || isProvablyObjectShapedRoot(m))
```

**Flow:** guard → per-vendor conversion (`~standard.jsonSchema[io]({target})` / zod fallback / vendor error) → io-specific root policy. The provability check exists because pre-SEP 2025 wire data got an UNCONDITIONAL object stamp; keeping back-compat where safe (`z.discriminatedUnion`) while refusing self-contradictory stamps (`{anyOf:[string,number]}`) — those flow to the 2025 codec's legacy wrap instead (legacy-output-schema-ref-rewrite). Format companions: a library-emitted `pattern` realizing `format:'email'/'uri'/…` is dropped for zod (patterns re-derived from the resolved zod and compared) but TRUSTED-and-dropped for other vendors whose realizations are unknowable.

**Invariant:** never stamp what you can't prove — a wrong `type:'object'` on a primitive-rooted union makes validators accept/reject the OPPOSITE of the author's intent; never throw on non-object OUTPUT roots or every discriminated-union tool breaks at registration. The elicitation wire schema cannot carry format-companion patterns, which is why they are realized-then-compared rather than shipped.

**Probe (direct tests):** `packages/core-internal/test/util/standardSchema.test.ts` describe 'standardSchemaToJsonSchema' pins input throwing on `z.string()`, output pass-through of non-object roots, union-stamp behavior; `test/util/standardSchema.zodFallback.test.ts` pins the 4.x fallback + zod-3 error.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "standardSchemaToJsonSchema provably object output input", limit: 3 });
```

## Verdict
Adopt the io-split root policy and provability predicate; adapt vendor fallbacks to your schema libraries; omit the zod-version archaeology if you pin zod ≥ 4.2.
