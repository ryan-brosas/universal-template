<!-- capsule-v2 -->
# Handoff turn-taking via kernel functions — handoffs become transfer_to_* tools plus a terminate filter

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does a multi-agent handoff group express turn-taking without a manager model — and why does each actor get a cloned kernel?

## HandoffAgentActor + HandoffOrchestration
**Path/Symbol:** `python/semantic_kernel/agents/orchestration/handoffs.py:HandoffAgentActor` (lines 145–356: `_add_handoff_functions` 184–216, `_handoff_function_filter` 223–227, `_handle_request_message` 262–305, `_invoke_agent_with_potentially_no_response` 315–356), `HandoffOrchestration` (364–530: `_start` 419–452, `_validate_handoffs` 518–530), `OrchestrationHandoffs` (82–126).
**Signature:** `def _add_handoff_functions(self) -> None`; `async def _handoff_to_agent(self, agent_name: str) -> None`; `async def _handoff_function_filter(self, context: AutoFunctionInvocationContext, next)`; `async def _handle_request_message(self, message: HandoffRequestMessage, cts: MessageContext) -> None`.
**Data Shape:** `OrchestrationHandoffs` is a `dict[source_agent, dict[target_agent, description]]`. Wire messages: `HandoffStartMessage(body: DefaultTypeAlias)`, `HandoffRequestMessage(agent_name: str)`, `HandoffResponseMessage(body: ChatMessageContent)`. All injected functions live in one plugin named `Handoff` (`HANDOFF_PLUGIN_NAME`).

### Decisive source
```python
def _add_handoff_functions(self) -> None:
    functions: list[KernelFunctionFromMethod] = []
    for handoff_agent_name, handoff_description in self._handoff_connections.items():
        function_name = f"transfer_to_{handoff_agent_name}"
        function_metadata = KernelFunctionMetadata(
            name=function_name, description=handoff_description, parameters=[],
            return_parameter=..., is_prompt=False, is_asynchronous=True,
            plugin_name=HANDOFF_PLUGIN_NAME, additional_properties={})
        functions.append(KernelFunctionFromMethod.model_construct(
            metadata=function_metadata,
            method=partial(self._handoff_to_agent, handoff_agent_name)))
    functions.append(KernelFunctionFromMethod(self._complete_task, plugin_name=HANDOFF_PLUGIN_NAME))
    self._kernel.add_plugin(plugin=KernelPlugin(name=HANDOFF_PLUGIN_NAME, functions=functions))
    self._kernel.add_filter(FilterTypes.AUTO_FUNCTION_INVOCATION, self._handoff_function_filter)

async def _handoff_to_agent(self, agent_name: str) -> None:
    self._handoff_agent_name = agent_name

async def _handoff_function_filter(self, context: AutoFunctionInvocationContext, next):
    await next(context)
    if context.function.plugin_name == HANDOFF_PLUGIN_NAME:
        context.terminate = True        # ends the agent's auto-invoke loop immediately

# turn-taking loop
async def _handle_request_message(self, message: HandoffRequestMessage, cts: MessageContext) -> None:
    if message.agent_name != self._agent.name:
        return
    response = await self._invoke_agent_with_potentially_no_response(kernel=self._kernel)
    while not self._task_completed:
        if self._handoff_agent_name:
            await self.publish_message(HandoffRequestMessage(agent_name=self._handoff_agent_name),
                                       TopicId(self._internal_topic_type, self.id.key))
            self._handoff_agent_name = None
            break
        if response is None:
            raise RuntimeError(f'Agent "{self._agent.name}" did not return any response nor did not set a handoff agent name.')
        await self.publish_message(HandoffResponseMessage(body=response), ...)
        if self._human_response_function:
            ...  # publish human response, re-invoke
        else:
            await self._complete_task(task_summary="No handoff agent name provided and no human response function set. Ending task.")
            break
```

**Flow:** Each member agent gets an actor whose kernel is a CLONE of the agent's kernel
(`self._kernel = agent.kernel.clone()`, line 169) so the injected Handoff plugin never leaks into
the caller's agent. Handoff connections become one `transfer_to_<target>` kernel function per
connection (description = the handoff description; the method is a `partial` that just records
the target name) plus a `complete_task` function. The AUTO_FUNCTION_INVOCATION filter lets the
handoff function run, then sets `context.terminate = True` — the agent's auto-invoke loop ends
right after the transfer, which is why the actor's invoke helper tolerates a `None` response
(streaming buffer empty → return None instead of raising). The turn loop: only the requested
agent reacts; it invokes; if a handoff was recorded it publishes a `HandoffRequestMessage` for
the target and stops; otherwise it publishes its response and either loops with a human response
or auto-completes. `HandoffOrchestration._start` first fans `HandoffStartMessage` to ALL members
via `asyncio.gather` (so every actor has context), then sends the first request to
`members[0]`. `_validate_handoffs` rejects empty handoffs, non-member names, and self-handoffs.
**Invariant:** The model chooses handoffs through the normal tool-call channel — no separate
router model — but a handoff call terminates the agent's tool loop immediately (terminate
filter), and the recorded target is consumed exactly once (reset to None after publishing).
Actor kernels are clones: the test asserts the agents' own kernels stay plugin-free. The first
member in the list is the entry agent.
**Probe:** `python/tests/unit/agents/orchestration/test_handoff.py::test_invoke_with_handoff_function_call` (line 612 — `mock_handoff_to_agent.call_count == 1` with target name; `len(agent_a.kernel.plugins) == 0` proves the clone), `test_response_callback_with_handoff_function_call` (502), `test_init_with_invalid_handoff` (188), `test_invoke_cancel_before_completion` (646), `test_invoke_with_human_response_function` (569).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "HandoffAgentActor _add_handoff_functions transfer_to _handoff_function_filter terminate HandoffRequestMessage", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: handoffs-as-tools with a terminate-on-handoff auto-invoke filter, the cloned-kernel actor
isolation, and the start-fan-before-first-request ordering. Adapt the pub-sub transport (topics,
subscriptions, actor ids) to your runtime. Omit the human-in-the-loop branch if your port has no
human response function.
