<!-- capsule-v2 -->
# Structured output capture — how does a json_schema prompt force and capture a final tool call?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How is the StructuredOutput tool injected, forced, captured into message state, and failed when the model never calls it?

## Tool-forced final answer
**Path/Symbol:** `packages/opencode/src/session/prompt.ts` (`createStructuredOutputTool` :1565–1591, exported for testing; injection :1243–1250; enforcement :1270–1285; capture :1288–1293; failure :1309–1316).
**Signature:** `createStructuredOutputTool({schema: Record<string, any>, onSuccess: (output) => void}): AITool`.
**Data Shape:** Strips `$schema`, wraps the rest via `jsonSchema()`; description commands exactly-once end-of-response usage. `lastUser.format = {type:"json_schema", schema}`; closure variable `structured: unknown` lives in runLoop scope so the tool's `execute` writes straight into loop state.

### Decisive source
```ts
// prompt.ts:1243-1249 + 1285 + 1288-1292 — inject, force, capture
if (lastUser.format?.type === "json_schema") {
  tools["StructuredOutput"] = createStructuredOutputTool({ schema: lastUser.format.schema,
    onSuccess(output) { structured = output } })
}
toolChoice: format.type === "json_schema" ? "required" : undefined,
...
if (structured !== undefined) {
  handle.message.structured = structured          // persisted on the assistant message
  handle.message.finish = handle.message.finish ?? "stop"
  yield* sessions.updateMessage(handle.message)
  return "break" as const                          // exit the turn loop immediately
}
// :1309-1315 — model finished WITHOUT calling the tool ⇒ typed error, retries recorded
handle.message.error = new SessionV1.StructuredOutputError({
  message: "Model did not produce structured output", retries: 0 }).toObject()
```

**Flow:** user part carries `format.json_schema` → each loop step adds StructuredOutput to resolved tools AND appends `STRUCTURED_OUTPUT_SYSTEM_PROMPT` ("You MUST use the StructuredOutput tool… Do NOT respond with plain text") to system → `toolChoice: "required"` → execute() runs AI-SDK's own validation first, then `onSuccess(args)` stores raw args → next loop iteration sees `structured !== undefined`, stamps it on the message, breaks.
**Invariant:** The schema travels as the tool's INPUT schema — the AI SDK validates arguments before execute fires, so no second validator is needed; `$schema` must be stripped or some providers 400. Capture is a closure write, not an event: if the loop were re-entered without resetting `structured`, stale output from a previous step would leak into a new message. Missing call after a terminal finish is an ERROR (`retries: 0` here), not silent text fallback.
**Probe:** `packages/opencode/test/session/structured-output.test.ts:12–79` (OutputFormat parse/reject matrix + error shape); `createStructuredOutputTool` unit coverage at test/session (exported `/** @internal Exported for testing */`); integration path in `structured-output-integration.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "structured output tool schema", limit: 8 });
```

## Verdict
Adopt the inject+force+capture triple and the missing-call error contract; adapt the AI SDK `tool()/jsonSchema()` specifics to host SDK; omit the literal English prompt wording (product surface).
