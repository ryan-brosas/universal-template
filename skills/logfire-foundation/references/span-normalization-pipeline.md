<!-- capsule-v2 -->
# Span normalization pipeline — what ordered tweaks turn raw OTEL-instrumentation spans into consistent, queryable records?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** In what order does MainSpanProcessorWrapper mutate ended spans, and what are the per-tweak contracts a porter must preserve?

## MainSpanProcessorWrapper.on_end chain
**Path/Symbol:** `logfire/_internal/exporters/processor_wrapper.py:MainSpanProcessorWrapper.on_end` (`processor_wrapper.py:61-113`).
**Signature:** `on_end(self, span: ReadableSpan)` — converts to mutable `ReadableSpanDict` via `span_to_dict`, runs tweak functions, rebuilds `ReadableSpan(**span_dict)`.
**Data Shape:** dict mutation (ReadableSpan is immutable); scrubber runs LAST inside the wrapper.

### Decisive source
```python
def on_end(self, span: ReadableSpan) -> None:
    with handle_internal_errors:
        span_dict = span_to_dict(span)
        _tweak_asgi_send_receive_spans(span_dict)   # 'GET /foo http send' -> '... http send response.body'
        _tweak_sqlalchemy_connect_spans(span_dict)  # bare 'connect' span -> debug level (hidden by default)
        _tweak_http_spans(span_dict)                # name=method+route (low cardinality), msg=method+target(+host,+?params sorted by len, values truncated to 20 chars)
        _set_error_level_and_status(span_dict)      # bidirectional status<->level defaulting + HTTP-kind heuristics
        _tweak_fastapi_span(span_dict)              # dedupe repeated exception events keeping LATER fuller traceback (reverse walk)
        _summarize_db_statement(span_dict)          # db.statement -> compact message
        _transform_langchain_span(span_dict)        # langsmith/openinference attrs -> gen_ai.* + all_messages_events JSON array
        _transform_google_genai_span(span_dict)     # gen_ai.* events -> 'events' attribute w/ json_schema
        _transform_litellm_span(span_dict)          # openinference litellm -> request_data/response_data + token counts + tags=['LLM']
        _default_gen_ai_response_model(span_dict)   # copy request.model -> response.model when missing
        self.scrubber.scrub_span(span_dict)
        span = ReadableSpan(**span_dict)
    super().on_end(span)
```
Key sub-contract — `_set_error_level_and_status`: ERROR-status spans without explicit level get error level; UNSET-status spans WITH an int level ≥ error threshold get ERROR status (making `level` and `otel_status_code` interchangeable query keys); otherwise SERVER kind with http.status_code ≥500 ⇒ error, CLIENT kind ≥400 ⇒ error, SERVER 400–499 ⇒ warning only.
Key sub-contract — `_tweak_http_spans` guard: bails immediately if `logfire.msg_template` present ("intended for OTEL instrumentations … written to be general") or name ≠ message; derives `http.target` from `http.url` path when absent; client messages prepend server.address/http.host/URL-hostname.
**Flow:** every ended span funnels through ONE wrapper placed above the whole multiprocessor tree (`config.py:1463-1467`: `CheckSuppressInstrumentationProcessorWrapper(MainSpanProcessorWrapper(root_processor, scrubber))`), so instrumentation-suppression check is outermost and suppression context is applied around user processors too.
**Invariant:** Tweak ORDER is load-bearing (HTTP name/message fixes precede level/status derivation which inspects http attributes; dedupe precedes scrubbing so notes reflect final state). The dict-rebuild pattern exists because OTEL ReadableSpan is immutable — port it rather than fighting immutability.
**Probe:** `tests/test_processor_wrapper.py` — pins each tweak's trigger conditions and output shapes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "MainSpanProcessorWrapper _set_error_level_and_status _tweak_http_spans", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: single normalization choke-point over a mutable dict, ordered tweak registry, bidirectional status/level defaulting, low-cardinality-name/high-information-message split. Adapt vendor-specific transforms to your instrumented frameworks. Omit LangSmith/LiteLLM arms unless those ecosystems matter to you.
