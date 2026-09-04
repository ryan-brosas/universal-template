<!-- capsule-v2 -->
# Resolution ladder — one dispatch pass then a fixed priority chain

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e7dd83a427cff9076e58356d00c4f90b2`; Codebase Memory `openai-agents-python`. **Question:** How does a model response become action, and what priority decides the winner when multiple things could happen?

## The resolution ladder
**Path/Symbol:** `src/agents/run_internal/turn_resolution.py:process_model_response` (:2684) + `execute_tools_and_side_effects` (:784).
**Signature:** `process_model_response(*, agent, all_tools, response, output_schema, handoffs, existing_items=None, run_config=None, server_manages_conversation=False, ...) -> ProcessedResponse`; `execute_tools_and_side_effects(*, bindings, original_input, pre_step_items, new_response, processed_response, output_schema, hooks, context_wrapper, run_config, error_handlers=None, ...) -> SingleStepResult`.
**Data Shape:** `response.output` items are routed by type into disjoint buckets (handoffs, functions, computer_actions, custom_tool_calls, local_shell_calls, shell_calls, apply_patch_calls, mcp_approval_requests, function_tools_not_found); display-only items land in `items`.

### Decisive source
```python
# process_model_response iterates response.output EXACTLY ONCE, routing each item by type.
# Totality is enforced: every item lands somewhere or raises ModelBehaviorError.

# execute_tools_and_side_effects resolves buckets through a strict priority ladder:
# 1. tool plan execution -> any interruption wins (NextStepInterruption)
# 2. handoffs beat tools (NextStepHandoff)
# 3. tool_use_behavior-driven final output from tool results
# 4. refusal detection on the last message -> ModelRefusalError unless an error handler supplies output
# 5. structured-output schema validation of the final message, with error-handler fallback
# 6. plain-text final output
# 7. otherwise NextStepRunAgain
```

**Flow:** Human approvals block everything (interruption wins); handoffs beat tools; tools can short-circuit to final output; only a bare message with no pending tool activity may become the answer. Handoff matching is name-based but namespace-aware — "Namespaced calls never resolve to a handoff, so only bare names are matched" (:208-210). Unknown tool names either raise or, under `tool_not_found_behavior='return_error_to_model'`, become a `ToolCallOutputItem` the model can self-correct from (:3393-3399). One deliberate tolerance (:239-241): "Model returned a final output of None. Not raising an error because we assume you know what you're doing."
**Invariant:** Model output becomes action via ONE exhaustive type-dispatch pass into typed buckets, then a fixed priority ladder ending in `NextStep*` variants — copy the ladder shape, not ad-hoc ifs.
**Probe:** `tests/test_tool_name_collision_policy.py:842-884` (parametrizes return-vs-raise for not-found tools); `tests/test_run_config.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "process_model_response execute_tools_and_side_effects NextStep", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exhaustive-dispatch-then-priority-ladder shape; adapt the specific bucket set to your tool taxonomy; omit provider-specific `ModelRefusalError` semantics. Direct tests pin the not-found routing.
