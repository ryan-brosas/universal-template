<!-- capsule-v2 -->
# Managed-agent composition — how do sub-agents become callable tools, and what do they hide from the caller?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** How are managed agents registered, invoked, and reported back, and which name/shape rules make multi-agent systems addressable from generated code?

## Agent-as-tool with report templating
**Path/Symbol:** `src/smolagents/agents.py:MultiStepAgent.__call__` (:868-890), `_setup_managed_agents` (:369-387), `_validate_tools_and_managed_agents` (:404-414), execute_tool_call's managed branch (:1473, :1492-1496); `visualize_agent_tree` (`monitoring.py:232-273`).
**Signature:** `__call__(task, **kwargs)` — "called only by a managed agent"; managed agents REQUIRE both `name` and `description` (asserted), and get inputs/output_type FORCED to `{task:string, additional_args:object?} → string`.
**Data Shape:** Registry `self.managed_agents: dict[name, agent]`; merged into available calls via `{**self.tools, **self.managed_agents}`.

### Decisive source
```python
# :876-889 — result is re-wrapped through a template, never returned raw:
result = self.run(full_task, **kwargs)
...
answer = populate_template(self.prompt_templates["managed_agent"]["report"],
                           variables=dict(name=self.name, final_answer=report))
if self.provide_run_summary:
    answer += "\n\nFor more detail, find below a summary of this agent's work:\n<summary_of_work>\n"
    for message in self.write_memory_to_messages(summary_mode=True): ...
```

**Flow:** Parent init coerces each managed agent into tool shape (fixed task/additional_args input schema, string output) and asserts global name uniqueness across parent tools + managed agents + parent's own name — because code actions call them identically. Invocation goes through execute_tool_call's `is_managed_agent` fork: no sanitize flag (the agent re-templates internally), team-member error phrasing on failure. The child's RunResult-or-output collapses to text via the report template; `provide_run_summary` appends a `<summary_of_work>` transcript (summary_mode strips system prompt + plan noise). Name validity = Python identifier AND not keyword (`is_valid_name`) since the model writes real Python referencing these names.
**Invariant:** The forced string-output contract keeps generated-code call sites uniform (`final_answer(manager(task="..."))`); letting a child return images would require the AgentType plumbing across the boundary. Uniqueness spans THREE namespaces at once — validating only within one table permits shadowing bugs.
**Probe:** `tests/test_agents.py::test_validate_tools_and_managed_agents` (:1471-1494 parametrized incl. cross-table duplicates legal inside different managed agents), `test_init_managed_agent` (:572), `test_multiagents` (:2445). Live: duplicate tool/managed-agent names → ValueError listing collisions; valid same-name tools under DIFFERENT parents → passes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "_setup_managed_agents provide_run_summary managed_agent report", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt agent-as-tool coercion with forced schemas and three-way name uniqueness. Adapt the report template vocabulary. Omit run-summary only if your callers never need the child's trace.
