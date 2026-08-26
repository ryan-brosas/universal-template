<!-- capsule-v2 -->
# OpenAI-conversation item sanitization — which provider IDs must survive persistence and which must be stripped?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** When history is stored for/replayed against the Conversations API, per item type, is the server-assigned `id` load-bearing?

## Required-ID allowlist + reasoning carve-out
**Path/Symbol:** `src/agents/run_internal/session_persistence.py:` `_OPENAI_CONVERSATION_ITEM_TYPES_WITH_REQUIRED_ID` (:891–906), `_sanitize_openai_conversation_item` (:910–930), `_openai_conversation_item_requires_id` (:933–935), `_is_unpersistable_for_openai_conversation` (:938–942), assistant-only replay sanitizer (:959–968).
**Signature:** `def _sanitize_openai_conversation_item(item: TResponseInputItem) -> TResponseInputItem`.
**Data Shape:** required-id types = `{file_search_call, web_search_call, computer_call, code_interpreter_call, image_generation_call, local_shell_call, local_shell_call_output, mcp_list_tools, mcp_approval_request, mcp_call, item_reference, program, program_output}`; `FAKE_RESPONSES_ID` is the SDK's own placeholder id.

### Decisive source
```python
if clean_item.get("id") == FAKE_RESPONSES_ID or (
    clean_item.get("type") != "reasoning"
    and not _openai_conversation_item_requires_id(clean_item)
):
    clean_item.pop("id", None)
clean_item.pop("provider_data", None)
```
```python
def _is_unpersistable_for_openai_conversation(item):
    if not isinstance(item, dict) or item.get("type") != "reasoning":
        return False
    return not item.get("id") and not item.get("encrypted_content")
```

**Flow:** strip internal metadata → drop id when it is the fake placeholder OR (type ≠ reasoning AND type ∉ required set) → always drop `provider_data`. Reasoning items KEEP their id or encrypted content — without one of them the conversation cannot restore hidden-reasoning state. Items that are reasoning-typed with NEITHER id NOR encrypted_content are counted as persisted (so counters stay aligned) but filtered from what is actually sent (`_is_unpersistable...`). On READ back into model input, only ASSISTANT message items get id/provider_data stripped (`_sanitize_..._history_item_for_model_input`) — user/tool items keep their ids for round-trips.

**Invariant:** Two opposite rules coexist deliberately: stale client-side ids on ordinary messages cause 404s on replay (strip), while hosted-tool call records REQUIRE their ids to address server-side results (keep). Misclassifying either direction breaks the conversation.

**Probe:** `tests/memory/test_session_persistence_sanitize.py::test_sanitize_preserves_ids_required_by_openai_conversation_items` (:33) and the per-type pins at :42/:58/:75.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "sanitize openai conversation item requires id fake responses", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the keep/strip taxonomy for any provider whose item identity is partially server-owned; adapt the type set to your wire schema; omit entirely if your store owns all identities.
