<!-- capsule-v2 -->
# Harness start-part id contract — why must a synthesized result stream open with `{type:'start'}` before anything else?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Your fake result stream feeds `toUIMessageStream` for useChat clients — what happens to assistant message identity if the first chunk isn't the message-level `start` part?

## Prologue enqueue in the ReadableStream `start` callback

**Path/Symbol:** `packages/harness/src/agent/internal/harness-stream-text-result.ts` — constructor (:170–213), specifically the baseStream `start(c)` callback :186–197.
**Signature:** `new ReadableStream<TextStreamPart<TOOLS>>({ start(c) { c.enqueue({ type: 'start' }); } })`; controller captured by reference into `fullStreamController` for the driver.
**Data Shape:** `{type:'start'}` is the FIRST TextStreamPart ever queued — before any driver event, before any step boundary.

### Decisive source
```ts
// :189–195 — the comment IS the invariant
// Send the message-level start event as the first part, mirroring
// `streamText`. Downstream UI message stream consumers depend on it:
// `toUIMessageStream`'s persistence mode injects the response message
// id into this part (it never synthesizes one), so without it
// `useChat` clients keep a locally generated assistant message id
// that diverges from the id the server persists under.
c.enqueue({ type: 'start' });
```

**Flow:** constructor runs at turn start → `start(c)` fires synchronously on first read → the `start` part rides ahead of everything → ai-core's `toUIMessageStream` (persistence mode) stamps its response message id onto THAT part → useChat adopts the server-persisted id instead of minting a local one.
**Invariant:** Message identity is assigned downstream BY CONSUMPTION of the start part, not synthesized; a result-stream producer that omits (or delays) it forks client-visible ids from persisted ids. This is why the prologue lives in the stream's `start` callback, not in the driver's first event: even a zero-event turn still opens correctly (pairs with harness-result-finish-gate-and-steps.md's empty-turn rule).
**Probe:** deterministic content probe at pin: harness-stream-text-result.ts :195 `c.enqueue({ type: 'start' });` inside `start(c)` with the load-bearing four-line comment above it (read-verified byte-exact); companion capsule ui-stream-writer-kernel.md documents the consumer side (`createUIMessageStream` persistence injecting ids). Direct test coverage is indirect via run-prompt.test.ts :2066–2086 (toUIMessageStream chunk sequences always begin with start-family chunks).
**Retrieve:** `search_graph { project:"ai", query:"harness stream text result turn telemetry" }` → `HarnessStreamTextResult.constructor :170–213` ranked on harness-stream-text-result.ts (verified live @pin).

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ai", qualified_name: "ai.packages.harness.src.agent.internal.harness-stream-text-result.HarnessStreamTextResult.constructor" });
```

## Verdict
Adopt "first frame assigns message identity" whenever synthesizing streams for UI-message consumers; adapt the exact part shape to your wire union; omit only if your host never reconciles client and persisted message ids.
