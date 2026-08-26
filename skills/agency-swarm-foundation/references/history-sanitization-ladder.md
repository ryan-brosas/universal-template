<!-- capsule-v2 -->
# History sanitization ladder — what must be stripped or repaired before a stored transcript can be replayed to the model?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** In what ORDER do metadata stripping, tool-call repair, id dedup, and protocol guards run, and why does each step exist?

## prepare_history_for_runner five-step ladder
**Path/Symbol:** `src/agency_swarm/messages/message_formatter.py:prepare_history_for_runner` (:256-320) with `strip_agency_metadata` (:351-366), `sanitize_tool_calls_in_history` (:368-389), `ensure_tool_calls_content_safety` (:391-417), `sanitize_replayed_tool_item_ids` (:419-447), `_ensure_store_false_replay_settings` (:449-471).
**Signature:** `prepare_history_for_runner(processed_current_message_items, agent, sender_name, agency_context=None, agent_run_id=None, parent_run_id=None, run_trace_id=None, run_config_override=None) -> list[TResponseInputItem]`.
**Data Shape:** input = stored dicts carrying agency metadata; output = provider-clean items. Metadata field list: `agent, callerAgent, timestamp, citations, agent_run_id, parent_run_id, message_origin, run_trace_id, history_protocol`.

### Decisive source
```python
history_for_runner = MessageFormatter.sanitize_tool_calls_in_history(full_history)
history_for_runner = MessageFormatter.ensure_tool_calls_content_safety(history_for_runner)
history_for_runner = MessageFormatter.strip_agency_metadata(history_for_runner)   # AFTER repairs
history_for_runner = MessageFormatter.sanitize_replayed_tool_item_ids(history_for_runner)
if MessageFormatter._ensure_store_false_replay_settings(agent, run_config_override):
    history_for_runner = sanitize_store_false_responses_input(history_for_runner)
```
```python
# Only the LAST assistant message keeps tool_calls — earlier ones lose them:
for idx, msg in enumerate(history):
    if msg.get("role") == "assistant" and "tool_calls" in msg and idx != last_assistant_idx:
        msg.pop("tool_calls", None)
# Null-content tool-call assistant messages get synthesized text:
msg["content"] = f"Using tools: {', '.join(tool_descriptions)}"
# Replay artifact: id == call_id means FAKE_RESPONSES_ID normalization leaked into storage → drop id
if message_type == "function_call" and message_id == call_id:
    msg_copy.pop("id", None)
```

**Flow:** protocol compatibility is checked FIRST (raise `IncompatibleChatHistoryError` on mixed or mismatched protocols before anything else mutates state) → current items stamped + saved (ephemeral content parts marked `_agency_swarm_ephemeral` go to the runner but are DROPPED from storage) → then the ladder above runs on the combined history.
**Invariant:** (1) Order matters: tool-call repairs must see original fields BEFORE metadata strip; id-dedup must run after repairs so it only touches true replay artifacts (`id == call_id`) while Responses-native items with distinct ids keep them for reasoning continuity across turns; (2) `store:false` replay requires encrypted-reasoning include settings — the helper MUTATES agent/run-config model_settings to add `reasoning.encrypted_content` when store is False; (3) mixed-protocol history is never silently coerced — it raises with a "start a new chat" remedy because cross-protocol repair would corrupt tool linkage.
**Probe:** `tests/test_messages_modules/test_message_formatter_history_protocol.py::test_prepare_history_for_runner_stores_responses_protocol_and_strips_runner_metadata` (:104), `test_prepare_history_for_runner_keeps_ephemeral_content_out_of_storage` (:124), `test_prepare_history_for_runner_rejects_inferred_protocol_mismatch` (:296), `test_prepare_history_for_runner_uses_run_config_store_false_settings` (:183).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "sanitize_tool_calls_in_history strip_agency_metadata", limit: 10 });
```

## Verdict
Adopt the ordered ladder and the raise-don't-coerce protocol guard; adapt which repairs your providers need (the null-content synthesis fixes a Chat Completions 400); omit the store:false reasoning plumbing if you never disable response storage. Four direct tests pin the ladder at HEAD.
