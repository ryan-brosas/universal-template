<!-- capsule-v2 -->
# Memory step rendering — how does the agent's memory become the next prompt, and why do planning steps need a role change?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** How do ActionStep/PlanningStep/TaskStep objects convert into ChatMessages (including error coaching and summary mode), and what keeps models from continuing a plan instead of executing it?

## Step → message projection
**Path/Symbol:** `src/smolagents/memory.py` — `ActionStep.to_messages` (:92-150), `PlanningStep.to_messages` (:174-183), `TaskStep` (:186-196), `SystemPromptStep` (:199-206), `AgentMemory.get_succinct_steps/:return_full_code` (:236-277), `CallbackRegistry` (:280-316).
**Signature:** `to_messages(summary_mode: bool = False) -> list[ChatMessage]`; `CallbackRegistry.callback(memory_step, **kwargs)` dispatches by MRO with arity sniffing.
**Data Shape:** Message roles come from the 5-value enum (user/assistant/system/tool-call/tool-response); error text embeds call id when tool_calls exist.

### Decisive source
```python
# :138-148 — errors are coached observations, not exceptions:
error_message = ("Error:\n" + str(self.error) +
    "\nNow let's retry: take care not to repeat previous errors! "
    "If you have retried several times, try a completely different approach.\n")
message_content = f"Call id: {self.tool_calls[0].id}\n" if self.tool_calls else ""
# :174-183 — the anti-continuation trick:
return [
    ChatMessage(role=MessageRole.ASSISTANT, content=[{"type": "text", "text": self.plan.strip()}]),
    ChatMessage(role=MessageRole.USER,
        content=[{"type": "text", "text": "Now proceed and carry out this plan."}]),
    # This second message creates a role change to prevent models from simply continuing the plan message
]
```

**Flow:** Prompt assembly (`write_memory_to_messages`, agents.py:758-770) = system prompt + each step's projection in order. An ActionStep contributes: assistant text (model output), a TOOL_CALL message listing serialized calls, image parts, an "Observation:\n..." TOOL_RESPONSE, and — only on error — the retry-coaching TOOL_RESPONSE above. PlanningStep emits plan-as-assistant then a USER pivot; update plans additionally run in summary_mode so prior plans don't bias the new one (agents.py:682-684). CallbackRegistry walks the step's MRO collecting handlers; single-parameter callbacks get just the step (legacy contract), multi-parameter ones receive kwargs like `agent=` — this is how monitor updates and user interrupts hook in without subclassing.
**Invariant:** The role change after a plan is semantic glue: same-role continuation lets models ramble the plan onward instead of acting. Error-as-data (never raise through memory) is what makes multi-step self-correction possible; the coaching sentence is part of the tested behavior surface.
**Probe:** `tests/test_memory.py::test_action_step_to_messages` (:119+), `test_planning_step_to_messages` (:180), callback registry cases in `tests/test_agents.py::test_setup_step_callbacks/test_finalize_step_callbacks_with_list/_by_type` (:1090-1216). Live: build ActionStep with error and no tool_calls → messages end with coaching text lacking a call-id prefix.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "ActionStep to_messages PlanningStep summary_mode CallbackRegistry", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the projection order and both psychological invariants (role pivot, error coaching). Adapt role names to your provider via conversions. Omit summary_mode and every replan inherits stale-plan bias.
