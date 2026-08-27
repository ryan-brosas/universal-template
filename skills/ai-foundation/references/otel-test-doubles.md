<!-- capsule-v2 -->
# otel test doubles — MockTracer/noopTracer and the InMemorySpanExporter integration harness

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai`. **Question:** How do you make span-tree behavior deterministic in tests — both unit-level assertions and full OTel SDK round-trips?

## Path/Symbol
`packages/otel/src/mock-tracer.ts:MockTracer/MockSpan` (:14–156); `noop-tracer.ts:noopTracer/noopSpan` (:6–69); open-telemetry.test.ts harness `createMockSpan/createMockTracer/serializeTrace` (:43–156), `createSdkTracer` (:103–113).

**Signature:** `MockTracer implements Tracer` recording `spans: MockSpan[]`; its THREE-ARGUMENT `startActiveSpan` overload discrimination (`typeof arg1 === 'function'` → callback-only, else options/context forms :36–66) mirrors the real API's overloads. `noopTracer` is a frozen null-object whose every Span method returns the same singleton.

**Data Shape:** MockSpan captures `{name, attributes (merged on setAttributes), events[], status}` and synthesizes exception EVENTS from `recordException` (:136–149) with `exception.type/name/message/stack`. The test-file mock goes further: `ended` flag + `exceptions[]` raw array + `initAttributes` recovered from `tracer.startSpan.mock.calls[i][1].attributes` so tests can assert START-time vs RUNTIME attributes separately (`serializeSpan` :138–152).

### Decisive source
```ts
  get jsonSpans() {
    return this.spans.map(span => ({
      name: span.name,
      attributes: span.attributes,
      events: span.events,
      ...(span.status && { status: span.status }),
    }));
  }
```
(mock-tracer.ts :17–24)

**Flow:** unit suites inject `new OpenTelemetry({ tracer })` with either the shipped MockTracer or the file-local vi.fn mock; assertions run against `jsonSpans`/`serializeTrace` snapshots. Integration suites instead build a REAL pipeline — `BasicTracerProvider` + `SimpleSpanProcessor(InMemorySpanExporter)` (:103–113) — run actual generateText/streamText/embed against `MockLanguageModelV4`/`MockEmbeddingModelV4` from `ai/test`, then pull finished spans via `exporter.getFinishedSpans()` and match by name (`getExportedSpan` :115–119). record-span.test.ts exercises `recordSpan`'s error contract against MockTracer: rejects-with-error → status `{code:2, message}` + one 'exception' event; double-record path yields TWO events (:93–112).

**Invariant:** (1) Two mock layers exist because they verify different things — attribute CONTENT needs start-vs-runtime split (mock calls array), while parenting/export needs a real context engine (InMemory exporter proves spans actually close under the SDK). (2) noopTracer must keep returning `this` from setters so call-site chaining never branches on null — a porter whose noop returns undefined crashes enabled=false paths at the first setAttribute. (3) `recordSpan`'s captured-context trick (`const ctx = context.active(); await context.with(ctx, () => fn(span))` :26–31) exists because async generators lose active span context across yields — that re-binding is what makes provider doStream tracing work at all.

**Probe:** `grep -n "trace.getTracer('ai')" packages/otel/src/get-tracer.ts` → :19. `grep -n "isRecording()" packages/otel/src/mock-tracer.ts packages/otel/src/noop-tracer.ts | head -3`. Direct tests: record-span.test.ts whole (:13 result pass-through, :50 error status+event, :73 Promise attrs); stringify-for-telemetry.test.ts :22 Uint8Array→base64 snapshot `"iVBOR///"`.

**Retrieve:** live-resolved rank-1 @pin:
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "recordSpan startActiveSpan endWhenDone recordErrorOnSpan", limit: 3 });
// → otel recordSpan Function 8-50 rank-1, recordErrorOnSpan 60-74 rank-2
```

**Verdict:** ADOPT — the double-layer test architecture ports to any event-driven telemetry integration.
