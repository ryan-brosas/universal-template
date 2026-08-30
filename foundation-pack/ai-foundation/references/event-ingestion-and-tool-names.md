<!-- capsule-v2 -->
# SSE JSON event-stream ingestion + provider tool-name translation — how do you consume `data:`-framed model events and reconcile renamed tools across the wire boundary?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What does per-event parse-failure look like (stream-level vs item-level), and when must tool names be mapped between client and provider namespaces?

## parseJsonEventStream: fail-per-item, never fail-the-stream
**Path/Symbol:** `packages/provider-utils/src/parse-json-event-stream.ts:parseJsonEventStream` (:11–33).
**Signature:** `({stream: ReadableStream<Uint8Array>, schema: FlexibleSchema<T>}): ReadableStream<ParseResult<T>>`.
**Data Shape:** output items are `ParseResult<T>` — `{success: true, value}` OR `{success: false, error}` — NOT raw values; consumers branch per event.

### Decisive source
```ts
return stream
  .pipeThrough(new TextDecoderStream())
  .pipeThrough(new EventSourceParserStream())
  .pipeThrough(
    new TransformStream<EventSourceMessage, ParseResult<T>>({
      async transform({ data }, controller) {
        // ignore the 'DONE' event that e.g. OpenAI sends:
        if (data === '[DONE]') {
          return;
        }
        controller.enqueue(await safeParseJSON({ text: data, schema }));
      },
    }),
  );
```
(parse-json-event-stream.ts:18–32, verbatim)

**Flow:** bytes → text → SSE frames (`eventsource-parser`) → each frame's `data` is validated against the schema INDEPENDENTLY → results enqueue in order; `[DONE]` sentinel is swallowed; a malformed frame yields a failed `ParseResult` while the stream itself stays alive.
**Invariant:** (1) Validation failures are DATA, not stream errors — one poisoned event must not kill the remaining events (providers interleave keep-alives, usage frames, and content). A porter who throws on parse failure truncates every response that contains a single unknown field. (2) Unknown fields are forward-compat: newer-server chunks with extra keys still validate (additive evolution contract). (3) The `[DONE]` check happens BEFORE parsing — it is a framing convention, not data.
**Probe:** `packages/ai/src/ui-message-stream/ui-message-chunks.test.ts:44` feeds a chunk carrying `optionalFieldFromNewerServer` and snapshot-asserts the successful `rawValue` passthrough; consumers like `gateway/src/gateway-video-model.ts` show the branch-on-result loop.

## createToolNameMapping: id-keyed two-way rename table
**Path/Symbol:** `packages/provider-utils/src/create-tool-name-mapping.ts:createToolNameMapping` (:33–66); interface :9–27.
**Signature:** `({tools: Array<FunctionTool|ProviderTool>, providerToolNames: Record<`${string}.${string}`, string>}) => {toProviderToolName(custom): string; toCustomToolName(provider): string}`.
**Data Shape:** built ONLY from `type === 'provider'` tools whose `tool.id` exists in `providerToolNames` (provider-defined ids like `namespace.tool_name`); both directions fall back to identity for unmapped names.

### Decisive source
```ts
for (const tool of tools) {
  if (tool.type === 'provider' && tool.id in providerToolNames) {
    const providerToolName = providerToolNames[tool.id];
    customToolNameToProviderToolName[tool.name] = providerToolName;
    providerToolNameToCustomToolName[providerToolName] = tool.name;
  }
}
return {
  toProviderToolName: (customToolName: string) =>
    customToolNameToProviderToolName[customToolName] ?? customToolName,
  toCustomToolName: (providerToolName: string) =>
    providerToolNameToCustomToolName[providerToolName] ?? providerToolName,
};
```
(create-tool-name-mapping.ts:52–65, verbatim)

**Flow:** request build → outgoing tool definitions translated custom→provider; response handling → incoming call/result names translated back provider→custom so client callbacks fire under the name the user declared.
**Invariant:** (1) Function tools are NEVER mapped — their names already ARE the wire names; mapping them would break user tools whose names collide with provider conventions. (2) Identity fallback is load-bearing: unmapped names pass through untouched, making the mapping safe on partial provider tables. (3) The map is keyed by provider TOOL ID, not guessed by name — renaming is authoritative, not heuristic. Consumers: `anthropic/src/anthropic-language-model.ts`, `openai/src/responses/openai-responses-language-model.ts`.
**Probe:** `create-tool-name-mapping.test.ts:48` ("should ignore function tools"), `:72/:92` identity fallbacks, `:131` mixed function+provider sets.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "parseJsonEventStream EventSourceParserStream", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ai", query: "createToolNameMapping toCustomToolName", limit: 5 });
```

## Verdict
Adopt per-item `ParseResult` semantics with `[DONE]` swallowing, and the id-keyed bidirectional rename map with function-tool exclusion and identity fallbacks. Adapt the frame codec (SSE here; NDJSON hosts swap only the middle pipe stage) and the id format. Omit schema validation if your transport guarantees server-side validation. Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2; decisive ranges read at HEAD this session.
