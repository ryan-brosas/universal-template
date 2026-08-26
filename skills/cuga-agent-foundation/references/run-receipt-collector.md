<!-- capsule-v2 -->
# Run receipt — how do you produce a per-invocation token/timing receipt that survives malformed provider responses and never breaks the run?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** The SDK wants a per-run token/latency picture (models, tokens, cache-read, reasoning, tool timings) — how does a LangChain AsyncCallbackHandler accumulate usage without ever raising, and how is it aggregated into a receipt?

## Fail-safe per-run collector + aggregate receipt
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/run_receipt.py:70-157` (`RunMetricsCollector(AsyncCallbackHandler)`), `:160-201` (`build_run_receipt`), dataclasses `RunReceipt` `:25-67`, `ToolTiming` `:19-22`.
**Signature:** `RunMetricsCollector` — `on_chat_model_start/on_llm_start` record start time + model name per run_id; `on_llm_end` accumulates usage; `on_llm_error` clears pending state. `build_run_receipt(collector, tool_calls: list[dict]|None, wall_time_s) -> RunReceipt | None`.
**Data Shape:** `RunReceipt` = `{models: [str], input_tokens, output_tokens, total_tokens, cache_read_tokens, reasoning_tokens, llm_calls, tool_call_count, llm_time_s, tool_time_s, wall_time_s, slowest_tool, tool_timings: [ToolTiming]}`. `ToolTiming` = `{name, calls, total_ms}`. Deliberately reports TOKENS only, not cost — CUGA runs against self-hosted/internal deployments whose price is unknown, so a cost figure would be wrong for some users.

### Decisive source
```python
# run_receipt.py:105-155 — on_llm_end: never raise, read usage from message OR llm_output
try:
    self.llm_calls += 1
    started = self._started_at.pop(str(run_id), None)
    if started is not None:
        self.llm_time_s += time.monotonic() - started
    generations = getattr(response, "generations", None) or []
    first = generations[0][0] if generations and generations[0] else None
    message = getattr(first, "message", None)
    usage = getattr(message, "usage_metadata", None) or {}
    cache_read_tokens = int((usage.get("input_token_details") or {}).get("cache_read") or 0)
    reasoning_tokens = int((usage.get("output_token_details") or {}).get("reasoning") or 0)
    if not usage:
        legacy = llm_output.get("token_usage") or {}
        usage = {"input_tokens": legacy.get("prompt_tokens",0), "output_tokens": legacy.get("completion_tokens",0), ...}
    ...
    if not (input_tokens or output_tokens or total_tokens or cache_read_tokens):
        return  # no usage anywhere — don't record a zero "unknown" model
except Exception as e:
    logger.debug(f"RunMetricsCollector.on_llm_end skipped: {e}")
```

**Flow:** A fresh `RunMetricsCollector` is attached per `CugaAgent.invoke()` so concurrent runs never share counters (unlike the process-global ActivityTracker). `on_llm_end` reads usage from `message.usage_metadata` first, falls back to `llm_output.token_usage` (legacy), extracts `cache_read` from `input_token_details` and `reasoning` from `output_token_details`, and skips recording entirely if there's no usage anywhere (avoiding a zero "unknown" model). `build_run_receipt` aggregates per-model usage, sums tool timings into `ToolTiming` sorted by total_ms (slowest first), and returns None on any failure (the run is never affected by a broken receipt). `RunReceipt.__str__` renders a box with model, tokens (incl. %-cached and reasoning), call counts, and timing.

**Invariant:** Every code path is fail-safe — a broken provider response or malformed tool-call record degrades the receipt (or drops it), never the run. The collector is per-run (not global) so concurrent SDK invocations don't cross-contaminate counters. Token counts are reported, never cost.

**Probe:** `tests/unit/test_run_receipt.py:31` (`test_collector_accumulates_usage_metadata_per_model`), `:44` (`test_collector_falls_back_to_legacy_llm_output`), `:64` (`test_collector_reads_usage_from_llm_output_when_generations_empty`), `:81` (`test_collector_accumulates_cache_read_tokens`), `:100` (`test_collector_accumulates_reasoning_tokens`), `:119` (`test_collector_never_raises_on_malformed_response`), `:129` (`test_build_receipt_aggregates_tools_and_tokens`), `:151` (`test_empty_receipt_builds_and_renders`), `:183` (`test_build_receipt_returns_none_on_broken_collector`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "RunMetricsCollector build_run_receipt RunReceipt on_llm_end", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fail-safe per-run collector with usage-metadata-first-then-legacy fallback, the cache-read/reasoning extraction, the no-usage skip, and the None-on-failure aggregate. Adapt the receipt fields to your telemetry needs. Omit the box-drawing `__str__` if you don't need a console render. Direct-test coverage is comprehensive.
