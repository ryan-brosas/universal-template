<!-- capsule-v2 -->
# Plan-ahead tool grounding — how does an upfront planner produce phases the executing loop can actually run?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A planner that only sees goal text emits abstract phases ("fetch data") the ReAct loop can't map onto tools — how does the system prompt ground the plan in real, callable names?

## Tool-name injection + delegate fallback + network-truth steering
**Path/Symbol:** `backend/python/app/agent_loop_lib/modules/pipeline/planner/plan_ahead.py:PlanAheadPlanner.plan` (L47–100); `_PLAN_SYSTEM` (L12–17).
**Signature:** `PlanAheadPlanner(model=None, tool_names=None, *, sandbox_has_network=False)`; `async def plan(goal) -> Plan` (free-text plan; empty text when no model).
**Data Shape:** Prompt = Goal{description/requirements/success_criteria/constraints}; system prompt grows: available-tool list → file-generation MUST reference code_tool → network branch steering live-data phases.

### Decisive source
```python
# Without this, the planner only ever sees the goal text and has no idea
# run_code (or any other real tool) exists, so it produces abstract phases
# ("fetch data", "create document") the executing ReAct loop has no
# obligation to map back onto an actual tool call.
self._tool_names = tool_names or []

# When the caller composed top-level tools, run_code/web_search/fetch_url
# are no longer directly callable — the plan must reference the DELEGATE:
code_tool = "coding_agent" if "coding_agent" in self._tool_names else "run_code"
if "web_agent" in self._tool_names:
    web_phrase, web_verb = "`web_agent`", "is"
else:
    web_phrase, web_verb = "`web_search`/`fetch_url`", "are"

# mirrors the SAME flag threaded into the tool's description/CodeRequest —
# the upfront plan and the executing tool never disagree about what
# run_code can do:
if self._sandbox_has_network:
    "...a single phase may reference `{code_tool}` directly to call that API..."
else:
    "...any phase that needs live/external data MUST reference {web_phrase}
    as an earlier phase, never `{code_tool}`, to fetch that data."
```

**Flow:** build user prompt from Goal sections → append tool roster + EXACT-name instruction → append network branch (API-direct vs fetch-first phase ordering; web tools still preferred for discovery/research) → one `complete()` call → verbatim text into `Plan` (no parsing — confidence/structure live in other planners).
**Invariant:** (1) Plans must reference EXISTING callable names — after delegation composition, that means the DELEGATE name, not the underlying primitives. (2) The sandbox's network capability is stated identically to the tool's runtime behavior (same flag threaded through `sandbox_bridge.sandbox_network_enabled()`) — a planner promising API calls through a no-network sandbox guarantees failed execution. (3) No-model ⇒ empty Plan, never a fabricated plan.
**Probe:** `tests/unit/agent_loop_lib/modules/pipeline/planner/test_plan_ahead.py::test_run_code_mentioned_as_mandatory_for_file_generation` (:119), `::test_hint_clarifies_run_code_has_no_network_access` (:126), `::test_sandbox_has_network_true_steers_toward_calling_apis_from_run_code` (:153), `::test_coding_agent_referenced_instead_of_run_code` (:176), `::test_web_agent_referenced_instead_of_web_search_fetch_url` (:183), `::test_empty_tool_names_list_leaves_system_prompt_unchanged` (:113).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "PlanAheadPlanner _PLAN_SYSTEM tool_names sandbox_has_network", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tool-grounded planning prompts + capability-truth mirroring for any planner-to-executor pipeline; adapt tool/delegate names and the network flag plumbing. Omit PipesHub's delegate naming. Direct tests cover all four grounding branches plus no-op cases at HEAD.
