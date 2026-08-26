<!-- capsule-v2 -->
# Usage ledger aggregation — how do per-request token counts accumulate across turns, streams, and hostile provider payloads without ever throwing?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** What are the rules for merging a provider Usage into the run-level ledger — including when a per-request entry is recorded and when None-poisoned details are tolerated?

## Null-guarded add + entry synthesis rule
**Path/Symbol:** `src/agents/usage.py:` `Usage.add` (:257–312), `__post_init__` (:231–255), `request_usage_entries` (:218–229), raw sidecar `_raw_usage_snapshot`/`_attach_raw_usage_snapshot` (:20–56), without-usage marker `_mark_request_completed_without_usage`/`_requests_for_response_without_usage` (:318–343); stream-side conversion `ChatCmplStreamHandler._build_response_usage` (`chatcmpl_stream_handler.py:1353–1373`).
**Signature:** `Usage.add(self, other: Usage) -> None`; aggregation call sites `run_internal/run_loop.py:2636` (non-stream) and `:2306` (streamed): `context_wrapper.usage.add(response.usage)` before on_llm_end hooks.
**Data Shape:** `Usage{requests, input_tokens, output_tokens, total_tokens, input_tokens_details(cached_tokens, cache_write_tokens), output_tokens_details(reasoning_tokens), request_usage_entries: list[RequestUsage]}`.

### Decisive source
```python
self.requests += other.requests if other.requests else 0
...
other_cached = _cached_tokens(other.input_tokens_details)      # getattr(...) or 0
other_reasoning = (other.output_tokens_details.reasoning_tokens
                   if other.output_tokens_details and ... else 0)
self.input_tokens_details = _make_input_tokens_details(
    cached_tokens=self_cached + other_cached,
    cache_write_tokens=self_cache_write + other_cache_write)
...
if other.request_usage_entries:
    self.request_usage_entries.extend(copy.deepcopy(other.request_usage_entries))
elif other.requests == 1 and other.total_tokens > 0:
    # synthesize exactly one per-request entry from top-level fields
```

**Flow:** each completed model response adds its usage to `context_wrapper.usage` once, immediately after the response settles (streamed: only after the final response is assembled; `_build_response_usage` maps CompletionUsage→ResponseUsage null-guarding every detail) → totals sum with `if x else 0` guards because SDK `model_construct` can inject None past pydantic validation → details objects are REBUILT rather than mutated → per-request entries: existing entries merge deep-copied; otherwise one entry synthesizes iff exactly requests==1 AND total_tokens>0 (zero-token adds record nothing; multi-request aggregates never fabricate a fake breakdown) → raw provider payloads travel as fail-soft JSON sidecars (`_agents_sdk_raw_usage`; any conversion failure returns None instead of failing the call) → responses that legitimately carry no usage count toward `requests` only via explicit adapter opt-in marker.
**Invariant:** aggregation is total but honest — it can lose granularity (no synthesized entry for ambiguous adds) but never invents numbers or raises on malformed provider data; the ledger's top-level sums stay consistent with its detail rebuilds.
**Probe:** `tests/test_usage.py::test_usage_add_aggregates_with_none_values` (:142 asserts None-poisoned u1 still aggregates), `::test_usage_add_ignores_zero_token_requests` (:210), `::test_usage_add_ignores_multi_request_usage` (:230), `::test_usage_add_merges_existing_request_usage_entries` (:250), `::test_runner_run_carries_request_usage_entries` (:74).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "openai-agents-python", pattern: "usage.add", path_filter: "src/agents" });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.models.chatcmpl_stream_handler.ChatCmplStreamHandler._build_response_usage" });
```

## Verdict
Adopt guarded additive aggregation with rebuild-not-mutate details and the strict single-request synthesis rule for cost ledgers; adopt fail-soft raw snapshots for diagnostics. Adapt field names/details to your provider SDK. Omit the without-usage marker only if your adapters always receive usage. Coverage: no_recorded_issue @ gen 2026-08-24T14:05:06Z.
