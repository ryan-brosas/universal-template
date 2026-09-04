<!-- capsule-v2 -->
# Dialect JSON-Schema→Zod conversion — how do you turn host-provided JSON Schemas into runtime validators for SDKs that demand Zod?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Two dialect bridges must expose host tools to runtimes whose tool APIs require Zod schemas (Claude Agent SDK `McpServer.tool(name, desc, shape, handler)`; LangChain `tool(fn, {schema})`) while the host only speaks JSON Schema — what conversion ladder keeps validation honest without ever throwing on a schema the converter cannot express?

## Two independent converters, one shared philosophy
**Path/Symbol:** `packages/harness-claude-code/src/bridge/json-schema-to-zod.ts` whole 141L — `jsonSchemaToZodShape` (:20–23), `toZodShape` (:25–38), `toZodType` (:40–52), `zodForType` (:54–80), `zodForConst` (:82–85), `zodForEnum` (:87–91), `zodForUnion` (:93–103), `zodForLiterals` (:105–115), `getNonNullTypes` (:117–121), `isNullable` (:123–128); `packages/harness-deepagents/src/bridge/json-schema-to-zod.ts` whole 64L — `jsonSchemaToZodObject` (:13–17), `toZodShape` (:19–28), `toZodType` (:30–63).
**Signature:** claude-code: `jsonSchemaToZodShape(input: unknown): Record<string, z.ZodTypeAny>` (a SHAPE for McpServer.tool); deepagents: `jsonSchemaToZodObject(input: unknown): z.ZodObject<...>` (a wrapped OBJECT for LangChain tool()). Both accept `unknown` and never throw.
**Data Shape:** shared core — non-object input ⇒ empty shape; properties iterated in order; required-set membership decides `.optional()`; description rides `.describe()`; type dispatch string/number/integer(→number().int())/boolean/array/object/null with default `z.any()`. Divergence: claude-code adds a const/enum/union rung BEFORE type dispatch (`zodForConst ?? zodForEnum ?? zodForUnion ?? zodForType`), nullable via `nullable:true` OR `'null'` inside a type array (applied as `.nullable()` AFTER the base type), multi-type arrays collapse to `z.any()` when >1 non-null type remains, array items that are themselves arrays collapse to `z.array(z.any())`, and enum/const values that are not JSON literals (finite number/string/boolean/null) fall back to `z.any()`. deepagents handles only the flat core (no const/enum/union; items always single-schema) — its test file names this explicitly ("the flat converter dropped this" for nested objects it later gained).

### Decisive source
```ts
// harness-claude-code json-schema-to-zod.ts:40–52 — rung order + post-hoc nullable/describe
function toZodType(schema: JsonSchemaObject | undefined): z.ZodTypeAny {
  if (!schema) return z.any();
  let zType = zodForConst(schema) ?? zodForEnum(schema) ?? zodForUnion(schema) ?? zodForType(schema);
  if (isNullable(schema)) zType = zType.nullable();
  if (schema.description) zType = zType.describe(schema.description);
  return zType;
}
// harness-claude-code json-schema-to-zod.ts:93–103 — unions need ≥2 branches, else fall through to type dispatch
const unionSchemas = schema.anyOf ?? schema.oneOf;
if (!unionSchemas || unionSchemas.length < 2) return undefined;
const options = unionSchemas.map(item => toZodType(item)) as unknown as [z.ZodTypeAny, z.ZodTypeAny, ...z.ZodTypeAny[]];
return z.union(options);
```

**Flow:** host start-frame tools carry `inputSchema` (JSON Schema). The claude-code bridge converts each to a shape at McpServer construction time (index.ts :273); the deepagents bridge converts each to a wrapped object at host-tool build time (index.ts :180). Conversion is pure and total: every input yields some Zod type, expressiveness degrades toward `z.any()` rather than throwing, so a hostile or exotic schema can break validation strictness but never the bridge. The claude-code converter's extra rungs exist because MCP tool schemas in the wild carry enums/consts/unions (reporter-style nested schemas are the pinned fixture); the deepagents converter stayed flat because LangChain's own schema handling absorbs the rest.
**Invariant:** the converter is TOTAL (unknown input ⇒ `{}` shape / empty object schema, never an exception); required-ness is decided by the `required` array alone (absent ⇒ all optional); nullability is orthogonal to the base type (applied after dispatch, so `type:['string','null']` yields `z.string().nullable()`); unsupported constructs degrade to `z.any()` at the narrowest node (one bad enum value poisons only that property, not the whole shape); descriptions are preserved on both property and type levels in the superset converter.
**Probe:** `harness-claude-code/src/bridge/json-schema-to-zod.test.ts` (291L, 10 cases): reporter-style nested schema preservation; array item types incl. arrays of objects; nullable from `nullable`, type arrays, anyOf, oneOf; recursive anyOf/oneOf unions; safe fallback for unsupported union branches; enum/const as representable literals; fallback-to-any for unsupported enum/const values; fallback-to-any for unsupported non-null type unions; property description preservation; empty shape for missing/non-object schemas. `harness-deepagents/src/bridge/json-schema-to-zod.test.ts` (81L, 6 cases): flat scalar required/optional; nested object structure; array item types; arrays of objects; nullable honored; empty object schema for missing/non-object input.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "jsonSchemaToZodShape jsonSchemaToZodObject zodForUnion zodForConst", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the total-converter contract (never throw; degrade to `z.any()` at the narrowest node) for any host→sandbox tool surface where the schema originates outside your control; adopt the rung order const → enum → union → type with nullable/describe applied AFTER dispatch (order matters: a nullable enum must stay an enum); adopt required-set membership as the sole optionality signal; size the converter to your runtime's real schema population — the two dialects prove the same seam can ship as a 64L flat converter or a 141L superset depending on what the target SDK sees; adapt the output wrapper (bare shape vs z.object) to the consuming API; omit conversion entirely where the runtime accepts JSON Schema natively (ACP builtins re-identify through raw schemas per the pass-22 ACP translator capsule). Cross-dialect twin of the pass-25 tool-relay plane (harness-dialect-tool-relay-plane.md): same pattern — one kernel, per-dialect surface. Caveat: neither converter has a test for `$ref`/`$defs` (unsupported by design — both degrade via the default branch); recorded as a known limitation, not a gap.
