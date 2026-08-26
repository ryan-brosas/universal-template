<!-- capsule-v2 -->
# Spill-read-back tool output: lossless bands, per-retry handle keys, bounded read slicing

## Source / Question
`pydantic_ai_harness/tool_output_limits/` (`_capability.py`, `_bands.py`, `_store.py`) — How do you keep an oversized tool return from dominating the context window FOREVER (returns persist in history and are re-sent every later request) without losing data the model still needs? Porters truncate in place and destroy the payload; or spill without a safe read-back path.

## Path / Symbol
`tool_output_limits/_capability.py` — `ToolOutputLimits(AbstractCapability)` (:74–154), `after_tool_execute` (:194–243), `_reduce`/`_apply`/`_fallback`/`_spill`/`_summarize_action` (:287–401), `_handle_key` (:448–455), `_build_spill_preview` (:486–509), `_read_slice` (:529–580); `_bands.py` — `Band(over, action)`, actions `Passthrough|Truncate|Spill|Summarize` each with `then` fallback; `_store.py` — `OverflowStore` protocol + `LocalFileStore` (:60–153).

## Signature
```python
bands=[Band(over=100_000, action=Spill()),        # sorted largest-first; first match wins
       Band(over=20_000, action=Summarize()),
       Band(over=5_000,  action=Truncate())]
key = f'{ctx.run_id or "run"}/{call.tool_call_id or "call"}.{ctx.retry}{suffix}'  # suffix=''|'.content'
```

## Data Shape
Reduction happens ONCE in `after_tool_execute`; the reduced form persists. Both reducible units — `return_value` and model-visible `content` — spill to distinct handles (suffix `.content`). Spill stand-in = header marker + optional JSON shape sketch + head/tail preview. Handles land in `ToolReturn.metadata` (`overflow_handle`/`overflow_bytes`/`overflow_content_handle`) — app-only, costs no model tokens.

### Decisive source
1. **Default band is lossless** (:54–56): `[Band(over=10_000, action=Spill(then=Truncate()))]` — "lossless when a store accepts the write, a bounded truncation otherwise," never a silent drop.
2. **Per-retry keys** (_handle_key :448–455): run_id/call_id/retry/suffix in the key "so concurrent and retried calls never clash."
3. **Read-back is bounded on both axes** (:522–580): `limit` clamped ≤1000 lines AND output capped at 50k chars ("output capped" flag); `pattern` is a LITERAL substring so a model-supplied value cannot hang the host with regex backtracking; negative offset / <1 limit raise `ModelRetry`.
4. **Wrong-handle returns, never raises** (:551–561): OSError on read ⇒ guiding text, not an exception — must not consume a retry and escalate to fatal; store error detail intentionally not echoed.
5. **Envelope preservation** (:245–276): wrapped `ToolReturn` keeps metadata and content shape; plain results upgrade to a ToolReturn only when spilled.
6. **Summarize escalation guard** (:396–398, :419–429): `UserError` (misconfiguration, e.g. realtime run without summarizer model= #585) re-raises — masking it with silent truncation would hide the user's bug; other exceptions fall back to `then`.

## Flow / Invariant
Intercept return → skip own read tool + non-matching filter + exception results → pick unit(s) → select first band by size → apply (binary always falls back for Truncate/Summarize; Spill failure falls back to `then`) → assemble preserving envelope. Invariants: reduction is production-time once, not per-request; errors the model needs (`ModelRetry`) never reach the hook (raised, not returned); read-back can never return unbounded text.

## Probe (direct test)
`tests/tool_output_limits/test_tool_output_limits.py`: `test_default_band_is_spill_then_truncate` (:299), `test_bands_sorted_descending` (:306), `TestSpill::test_spill_roundtrip` (:402), `test_handle_distinct_per_retry` (:443), `test_read_slice_literal_pattern_not_regex` (:683), `test_read_slice_limit_clamped` (:702), `test_read_slice_output_capped` (:708), `test_read_slice_missing_handle` (:715), `test_symlink_escape_rejected` (:231), `test_dotdot_handle_stays_in_root` (:223).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'ToolOutputLimits after_tool_execute _spill _read_slice OverflowStore'`

## Verdict
**Adopt** spill-with-bounded-read-back as the default large-return contract; adopt per-call/per-retry handle keying and literal-substring filtering. **Adapt** thresholds/bands per tool via `per_tool`. **Omit** LocalFileStore's temp-dir default if you have a durable object store — the protocol is two methods.
