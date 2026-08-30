<!-- capsule-v2 -->
# Agent.step() turn primitive — how do you make ONE fixed turn unit serve every loop shape without letting loop shapes bypass deterministic guards?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What does one agent turn consist of, and which concerns must fire inside it no matter which loop strategy drives it?

## The step pipeline (PRE_TURN → shaping → guarded LLM call → tool dispatch → POST_TURN)
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/__init__.py:Agent` (85–1026); `Agent.step` (569–992); `Agent.run` (494–565); `succeed`/`fail` shared tails (399–458); `_AG_UI_ALIASES` translation table (75–82).
**Signature:** `async def step(self, goal: Goal, turn_index: int) -> StepOutcome` where `StepOutcome = {status: "continue"|"stop", turn?, result?}` (`agent/loops.py:51-66`).
**Data Shape:** `RunScope` (created once per `run()`, holds turns/todos/visible_tools/extra_prompt_sections) + `TurnScope` per step; `self._usage` accumulates `RunUsage` across every LLM call; `self._stale_tool_rounds` counts consecutive all-empty/all-error result rounds.

### Decisive source
```python
# agent/__init__.py:720-747 — input guardrail RACES the LLM call instead of
# running serially before it; first exception cancels the sibling task.
guardrail_task = asyncio.create_task(hooks.dispatch_guardrail_input(self._hooks, messages, scope=turn_scope))
model_task = asyncio.create_task(hooks.call_model_wrapped(self._hooks, _call_llm))
await asyncio.wait({guardrail_task, model_task}, return_when=asyncio.FIRST_EXCEPTION)
if guardrail_task.done() and guardrail_task.exception() is not None:
    model_task.cancel()
    ...
    raise guardrail_task.exception()
```

**Flow:** `run()` builds `RunScope`, consumes a stashed parent scope ONCE (one-shot `_inherit_from`, :517-520), dispatches PRE_AGENT (HookBlocked ⇒ failed result), adds goal as UserMessage → delegates to `spec.loop.run(agent, goal)` → inside each `step`: PRE_TURN guards (RunCancelled/HookBlocked ⇒ stop+fail) → `dispatch_pre_model` context shaping over a COPY of messages (stored history untouched) → guarded parallel guardrail/model call → usage/budget record → POST_MODEL hook may set `recovery_message` to veto "no tools = done" (:789-803) or supply truncation-recovery results (:770-787) → output guardrail on terminal text → tool dispatch → step footer appended to every non-terminal ToolMessage (`[loop: step N/M, stale_rounds=K]`, :953-963) → POST_TURN + checkpoint + turn memory.
**Invariant:** Every deterministic concern (budget, cancellation, deadline warning, truncation recovery, guardrails, permission) fires INSIDE step via the shared HookRegistry kernel regardless of loop shape — a loop changes WHEN the model is called, never WHETHER guards run. Terminal text-only responses are deliberately NOT appended to `scope.turns` (:813-818); every emit also fires its AG-UI alias alongside (never instead of) the legacy event, with TOOL_BLOCKED aliased to TOOL_CALL_END.
**Probe:** `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_turn_guards.py` (:90 supervisor confidence gate blocks only when opted-in, :97/:118 idempotent installs); `tests/unit/agent_loop_lib/runtime/test_run_child_streaming.py::test_run_child_seeds_context_via_public_seam` (:111).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "Agent step RunScope succeed fail", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.trace_path({ project: "pipeshub-ai", function_name: "pipeshub-ai.backend.python.app.agent_loop_lib.agent.Agent.inject_user_message", direction: "inbound" });
```

## Verdict
Adopt the fixed hook-instrumented step primitive with loop-shape inversion (LoopStrategy owns iteration), the parallel guardrail/LLM race, the recovery_message veto seam, and stale-round footers for reactive stops; adapt event-type names, footer format, and scope field layout to host; omit the AG-UI alias table if your frontend speaks only one event dialect. Direct tests cover turn guards and child-context seeding; caveat: full e2e lives in `tests/integration/test_chat_stream_agent_loop_e2e.py` (integration-marked).
