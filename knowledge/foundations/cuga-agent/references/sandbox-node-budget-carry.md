<!-- capsule-v2 -->
# Sandbox node budget-carry invariant — why must EVERY exit path from the code-execution node re-emit tool-budget state?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Your LangGraph execution node spends tool-call budget mid-block, then errors — what does the state update need so checkpointed ceilings don't under-count?

## Absent keys keep checkpoint values; a path that omits spent budget makes those calls VANISH from the thread ceiling
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/adapter/sandbox_node.py` — `_budget_updates()` :77-92 (with load-bearing docstring), seed at block open :150-153, success update :301-311 (inline budget fields), error-path additional_updates :280-298 (`**_budget_updates()` with comment :290-295), exception path :339-349, find-tools var filtering :123-130 + :191-196, weak-schema shape recording :57-74 + :274-275/:317-318, timings_only vs shape-tracking precedence :135-145.
**Signature:** `_budget_updates() -> {"tool_calls_used_run": int, "tool_calls_used_thread": int, "tool_budget_exhausted": bool}` read from ToolCallTracker AFTER `stop_tracking()`; `ToolCallTracker.seed_call_budget(run_used, thread_used)` re-arms per-block counters from state.
**Data Shape:** budgets are conversation-monotonic via AgentState's `keep_highest` reducer — but reducers only see WRITTEN keys.

### Decisive source
```python
# :80-84 docstring — the invariant in one sentence
# Every path out of the node runs *after* the code block, so every one of them
# can be leaving spent budget behind — including the error and step-limit
# paths. A path that omits these leaves the keys absent from the state update,
# and LangGraph then keeps the checkpoint's pre-block values, silently
# under-counting the conversation ceiling.
# :290-295 — "keep_highest cannot rescue a value that was never written."
```
**Flow:** denial check → resolve configurable/thread/apps → purge stale find-tools listing vars → start tracking (`timings_only` unless an unobserved weak-schema shape forces FULL recording) → seed budgets from state → execute block → collect steps → persist new vars (skipping listing-markdown values) → optional reflection (truncated context + watsonx clamp, failure ⇒ empty string, never fatal) → stop tracking + record first observed weak-schema shapes → return update WITH budgets on success AND both error paths.
**Invariant:** (1) Budget fields ride every return dict including exceptions. (2) Weak-schema shape tracking OVERRIDES timings_only privacy mode for the block where a shape is still unobserved (it must read results). (3) Reflection failure degrades to no-summary — never fails the step. (4) find_tools listing markdown is recognized by marker substrings ("# Found" + "Matching Tool(s)" + "**Query:**") and kept out of persisted variables in BOTH directions (pre-execution purge + post-execution skip).

**Probe:** `cuga_lite/executors/tests/test_tool_call_budget_levels.py`, `test_tool_call_cap.py` (run-level cap incl. timeout), `test_tool_call_budget_delegation.py` (supervisor delegation), plus `cuga_lite/tests/test_prepare_node_weak_schema_tools.py` / `test_sandbox_node_weak_schema_shapes.py` pinning the tracking-precedence behavior.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "sandbox _budget_updates seed_call_budget tool_calls_used_thread", limit: 8 });
```
## Verdict
Adopt the every-exit-carries-spent-state rule for ANY metered resource in a checkpointed graph. Adapt tracker API. This composes with the agent-state keep_highest capsule — they are two halves of one contract.
