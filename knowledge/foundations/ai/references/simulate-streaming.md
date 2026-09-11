<!-- capsule-v2 -->
# simulateStreamingMiddleware — how do you fake a stream from a non-streaming model so downstream stream consumers cannot tell the difference?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** When porting a generate→stream shim, which stream parts must the shim synthesize itself, and which pass through untouched?

## simulateStreamingMiddleware
**Path/Symbol:** `packages/ai/src/middleware/simulate-streaming-middleware.ts:simulateStreamingMiddleware` (:7–79).
**Signature:** `function simulateStreamingMiddleware(): LanguageModelMiddleware` — a middleware whose ONLY hook is `wrapStream`, implemented as `async ({ doGenerate }) => { const result = await doGenerate(); ... }` (calls the GENERATE thunk inside wrapStream).
**Data Shape:** Emits a full `LanguageModelV4StreamPart` sequence: `stream-start(warnings)` → `response-metadata(...result.response)` → per content part: text → `text-start/text-delta/text-end` triple with stringified counter id (EMPTY text parts skipped); reasoning → `reasoning-start/delta/end` (no skip); everything else (tool-call, source, file…) enqueued verbatim → `finish(finishReason, usage, providerMetadata)` → close. Returns `{ stream, request: result.request, response: result.response }`.

### Decisive source
```ts
wrapStream: async ({ doGenerate }) => {
  const result = await doGenerate();          // NOT doStream
  let id = 0;
  const simulatedStream = new ReadableStream<LanguageModelV4StreamPart>({
    start(controller) {
      controller.enqueue({ type: 'stream-start', warnings: result.warnings });
      controller.enqueue({ type: 'response-metadata', ...result.response });
      for (const part of result.content) {
        switch (part.type) {
          case 'text': {
            if (part.text.length > 0) {       // empty text emits NO parts at all
              controller.enqueue({ type: 'text-start', id: String(id) });
              controller.enqueue({ type: 'text-delta', id: String(id), delta: part.text });
              controller.enqueue({ type: 'text-end', id: String(id) });
              id++;
            }
            break;
          }
          ...
          default: controller.enqueue(part); break;   // tool-calls pass through raw
        }
      }
      controller.enqueue({ type: 'finish', finishReason: result.finishReason,
                           usage: result.usage, providerMetadata: result.providerMetadata });
      controller.close();
    },
  });
  return { stream: simulatedStream, request: result.request, response: result.response };
},
```

**Flow:** wrapStream invoked by the model-call pipeline with BOTH `doGenerate`/`doStream` thunks available (see provider-interface capsule) → this middleware deliberately invokes `doGenerate` → replays the whole result as one synchronous burst inside `start()` → consumers see normal stream semantics (single delta per text block).
**Invariant:** Stream framing must be complete: every started part gets its end part, ids stay unique via the counter, and metadata/usage arrive in the same places real streams put them — otherwise UI state machines and timeout ladders that key on start/end pairs wedge. Empty text must not emit a bare `text-start`/`text-end` pair.
**Probe:** `packages/ai/src/middleware/simulate-streaming-middleware.test.ts` — text response :60, reasoning string/array/mixed :169/:307/:491, tool calls passthrough :657, metadata preserved :826, EMPTY text response :940, warnings passthrough :963.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "simulateStreamingMiddleware", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the generate-inside-wrapStream trick, the exact synthesized part choreography, and the empty-text skip. Adapt part-type names to your stream protocol; omit nothing else — it is 80 lines. Coverage caveat: best-effort index; excerpts read directly at HEAD.
