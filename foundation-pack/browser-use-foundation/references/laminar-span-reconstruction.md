<!-- capsule-v2 -->
# Laminar span reconstruction — how do you emit OTel/GenAI-convention LLM and tool spans from a run you never called the LLM for?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** when inference happens inside a native core, how do you rebuild faithful per-turn LLM spans (inputs, outputs, usage, cost) plus tool spans from events alone — without blowing export limits on images?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py` — guarded shim family `_laminar_*` (:121-183: every call no-ops via `_laminar_ready()` and try/except→debug-log); turn spans `_record_laminar_terminal_llm_spans` (:3916, cap `BROWSER_USE_RUST_LAMINAR_MAX_LLM_SPANS`=80) over ranges from `model.turn.request`; tool spans `_record_laminar_terminal_tool_spans` (:3883, cap 160); GenAI attributes `_terminal_laminar_gen_ai_attributes` (:3742) with semconv converter `_terminal_laminar_semconv_content_part` (:3620); cost math `_terminal_laminar_usage_cost` :3342 over CUSTOM_MODEL_PRICING.
**Signature:** `_record_laminar_terminal_llm_spans(events, *, default_model, default_provider) -> None`.
**Data Shape:** turn input extracted from `model.turn.request` payload (`composition.tools|llm_input.{tools,messages,system}`, counts, `truncated`); usage summary dict `{input_tokens, cached_input_tokens, output_tokens, total_tokens, cache_creation…, cost_usd}`; image parts become data-URI `image_url` or `[image in span input]` blob placeholders.

### Decisive source
```python
# base64 blobs live ONCE in message content; attributes carry placeholders:
'Keep the full image-bearing messages in the span input/output. Repeating '
'base64 blobs in attributes makes OTLP exports exceed Laminar limits.'
'gen_ai.input.messages': json(_terminal_laminar_semconv_messages(input_messages, inline_image_data=False)),
# data URI → {type:'blob', blob, mimeType} inline / {type:'blob', content:'[image in span input]'} in attrs
if url.startswith('data:') and ';base64,' in url:
    header, blob = url.split(';base64;', 1)
    ...
# local screenshot files are re-read + inlined so judge spans show the page:
data = base64.b64encode(image_path.read_bytes()).decode('ascii')   # _terminal_laminar_image_part_from_path
# cost = (uncached×in + cached×read + creation(5m/1h) + out) × pricing_multiplier(1.1 default 'us')
# every span flushes immediately so a crashed run still exports:
with _laminar_start_span('rust_core.llm', input=..., span_type='LLM'):
    _laminar_set_span_attributes({...}); _laminar_set_span_attributes(gen_ai_attrs)
_laminar_force_flush()
```

**Flow:** after history assembly (`_record_laminar_run_observability` :4809), replay event ranges → one `rust_core.llm` span per turn (attributes = model/provider/turn_idx/usage/cost/duration + full gen_ai.* set + indexed `gen_ai.prompt.N.*` previews capped 20×12k chars) → one `rust_core.tool.<name>` span per started call matched to its result payload (images preserved as real parts; empty outputs get synthetic text; truncation emits `rust_core.llm_spans_truncated` events).
**Invariant:** telemetry can NEVER throw into the agent path (shim swallows everything); attribute payloads must stay under exporter limits (placeholder rule above is load-bearing); caps convert silently into explicit truncation marker events rather than dropping data quietly.
**Probe:** `tests/ci/test_beta_agent.py:7130` `test_rust_laminar_replay_flush_avoids_context_reset`, `:7130`+`:7368` `test_beta_agent_laminar_tool_span_preserves_image_only_outputs`, `:7103` trace-id exposure.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_record_laminar_terminal_llm_spans _terminal_laminar_gen_ai_attributes inline_image_data", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shim-guard pattern + post-hoc span replay + placeholder-image attribute budgeting for observability over foreign cores; adapt vendor attribute names; omit cost math if your pricing table is absent (spans still emit with None costs).
