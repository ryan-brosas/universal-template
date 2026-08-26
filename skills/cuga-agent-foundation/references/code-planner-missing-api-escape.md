<!-- capsule-v2 -->
# report_missing_api escape hatch — how does a bound tool signal "the catalogue is insufficient" without executing anything?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How is a tool-call used purely as a control-flow signal, and what must the receiving node rewrite before looping back to the planner?

## Tool-call-as-signal with history rewrite
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/api/api_code_planner_agent/api_code_planner_agent.py:report_missing_api` (:21-27), chain wiring (:34); consumer `src/cuga/backend/cuga_graph/nodes/api/api_code_planner.py:ApiCodePlanner.node_handler` (:32-58).
**Signature:** chain = `prompt_template | llm.bind_tools([report_missing_api])`; handler returns `Command[Literal['CodeAgent','APIPlannerAgent']]`.
**Data Shape:** the tool's return value is never consumed — only its PRESENCE as `res.tool_calls[0]` with `args.message` matters.

### Decisive source
```python
@tool
def report_missing_api(message: str):
    """
    `report_missing_api(message: str)`: Use this tool **only** when the available tools are insufficient...
    """
    return message + ", I advise calling ApiShortlistingAgent. with refined task."
```
```python
        if (
            res.tool_calls
            and len(res.tool_calls) > 0
            and res.tool_calls[0].get("name") == "report_missing_api"
        ):
            missing_apis_msg = res.tool_calls[0].get("args").get("message")
            state.api_planner_codeagent_plan = ""
            state.api_planner_history[-1].agent_output = CoderAgentHistoricalOutput(
                final_output=missing_apis_msg + "\n *Please use ApiShortlistingAgent with refined task*",
            )
            return Command(update=state.model_dump(), goto="APIPlannerAgent")
```

**Flow:** planner-agent emits the tool call instead of a plan → node detects by NAME → clears any stale `api_planner_codeagent_plan`, records the miss INTO the existing history entry (`api_planner_history[-1].agent_output`) so the planner's next prompt sees why the previous coding attempt aborted → back to APIPlannerAgent. Otherwise the plan text lands in `state.api_planner_codeagent_plan` and flow proceeds to CodeAgent. `create()` swaps `system_fast.jinja2` when `settings.features.code_generation == "fast"` (:63-76).
**Invariant:** The escape REWRITES the last history entry rather than appending — appending would leave a phantom "CoderAgent ran" record. The plan field MUST be cleared or the next CodeAgent visit could execute a stale plan. Only index `[0]` of tool_calls is inspected: this agent binds exactly one tool.
**Probe:** Recorded upstream gap — no direct unit test for this seam at HEAD. Deterministic: `grep -n "report_missing_api" src/cuga/backend/cuga_graph/nodes/api/api_code_planner.py` hits :40 and the goto line :51.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "report_missing_api ApiCodePlanner missing apis", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt bind-tools-as-control-flow with name-checked detection and last-entry history rewrite; adopt the stale-plan clearing. Adapt the tool name/docstring wording to your domain. Omit the fast/accurate prompt split unless you carry the same feature flag surface.
