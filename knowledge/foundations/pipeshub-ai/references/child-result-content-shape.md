<!-- capsule-v2 -->
# child_result_content (one child→parent result shape for BOTH dispatch paths)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What exact dict does a completed sub-agent's AgentResult become in its caller's context — and why must LLM-mediated and programmatic dispatch share it?

## Path/Symbol
`tools/builtin/coordination/spawn_agent.py` — `child_result_content(child_result: AgentResult) -> dict` (:24–55). Shared by `SpawnAgentTool.handle()` (:359) and `orchestrator.py::_programmatic_dispatch`.

## Signature
Base `{output, success}`; adds ONLY set fields: `artifacts` as refs (`{name, type.value, description}` — NEVER full content), `confidence.value`, `record_ids`, and `needs_input` rewritten with an explicit escalation prefix.

## Data Shape
```python
content["needs_input"] = (
    f"This sub-agent could not fully complete its task — it needs: {child_result.needs_input}"
)
```

### Decisive source
```python
Artifacts are refs only (name/type/description), never the full
`content` — the full bytes reach a DEPENDENT, not this caller, via
`spawn_scheduler._artifact_files/`stage_input_files`. ...
`needs_input` is called out with an explicit prefix: it means the child
could not fully complete its goal and is escalating upward — burying that
key inside an otherwise-ordinary dict risks the calling model treating a
partial result as a complete one.
```

**Flow:** either dispatch path completes a child → this ONE function renders the result → calling agent's ToolMessage. Absent optional fields are OMITTED not null (test :57–66): a `None`-valued key would still be new surface for every consumer doing `if "confidence" in content`.

**Invariant:** Both dispatch paths MUST expose the same shape or "which path ran" leaks into what the orchestrator model sees (skews its downstream decisions). Full artifact bytes flow to DEPENDENT steps only (staged files), never back to the caller — context economy + single-source-of-truth for big payloads. Escalation must be un-skimmable: prefix text forces even a lazy model to see partial-completion.

**Probe:** `tests/unit/agent_loop_lib/tools/builtin/coordination/test_child_result_content.py` — plain shape :17, artifact refs without content key :22–34 (`"content" not in content["artifacts"][0]`), pass-through :36, needs_input prefix :45–55, absent-fields-omitted :57.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["child_result_content","_programmatic_dispatch","SpawnAgentTool"]'
```

## Verdict
Adopt the omit-not-null field discipline, artifacts-as-refs-to-dependents rule, and explicit escalation prefix; adapt field names to host's AgentResult.
