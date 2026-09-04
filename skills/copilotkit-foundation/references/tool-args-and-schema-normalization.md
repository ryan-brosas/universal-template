<!-- capsule-v2 -->
# Tool-args coercion & schema sanitation — what do providers send that would crash JSON.parse, and what must be stripped before a tool schema reaches the wire?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** How are tool-call arguments normalized across providers, and how is a Zod/Standard-Schema tool converted into the exact JSON Schema shape agents accept?

## parseToolArguments + createToolSchema/stripAdditionalProperties
**Path/Symbol:** `packages/core/src/core/run-handler.ts:parseToolArguments` (:1421-1433) → `ensureObjectArgs` (:1397-1407); `createToolSchema` (:1339-1367), `stripAdditionalProperties` (:1369-1388), `EMPTY_TOOL_SCHEMA` (:1331-1334).
**Signature:** `parseToolArguments(rawArgs: unknown, toolName: string): Record<string, unknown>`; `createToolSchema(tool): Record<string, unknown>`.
**Data Shape:** raw args may arrive as `""`, `null`, `undefined`, a JSON string, or an already-parsed object. Schema output is guaranteed `{type:"object", properties:{...}}` with `$schema` removed and `additionalProperties` stripped at EVERY depth.

### Decisive source
```typescript
export function parseToolArguments(rawArgs: unknown, toolName: string): Record<string, unknown> {
  if (rawArgs === "" || rawArgs === null || rawArgs === undefined) {
    logger.debug(`[parseToolArguments] Tool "${toolName}" received empty/null/undefined arguments — defaulting to {}`);
    return {};
  }
  const parsed = typeof rawArgs === "string" ? JSON.parse(rawArgs) : rawArgs;
  return ensureObjectArgs(parsed, toolName);   // throws `... parsed to non-object (${typeof parsed})`
}

const { $schema: _$schema, ...schema } = rawSchema as Record<string, unknown>;
if (typeof schema.type !== "string") schema.type = "object";
if (typeof schema.properties !== "object" || schema.properties === null) schema.properties = {};
stripAdditionalProperties(schema);            // recursive delete of additionalProperties
```

**Flow:** handler execution starts with arg parsing — empty/nullish coerce to `{}` with an observable debug log (never silent), strings parse, non-objects (arrays included) THROW so the caller emits structured `TOOL_ARGUMENT_PARSE_FAILED` with rawArguments attached → schema building converts via shared `schemaToJsonSchema` (Zod injected through it), drops `$schema`, force-fixes `type`/`properties`, then recursively strips `additionalProperties`.
**Invariant:** The stripping is a hard regression contract — some model backends reject schemas carrying `additionalProperties`; nested objects and catchall/passthrough schemas must come out clean too. Coercion must stay OBSERVABLE (debug log), never a silent rewrite.
**Probe:** `packages/core/src/core/__tests__/run-handler-ensureObjectArgs.test.ts` :6-45 (throws for string/number/array/null/boolean/undefined, passes objects) and `packages/core/src/core/__tests__/run-handler-zod-regression.test.ts` :24-50 ("strips top-level additionalProperties", nested, catchall). Deterministic anchor `grep -c "additionalProperties" packages/core/src/core/__tests__/run-handler-zod-regression.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "parseToolArguments ensureObjectArgs createToolSchema stripAdditionalProperties", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt both normalizers verbatim for any LLM tool bridge. Adapt only the log channel. Omit permissive parsing (returning arrays as-is) — the non-object throw is load-bearing for error attribution.
