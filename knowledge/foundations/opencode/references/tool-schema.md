<!-- capsule-v2 -->
# Tool schema — Effect Schema → JSON Schema for tool parameters

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a tool's Effect Schema become a JSON Schema for the model's tool-call validation?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/json-schema.ts` (164 lines): `fromSchema(schema: Schema.Top): JSONSchema7` (:8), `fromTool(tool: Tool.Def): JSONSchema7` (:24).
**Signature:** `fromSchema(schema)` converts an Effect `Schema.Top` to a `JSONSchema7`; `fromTool(tool)` returns `tool.jsonSchema ?? fromSchema(tool.parameters)`.
**Data Shape:** input = Effect Schema (struct of typed fields with annotations); output = `JSONSchema7` (properties, types, descriptions).

### Decisive source
```ts
export function fromSchema(schema: Schema.Top): JSONSchema7 { /* Effect Schema -> JSON Schema */ }
export function fromTool(tool: Tool.Def): JSONSchema7 {
  return tool.jsonSchema ?? fromSchema(tool.parameters as Schema.Top)
}
```

**Flow:** each tool declares `Parameters = Schema.Struct({...})`; `fromTool` either uses the tool's explicit `jsonSchema` or converts the Effect Schema to JSON Schema, so the model receives a validated parameter contract.
**Invariant:** a tool can override with an explicit `jsonSchema`; otherwise the Effect Schema is auto-converted (single source of truth for params).
**Probe:** `packages/opencode/test/tool/parameters.test.ts` (Effect Schema converts to JSON Schema; descriptions/annotations preserved; explicit jsonSchema override).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "fromSchema fromTool jsonSchema parameters Effect Schema JSONSchema", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Effect-Schema → JSON-Schema conversion with explicit-override support; adapt the schema dialect to host.
