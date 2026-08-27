<!-- capsule-v2 -->
# Model-client stream contract — how does token streaming fold into ONE authoritative result with honest usage?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** What exactly does a streaming completion yield, and which yield carries the truth the agent acts on?

## Chunks are cosmetic; the terminal CreateResult is authoritative; missing terminal fails loud
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/models/_model_client.py` (`ChatCompletionClient.create_stream` :242–269, protocol contract); consumption `python/packages/autogen-agentchat/src/autogen_agentchat/agents/_assistant_agent.py` `_call_llm` :1056–1115.
**Signature:** `def create_stream(self, messages, *, tools=[], tool_choice="auto", json_output=None, extra_create_args={}, cancellation_token=None) -> AsyncGenerator[Union[str, CreateResult], None]`.
**Data Shape:** yields `str` content chunks in order, then EXACTLY ONE terminal `CreateResult` (whose `content` may be a str OR a `List[FunctionCall]`). Chunks carry no usage/metadata; only the CreateResult does.

### Decisive source
```python
# _call_llm streaming arm: capture-don't-yield the terminal; chunk typing is closed
if model_client_stream:
    model_result: Optional[CreateResult] = None
    async for chunk in model_client.create_stream(llm_messages, tools=tools,
                                                  json_output=output_content_type,
                                                  cancellation_token=cancellation_token):
        if isinstance(chunk, CreateResult):
            model_result = chunk          # captured, NOT yielded inline
        elif isinstance(chunk, str):
            yield ModelClientStreamingChunkEvent(content=chunk, source=agent_name, full_message_id=message_id)
        else:
            raise RuntimeError(f"Invalid chunk type: {type(chunk)}")
    if model_result is None:
        raise RuntimeError("No final model result in streaming mode.")
    yield model_result                    # single terminal yield AFTER the loop
```

**Flow:** tools gathered across ALL workbenches plus handoff_tools first (:1088) → `create_stream(...)` → each str chunk becomes an observable `ModelClientStreamingChunkEvent` while inference is still running → terminal CreateResult held back and yielded once, AFTER the generator exhausts → downstream `_process_model_result` sees ONLY the CreateResult (tool-call dispatch, reflection, usage accounting all read it).
**Invariant:** consumers must treat chunks as display-only and gate all decisions on the terminal result; a stream that ends without one is a CONTRACT VIOLATION raised as RuntimeError, as is any foreign chunk type. Joined chunks equal the terminal text by convention (`"".join(chunks) == final.content`) but nothing enforces it client-side — providers own that honesty. Non-streaming mode collapses to a bare `create()` yielding one item.
**Probe:** `python/packages/autogen-agentchat/tests/test_assistant_agent.py::test_model_client_stream` (:189–207 — joined chunks == TaskResult's final TextMessage) and `::test_model_client_stream_with_tool_calls` (:211–251 — tool-call CreateResult arrives WITHOUT preceding chunks; only the later reflection turn streams).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "autogen", query: "create_stream ChatCompletionClient stream chunks CreateResult usage accumulation ModelClientStreamingChunkEvent", limit: 15 });
```

## Verdict
Adopt chunk-cosmetic/terminal-authoritative streaming with fail-loud missing-terminal detection for any LLM client abstraction. Adapt chunk event shape to your UI bus (full_message_id correlation is worth keeping). Omit the closed-typing RuntimeError if your host forwards provider-specific chunk kinds deliberately.
