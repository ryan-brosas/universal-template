<!-- capsule-v2 -->
# Deferred-call collection & resolution — when is an external/approval call stubbed, collected, or inline-resolved inside one step?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** During a single step's tool walk, what decides whether a deferred call becomes a skip-stub, a pending request handed to the host, or an inline-resolved execution?

## The collect → resolve ladder
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_tool_execution.py:_ToolCallProcessor._finalize_deferred` (910–919) with `_collect_deferred_calls` (921–962), `_resolve_deferred_calls` (964–1050), and `_populate_deferred_calls` (862–877).
**Signature:** `_finalize_deferred() -> AsyncIterator[HandleResponseEvent]`; state inputs are the processor's `deferred_calls: dict[Literal['external','unapproved'], list[ToolCallPart]]`, `deferred_metadata: dict[str, dict[str, Any]]`, `final_result`, and `tool_call_results` (resume flag).
**Data Shape:** Deferred calls grouped by kind (`'external'` = run outside, `'unapproved'` = needs approval); metadata keyed by `tool_call_id`; final output is either a `DeferredToolRequests` FinalResult or nothing.

### Decisive source
```python
# _tool_execution.py:910-919 — the three-way decision, in order
async def _finalize_deferred(self):
    # Collect deferred calls (unless they were already included in the run because results were provided).
    if self.tool_call_results is None:
        async for event in self._collect_deferred_calls():
            yield event
    if not self.final_result and self.deferred_calls:
        async for event in self._resolve_deferred_calls():
            yield event

# :927-938 — stub rule: a settled non-deferred final result wins over pending calls
if self.final_result:
    if not isinstance(self.final_result.output, DeferredToolRequests):
        for call in calls:
            self.output_parts.append(_messages.ToolReturnPart(
                tool_name=call.tool_name,
                content=_TOOL_SKIPPED_FINAL_ALREADY_PROCESSED,
                tool_call_id=call.tool_call_id))
```

**Flow:** (1) Resume runs (`tool_call_results` supplied) never re-collect — deferred kinds already execute through the regular pipeline with their supplied results. (2) Fresh runs validate each deferred call first (`validate_tool_call`) — invalid args become normal retry/failure parts, NOT deferrals. (3) If some other final result already exists, every deferred call is stubbed with `'Tool not executed - a final result was already processed.'`. (4) Otherwise the batch is announced (`DeferredToolRequestsEvent`), a capability handler gets one shot at inline resolution (`resolve_deferred_tool_calls`), and handler results re-enter through the SAME `_call_tools` pipeline so approvals/denials/retries behave identically to the resume path. (5) Anything still unresolved (including calls that re-deferred during inline resolution) becomes `FinalResult(DeferredToolRequests)` — but only if the agent's output schema allows deferred tools, else `UserError`.
**Invariant:** A deferred call is only collected once its arguments validate; duplicate `tool_call_id`s in the outgoing batch are rejected before hand-out (`_resolve_deferred_calls:968-973`) because resume matching is by id. Re-deferral during inline resolution extends the SAME batch silently (no second `DeferredToolRequestsEvent` — re-announcing ids under a different kind would be ambiguous). The kind gate matters under `end_strategy='early'`: a structured-output win must NOT stub away co-emitted external calls.
**Probe:** `tests/test_agent.py::TestEndStrategy::test_early_strategy_does_not_preempt_deferred_tool_calls` (:5024) — pins that `DeferredToolRequests` still surfaces under 'early'; `test_agent_run_id_fresh_on_deferred_resume` (:4052) covers the resume arm.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_collect_deferred_calls _resolve_deferred_calls _finalize_deferred", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered ladder (skip-on-resume → validate-before-collect → stub-if-final → inline-handler-shot → emit-as-output) and the unique-id gate; adapt the capability-handler hook point (your framework's equivalent of a root capability); omit pydantic-ai's `output_schema.allows_deferred_tools` check if your pause mechanism isn't expressed as an output type. Caveat: none — all four methods read at HEAD this session.
