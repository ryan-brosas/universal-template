<!-- capsule-v2 -->
# Handoff reminder filter — how does a control transfer stay attributed, reminded, and ordered in shared history?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** How is the SDK handoff object reshaped so the receiving agent gets a system reminder AND the tool-call schema matches the send_message shape?

## Handoff.create_handoff with input-schema unification + input_filter
**Path/Symbol:** `src/agency_swarm/tools/send_message.py:Handoff.create_handoff` (:575-642) + inner `message_filter` (:596-641); runtime alignment in `src/agency_swarm/agent/execution_helpers.py:setup_execution` (:387-409) + `cleanup_execution` (:479-482).
**Signature:** `create_handoff(recipient_agent: Agent)` → SDK `handoff()` object with overridden name/description/schema/filter; class attr `add_reminder: bool = True`.
**Data Shape:** handoff tool named `transfer_to_<Name_with_underscores>`; input schema reduced to exactly `{recipient_agent: Literal[<name>]}` (strict JSON schema) so downstream consumers treat handoffs and send_message uniformly; `_agency_swarm_tool_class` attribute tags the origin class for dedup identity.

### Decisive source
```python
handoff_object = handoff(agent=recipient_agent,
    tool_description_override=recipient_agent.description,
    tool_name_override=f"transfer_to_{recipient_agent_name.replace(' ', '_')}")
class InputArgs(BaseModel):
    recipient_agent: Literal[recipient_agent_name]
handoff_object.input_json_schema = strict_schema.ensure_strict_json_schema(InputArgs.model_json_schema())

async def message_filter(input_data: HandoffInputData) -> HandoffInputData:
    last_message = ctx.context.thread_manager.get_all_messages()[-1]
    reminder_content = getattr(recipient_agent, "handoff_reminder", None) or \
        f"Transfer completed. You are {recipient_agent_name}. Please continue the task."
    reminder_msg = {"role": "system", "content": reminder_content}
    new_input_history = input_data.input_history + (reminder_msg.copy(),)
    reminder_msg["message_origin"] = "handoff_reminder"
    for property_name in MessageFormatter.metadata_fields:          # copy caller attribution
        if property_name in last_message:
            reminder_msg[property_name] = last_message[property_name]
    if isinstance(reminder_msg.get("timestamp"), int | float):
        reminder_msg["timestamp"] = reminder_msg["timestamp"] + 1   # keep sort order AFTER parent
    ctx.context.thread_manager.add_message(reminder_msg)
```

**Flow:** setup_execution aligns runtime handoffs onto EVERY agency agent before Runner.run (chained handoffs switch agents mid-run without re-entering setup) → identity-dedup by `(agent_name, tool_name, tool_class)` so same-name variants from different classes coexist but true duplicates don't → restore entries snapshot original lists and cleanup puts them back exactly.
**Invariant:** (1) The reminder must be added to BOTH the runner input and the thread store, with timestamp+1 so it sorts after its triggering message — forgetting the increment reorders history; (2) caller attribution (`agent`, `callerAgent`, run ids) is copied onto the reminder so pair-scoped retrieval still finds it; (3) `reminder_override` raises TypeError — the migration path is per-agent `handoff_reminder`, not a class attribute; (4) handoff alignment mutates SHARED agent objects, hence the mandatory save/restore around each execution.
**Probe:** `tests/test_agency_modules/test_agent_flow_integration.py::test_agent_pair_can_use_send_message_and_handoff` (:114), `test_send_message_handoff_name_is_deprecated` (:351), `test_agent_flow_with_handoff_tool` (:324); runtime alignment pinned by `test_runtime_handoff_variant_is_preserved_with_static_handoff` (:172), `test_same_name_handoff_variants_are_preserved_with_static_handoff` (:196), `test_same_base_handoff_is_deduplicated_with_static_handoff` (:220); end-to-end `tests/integration/agency/test_agent_handoffs.py::TestHandoffsWithCommunicationFlows.test_communication_flow_isolation` (:206).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "create_handoff message_filter transfer_to", limit: 10 });
```

## Verdict
Adopt schema-unified handoffs + reminder-with-attribution filtering; adapt the reminder text/default to your product voice; omit the strict-Literal schema trick only if your provider tolerates free-form handoff args (it usually doesn't for small models). Seven direct tests pin this seam at HEAD.
