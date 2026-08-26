<!-- capsule-v2 -->
# Turn-aware tool blocking — should consecutive-failure blocking count calls or turns when tool calls run in parallel waves?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** the legacy planner blocked flaky tools by excluding them from the next registry build; with one registry per request and concurrent same-turn calls, what is the correct blocking mechanism and unit?

## PRE-deny + POST record over a shared tracker instance
**Path/Symbol:** `backend/python/app/agents/agent_loop/hooks/tool_blocking.py:32-85` (`ToolErrorTracker`, wired PRE+POST_TOOL_USE at `factory.py:914-916`).
**Signature:** `ToolErrorTracker(threshold=3)`; `record(tool_path, *, is_error: bool, turn_index: int | None = None)`; `pre_tool_use(ctx, next_fn)` / `post_tool_use(ctx, next_fn)`.
**Data Shape:** `_consecutive_errors: dict[str,int]`, `_last_failed_turn: dict[str,int]`; deny message tells the model to try a different tool.

### Decisive source
```python
if is_error:
    if turn_index is not None and self._last_failed_turn.get(tool_path) == turn_index:
        return
    self._consecutive_errors[tool_path] = self._consecutive_errors.get(tool_path, 0) + 1
    if turn_index is not None:
        self._last_failed_turn[tool_path] = turn_index
else:
    self._consecutive_errors.pop(tool_path, None)
    self._last_failed_turn.pop(tool_path, None)
```

**Flow:** POST_TOOL_USE → next first → record outcome with `ctx.scope.turn.turn_index`; success pops both maps → PRE_TOOL_USE on later calls denies with a model-readable message once threshold reached (blocked tool never reaches next_fn).
**Invariant:** only CONSECUTIVE failures count; parallel calls inside ONE gathered wave fail together from the model's perspective — that is one attempt fanned out, so the streak counts TURNS not calls (`_last_failed_turn` dedupes same-turn contributions); without scope/turn info it degrades gracefully to call-aware counting. Blocking uses `ctx.deny(...)` because `visible_tools.discard` is never consulted in this configuration (schemas are re-sent every turn regardless).

### Direct test
**Probe:** `tests/unit/agents/adapter/test_hooks.py::TestToolErrorTracker.test_parallel_failures_in_same_turn_count_once` :89, `.test_failures_across_separate_turns_still_accumulate` :106, `.test_success_resets_the_streak` :52. Execute: `/tmp/psh17venv/bin/python -m pytest "tests/unit/agents/adapter/test_hooks.py::TestToolErrorTracker" -q` (9 passed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "ToolErrorTracker consecutive failures turn-aware record deny", limit: 4, fields: ["signature", "name", "file"] });
// rank hits test_hooks.py TestToolErrorTracker tests + hooks/tool_blocking.py Methods (init 40-45, record 50-71, is_blocked 47-48)
```

## Verdict
Adopt turn-aware consecutive-failure blocking via PRE-deny for single-registry agent loops with parallel dispatch; adopt the explicit degrade-to-call-aware fallback. Adapt threshold and deny copy. Omit the legacy exclude-from-next-load mechanism (only valid with per-iteration registries).
