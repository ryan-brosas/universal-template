<!-- capsule-v2 -->
# ChatHistoryChannel content gates — whitelist filter, last-message visibility, and identity dedupe

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** When a chat's messages flow into a channel backed by a plain ChatHistory, which content survives, which messages become user-visible, and how are duplicates between the agent's own history writes and its returned messages prevented?

## ChatHistoryChannel
**Path/Symbol:** `python/semantic_kernel/agents/channels/chat_history_channel.py:ChatHistoryChannel` (whole file, 183 ln — ALLOWED_CONTENT_TYPES 44–50, invoke 52–104, invoke_stream 106–135, `_is_message_visible` 137–145, receive 147–172, get_history 174–181, reset 183).
**Signature:** `receive(history: list[ChatMessageContent]) -> None`; `invoke(agent) -> AsyncIterable[tuple[bool, ChatMessageContent]]`; `invoke_stream(agent, messages: list) -> AsyncIterable[StreamingChatMessageContent]`; `_is_message_visible(message, message_queue_count: int) -> bool`.
**Data Shape:** class inherits BOTH `AgentChannel` and `ChatHistory` — the channel IS the history; `ALLOWED_CONTENT_TYPES: ClassVar[tuple[type, ...]]` = (ImageContent, FunctionCallContent, FunctionResultContent, StreamingTextContent, TextContent); a `deque` message_queue plus a `set` mutated_history per invoke call.

### Decisive source
```python
async def receive(self, history: list[ChatMessageContent]) -> None:
    filtered_history: list[ChatMessageContent] = []
    for message in history:
        new_message = deepcopy(message)
        if new_message.items is None:
            new_message.items = []
        allowed_items = [item for item in new_message.items if isinstance(item, self.ALLOWED_CONTENT_TYPES)]
        if not allowed_items:
            continue
        new_message.items.clear()
        new_message.items.extend(allowed_items)
        filtered_history.append(new_message)
    self.messages.extend(filtered_history)

def _is_message_visible(self, message: ChatMessageContent, message_queue_count: int) -> bool:
    return (
        not any(isinstance(item, (FunctionCallContent, FunctionResultContent)) for item in message.items)
        or message_queue_count == 0
    )
```

**Flow:** `receive` is the inbound gate: every message is deep-copied (caller's objects never shared), items are filtered against the whitelist, and a message left with ZERO allowed items is dropped entirely — file-reference-only messages never enter channel history. `invoke` sends ONLY `self.messages[-1]` to the agent (the channel assumes the agent holds the thread; the channel history is the turn window) and reconciles two sources per iteration: messages the agent appended into the shared channel history (tracked via a `message_count` pointer into `mutated_history` + `message_queue`) and the `response.message` itself, which is appended to the channel only if NOT already in the mutated set — dedupe is by object identity, so an agent that returns the same object it stored never double-counts, but a copy would. Each yielded message is popped from the queue and paired with `_is_message_visible`: function-call/result-only messages are hidden from the caller UNLESS the queue is empty (`message_queue_count == 0` forces the LAST message visible so a tool-only turn still surfaces something). After the agent finishes, remaining queued messages drain. `invoke_stream` yields only deltas with non-empty `.content`, then appends every message the agent added during streaming (message_count pointer again) to the CALLER's `messages` list — the AgentChat-level accumulation contract. `get_history` yields messages REVERSED (newest first), matching AgentChat's descending-order read path. `reset` clears messages only — the bound thread is untouched.
**Invariant:** Inbound content is whitelisted and deep-copied at the channel boundary; empty-after-filter messages are dropped; the final message of any invoke is always user-visible even when it is tool traffic; dedupe between agent-side history writes and returned messages is identity-based, not value-based.
**Probe:** NO dedicated unit test file at this pin — `python/tests/unit/agents/channels/` does not exist and grep finds no test importing ChatHistoryChannel; the channel is exercised only indirectly through agent-level tests. Evidence gap recorded; the capsule rests on whole-file source reading at the pin. Anchor symbols verified present by direct read: ALLOWED_CONTENT_TYPES (line 44), `_is_message_visible` (137), `deepcopy(message)` (receive body), `message_queue_count == 0` (144).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "ChatHistoryChannel ALLOWED_CONTENT_TYPES _is_message_visible receive filtered_history mutated_history message_queue", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the whitelist+deepcopy inbound gate and the last-message-always-visible rule for any channel that mirrors a shared chat history. Adapt: identity-based dedupe assumes the agent stores the same objects it returns — if your agent copies messages, switch to id-based dedupe. Omit: the reversed get_history if your host reads history in natural order (AgentChat's descending contract is a UI choice, not a storage invariant).
