<!-- capsule-v2 -->
# ChatNode HITL routing — how do four tool-call shapes decide between auto-execution, human approval, and planner hand-off?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What is the ordered decision ladder from a chat response containing tool_calls to a graph Command?

## Ordered tool_call dispatch ladder
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/chat/chat.py:ChatNode.node_handler` (:138-238), `_execute_direct_tool_calls` (:87-120), approval predicates `chat_agent.py:should_auto_execute_tool/requires_human_approval` (:180-186); resume arms :142-177.
**Signature:** `node_handler(state, agent, hitl_handler, name) -> Command[Literal["FinalAnswerAgent","TaskAnalyzerAgent","SuggestHumanActions"]]`.
**Data Shape:** auto-execute set = tool names starting `knowledge_`; approval-gated = everything else when `features.save_reuse`; planner hand-off = `execute_task` args `{task, relevant_variables}`; new-flow = `run_new_flow{user_task}`.

### Decisive source
```python
        while (
            getattr(response, "tool_calls", None)
            and response.tool_calls
            and round_trips < max_round_trips          # 4
            and all(
                agent.should_auto_execute_tool(tool_call.get("name")) for tool_call in response.tool_calls
            )
        ):
```
and the resume arm that stores results as variables:
```python
            var_name = f"tool_result_{str(uuid.uuid4())[:5]}"
            state.variables_manager.add_variable(
                parsed_result, var_name, f"Result of tool {tool_name} with args {tool_args}"
            )
            state.sender = "ChatAgentTool"
```

**Flow:** resume-first — sender==WaitForResponse + FLOW_APPROVE ⇒ execute stored tool, JSON-parse-or-string result into a `tool_result_XXXXX` variable, present it via `last_planner_answer` → FinalAnswerAgent; NEW_FLOW_APPROVE ⇒ rewrite `state.input` from `run_new_flow.user_task` → TaskAnalyzerAgent (full replan). Fresh input: chat disabled ⇒ straight to analyzer; else invoke agent; auto-execute loop runs ≤4 all-knowledge_* rounds; THEN first tool_call decides: run_new_flow ⇒ SuggestHumanActions (new_flow_approve), other non-auto names under save_reuse ⇒ SuggestHumanActions (flow_approve), execute_task without save_reuse ⇒ compose task(+relevant variables) into state.input → analyzer; plain content ⇒ variable-placeholder substitution → FinalAnswerAgent.
**Invariant:** ALL-calls-auto gate: one non-knowledge tool in the batch stops the whole auto loop (the `all(...)` predicate) — mixed batches never half-execute. Approval payloads carry the ORIGINAL ToolCall dict in `additional_data.tool` so the resume arm executes exactly what the model proposed. `requires_human_approval` is defined as the exact complement of `should_auto_execute_tool`.
**Probe:** Direct tests pin the knowledge-toggle side (`tests/unit/test_chat_knowledge_mode.py::FakeChatAgent.should_auto_execute_tool` :19). Deterministic: `grep -n "max_round_trips" src/cuga/backend/cuga_graph/nodes/chat/chat.py` shows the bound default 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ChatNode _execute_direct_tool_calls flow_approve run_new_flow requires_human_approval", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the prefix-based auto-execute allowlist with all-or-nothing batch gating, uuid-suffixed result variables, and resume-arm-before-fresh-processing ordering. Adapt action ids/approval UI wiring. Omit the save_reuse feature split if your host always approves.
