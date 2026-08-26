<!-- capsule-v2 -->
# Tool-arg parse & schema coerce — how do streamed, partially-parsed model arguments become safe typed inputs?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does a porter handle tool-call arguments that arrive as raw JSON strings, already-parsed objects, or deeply-parsed-by-accident objects — without any of the three shapes breaking execution?

## object-shortcut parse + two schema-aware repair sites for deep-parsed strings
**Path/Symbol:** `core/tools/parseArgs.ts` whole (153 lines): `safeParseToolCallArgs` (:3–25), `coerceArgsToSchema` (:34–63), `getStringArg`/`getNumberArg`/`getBooleanArg` (:65–153).
**Signature:** `safeParseToolCallArgs(toolCall: ToolCallDelta): Record<string, any>`; `coerceArgsToSchema(args: Record<string, any>, schema?: Record<string, any>): Record<string, any>`.
**Data Shape:** in: tool-call delta whose `function.arguments` may be an object (streamed accumulation) or JSON string; out: plain args record; parse failure ⇒ `{}`.

### Decisive source
```ts
// JSON.parse() deeply parses all values, so string-typed parameters
// that contain valid JSON (e.g. file content for a .json file) get
// converted to objects. This checks the schema and re-stringifies
// any values that should be strings.
if (propSchema.type === "string" && typeof value === "object" && value !== null) {
  try { coerced[key] = JSON.stringify(value); } catch { /* leave as-is */ }
}
```

**Flow:** `safeParseToolCallArgs` returns arguments AS-IS when already a non-array object with keys; otherwise `JSON.parse(trim() || "{}")` with catch ⇒ `{}` — partial stream deltas can never throw. Then TWO independent repair sites handle the deep-parse hazard: (1) `coerceArgsToSchema` walks only KNOWN schema properties before the MCP wire call; (2) each impl-side accessor (`getStringArg`, etc.) repeats the same object→stringify repair inline, because built-in impls receive raw parsed args. Accessor contracts: missing required arg throws a shaped `` `<arg>` argument is required… `` message; `getNumberArg` parses numeric strings and floors (integer line numbers, negatives allowed); `getBooleanArg` accepts `"true"`/`"false"` strings case-insensitively.
**Invariant:** argument parsing NEVER rejects; type coercion is best-effort and localized — one un-coercible value degrades to "as-is", not to call failure. The deep-parse repair must exist at BOTH layers: schema coercion covers MCP servers, accessor-level repair covers built-ins whose schemas aren't consulted at dispatch time.
**Probe:** no dedicated vitest suite exists for this file — coverage caveat: verified by whole-file source read + graph retrieval this pass; the invariant is enforced by usage sites (`callTool` funnel, `readFileImpl` accessors); port with table tests over the three input shapes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "safeParseToolCallArgs coerceArgsToSchema string arg accessor", limit: 10 });
```

## Verdict
Adopt the never-throwing parse with `{}` fallback and the twin-layer deep-parse repair; adapt accessor messages/error taxonomy to your tool errors; omit the number-floor if your tools accept floats. Trap: `coerceArgsToSchema` copies args shallowly (`{...args}`) and skips unknown keys untouched — extra garbage from the model passes through to implementations unchanged.
