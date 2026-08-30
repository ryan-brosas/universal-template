<!-- capsule-v2 -->
# Stream chunk aggregation — how do accumulated stream chunks fold into one final response without billing the Anthropic cursor placeholder?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `litellm`. **Question:** What ordering, merging, and usage-accumulator rules turn a chunk list into a `ModelResponse`, and when must a stale usage placeholder be reset to 0?

## ChunkProcessor fold kernel
**Path/Symbol:** `litellm/litellm_core_utils/streaming_chunk_builder_utils.py:ChunkProcessor` (:176-1025); `_sort_chunks` (:182-209); `_get_model_from_chunks` (:278-293); `get_combined_tool_content` join-by-(index, field) (:377-390+); `_reset_anthropic_cursor_completion_tokens` (:881-917); `calculate_usage` (:919-1025).
**Signature:** `def __init__(self, chunks: list, messages: list | None = None)` → `chunk_processor(...)` builds a `ModelResponse` with merged content/tool-calls/thinking/audio and a computed `Usage`.
**Data Shape:** input chunks are dicts or `ModelResponseStream` objects carrying optional `_hidden_params` (`created_at`, `custom_llm_provider`) and optional per-chunk `Usage` (Anthropic puts usage on `message_start` + final `message_delta`).

### Decisive source
```python
        saw_non_cursor_completion: Final = completion_tokens > 1 or completion_usage_updates >= 2
        if saw_non_cursor_completion:
            return completion_tokens
        ...
        if custom_llm_provider == "anthropic" and completion_tokens == 1:
            return 0
        return completion_tokens
```
(:901-917) — docstring :886-899: Anthropic `message_start` carries `output_tokens=1` as a *cursor*; if that was the only completion update (cancelled stream), reset to 0 so the fallback estimates from real text. The fallback itself:
```python
        returned_usage.completion_tokens = (
            completion_tokens
            or token_counter(model=model, text=completion_output, count_response_tokens=True)
        )
```
(:953-960). Ordering rule: chunks are re-sorted by `_hidden_params.created_at` **only when the first chunk carries it**, otherwise arrival order is kept (:197-209); model-from-chunks prefers any later differing model over the first chunk's model (Azure Model Router) (:279-293).

**Flow:** sort conditionally → build base response (first-chunk id/model, later-model override) → merge content / tool-call fragments grouped by `(index, field)` → compute usage via last-wins accumulator over usage-bearing chunks (+cache/server-tool/reasoning details) → cursor reset gate → `or token_counter(...)` text fallbacks for prompt/completion.
**Invariant:** a truthy-but-stale usage value must not suppress the token-counter estimate; provider-specific heuristics are gated on `_hidden_params.custom_llm_provider` so they never touch other providers' legitimate values.
**Probe:** direct tests run live at the pin: `python3 -m pytest tests/test_litellm/litellm_core_utils/test_streaming_chunk_builder_cursor.py -q` → **11 passed in 0.37s** (pins cursor-only→0, message_delta last-wins→real value, end-to-end fallback).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm", query: "anthropic message_start cursor output_tokens placeholder reset", limit: 5 });
// adversarial prose query at pin: rank-1 = TestAnthropicCursorBug.test_only_message_start_cursor_resets_completion_to_zero,
// rank-2 = ChunkProcessor._reset_anthropic_cursor_completion_tokens :881-917
```

## Verdict
Adopt the conditional created_at sort, the (index, field) tool-call fragment join, last-wins usage accumulation with explicit detail fields, the provider-gated cursor reset, and the `or token_counter(text=...)` fallback ladder. Adapt chunk/usage type names to your stream envelope; re-derive Anthropic's exact SSE shapes from its docs before porting the heuristic elsewhere. Omit provider pricing fields passthrough (`inference_geo`, `speed`) unless your Usage schema has them.
