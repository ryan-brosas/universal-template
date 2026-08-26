<!-- capsule-v2 -->
# JSON-Schema→zod shape back-fill — how do I feed JSON-Schema tool parameters to a zod-typed SDK validator?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** When a tool SDK validates parameters with zod but my host declares them as JSON Schema, what minimal conversion preserves requiredness, enums, and nesting?

## Enum-first property mapping; required set decides .optional()
**Path/Symbol:** `src/schema-to-zod.ts:jsonSchemaToZodShape` (38-49), `jsonSchemaPropertyToZod` (6-36).
**Signature:** `jsonSchemaToZodShape(schema: unknown): Record<string, z.ZodTypeAny>` — `jsonSchemaPropertyToZod(prop: Record<string, unknown>): z.ZodTypeAny`.
**Data Shape:** Input is a JSON-Schema object (`{type:"object", properties, required?}`); output is a named-property zod shape for the SDK's tool registration. Anything that isn't an object schema returns `{}`.

### Decisive source
```ts
export function jsonSchemaToZodShape(schema: unknown): Record<string, z.ZodTypeAny> {
  const s = schema as Record<string, unknown> | null | undefined;
  if (!s || s.type !== "object" || !s.properties || typeof s.properties !== "object") return {};
  const required = new Set(Array.isArray(s.required) ? s.required : []);
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const [key, prop] of Object.entries(s.properties)) {
    const zodProp = jsonSchemaPropertyToZod(prop ?? {});
    shape[key] = required.has(key) ? zodProp : zodProp.optional();
  }
  return shape;
}
```

```ts
// enum wins over type — before the type switch:
if (Array.isArray(prop.enum) && prop.enum.length > 0) {
  base = z.enum(prop.enum as [string, ...string[]]);
} else {
  switch (prop.type) {
    case "string": base = z.string(); break;
    case "number": case "integer": base = z.number(); break;
    case "boolean": base = z.boolean(); break;
    case "array": base = prop.items
      ? z.array(jsonSchemaPropertyToZod(prop.items))   // recursive
      : z.array(z.unknown()); break;
    case "object": base = z.record(z.string(), z.unknown()); break;
    default: base = z.unknown();
  }
}
if (typeof prop.description === "string") base = base.describe(prop.description);
```

**Flow:** `buildPiToolsMcpServer` converts each Pi tool's JSON-Schema parameters → zod shape → non-empty shapes register the typed `droidTool(name, description, shape, handler)` overload; an empty shape (no properties, or a non-object schema) falls back to the parameterless registration.
**Invariant:** Requiredness is decided by the schema's `required` array, not by zod defaults: required props keep their validator, everything else gets `.optional()`. Enum takes precedence over `type` because a string-typed enum must become `z.enum`, not `z.string()`. Unknown types degrade to `z.unknown()` instead of throwing. Nested objects are intentionally flattened to `z.record(z.string(), z.unknown())` rather than recursed — only array items recurse.
**Probe:** `test/pi-tools-bridge.test.ts:13-27` ("maps required/optional object properties"): both keys present in the shape, `shape.cmd.safeParse("echo").success === true`, and the OPTIONAL numeric prop accepts `undefined`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "jsonSchemaToZodShape jsonSchemaPropertyToZod z.enum optional describe", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt this as a lossless-enough minimal converter when full JSON-Schema fidelity is unnecessary: enum-first, required-set-driven optionality, recursion ONLY where the target API demands real structure (arrays). Adapt by extending the type switch (e.g., anyOf/oneOf) if your tools need it. Omit nothing else — the file is deliberately tiny; growing it is the wrong port.
