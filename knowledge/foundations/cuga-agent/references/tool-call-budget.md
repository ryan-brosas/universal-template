<!-- capsule-v2 -->
# Three-tier tool-call budget — how to bound tool spend across a code-executing agent without breaking delegation or concurrency

**Source:** cuga-agent (Apache-2.0) `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do I cap tool calls per code block, per turn, and per conversation in an agent whose tools are called by generated code — while keeping a delegation tree charged to ONE ceiling and concurrent threads isolated?

## ToolCallTracker budget + tracking
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/tracking/tracker.py:ToolCallTracker` (158-378), `counted_tool_call` (393-438), `make_recording_awaitable` (441-492), `tracked_tool` (495-608), `BlockToolCallCounter` (128-155), `ToolCallBudgetExceeded` + subclasses (93-126), `thread_budget_exhausted` (380-390); `src/cuga/backend/cuga_graph/nodes/cuga_lite/tracking/arguments.py:merge_tool_call_args` / `unexpected_tool_arg_names` / `resolve_tool_call_args` (36-84).
**Signature:** `ToolCallTracker.enforce_call_budget() -> None` (raises `ToolCallBudgetExceeded`); `seed_call_budget(used, thread_used=0)`, `seed_block_budget()`, `budget_exhausted() -> bool`, `counted_tool_call(awaitable_func) -> Callable`.
**Data Shape:** three nested budgets — `block` (`max_tool_calls_per_block`, default 100), `run`/turn (`max_tool_calls_per_run`, default 256), `thread`/conversation (`max_tool_calls_per_thread`, default 2000). Each is a mutable `[count]` box in a `contextvars.ContextVar` so increments survive `asyncio.wait_for`/`create_task` context copies (the copy references the SAME box). Each cap is independently disabled by `0`. Exceptions subclass `RuntimeError` (so the CodeExecutor's in-code exception handler surfaces them as execution output) and carry a `scope` (`block`/`run`/`thread`).

### Decisive source
```python
def enforce_call_budget(self):
    if _counting_tool_call_context.get():
        return                      # already inside a counted call => charge once
    box = _tool_call_budget_context.get()
    if box is None:
        return                      # outside a seeded sandbox context => no-op
    # Check BEFORE counting so a rejected call never inflates the counters.
    if max_per_thread and thread_box[0] >= max_per_thread:
        raise ThreadToolCallBudgetExceeded(...)   # widest wins the error
    if max_tool_calls_per_run and box[0] >= max_tool_calls_per_run:
        raise RunToolCallBudgetExceeded(...)
    if max_per_block and block_box[0] >= max_per_block:
        raise BlockToolCallBudgetExceeded(...)    # recoverable: model retries narrower
    box[0] += 1; thread_box[0] += 1; block_box[0] += 1
```

**Flow:** `seed_call_budget` opens the run+thread boxes and clears any stale block budget; `seed_block_budget` opens a fresh per-block box each executed code block. `counted_tool_call` wraps every coroutine in the sandbox namespace (the single point both Lite and Supervisor graphs share) so name-invoked tools that never pass through `call_api` cannot escape the cap; a wrapped tool is ALWAYS its own logical call (the nested guard only suppresses the unwrapped inner `call_api` a registry-backed tool calls in its own body). `budget_exhausted()` is true only for the terminal run/thread ceilings — a block breach must NOT end the turn.
**Invariant:** Only the budgets that do NOT reset are bounds — the per-block cap is a fail-fast latency guard, and alone lets ~70 blocks × 100 calls = 7,000 calls through (the runaway it exists to stop). A delegation tree (`delegate_to_*` / `spawn_agent`) charges ONE ceiling — the caller's — because `seed_call_budget` inherits (does not replace) the boxes when already inside a counted call; `ContextVar.set` has no token to unwind, so replacing would destroy the caller's counters. Concurrent threads each get a full independent budget via contextvar isolation.
**Probe:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/tests/test_tool_call_budget_levels.py::test_per_block_cap_alone_does_not_bound_the_task` (7,000 calls through a block-only cap), `::test_task_cap_is_what_actually_bounds_the_same_loop` (stops at 256), `::test_thread_cap_bounds_what_the_task_cap_cannot` (20 turns × 256 bounded at 1000), `::test_block_breach_leaves_the_task_budget_spendable` (recoverable), `::test_widest_budget_wins_the_error` (thread reported when all spent), `::test_rejected_calls_never_inflate_any_counter`; `test_tool_call_budget_delegation.py::test_delegated_child_is_bounded_by_the_callers_ceiling`, `::test_delegation_does_not_destroy_the_callers_counters` (parent 2→8 not 2→0), `::test_separate_threads_each_get_a_full_budget`; `test_run_tool_call_cap.py::test_exhaustion_returns_control_to_the_model` (cap surfaces as execution output, no raise); `tests/unit/test_tool_tracker_timings_only.py::test_timings_only_drops_arguments_results_and_error` (metrics flag must not capture payloads).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ToolCallTracker enforce_call_budget counted_tool_call seed_call_budget", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-tier budget (block=latency guard, run+thread=real bounds), the check-before-count ordering, the mutable-box contextvar pattern for async-task visibility, the widest-wins error selection, and the delegation-inherits-caller's-ceiling rule (a child graph must not get a fresh budget nor destroy the parent's counters). Adopt `counted_tool_call` to close the escape hatch for name-invoked tools, and the `timings_only` mode so a metrics flag never captures tool payloads into checkpointed state. Adapt the cap defaults and config keys to your host; the `keep_highest` thread-counter reducer pairs with `agent-state`. Omit the `tracked_tool` decorator's `_cuga_tracked`/`_cuga_budget_counted` marker conventions unless you adopt the same double-wrap protection. Coverage: all cited source/test paths `no_recorded_issue` + `metadata_match` on the live full index.
