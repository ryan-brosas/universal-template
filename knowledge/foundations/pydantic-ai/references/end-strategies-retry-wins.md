<!-- capsule-v2 -->
# End strategies & retry-wins — how do early/graceful/exhaustive order output tools against function tools, and when does a function-tool retry revoke a won result?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** Given one model response with mixed output + function tool calls, what execution order and winner-selection rules apply per strategy — and under what condition is an already-chosen final result suppressed?

## The three-strategy processor family
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_tool_execution.py:process_tool_calls` (254–321), `_ToolCallProcessor` (324–1050) with subclasses `_EarlyProcessor` (1053–1078), `_GracefulProcessor` (1081–1107), `_ExhaustiveProcessor` (1110–1291); retry-wins at `_is_retry_wins_trigger` (881–890) + `_apply_retry_wins` (892–908).
**Signature:** `process_tool_calls(tool_manager, *, tool_calls, tool_call_results, tool_call_metadata, final_result, ctx, output_parts, output_final_result=None) -> AsyncIterator[HandleResponseEvent]`; strategy picked from `ctx.deps.end_strategy ∈ {'early','graceful','exhaustive'}`.
**Data Shape:** Output parts accumulate in-place in `output_parts` (survives exceptions — partial capture); the final result travels via a 1-deep deque (`output_final_result`) because async generators can't return values.

### Decisive source
```python
# _tool_execution.py docstring contract :265-290 (condensed; verified against impls)
# 'early':     output tools sequentially, stop at first success;
#              function tools run ONLY if every output failed.
# 'graceful':  emission order — pending function tools flush before each output tool;
#              outputs stop at first success; function tools parallelize per segment.
# 'exhaustive': everything runs; first valid output BY EMISSION ORDER wins while the rest execute.

# :881-890 — the single predicate behind retry-wins on every path
def _is_retry_wins_trigger(self, part, *, kind):
    # A RetryPromptPart from a real FUNCTION tool suppresses an otherwise-valid output,
    # so the model addresses the retry next round. Retries from UNKNOWN/hallucinated
    # tools don't — they aren't work that needs to complete before the output is valid.
    return isinstance(part, _messages.RetryPromptPart) and kind == 'function'

# :892-908 — suppression mechanics: replace the winner's status part by identity
idx = self.output_parts.index(self.winning_output_part)
self.output_parts[idx] = dataclasses.replace(self.winning_output_part, content=_RETRY_WINS)
self.final_result = None
```

**Flow:** Classify each call once by kind (`__post_init__`, preserving emission order) → run the strategy → `_apply_retry_wins()` (graceful/exhaustive only; never when the final result was committed externally by `run_stream`) → `_finalize_deferred()`. Status constants are centralized (`_FINAL_RESULT_PROCESSED = 'Final result processed.'` etc., :29-38) so producers and `_apply_retry_wins` share wording. Under exhaustive, output tasks that hit max-retries are absorbed as skip-status parts if another output won, and re-raised only if none did (:1224-1231).
**Invariant:** Retry-wins triggers ONLY on kind `'function'` retries — output-tool retries and unknown-tool retries never revoke. Externally pre-set results (`run_stream`) can't be revoked. The winning status part is tracked as an object reference (`winning_output_part`) so replacement is identity-based, not string-matching. `_prune_duplicate_tool_reveals` must run exactly once per pass (non-idempotent).
**Probe:** `tests/test_agent.py::TestMultipleToolCalls::test_early_strategy_stops_after_first_final_result` (:4707) — snapshot pins all four skip-stub contents incl. the deferred one; `test_early_strategy_skips_unknown_tool_call_when_structured_output_wins` (:5066) pins the missing-kind arm.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "process_tool_calls _EarlyProcessor _GracefulProcessor _ExhaustiveProcessor _apply_retry_wins", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three named strategies + the single retry-wins predicate + identity-tracked status-part replacement; adapt which strategies you expose (graceful default here); omit streaming-specific external-commit handling if you have no stream-committed outputs. Caveat: none — full file read this session.
