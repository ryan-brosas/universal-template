<!-- capsule-v2 -->
# Interrupt-pair HITL pattern (SuggestHumanActions + WaitForResponse) — how do you suspend a LangGraph run for a UI action and resume at the RIGHT node?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You want structured human-in-the-loop actions (buttons, selects, approvals) in a graph — what's the minimal two-node interrupt/resume pair, and where does the return routing decision actually live?

## Suggest node APPENDS the action as an AI message; wait node interrupts, mutates state, and Command(goto=prev_sender) — return_to is DATA, not the goto
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/human_in_the_loop/suggest_actions.py` :21-27 (`node_handler` appends `AIMessage(state.hitl_action.model_dump_json())`, `Command(update=state.model_dump(), goto="WaitForResponse")`); `wait_for_response.py` :22-36 (`response = interrupt(state.hitl_action.model_dump())`, `state.hitl_response = ActionResponse(**response)`, `state.hitl_action = None`, `return Command(update=state.model_dump(), goto=prev_sender)`); contract models `followup_model.py` — `ActionType` :10-19 (7 types), `FollowUpAction` :35-68 (`action_id/action_name/description/type/callback_url` + per-type optionals + `return_to` :47 + validation/display fields), factories :71-223 (`create_save_reuse_action`, `create_flow_approve`, `create_tool_approval_action(policy_name, required_tools, code_preview, full_code, ...)` with `>3 tools ⇒ "X, Y, Z and N more"` truncation :139-143, `create_agent_approval_action`), `ActionResponse` :226-251.
**Signature:** `WaitForResponse.node_handler(state) -> Command[Literal["__end__","FinalAnswerAgent","ChatAgent","APIPlannerAgent","CugaLite"]]`; wiring: `graph.py:85` instantiates + `:160` `add_node`.
**Data Shape:** `FollowUpAction.additional_data.tool` is a free-form payload — tool approval stuffs `{required_tools, code_preview, full_code, policy_name}`; `ActionResponse` mirrors it plus `text_response/button_clicked/selected_values/confirmed/response_time_ms`.

### Decisive source
```python
# wait_for_response.py:26-36 — the whole resume protocol
response = interrupt(state.hitl_action.model_dump())
state.hitl_response = ActionResponse(**response)
...
prev_sender = state.sender          # captured BEFORE overwriting
state.sender = "WaitForResponse"
state.hitl_action = None            # one-shot consumed
return Command(update=state.model_dump(), goto=prev_sender)
```
**Flow:** any agent needing input sets `state.hitl_action = create_*_action(...)` → routes to SuggestHumanActions → action JSON becomes a visible AI message → WaitForResponse `interrupt()`s (graph suspends; checkpoint holds) → UI POSTs an ActionResponse → graph resumes inside interrupt → response parsed into state, action cleared → goto the CAPTURED prev_sender (per-node routing decided elsewhere by reading hitl_response).
**Invariant:** (1) Capture `prev_sender` BEFORE mutating `state.sender`. (2) Consume `hitl_action` (None it) so resumes can't loop. (3) The action must ALSO be appended as a message — checkpointed conversation history is what the UI renders after restarts. (4) `FollowUpAction.return_to` is advisory data for routers (e.g. approval ladder), NOT what WaitForResponse goto's. (5) `model_config = ConfigDict(use_enum_values=True)` on BOTH sides so serialized state carries plain strings across checkpoints.

**Probe:** No direct unit suite for these two nodes at HEAD (coverage caveat — the pattern is exercised end-to-end by `policy/tests/test_tool_approval_full_graph.py` which drives hitl_action through a full graph, and pinned indirectly by the supervisor approval-callback capsules).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "interrupt hitl_action WaitForResponse FollowUpAction ActionResponse", limit: 8 });
```
## Verdict
Adopt this pair verbatim for LangGraph HITL; keep action-as-message + one-shot consumption + prev-sender goto. Adapt the ActionType set to your UI vocabulary.
