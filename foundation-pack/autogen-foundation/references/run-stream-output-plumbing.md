<!-- capsule-v2 -->
# Run-stream output plumbing — how does a team turn bus chatter into an ordered message stream plus one TaskResult?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** Who guarantees the caller sees every event exactly once and always gets a terminal marker, even when the runtime dies?

## Manager relays output topic → asyncio.Queue; shutdown task backstops
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py` (`run_stream` :351–578 esp. :495–578; `_init` output subscription :241–243).
**Signature:** `async def run_stream(self, *, task=None, cancellation_token=None, output_task_messages: bool = True) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]`.
**Data Shape:** `_output_message_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination]`; the manager is the ONLY subscriber of `output_topic_*` and puts each relayed chat message into this queue (`_base_group_chat_manager.handle_group_chat_message` :262–265); stream ends at the first `GroupChatTermination`.

### Decisive source
```python
async def stop_runtime() -> None:
    try:
        await self._runtime.stop_when_idle()
        await self._output_message_queue.put(GroupChatTermination(
            message=StopMessage(content="The group chat is stopped.", source=self._group_chat_manager_name)))
    except Exception as e:
        # runtime died: manager can't be trusted to emit termination -> synthesize it HERE
        await self._output_message_queue.put(GroupChatTermination(
            message=StopMessage(content="An exception occurred in the runtime.", ...),
            error=SerializableException.from_exception(e)))
shutdown_task = asyncio.create_task(stop_runtime())

# consumer side:
if isinstance(message, GroupChatTermination):
    if message.error is not None:
        raise RuntimeError(str(message.error))    # runtime failure re-raised to caller
    stop_reason = message.message.content
    break
...
finally:
    while not self._output_message_queue.empty():
        self._output_message_queue.get_nowait()   # never leak messages across runs
```

**Flow:** run → RPC GroupChatStart into the manager → agents' events flow container→output-topic→manager→queue→caller; ModelClientStreamingChunkEvents are yielded but excluded from the final TaskResult (:558–561) → termination event ends the loop → yield TaskResult(messages, stop_reason).
**Invariant:** EVERY code path must enqueue exactly one GroupChatTermination (normal stop, manager-signaled stop with reason, or synthetic error wrapper) — a missing marker hangs the async-for forever; cancellation tokens link futures so cancel propagates into the queue wait; queue drain in `finally` prevents cross-run contamination since the queue object persists on the team instance.
**Probe:** `python/packages/autogen-agentchat/tests/test_group_chat.py::test_round_robin_group_chat_output_task_messages_false` (flag gates task-message emission); `::test_round_robin_group_chat_with_exception_raised_from_termination_condition` (error path reaches the caller as RuntimeError).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "run_stream GroupChatTermination _output_message_queue stop_runtime", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "single relay subscriber + guaranteed terminal marker" for any stream API over a bus. Adapt marker payload shape to your result type. Omit chunk-vs-final filtering if your host has no token streaming.
