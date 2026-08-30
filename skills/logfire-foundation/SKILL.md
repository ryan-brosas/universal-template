---
name: logfire-foundation
description: "Use when porting logfire's OTel-native telemetry machinery: fail-soft span factories, disk-backed export reliability, scrubbing, tail sampling, managed variables."
disable-model-invocation: true
---

# logfire: OTel-Native Observability SDK Foundation

## Use this for
Use when building or porting an observability/tracing SDK on OpenTelemetry primitives: proxy-provider deferred configuration, message-template spans with f-string magic, attribute coercion to OTLP wire types, resilient OTLP export (bisection + disk retry), pending-span live-tail protocol, scrubbing with audit trails, head+tail sampling, exception fingerprinting, and remote-managed variables with compose→render→deserialize resolution. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/proxy-provider-swap.md` — how pre-configure spans/instruments flow into real providers after configure().
- `references/logfirespan-lazy-lifecycle.md` — lazy start/attach/end state machine and post-creation attribute consistency.
- `references/otlp-attribute-coercion-ladder.md` — Enum→int-guard→float-guard→JSON ladder that never raises.
- `references/disk-retry-export-plane.md` — failed POST → 1s retry → 512MB-budgeted disk queue with jittered backoff.
- `references/body-size-bisection-export.md` — oversized batches split recursively via exception signal.
- `references/dynamic-batch-warmup.md` — 100ms first-10-spans responsiveness settling to configured cadence.
- `references/pending-span-protocol.md` — zero-duration shadow events that render in-flight traces in the UI.
- `references/fstring-magic-formatting.md` — executing-based f-string template reconstruction with structured degradation.
- `references/scrubbing-engine.md` — pattern/key matching, whole-value exemption, JSON recursion, path-addressed audit notes.
- `references/span-normalization-pipeline.md` — ordered dict-mutation tweaks turning raw instrumentation spans into queryable records.
- `references/attribute-driven-tail-sampling.md` — deterministic span-id-threshold sampling transported on the span itself.
- `references/exception-fingerprint-canonicalization.md` — line/path-insensitive traceback hashing incl. groups/cycles.
- `references/resource-precedence.md` — five-tier resource merge order with derived-version write-back.
- `references/multi-token-fanout.md` — per-token exporter pipelines for project migration with header reassertion.
- `references/variable-resolution-pipeline.md` — override→provider/label→code-default chain with strict-vs-lenient composition.
- `references/targeting-key-resolution.md` — call-site→contextvar→trace-id targeting ladder for rollouts.
- `references/remote-variable-provider-lifecycle.md` — SSE-push/poll-fallback config freshness with first-resolve blocking.
- `references/tail-sampling-buffer-fsm.md` — whole-trace buffering with immediate-vs-deferred processor replay.
- `references/log-method-internals.md` — logs as zero-duration spans; exc_info normalization and status gating.
- `references/json-schema-sidecar.md` — inline per-attribute JSON Schema with size-tiered shapes.
- `references/distributed-tracing-propagator-guard.md` — warn/suppress wrappers around global textmap extraction.
- `references/fail-soft-telemetry-discipline.md` — four-layer error containment guaranteeing zero user-facing crashes.
- `references/level-scale-gating.md` — sparse OTEL severity scale with create-time min_level gates.
- `references/exit-flush-choreography.md` — atexit ordering, open-span registry, os._exit patch.
- `references/credentials-bootstrap-ladder.md` — env > creds-file > interactive token bootstrap with background validation.

## Capsule map
- **Core span factories** — `proxy-provider-swap`, `logfirespan-lazy-lifecycle`, `otlp-attribute-coercion-ladder`: deferred configuration via factory registries, lazy CM lifecycle, never-raise wire coercion.
- **Export reliability** — `disk-retry-export-plane`, `body-size-bisection-export`, `dynamic-batch-warmup`: two-tier retry to a byte-budgeted disk queue, recursive payload splitting, responsive batching warmup.
- **Live-tail & sampling** — `pending-span-protocol`, `attribute-driven-tail-sampling`, `tail-sampling-buffer-fsm`: shadow start-events, per-span deterministic rates, whole-trace buffered decisions with deferred replay.
- **Data quality** — `fstring-magic-formatting`, `scrubbing-engine`, `span-normalization-pipeline`, `json-schema-sidecar`: template reconstruction from AST, audited redaction, ordered normalization tweaks, typed sidecars.
- **Error semantics** — `exception-fingerprint-canonicalization`, `fail-soft-telemetry-discipline`, `log-method-internals`, `level-scale-gating`: stable issue grouping, four-layer containment, log-as-span records, sparse severity scale.
- **Configuration plane** — `resource-precedence`, `multi-token-fanout`, `distributed-tracing-propagator-guard`, `credentials-bootstrap-ladder`, `exit-flush-choreography`: tiered resource merges, migration fanout, guarded propagation, token bootstrap, exit hooks.
- **Managed variables** — `variable-resolution-pipeline`, `targeting-key-resolution`, `remote-variable-provider-lifecycle`: three-tier resolution with composition strictness asymmetry, rollout targeting ladders, push-primary freshness.

## Extending the foundation
Add one `references/<seam>.md` capsule-v2 for one graph-selected, source-confirmed porting question (candidates pass 2+: `logfire/_internal/auto_trace/` AST rewrite engine (`rewrite_ast.py` import-hook function wrapping), `baggage.py` DirectBaggageAttributesSpanProcessor, `integrations/asgi.py` request-span choreography, `experimental/forwarding.py` browser-telemetry proxy, `db_api.py` LogfireSQLAlchemy client, console exporters' show-parents rendering). Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
logfire (Pydantic, MIT), `main@e484a6b53a0df3062d304ce258573e387cf3140a`; Codebase Memory project `ext-logfire` (8,979n / 40,037e FULL mode, generation matches HEAD, parse_partial ×0; not_indexed = docs images only by design; all Retrieve queries resolve rank#1 line-exact). Upstream is 1 docs-only commit ahead (4037e19, service-monitoring docs/screenshots) — pin still current for code. Pass-1 squeeze, LLM-serving + RAG broad lane.

## Full view (memory graph)
Revalidate `ext-logfire` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Graph entry points: `Logfire._span`, `LogfireConfig._initialize`, `MainSpanProcessorWrapper.on_end`, `DiskRetryer._run`, `TailSamplingProcessor.on_start/on_end`, `Variable._resolve_inner`. BM25 is the working retrieval primitive (semantic mode untested this pass); upstream test suite runs under pytest with opentelemetry dev deps.

## Boundaries
Adopt pure contracts: coercion ladders, retry/budget math, sampling thresholds, scrubbing match rules, fingerprint canonicalization, resolution priority chains. Adapt host-specific integration: OTEL SDK provider/exporter classes, Rich CLI prompts, requests sessions, pydantic TypeAdapter validation, anyio threading. Omit product behavior: Logfire-cloud endpoints/region tokens, web UI record shapes, vendor LLM-instrumentation transforms beyond their pattern lesson, Pyodide/Emscripten branches unless porting there.
