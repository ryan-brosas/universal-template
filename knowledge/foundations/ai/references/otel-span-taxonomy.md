<!-- capsule-v2 -->
# otel span taxonomy & naming — operation/step/languageModel/tool/embedding/reranking hierarchy and its performance attributes

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai`. **Question:** What span types, names, SpanKinds, and timing attributes does a GenAI tracer emit so backends can build service graphs and latency histograms?

## Path/Symbol
`packages/otel/src/supplemental-attributes.ts:OpenTelemetrySpanType` (:24–30) — the six-value union `'operation' | 'step' | 'languageModel' | 'tool' | 'embedding' | 'reranking'` consumed by `enrichSpan`; names/kinds at open-telemetry.ts :306–316/:496–510/:664–677/:734–747/:931–944/:1201–1214/:1288–1297.

**Signature:** root = INTERNAL `` `${operationName} ${modelId}` `` (e.g. `invoke_agent gpt-4`, `embeddings text-embedding-3`, `rerank …`); step = INTERNAL `` `step ${event.steps.length + 1}` `` (:665 — 1-based counter from PRIOR steps array); chat = CLIENT `chat <modelId>` (:496/:735); tool = INTERNAL `execute_tool <toolName>` (:864/:931).

### Decisive source
```ts
function getGenAIClientPerformanceAttributes(
  performance: LanguageModelCallEndEvent<ToolSet>['performance'],
): Attributes {
  return {
    'gen_ai.client.operation.duration': msToSeconds(performance.responseTimeMs),
    'gen_ai.client.operation.time_to_first_chunk': msToSeconds(
      performance.timeToFirstOutputMs,
    ),
    'gen_ai.client.operation.time_per_output_chunk': msToSeconds(
      performance.timeBetweenOutputChunksMs?.avg,
    ),
  };
}
```
(:96–108; `msToSeconds` returns undefined for nullish :92–94 — absent metrics emit NOTHING, not 0)

**Flow:** kind choice encodes topology: roots for embed/rerank are CLIENT (direct provider calls) but generateText/object roots are INTERNAL (agent orchestration wrapping client chat children). Usage/response attributes split by level — token usage lands on BOTH chat span (per-step) and root (totals, onGenerateEnd :1058–1095); `finish_reasons` arrays appear at both; cache tokens (`cache_read`/`cache_creation`) ride detailed usage. Tool spans additionally get `gen_ai.execute_tool.duration` from `event.toolExecutionMs` (:967). The multi-step lifecycle test pins the exact tree: `[invoke_agent, step 1, chat, execute_tool myTool, step 2, chat]` all ended (:2438–2522) and single-step trace snapshot shows which attributes are init vs runtime (:2524–2586).

**Invariant:** (1) Step numbering is DERIVED (`steps.length + 1`), not carried — a port that trusts an event-provided index breaks on retry/reordered steps. (2) Durations convert ms→SECONDS per SemConv metric conventions with undefined-passthrough; emitting 0 instead of omitting fabricates sub-millisecond latencies. (3) The six-type union is the enrichSpan contract surface — every startSpan site passes one, so integrators can tag any span class without string-matching names. (4) `chat` spans carry `gen_ai.request.*` replayed from state settings while `step` spans stay minimal (`gen_ai.operation.name:'agent_step'` + optional toolChoice) — sampling params belong to the model call, not the loop.

**Probe:** `grep -c "gen_ai\.operation\.name" packages/otel/src/open-telemetry.ts` → 11 sites. `grep -c "gen_ai\.client\.operation" packages/otel/src/open-telemetry.ts` → 3. `grep -n "msToSeconds" packages/otel/src/open-telemetry.ts | head -3` → :92 def, :100/:967 uses. Direct tests: open-telemetry.test.ts :726 ("sets GenAI client performance attributes"), :1246 ("sets GenAI execute_tool duration"), full-lifecycle snapshots :2489/:2532.

**Retrieve:** live-resolved @pin:
```ts
await mcp.codebase_memory.search_graph({ project: "ai", name_pattern: "executeLanguageModelCall", detail: "ids", limit: 5 });
// → ai.packages.otel.src.open-telemetry.OpenTelemetry.executeLanguageModelCall among 8 hits
```

**Verdict:** ADOPT — this is the concrete GenAI-semconv span blueprint; naming/kind table is the portable part.
