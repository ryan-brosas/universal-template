<!-- capsule-v2 -->
# run loop — How does Swarm drive the agent↔tool-call loop and what exactly does a "turn" cover?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** When porting the minimal agent loop, what is one turn, when does it stop, and which objects mutate per turn vs. get copied at entry?

## Turn = one model completion, not one tool batch
**Path/Symbol:** `swarm/core.py:Swarm.run` (231-292).
**Signature:** `run(self, agent: Agent, messages: List, context_variables: dict = {}, model_override: str = None, stream: bool = False, debug: bool = False, max_turns: int = float("inf"), execute_tools: bool = True) -> Response`.
**Data Shape:** `messages` is plain dicts (user/assistant/tool); `context_variables` a free-form dict; returns `Response(messages, agent, context_variables)`.

### Decisive source
```python
active_agent = agent
context_variables = copy.deepcopy(context_variables)
history = copy.deepcopy(messages)
init_len = len(messages)

while len(history) - init_len < max_turns and active_agent:
    completion = self.get_chat_completion(
        agent=active_agent,
        history=history,
        context_variables=context_variables,
        model_override=model_override,
        stream=stream,
        debug=debug,
    )
    message = completion.choices[0].message
    message.sender = active_agent.name
    history.append(
        json.loads(message.model_dump_json())
    )  # to avoid OpenAI types (?)

    if not message.tool_calls or not execute_tools:
        debug_print(debug, "Ending turn.")
        break

    partial_response = self.handle_tool_calls(...)
    history.extend(partial_response.messages)
    context_variables.update(partial_response.context_variables)
    if partial_response.agent:
        active_agent = partial_response.agent

return Response(
    messages=history[init_len:],
    agent=active_agent,
    context_variables=context_variables,
)
```

**Flow:** deepcopy inputs → while `len(history) - init_len < max_turns` → completion for `active_agent` → stamp `message.sender` → append **dict-ified** message to `history` → no tool calls or `execute_tools=False`: break → else execute tools, extend history with tool results, merge context deltas, switch `active_agent` on handoff → return `Response` sliced `history[init_len:]`.
**Invariant:** The caller's `messages` list and `context_variables` dict are never mutated — all work happens on deep copies; the returned `Response.messages` contains only NEW messages (slice from `init_len`). A "turn" counts every appended message (assistant AND each tool result), so `max_turns=N` bounds total appended messages, not assistant replies.
**Probe:** `tests/test_core.py:test_execute_tools_false` (`execute_tools=False` returns without executing; last message still carries raw `tool_calls`) plus `test_run_with_simple_message` / `test_tool_call` pinning append order.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "Swarm class run method completion tool calls", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole-file-copy + new-messages-only Response contract and the message-counting max_turns semantics. Adapt the OpenAI SDK call boundary to any chat-completions-shaped client (the loop only needs `.choices[0].message`). Omit `float("inf")` default if your host needs an unattended-run guard — keep an explicit bound instead.
