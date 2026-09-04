<!-- capsule-v2 -->
# Usage span projection — how does run usage reach tracing spans at three granularities without double counting or zero-noise?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When a run finishes (or aborts), how is the accumulated `Usage` projected onto turn, task, and generic spans — and why does the delta snapshot pattern matter?

## Span-type dispatch + zero-guard attachment
**Path/Symbol:** `src/agents/run_internal/agent_runner_helpers.py:` `attach_usage_to_span` (:123–160), `usage_delta` (:80–110); projection helpers `src/agents/usage.py:` `model_usage_to_span_usage` (:434–448), `total_usage_to_span_metadata` (:450–461), `turn_usage_to_span_data` (:469–476), `task_usage_to_span_data` (:479–484).
**Signature:** `attach_usage_to_span(span: Span[Any] | None, usage: Usage) -> None`; `usage_delta(start: Usage, end: Usage) -> Usage`.
**Data Shape:** turn/task spans get `span_data.usage: dict[str, int]`; generic spans get `metadata["usage"] = total_usage_to_span_metadata(usage)` merged over a copied existing metadata dict.

### Decisive source
```python
if span is None or (
    usage.requests == 0 and usage.input_tokens == 0 and usage.output_tokens == 0
    and usage.total_tokens == 0 and cached_tokens == 0
    and cache_write_tokens == 0 and reasoning_tokens == 0):
    return
if span.span_data.type == "turn":
    span.span_data.usage = turn_usage_to_span_data(usage); return
if span.span_data.type == "task":
    span.span_data.usage = task_usage_to_span_data(usage); return
metadata = dict(getattr(span.span_data, "metadata", None) or {})
metadata["usage"] = total_usage_to_span_metadata(usage)
span.span_data.metadata = metadata
```

**Flow:** every attachment site computes `usage_delta(task_usage_start, context_wrapper.usage)` — a per-field subtraction snapshot taken BEFORE the turn/task began — then attaches inside a `finally:` block so both success and `BaseException` teardown land usage on the span before `finish(reset_current=True)` → call sites: `run.py:957` (input-guardrail exception teardown), `run.py:1754` (per-turn finally), `run.py:2191` (task finally), `run_loop.py:1171` (streamed exception teardown), `:1780` (streamed per-turn), `:2016` (streamed task finalize) → projection shapes differ by granularity: model spans carry full details (`input_tokens_details`/`output_tokens_details` objects), turn spans drop `requests`/`total_tokens`, task spans add both back, generic spans get flat ints plus precomputed `cached_input_tokens`/`cache_write_input_tokens` keys → model-level spans are populated by the model adapters themselves (`openai_responses.py:602/:689`, `openai_chatcompletions.py:561`, `any_llm_model.py:437/:528/:824`, `litellm_model.py:491`) via `model_usage_to_span_usage`, never by the runner — so runner and adapter projections never overlap.
**Invariant:** one span receives usage at most once per attachment site (finally, not post-success), the delta is snapshot-based so retried/aborted turns cannot double count, an all-zero usage attaches nothing (no zero-noise spans), and `span is None` is a silent no-op — tracing failures can never alter run semantics.
**Probe:** `tests/test_usage.py::test_usage_snapshot_delta_and_span_preserve_cache_write_tokens` (:638 pins delta + `model_usage_to_span_usage` preserving cache_write_tokens through subtraction), `tests/models/test_any_llm_model.py:2095` (span populated before yielding completed event).
