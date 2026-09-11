<!-- capsule-v2 -->
# Legacy vs modern otel plane — ai.* attribute vocabulary, doGenerate step ids, and the deprecation boundary

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai`. **Question:** What EXACTLY differs between `LegacyOpenTelemetry` and `OpenTelemetry`, and which legacy behaviors must survive in ports that still speak the old wire format?

## Path/Symbol
`packages/otel/src/legacy-open-telemetry.ts:LegacyOpenTelemetry` (:144) — in-file private twins of selectAttributes (:66–118) and recordSpanError (:44–58); `assemble-operation-name.ts:assembleOperationName` (:3–21); `get-base-telemetry-attributes.ts` (:5–37); `stringify-for-telemetry.ts:stringifyForTelemetry` (:13–51).

**Signature:** constructor takes ONLY `{tracer}` (no enrichSpan/supplemental toggles) and defaults `trace.getTracer('ai')`; modern takes full options and defaults `'gen_ai'`. Both classes export from index.ts (:1–7) as the entire public surface.

**Data Shape:** legacy attributes are flat `ai.*` keys — `operation.name` = `` `${operationId} ${functionId}` `` + `resource.name` + `ai.operationId` + `ai.telemetry.functionId` (assembleOperationName :10–20), `ai.settings.<key>` spread, `ai.request.headers.<k>`, prompts via `stringifyForTelemetry(prompt)` (V4Prompt → JSON with Uint8Array file data base64'd, URL→toString — created precisely because raw JSON.stringify mangles Uint8Arrays into `{"0":42,"1":69}` per its docstring :7–12).

### Decisive source
```ts
    const stepOperationId =
      state.operationId === 'ai.streamText'
        ? 'ai.streamText.doStream'
        : 'ai.generateText.doGenerate';
```
(:544–547; object twin :378–381) — step spans are named by the UNDERLYING provider method id, whereas the modern plane names them `step ${n}` / `chat <model>`.

**Flow:** same callStates tree, but: root span name IS the operationId (`this.tracer.startSpan(event.operationId, …)` :286); streaming perf lands as span EVENTS (`addEvent('ai.stream.firstChunk', {msToFirstChunk})` :464–471/:754–758 plus `'ai.stream.finish'` with msToFinish/avgOutputTokensPerSecond :760–766) instead of modern `gen_ai.client.operation.*` numeric attributes; usage carries BOTH vocabularies side-by-side (`ai.usage.totalTokens` AND `gen_ai.usage.input_tokens` :728–750); tool spans named `ai.toolCall` with args marked as `{output: …}` thunks (:617–619 — note: tool ARGUMENTS ride the OUTPUT gate in legacy, INPUT in modern); rerank/embed child spans reuse `event.operationId` as span names.

**Invariant:** (1) The deprecation boundary is attribute-vocabulary-wide: the new suite asserts ZERO `^ai\.` keys anywhere ("does not use ai.* attribute prefix anywhere" open-telemetry.test.ts :2723–2738) while legacy emits almost nothing else — a port must pick ONE vocabulary, never mix. (2) Legacy keeps an in-file copy of selectAttributes/sanitize instead of importing from select-attributes.ts — duplication is deliberate isolation so the legacy file can be deleted whole. (3) `getBaseTelemetryAttributes` spreads settings via un-sanitized `ai.settings.${key}` (values may be objects — legacy predates strict sanitization). (4) `getTracer` helper (get-tracer.ts :4–20) returns noopTracer unless `isEnabled` — the packages/ai internal path; the otel package's own classes always construct real spans and rely on event-level gating instead.

**Probe:** `grep -c "recordErrorOnSpan" packages/otel/src/legacy-open-telemetry.ts` → 0 (local name is recordSpanError). `grep -n "'ai.streamText'" packages/otel/src/legacy-open-telemetry.ts` → :545/:671. `grep -c "ai.stream.firstChunk" packages/otel/src/legacy-open-telemetry.ts` → 2 addEvent sites (:465, :755). Direct tests: legacy-open-telemetry.test.ts describes at :443 onStepStart, :1082 telemetry-disabled trio, :1246 functionId, :1323+ integration suites for generate/stream/rerank/embed/embedMany/generateObject.

**Retrieve:** live-resolved rank-1 @pin:
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "LegacyOpenTelemetry assembleOperationName operation.name resource.name", limit: 3 });
// → otel assembleOperationName Function 3-21 rank-1
```

**Verdict:** ADAPT — mine for anyone maintaining V3-era telemetry or migrating old dashboards; new ports should take the modern plane.
