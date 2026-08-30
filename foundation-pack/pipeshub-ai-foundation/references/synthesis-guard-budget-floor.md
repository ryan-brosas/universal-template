<!-- capsule-v2 -->
# Synthesis guard (hard budget floor + fail-loud exception)

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/synthesis_guard.py` (whole file, 157L).

## Path/Symbol
- `ContextBudgetExceeded(token_count, budget)` (:32) — carries both numbers
- `_strip_thinking(messages)` (:102)
- `_clear_old_tool_results(messages, keep_last_n)` (:116)
- `_truncate_tool_results(messages, budget, running_total)` (:141)
- `shape_synthesis_guard(keep_last_n_tool_results=2)` (:44)

## Signature
PRE_MODEL middleware (Layer 8 — after every other shaper); each escalation step re-counts tokens and returns early once under `budget.effective_max_tokens`.

## Data Shape
Escalation ladder: (1) strip `ThinkingPart` from all assistant contents; (2) clear ALL but newest-N tool results — artifact-bearing get the shared compact reference, plain ones get `[cleared by synthesis_guard]`; (3) tail-truncate remaining >200-char tool results to 200 chars with a marker; (4) still over → RAISE.

## Decisive source
```python
messages, total = _truncate_tool_results(messages, budget, total)
if total > budget:
    logger.error("synthesis_guard: could not fit context under budget ...")
    raise ContextBudgetExceeded(total, budget)
```

## Invariant
**Fail loud beats fail provider**: an oversized request is raised as a typed exception instead of being sent for a guaranteed provider rejection. The guard is idempotent via its own `_GUARD_CLEARED` marker check and is the LAST shaper by contract — nothing may run after it.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_context_compaction.py::test_strips_thinking_first` (:253), `test_raises_on_unresolvable_overflow` (:271), `test_passes_when_under_budget` (:281); artifact-awareness pin `test_artifact_pipeline.py::TestSynthesisGuardArtifactAware::test_artifact_messages_get_compact_ref_not_generic_cleared` (:647).

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["shape_synthesis_guard","ContextBudgetExceeded"]'`

## Verdict
ADOPT. Every context-fitting system needs a terminal layer with a typed failure; the thinking-strip-first ordering is the cheap-win detail porters miss.
