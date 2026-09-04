<!-- capsule-v2 -->
# Terminal-tool protocol + typed sub-agent output contract — how do you stop a run from ANY tool's success without hardcoding task_complete?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How is loop termination detected by tag+protocol rather than name equality, and what rides out on AgentResult?

## TAG_LIFECYCLE_TERMINAL + TerminalTool.extract_outcome
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/tool_loop.py:TerminalTool` Protocol (:32-43) and terminal branch (:381-394); `ToolCallOutcome` dataclass (:147-165); consumption in `Agent.step` (:927-936, :980-990); shared default outcome in `tools/decorators.py:_default_terminal_outcome` (:67-87).
**Signature:** `class TerminalTool(Protocol): def extract_outcome(self, tr: ToolResult, call: ToolCall, fallback_text: str) -> TaskCompletionOutcome`; dispatch condition = `not tr.is_error and TAG_LIFECYCLE_TERMINAL in registry.tags_for_name(call.name)`.
**Data Shape:** TaskCompletionOutcome = `{task_done, final_output, artifacts?, error_result?, confidence?, record_ids?, needs_input?}`; the optional trio is the typed sub-agent output contract surfaced on AgentResult.

### Decisive source
```python
# tool_loop.py:33-39 — why a Protocol, not a name check
"""Structural type for any Tool tagged TAG_LIFECYCLE_TERMINAL — its own
successful result carries the loop's stop signal. extract_outcome
post-processes THIS tool's result shape into a TaskCompletionOutcome,
so the turn loop dispatches on the tag rather than hardcoding
call.name == "task_complete" — a future terminal tool just needs the
tag plus this method, no edit to execute_tool_call."""
# step footer interplay, agent/__init__.py:959-963
# Skip the footer on terminal-tool results — they stop the loop.
is_terminal = TAG_LIFECYCLE_TERMINAL in runtime.tool_registry.tags_for_name(tr.name)
```

**Flow:** model calls a tagged tool → executor returns its result → loop checks tag + non-error → isinstance TerminalTool ⇒ extract_outcome builds the completion (task_complete REFUSES empty results with an error_result forcing retry; ask_user_question-style tools use the permissive default that returns fallback_text) → step aggregates task_done/final_output/artifacts/confidence across outcomes (first terminal wins fields) → succeed() emits agent_complete with event="task_complete" and stops.
**Invariant:** Only a SUCCESSFUL terminal result stops the run (error terminal results flow back as ordinary corrections); `[loop: ...]` footers are skipped on terminal results since they'd be dead context; the output contract fields degrade to None/[] for older callers — never an error.
**Probe:** `tests/unit/agent_loop_lib/agent/test_task_complete_output_contract.py` (contract field surfacing); `tests/unit/agent_loop_lib/tools/test_special_route_agenthandle.py` (AgentHandle special-route surface); `tests/unit/agent_loop_lib/tools/test_executor_ask_decision.py` (ask/approval decision path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "TerminalTool extract_outcome TAG_LIFECYCLE_TERMINAL TaskCompletionOutcome needs_input confidence record_ids", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tag-based terminality with a two-method protocol and typed optional output contract; adapt which tools are terminal and the refusal rule per host; omit the confidence/record_ids/needs_input trio unless you orchestrate typed sub-agents. Direct tests pin contract surfacing and route handling; caveat: extract_outcome branches are covered through task_complete/route suites rather than one dedicated file.
