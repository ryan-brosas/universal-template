<!-- capsule-v2 -->
# Instructions sandwich + trace continuity — how do shared/additional instructions compose per run without corrupting agent state?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** In what order are shared → base → additional instructions combined, how are callables preserved, and how does a sub-agent run inherit the parent's trace id?

## setup_execution composition + get_run_trace_id ladder
**Path/Symbol:** `src/agency_swarm/agent/execution_helpers.py:setup_execution` (:305-414, esp. build_combined_instructions :327-342) + `get_run_trace_id` (:485-548); cleanup restore `cleanup_execution` (:462-463).
**Signature:** `setup_execution(agent, sender_name, agency_context, additional_instructions, method_name) -> original_instructions` (caller MUST restore in finally); `get_run_trace_id(run_config, agency_context) -> str` matching `^trace_[a-f0-9]{32}$`.
**Data Shape:** composition separator: `"\n\n---\n\n"` between core and additional WHEN shared instructions exist, else `"\n\n"`; callable instructions are wrapped in an async closure that awaits-or-calls the original then composes.

### Decisive source
```python
def build_combined_instructions(base_text):
    core_parts = [p for p in (shared_instructions_text, base_text) if p]
    core_instructions = "\n\n".join(core_parts) or None
    if not additional_for_run:
        return core_instructions
    separator = "\n\n---\n\n" if shared_instructions_text else "\n\n"
    return f"{core_instructions}{separator}{additional_for_run}" if core_instructions else additional_for_run
...
if isinstance(agent.instructions, str) and agent.instructions:
    agent.instructions = combined          # MUTATED — original saved for finally-restore
elif callable(agent.instructions):
    async def combined_instructions(run_context, agent_instance): ...
...
# Trace resolution priority: explicit config > active trace() context >
# last valid run_trace_id REVERSED-scanned from history > freshly generated
for message in reversed(messages):
    trace_from_history = message.get("run_trace_id")
    if isinstance(trace_from_history, str) and TRACE_REGEX.match(trace_from_history):
        resolved_trace_id = trace_from_history; break
```

**Flow:** delegation validation first (agent-to-agent requires an AgencyContext + agency instance, else RuntimeError) → instructions composed and temporarily assigned → handoff alignment snapshots → run with `RunConfig(workflow_name=agency_name, trace_id=run_trace_id)` → SendMessage passes `tool_call_id` as the sub-run's `parent_run_id`, and the sub-run reuses the SAME `run_trace_id` from history, so one user request yields one trace tree spanning all agents.
**Invariant:** (1) Instruction mutation is always paired with finally-restore — even when context preparation never happened (`else: self.agent.instructions = original_instructions`); (2) malformed explicit trace ids are ignored-and-regenerated (regex-gated), never propagated; (3) shared-instructions freshness is re-resolved from the agency instance at every setup (`_resolve_latest_shared_instructions`) so live edits apply to the next run; (4) the `---` separator only appears between distinct instruction CLASSES — additional-only composition uses plain newlines.
**Probe:** trace/history contract pinned by `tests/test_messages_modules/test_message_formatter_history_protocol.py::test_prepare_history_for_runner_stores_responses_protocol_and_strips_runner_metadata` (:104, run_trace_id round-trip); delegation validation pinned by `tests/integration/communication/test_communication.py::test_multi_agent_communication_flow` (:158). Coverage caveat: `build_combined_instructions`/`get_run_trace_id` have no dedicated unit file at HEAD — verified by whole-file read; both helpers are exercised transitively by every execution test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "setup_execution shared instructions get_run_trace_id", limit: 10 });
```

## Verdict
Adopt the ordered composition + mandatory restore discipline + regex-gated trace inheritance; adapt separators/naming to your prompt conventions; omit the callable-instructions wrapper if your prompts are static strings. Pinned via transitive suites; helper-level caveat recorded.
