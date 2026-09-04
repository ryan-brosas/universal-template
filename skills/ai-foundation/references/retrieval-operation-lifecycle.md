<!-- capsule-v2 -->
# Retrieval operation lifecycle — what is the shared callback/telemetry/retry skeleton that embed, embedMany, and rerank all execute?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** How do the three retrieval entrypoints structure call-id generation, event emission order, error fan-out, and deprecated-alias handling so observers see a consistent protocol?

## The shared skeleton
**Path/Symbol:** `packages/ai/src/embed/embed.ts:embed` (:41–269), `packages/ai/src/embed/embed-many.ts:49–416`, `packages/ai/src/rerank/rerank.ts:38–343` (identical ordering in all three).
**Signature:** common shape: `op({model, ..., onStart?, onEnd?, telemetry?, experimental_telemetry?, _internal?: {generateCallId?}})`.
**Data Shape:** two-tier events: outer `{callId, operationId:'ai.embed'|'ai.embedMany'|'ai.rerank', provider, modelId, ...}` and inner per-model-call `{callId, embedCallId, operationId:'....doEmbed'|'.doRerank', values/documents}` — `callId` is shared between both tiers.

### Decisive source
```ts
const callId = generateCallId();                       // 'call' prefix + 24 chars, injectable via _internal
...
await notify({ event: startEvent,
  callbacks: [resolvedOnStart, telemetryDispatcher.onStart] });
try {
  const {...} = await retry(async () => { /* notify doEmbed/doRerank start; model call; notify end */ });
  logWarnings({ warnings, provider: model.provider, model: model.modelId });
  await notify({ event: endEvent, callbacks: [resolvedOnEnd, telemetryDispatcher.onEnd] });
  return new Default...Result({...});
} catch (error) {
  await telemetryDispatcher.onError?.({ callId, error });
  throw error;                                          // user callbacks NEVER see onError
}
```

**Flow:** generate callId → resolve deprecated aliases (`onStart ?? experimental_onStart`) → wrap whole body in `runInTracingChannelSpan` (identity fallback when no telemetry) → notify(start: user+telemetry in ONE array) → try { retry(notify(inner-start) → doEmbed/doRerank → notify(inner-end)) → logWarnings → notify(end) → result } catch { telemetryDispatcher.onError only → rethrow }.
**Invariant:** (1) USER callbacks and TELEMETRY handlers ride the same swallowing bus (notify never rejects — see swallowing-callback-bus.md); (2) errors go ONLY to `telemetryDispatcher.onError` then rethrow verbatim — no user-facing onError exists on this plane; (3) `_internal.generateCallId` is the test seam that lets assertions pin exact ids ('empty-call-id'); (4) warnings are logged INSIDE the happy path after retries succeed — a retry exhausting means NO warning logging for partial attempts.
**Probe:** `packages/ai/src/embed/embed.test.ts:572–640` (consistent callId across start/end; onStart-before-doEmbed-before-onEnd ordering; onEnd still fires when onStart throws); byte-exact `grep -c "operationId: 'ai.embed" packages/ai/src/embed/embed.ts` → 2 (:165,:192).

## Deprecated alias resolution + UA header stamping
**Path/Symbol:** alias pattern :144–145 (embed), :160–161 (embedMany), :149–150 (rerank); UA stamping `packages/ai/src/embed/embed.ts:147–150`, `embed-many.ts:163–166`.
**Data Shape:** `experimental_*` aliases exist for telemetry AND callbacks in every signature; headers gain `ai/<VERSION>` suffix before first use.

### Decisive source
```ts
const resolvedOnStart = onStart ?? experimental_onStart;
const resolvedOnEnd = onEnd ?? experimental_onEnd;
const headersWithUserAgent = withUserAgentSuffix(headers ?? {}, `ai/${VERSION}`);
```

**Flow:** stable name wins when both supplied; aliases exist purely as a deprecation shim. Headers are stamped ONCE before the try block so every chunk/attempt reuses the identical header object.
**Invariant:** the UA suffix is appended (not replaced) preserving caller attribution — same chaining contract as tool-loop-agent.md. Aliases are resolved once at entry, not per event.
**Probe:** `packages/ai/src/embed/embed.test.ts:314/:630` ('accept deprecated experimental_telemetry as an alias'; telemetry fields present in events); byte-exact `grep -n 'onStart ?? experimental_onStart' packages/ai/src/embed/*.ts packages/ai/src/rerank/rerank.ts` → 3 hits (one per file).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "embed value doEmbed usage warnings response", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the skeleton verbatim for any new retrieval-style operation (single-value embed IS this skeleton with `values:[value]` → `embeddings[0]`). Adapt event payload fields to your domain; keep the two-tier id scheme if you need parallel-call correlation. Omit Node tracing-channel specifics if your host has a different telemetry substrate — but keep the identity-fallback shape so absence of telemetry costs nothing. Direct tests pin ordering, alias behavior, and id consistency across all three entrypoints; runner unavailable here (no node_modules).
