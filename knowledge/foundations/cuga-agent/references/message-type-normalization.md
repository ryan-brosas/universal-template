<!-- capsule-v2 -->
# Message-type normalization — how do you convert a generic BaseMessage into the proper LangChain subclass when a serialized/round-tripped message lost its concrete type?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Messages instantiated as generic `BaseMessage` (instead of AIMessage/HumanMessage/etc.) break downstream code that expects concrete types — how does a single helper recover the right subclass from a `type` attribute, and what are the edge cases (ToolMessage tool_call_id, ChatMessage role)?

## Attribute-inference type recovery
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/message_utils.py:19-81` (`convert_to_proper_message_type`).
**Signature:** `convert_to_proper_message_type(message: BaseMessage) -> BaseMessage`.
**Data Shape:** Returns a concrete subclass preserving `content`, `additional_kwargs`, `id`, and type-specific fields. `ToolMessage` requires `tool_call_id` — taken from the direct attribute or `additional_kwargs["tool_call_id"]`, defaulting to `"unknown"`. `ChatMessage` requires a `role` — taken from `additional_kwargs["role"]`, defaulting to `"user"`.

### Decisive source
```python
# message_utils.py:32-52 — validate, short-circuit concrete subclasses, infer from type attr
if not hasattr(message, 'content') or message.content is None:
    logger.warning(f"Message missing content attribute or content is None: {message}")
    return HumanMessage(content='')
if type(message) is not BaseMessage:   # already a concrete subclass — return as-is
    return message
msg_type = getattr(message, 'type', None)
if msg_type == 'ai' or msg_type == 'AIMessage':
    return AIMessage(content=message.content, additional_kwargs=message.additional_kwargs,
                      response_metadata=getattr(message,'response_metadata',{}), id=message.id,
                      tool_calls=getattr(message,'tool_calls',[]))
```

**Flow:** If the message lacks content or content is None, warn and return an empty `HumanMessage` (fail-safe). If `type(message) is not BaseMessage` — i.e. it's already a concrete subclass — return it unchanged (short-circuit). Otherwise inspect the `type` attribute (common in serialized messages) and dispatch: `ai`/`AIMessage` → AIMessage (carrying `response_metadata` and `tool_calls`), `human`/`HumanMessage` → HumanMessage, `system`/`SystemMessage` → SystemMessage, `tool`/`ToolMessage` → ToolMessage (with the tool_call_id fallback ladder), `chat`/`ChatMessage` → ChatMessage (with role from additional_kwargs). Unknown types default to HumanMessage with a debug log.

**Invariant:** The exact `type(message) is not BaseMessage` check (not `isinstance`) is deliberate — a genuinely generic BaseMessage must be converted, while any subclass passes through untouched. ToolMessage's `tool_call_id` and ChatMessage's `role` are the two fields that can't be inferred from the base class, so they have explicit fallback ladders.

**Probe:** No dedicated unit test file for `message_utils.py` at HEAD (thin 84-line helper; exercised indirectly across the message-handling suites). State this coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "convert_to_proper_message_type", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exact-`type is not BaseMessage` short-circuit, the `type`-attribute dispatch, and the ToolMessage/ChatMessage fallback ladders. Adapt the default-role/tool_call_id behavior to your message model. Omit if your message layer never produces generic BaseMessage. Coverage caveat: no direct unit test at HEAD.
