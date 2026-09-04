<!-- capsule-v2 -->
# repl streaming consumer — How does a UI consume the chunk stream, and what does the reference client loop look like?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** How should a consumer render deltas (sender attribution, tool-call lines, message boundaries) and keep history across REPL iterations?

## The canonical chunk consumer + conversation-carrying demo loop
**Path/Symbol:** `swarm/repl/repl.py:process_and_print_streaming_response` (6-34) and `swarm/repl/repl.py:run_demo_loop` (60-87).
**Signature:** `process_and_print_streaming_response(response) -> Response`; `run_demo_loop(starting_agent, context_variables=None, stream=False, debug=False) -> None`.
**Data Shape:** consumes `run_and_stream`'s chunk vocabulary (`delim`/delta/`response` keys).

### Decisive source
```python
for chunk in response:
    if "sender" in chunk:
        last_sender = chunk["sender"]
    if "content" in chunk and chunk["content"] is not None:
        if not content and last_sender:
            print(f"\033[94m{last_sender}:\033[0m", end=" ", flush=True)
            last_sender = ""
        print(chunk["content"], end="", flush=True)
        content += chunk["content"]
    ...
    if "delim" in chunk and chunk["delim"] == "end" and content:
        print()  # End of response message
        content = ""
    if "response" in chunk:
        return chunk["response"]
```
and the loop that carries state across turns:
```python
messages = []
agent = starting_agent
while True:
    user_input = input("\033[90mUser\033[0m: ")
    messages.append({"role": "user", "content": user_input})
    response = client.run(agent=agent, messages=messages, ...)
    ...
    messages.extend(response.messages)
    agent = response.agent
```

**Flow:** track `last_sender` from delta chunks → print it once when the first content shard arrives → stream content → reset buffer on delim-end → return the terminal `{"response": ...}` envelope. The demo loop EXTENDS its master list with each `Response.messages` (never replaces) and adopts `response.agent`, so the next `run()` sees full history plus the post-handoff agent.
**Invariant:** Because `run()` deep-copies, the caller's list must be extended with returned messages — REPLACING the master list with `response.messages` would drop prior turns (the naive `examples/basic/simple_loop_no_helpers.py` does exactly this and loses history beyond one exchange). Sender is only present on the first shard of each message; consumers must latch it.
**Probe:** No automated test; behavior pinned by usage in every example's main. Cite as source-confirmed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "run_demo_loop", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the consumer contract (latch sender, reset on delim-end, extract terminal response) and extend-don't-replace history accumulation across calls. Adapt printing to your UI framework. Omit ANSI styling; keep the semantics.
