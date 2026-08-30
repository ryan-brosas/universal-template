<!-- capsule-v2 -->
# Wave-level duplicate detection — why must the dedup check-then-add happen BEFORE any coroutine in the wave starts?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do you suppress exact-duplicate tool calls in an asyncio.gather wave without races, and without blocking intentional repeats?

## Synchronous pre-pass over the whole wave
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/tool_loop.py:compute_duplicate_flags` (57-84); consumption in `execute_tool_call` (295-311); wave wiring in `agent/__init__.py` step (909-925).
**Signature:** `def compute_duplicate_flags(calls: list[ToolCall], seen_tool_calls: set[str], registry: ToolRegistry) -> dict[call_id, bool]`.
**Data Shape:** signature = `f"{name}:{json.dumps(arguments, sort_keys=True)}"`; flag = `sig in seen AND tool tagged TAG_DEDUP_EXACT`; EVERY call's sig is added to `seen_tool_calls` regardless.

### Decisive source
```python
# tool_loop.py:60-69 — the docstring IS the invariant
"""Synchronous pre-pass over one asyncio.gather() wave of calls, run
BEFORE any of them starts its own coroutine — so seen_tool_calls is fully
updated before any call's await points exist.
This check-then-add used to live inline inside execute_tool_call, AFTER
that function's own await agent.emit(...). Two identical calls gathered
into the same wave could both reach the check before either had added its
own signature, and both would execute."""
flags: dict[str, bool] = {}
for call in calls:
    call_sig = f"{call.name}:{json.dumps(call.arguments, sort_keys=True)}"
    is_dedupable = TAG_DEDUP_EXACT in registry.tags_for_name(call.name)
    flags[call.id] = call_sig in seen_tool_calls and is_dedupable
    seen_tool_calls.add(call_sig)
```

**Flow:** step computes all flags synchronously → gathers parallel non-spawn calls with `is_duplicate=` flags → a flagged call short-circuits to a NON-error ToolResult telling the model "[Duplicate call skipped — use the results you already have or call task_complete]" instead of re-executing.
**Invariant:** Opt-in by tag: only tools declaring `TAG_DEDUP_EXACT` (builtin web_search/web_scrape; host tools opt in) are ever flagged — a non-idempotent repeat (re-read after write) MUST still run. Detection cannot live inside the per-call coroutine after its own awaits; the pre-pass makes the interleaving structurally impossible rather than unlikely.
**Probe:** `tests/unit/agent_loop_lib/agent/test_tool_loop_dedup_race.py::test_identical_parallel_calls_dedup_to_one_execution` (:91), `::test_second_identical_call_flagged_duplicate` (:174), `::test_seen_tool_calls_mutated_in_place_before_any_await` (:183), `::test_non_deduped_tool_names_never_flagged` (:196); `::test_distinct_queries_both_execute` (:116).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "compute_duplicate_flags TAG_DEDUP_EXACT seen_tool_calls", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the synchronous pre-wave check-then-add, sorted-key JSON signatures, tag-gated suppression with a steering (non-error) skip message; adapt which tools carry the dedup tag to host semantics; omit per-tool fuzzy dedup entirely (exact match only). Direct tests pin both the race fix and the opt-in boundary.
