<!-- capsule-v2 -->
# run_and_stream — How does streaming mode preserve the run loop contract while yielding chunks?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** What does a consumer receive on the wire, and how does the generator still deliver handoffs, context merges, and the final Response?

## Same loop, chunk-shaped surface
**Path/Symbol:** `swarm/core.py:Swarm.run_and_stream` (139-229), dispatched from `Swarm.run` when `stream=True`.
**Signature:** generator yielding dict chunks; final yield is `{"response": Response(...)}`.
**Data Shape:** Chunk vocabulary: `{"delim": "start"|"end"}`, per-delta dicts (role/sender/content/tool_calls), terminal `{"response": ...}`.

### Decisive source
```python
yield {"delim": "start"}
for chunk in completion:
    delta = json.loads(chunk.choices[0].delta.json())
    if delta["role"] == "assistant":
        delta["sender"] = active_agent.name
    yield delta
    delta.pop("role", None)
    delta.pop("sender", None)
    merge_chunk(message, delta)
yield {"delim": "end"}
...
partial_response = self.handle_tool_calls(...)
history.extend(partial_response.messages)
context_variables.update(partial_response.context_variables)
if partial_response.agent:
    active_agent = partial_response.agent
```

**Flow:** per turn: delim-start → yield each delta enriched with `sender = active_agent.name`, then STRIP role/sender before accumulating → delim-end → append merged message → tool execution identical to non-streaming → after the loop exactly one `{"response": Response}` with `history[init_len:]`.
**Invariant:** The accumulation copy must NOT contain role/sender (they're popped pre-merge) — merge_fields would otherwise concatenate them across turns. Consumers get speaker identity ONLY via the transient sender field. Tool execution happens AFTER the full message is assembled, so streamed runs execute tools at the same point as buffered runs; `execute_tools=False` breaks identically.
**Probe:** No unit test drives `run_and_stream`; `swarm/repl/repl.py:process_and_print_streaming_response` is the reference consumer (sender tracking, delim-based line resets, terminal response return). Cite as source-confirmed with test-coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "run_and_stream yields delim response generator", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-part chunk vocabulary (delims / enriched deltas / terminal response envelope) — it keeps one run-loop implementation serving both modes. Adapt delta JSON extraction to your SDK (pydantic `.json()` here). Omit nothing else: this IS the minimal streaming-agent shape most later frameworks re-derived.
