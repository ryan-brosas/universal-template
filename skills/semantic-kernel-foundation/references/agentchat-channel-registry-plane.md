<!-- capsule-v2 -->
# AgentChat channel registry — hashed channel identity, activity gate, and broadcast fan-out

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does AgentChat map an agent object to a channel, keep one channel per agent identity, and stop two agents from acting at once?

## AgentChat registry + activity gate
**Path/Symbol:** `python/semantic_kernel/agents/group_chat/agent_chat.py:AgentChat` (whole file, 197 ln — fields 35–40, activity gate 52–64, `_synchronize_channel` 96–102, `_get_agent_hash` 104–111, `_get_or_create_channel` 131–142, `invoke_agent` 144–168, `invoke_agent_stream` 170–190); `agents/agent.py:get_channel_keys` (420–428) + `create_channel` (430–438); `group_chat/agent_chat_utils.py:KeyEncoder.generate_hash` (whole, 34 ln).
**Signature:** `get_channel_keys() -> Iterable[str]`; `create_channel() -> AgentChannel`; `KeyEncoder.generate_hash(keys: Iterable[str]) -> str`; `_get_or_create_channel(agent) -> AgentChannel`; `set_activity_or_throw()` / `clear_activity_signal()`.
**Data Shape:** `agent_channels: dict[str, AgentChannel]` keyed by hash; `channel_map: dict[Agent, str]` (identity-keyed memo); `broadcast_queue: BroadcastQueue` with `queues: dict[str, QueueReference]` keyed by the same hash; `_is_active: bool` behind a `threading.Lock` PrivateAttr.

### Decisive source
```python
def _get_agent_hash(self, agent: Agent):
    hash_value = self.channel_map.get(agent, None)
    if hash_value is None:
        hash_value = KeyEncoder.generate_hash(agent.get_channel_keys())
        self.channel_map[agent] = hash_value
    return hash_value

# KeyEncoder.generate_hash — empty key set is a hard error:
if not keys:
    raise AgentExecutionException("Channel Keys must not be empty. Unable to generate channel hash.")
joined_keys = ":".join(keys)
return base64.b64encode(hashlib.sha256(joined_keys.encode("utf-8")).digest()).decode("utf-8")

def set_activity_or_throw(self):
    with self._lock:
        if self._is_active:
            raise Exception("Unable to proceed while another agent is active.")
        self._is_active = True
```

**Flow:** `get_channel_keys` yields exactly ONE key — `self.channel_type.__name__` — and raises NotImplementedError when `channel_type` is unset, so the default identity of an agent in a chat is its channel class name; a subclass may yield several keys (multi-channel agents), but no shipped agent does at this pin. The hash is computed once per agent object and memoized in `channel_map` (a plain dict keyed by Agent identity — two distinct agent instances with the same channel type get SEPARATE channels). `_get_or_create_channel` = hash → `_synchronize_channel` (await BroadcastQueue drain for that channel) → on miss, `agent.create_channel()` + registry insert + replay the ENTIRE shared `history` into the fresh channel via `channel.receive(history)` so a late-joining agent sees prior turns. Every public entry point (get_chat_messages, add_chat_messages, invoke_agent, invoke_agent_stream, reset) brackets its body in `set_activity_or_throw()` … `finally: clear_activity_signal()` — one `_is_active` bool behind a threading.Lock means exactly one agent acts per chat at a time; a concurrent entry raises a PLAIN `Exception` (not AgentChatException) with the "Unable to proceed while another agent is active." message. `add_chat_messages` rejects SYSTEM-role messages with AgentChatException BEFORE touching history. After invoke/add, messages fan out to every OTHER channel as `ChannelReference(channel, hash)`; `BroadcastQueue.enqueue` lazily creates the per-channel `QueueReference` (deque + asyncio.Lock) and spawns one `receive` task per channel, reused while alive. `receive` pops one batch under the lock, calls `channel.receive(messages)`, and on exception stores `receive_failure` and breaks WITHOUT popping the batch — the next `ensure_synchronized` re-raises it wrapped ("Unexpected failure broadcasting to channel: …") and polls every `block_duration=0.1s` until the queue drains. `invoke_agent` appends every channel message to shared history but yields only `is_visible=True` ones; `invoke_agent_stream` yields deltas live and appends the channel's accumulated messages list only after the stream ends.
**Invariant:** Channel identity = sha256 of colon-joined channel keys, memoized per agent OBJECT; one active agent per chat enforced by a lock-guarded flag with the release in `finally`; broadcast failures are stored per channel and re-raised at the next synchronization point, never silently dropped; a newly created channel is back-filled with the whole shared history exactly once at creation.
**Probe:** `python/tests/unit/agents/test_group_chat/test_agent_chat.py::test_set_activity_or_throw_when_active` (line 42 — concurrent entry raises with the exact message), `test_get_agent_hash_generates_new_hash` (182–193 — generate_hash called once with the key list, memoized into channel_map), `test_add_chat_messages_throws_exception_for_system_role` (196–201 — AgentChatException before mutation), `test_get_or_create_channel_creates_new_channel` (204–226 — create + `receive(history.messages)` back-fill), `test_get_or_create_channel_reuses_existing_channel` (229–246 — `create_channel.assert_not_called()`), `test_invoke_streaming_agent` (127–148 — `invoke_stream` called with a FRESH `[]` list).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "AgentChat _get_agent_hash KeyEncoder generate_hash set_activity_or_throw _get_or_create_channel BroadcastQueue ensure_synchronized", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: hash-of-keys channel identity with per-agent memoization, the single-activity gate with finally-release, and receive-failure storage with re-raise-at-sync for any multi-channel chat host. Adapt: the plain `Exception` on concurrent entry should be a typed error in your host; the 0.1s poll interval is a tuning knob, not an invariant. Omit: the identity-keyed `channel_map` dict if your agents are single-instance per chat — the hash lookup alone suffices.
