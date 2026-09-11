<!-- capsule-v2 -->
# OpenLit observability init — air-gap-safe OTel auto-instrumentation with local pricing

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you turn on zero-config LLM tracing/metrics that survives an air-gapped environment where GitHub egress is blocked?

## openlit_init wires global auto-instrumentation with bundled pricing
**Path/Symbol:** `src/cuga/backend/observability/openlit_init.py` (module docstring :1-60 research notes, `_BUNDLED_PRICING_JSON` :58, init body :60-404 incl. SessionSpanProcessor).
**Signature:** `openlit.init(...)` invoked at startup when `[observability] openlit = true`; endpoint from `OTEL_EXPORTER_OTLP_ENDPOINT` (default http://localhost:4318), optional `OTEL_EXPORTER_OTLP_HEADERS`.
**Data Shape:** settings keys `observability.pricing_json` (empty = bundled `observability/assets/pricing.json`) and `observability.litellm_local_model_cost_map` (default true).

### Decisive source
```python
# openlit_init.py docstring pins the two air-gap decisions verbatim:
# - OpenLit defaults to fetching pricing from raw.githubusercontent.com. CUGA always
#   passes a local pricing.json from settings.observability.pricing_json (empty =
#   bundled under observability/assets/). LiteLLM's remote model cost map is
#   controlled by settings.observability.litellm_local_model_cost_map (default true).
# - openlit.init() is pure global auto-instrumentation via monkey-patching.
#   Internally uses a TRACER_SET global flag in otel/tracing.py — already idempotent.
# - Fully synchronous — safe to call from any context (sync or async).
```

**Flow:** flag on → resolve pricing.json path (configured file wins, else bundled asset — NEVER the remote default) → `openlit.init()` instruments openai/groq/litellm/langchain_core/langgraph/mcp/mem0/fastapi/httpx globally → spans/metrics flow OTLP to any collector (local docker-compose stack documented in deployment/docker-compose/openlit). No per-request wiring exists because instrumentation is global; repeated calls are absorbed by OpenLit's own TRACER_SET flag.
**Invariant:** in air-gapped deployments the pricing fetch MUST be pinned local or startup traces fail against raw.githubusercontent.com; init is synchronous so it can be called before either sync or async loops start; do not add per-request handlers — this is deliberately NOT a callback-handler design like Langfuse.
**Probe:** no unit suite (integration surface); deterministic anchors: module docstring contract lines and `_BUNDLED_PRICING_JSON = Path(__file__).resolve().parent / "assets" / "pricing.json"` at openlit_init.py:58 — coverage caveat recorded.
**Retrieve:**
```python
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "OpenLit observability pricing airgap", limit: 5 });
```

## Verdict
Adopt the air-gap contract (always-local pricing + local cost map default) for any OpenTelemetry-based LLM observability rollout. Adapt collector endpoints/settings keys. Omit the CUGA-specific docker-compose stack reference.
