<!-- capsule-v2 -->
# Tool result output shaping — how does an arbitrary tool `output` become a typed model-facing result, and why does error mode bypass toModelOutput?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the precedence between `errorMode`, `tool.toModelOutput`, and default string/JSON wrapping — and what happens to `undefined` values?

## createToolModelOutput
**Path/Symbol:** `packages/ai/src/prompt/create-tool-model-output.ts:createToolModelOutput` (:4-30), private `toJSONValue` (:32-34).
**Signature:** `createToolModelOutput({toolCallId: string, input: unknown, output: unknown, tool?: Tool, errorMode: 'none' | 'text' | 'json'}): Promise<ToolResultOutput>`.
**Data Shape:** Returns exactly one of `{type:'error-text', value}`, `{type:'error-json', value}`, `{type:'text', value}` (string outputs), `{type:'json', value}` (everything else) — or whatever `tool.toModelOutput` returns.

### Decisive source
```ts
if (errorMode === 'text') {
    return { type: 'error-text', value: getErrorMessage(output) };
  } else if (errorMode === 'json') {
    return { type: 'error-json', value: toJSONValue(output) };
  }
if (tool?.toModelOutput) {
  return await tool.toModelOutput({ toolCallId, input, output });
}
return typeof output === 'string'
  ? { type: 'text', value: output }
  : { type: 'json', value: toJSONValue(output) };

function toJSONValue(value: unknown): JSONValue {
  return value === undefined ? null : (value as JSONValue);
}
```

**Flow:** error modes SHORT-CIRCUIT everything — even when the tool defines a custom projection, a flagged error is shaped by errorMode alone (`getErrorMessage` extracts `.message`; json mode serializes the whole error object). Only in `none` mode does `toModelOutput` get its chance with full context `{toolCallId, input, output}`; strings fall to text, everything else to JSON.
**Invariant:** Error presentation NEVER routes through `toModelOutput` — the SDK deliberately prevents tools from leaking stack traces or sensitive fields into model-visible errors. `undefined` normalizes to `null` at the JSON boundary because `undefined` would be dropped by `JSON.stringify` semantics and produce empty tool results. The `this` binding of class-based tools is preserved on the `toModelOutput` call (test-pinned).
**Probe:** `packages/ai/src/prompt/create-tool-model-output.test.ts:8/:25/:43` (error-text/error-json shapes incl. complex objects), `:69/:94/:129` (toModelOutput precedence + content-type returns), `:172` ("should preserve `this` when calling a class-based tool.toModelOutput"), `:202/:239` (string→text incl. empty string).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"createToolModelOutput ToolResultOutput error-text toModelOutput","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the three-layer precedence and the undefined→null JSON boundary verbatim; adapt the ToolResultOutput union names to your wire format but keep error modes OUTSIDE any custom projection; omit the `this`-preservation concern only if your tool registry never binds class methods. Fully direct-test-pinned at this HEAD.
