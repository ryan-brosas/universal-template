<!-- capsule-v2 -->
# AgentChannel protocol — five methods, isinstance gate, one-hop delegation to thread actions

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** What contract must a channel satisfy to plug an agent into AgentChat, and what does the thinnest real channel look like?

## AgentChannel ABC + AzureAIChannel delegation exemplar
**Path/Symbol:** `python/semantic_kernel/agents/channels/agent_channel.py:AgentChannel` (whole, 85 ln — five abstract methods); `python/semantic_kernel/agents/azure_ai/azure_ai_channel.py:AzureAIChannel` (whole, 121 ln).
**Signature:** abstract: `receive(history) -> None`; `invoke(agent, **kwargs) -> AsyncIterable[tuple[bool, ChatMessageContent]]`; `invoke_stream(agent, messages, **kwargs) -> AsyncIterable[ChatMessageContent]`; `get_history() -> AsyncIterable[ChatMessageContent]`; `reset() -> None`.
**Data Shape:** The channel holds only transport state — `AzureAIChannel.__init__(client: AIProjectClient, thread_id: str)` stores exactly those two fields; everything else is delegated. `invoke` yields `(is_visible, message)` tuples; `invoke_stream` appends streaming output into the caller-supplied `messages` list (via `output_messages=messages`) AND yields each chunk.

### Decisive source
```python
async def invoke(self, agent: "Agent", **kwargs) -> AsyncIterable[tuple[bool, "ChatMessageContent"]]:
    from semantic_kernel.agents.azure_ai.azure_ai_agent import AzureAIAgent   # lazy import
    if not isinstance(agent, AzureAIAgent):
        raise AgentChatException(f"Agent is not of the expected type {type(AzureAIAgent)}.")
    async for is_visible, message in AgentThreadActions.invoke(
        agent=agent, thread_id=self.thread_id, arguments=agent.arguments,
        kernel=agent.kernel, **kwargs,
    ):
        yield is_visible, message

async def reset(self) -> None:
    try:
        await self.client.agents.threads.delete(thread_id=self.thread_id)
    except Exception as e:
        raise AgentChatException(f"Failed to delete thread: {e}")
```

**Flow:** The channel is the AgentChat-side adapter: `receive` pushes each history item into the thread (`AgentThreadActions.create_message` per message — one round trip per item, no batching); `invoke`/`invoke_stream` type-gate the agent with an isinstance check that raises `AgentChatException` (never a TypeError) and then delegate one hop to the thread-actions class, passing `agent.arguments` and `agent.kernel` from the agent itself; `get_history` streams `AgentThreadActions.get_messages`; `reset` deletes the server thread and re-wraps ANY provider exception as `AgentChatException`. The AzureAIAgent import sits INSIDE the method body — a circular-import break that keeps the channel module importable without the agent module. This is the pass-11 "thin delegation" seam resolved into its porting question: the channel's whole value is the (client, thread_id) binding plus the visibility-tuple protocol; all run-loop logic lives in thread actions.
**Invariant:** A channel never runs agent logic — it binds transport state and translates the five-method protocol onto thread actions; agent-type mismatches fail as AgentChatException at the gate, and provider failures on reset are re-wrapped, never leaked raw. invoke_stream must both yield chunks and append to the caller's `messages` list (the AgentChat contract reads that list after the stream).
**Probe:** `python/tests/unit/agents/azure_ai_agent/test_azure_ai_channel.py::test_azure_ai_channel_invoke_invalid_agent` (line 15 — object() → AgentChatException), `test_azure_ai_channel_invoke_valid_agent` (line 21 — patched AgentThreadActions.invoke, one yielded tuple), `test_azure_ai_channel_get_history` (line 62 — patched get_messages, one message).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "AzureAIChannel AgentChannel receive invoke_stream get_history reset AgentChatException create_message", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the five-method channel protocol with transport-state-only constructors and the gate-then-delegate shape for any multi-agent chat host. Adapt: the visibility-tuple yield if your host has no hidden-message concept (always yield True); the lazy import if your module graph has no cycle. Omit: nothing in the protocol — but do not copy the per-item `receive` round trips into a high-throughput host without batching.
