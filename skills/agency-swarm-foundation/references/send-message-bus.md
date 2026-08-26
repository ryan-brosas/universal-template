<!-- capsule-v2 -->
# Send-message bus — how does one agent synchronously delegate a task to another and get its answer back as a tool result?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** What must a porter replicate so an LLM-visible tool routes a message to the right sibling agent, blocks until the sibling finishes, and returns its final text without deadlocking or double-dispatch?

## SendMessage FunctionTool with enum-driven recipient routing
**Path/Symbol:** `src/agency_swarm/tools/send_message.py:SendMessage` (`__init__` :57-183, `on_invoke_tool` :314-567).
**Signature:** `SendMessage(sender_agent: Agent, recipients: dict[str, Agent] | None = None, runtime_state: AgentRuntimeState | None = None, name: str = "send_message")`; `async on_invoke_tool(wrapper: ToolContext[MasterContext], arguments_json_string: str) -> str`.
**Data Shape:** recipients stored LOWERCASED (`{k.lower(): v}`); tool params schema has exactly `recipient_agent` (enum = recipient display names), `message`, `additional_instructions` — and OpenAI requires even optional fields inside `required` (:116-117). The tool description embeds every recipient's name + description ("Available recipient agents:" block) so the model picks targets by role text.

### Decisive source
```python
# Per-thread pending guard — the ONLY concurrency control on delegation
thread_key = id(thread_manager)
async with self._pending_lock:
    pending_set = self._pending_per_thread.setdefault(thread_key, set())
    if recipient_key in pending_set:
        return f"Error: Cannot send another message to '{recipient_agent_name}' while the previous message is still being processed..."
    pending_set.add(recipient_key)
self.recipient_agent = self.recipients[recipient_key]   # instance attr set pre-await
...
try:
    use_streaming = wrapper.context._is_streaming if wrapper.context else False
    if use_streaming:
        stream = self.recipient_agent.get_response_stream(..., parent_run_id=tool_call_id)
        async for event in stream:
            event = add_agent_name_to_event(event, self.recipient_agent.name, self.sender_agent.name, ...)
            if streaming_context:
                await streaming_context.put_event(event)   # forward into parent's queue
            ... # collect final_output_text from message_output_item
    else:
        response = await self.recipient_agent.get_response(..., parent_run_id=tool_call_id)
    ...
except InputGuardrailTripwireTriggered as e:
    ...
    if self.recipient_agent.raise_input_guardrail_error:
        return f"Error getting response from the agent: {message}"
    else:
        return message                       # guidance becomes the TOOL RESULT, not an exception
except Exception as e:
    return f"Error: Failed to get response from agent '{recipient_name_for_call}'. Reason: {e}"
finally:
    async with self._pending_lock:
        cleanup_set.discard(recipient_key); if not cleanup_set: pop thread_key
```

**Flow:** validate JSON args → validate extra params (subclass model) → case-insensitive recipient lookup (unknown ⇒ error string listing available names) → acquire per-thread pending slot → build `AgencyContext` for the RECIPIENT via `_create_recipient_agency_context` (MinimalAgency shim reusing parent's agents/user_context/shared_instructions + recipient's runtime state) → sub-`get_response` or sub-`get_response_stream` chosen by PARENT's `_is_streaming` flag (streaming consistency) → forward sub-events tagged with agent/caller names → merge sub-agent `raw_responses` into `wrapper.context._sub_agent_raw_responses` as `(model_name, response)` tuples for per-model pricing → return final text as the tool string.
**Invariant:** (1) ONE in-flight message per (thread_manager, recipient) — the pending set releases only in `finally`, so cancellation still unblocks; (2) errors NEVER raise out of `on_invoke_tool` — every failure mode returns a string the calling LLM can read and react to; (3) `parent_run_id=tool_call_id` ties the sub-run's trace to the delegating tool call; (4) recipient keys are lowercased everywhere but the schema enum uses original names — lookups must `.lower()` before dict access.
**Probe:** `tests/integration/communication/test_send_message_blocking.py::test_concurrent_messages_to_same_agent` (:17) pins the pending-guard rejection; `test_messages_to_different_agents` (:64) proves parallelism across DIFFERENT recipients; `test_pending_guard_is_isolated_between_agencies_that_share_agents` (:134) proves the guard key includes the thread manager, not just the recipient.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "SendMessage on_invoke_tool", limit: 10 });
```

## Verdict
Adopt the pending-set backpressure + errors-as-tool-result strings + parent-run-id plumbing (framework-neutral supervision machinery); adapt the MinimalAgency context shim to your own context object; omit the OpenAI-specific streaming event taxonomy and hosted pricing tuples if your harness tracks cost differently. Direct tests cover all three concurrency paths at HEAD; no coverage caveat.
