<!-- capsule-v2 -->
# Streaming callback containment — what happens when a user's onChunk/onError throws mid-stream?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** `streamText`/`streamObject` invoked some callbacks by direct await while others went through the swallowing bus — why must ALL of them route through `notify()`?

## Uniform notify routing
**Path/Symbol:** `packages/ai/src/generate-text/stream-text.ts` — onChunk :1225–1228, onError :1237–1240 (both inside eventProcessor transform); stepFinish :1410; abort :1548; plus :1490/:1701/:2084; stream-object twin at `generate-object/stream-object.ts:905–910`.
**Signature:** `await notify({event: {chunk: part}, callbacks: onChunk})` replacing `await onChunk?.({chunk: part})`.
**Data Shape:** unchanged event payloads; only dispatch mechanism changed.

### Decisive source
```ts
// BEFORE (#19161 root cause): a thrown user callback escaped into the
// TransformStream, killing the consumer's iteration and masking provider errors.
-        await onChunk?.({ chunk: part });
+        await notify({ event: { chunk: part }, callbacks: onChunk });
...
-          await onError({ error });
+          await notify({ event: { error }, callbacks: onError });
```
`notify` itself (`util/notify.ts`): `Promise.all(asArray(callbacks).map(async cb => { try { await cb(event) } catch {} }))` — one guard per callback.

**Flow:** every observer callback now dispatches through the swallowing bus: a throwing onChunk/onError neither interrupts chunk flow, nor rejects result promises, nor prevents onFinish/onError for later parts; provider errors still reach consumers through the STREAM (error parts) and result promises, never through callback exceptions.
**Invariant:** Callbacks are observers with zero authority over generation — an exception in any of them is contained to that invocation. Direct awaits are permitted ONLY where the callee is SDK-owned (telemetry dispatcher pairs ride INSIDE notify's array form).
**Probe:** `stream-text.test.ts:10186` — "should continue stream processing when onChunk throws"; deterministic probe: `grep -c "await notify({" packages/ai/src/generate-text/stream-text.ts` → `7`. Companion: `background-stream-drain.md` + `swallowing-callback-bus.md` own the underlying bus.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "onChunk notify streamText eventProcessor", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt uniform bus-dispatch for every user-facing streaming callback; adapt which SDK-internal listeners join the same notify arrays; audit YOUR port for direct-await stragglers — partial adoption reproduces #19161.
