<!-- capsule-v2 -->
# Stream-delta stitching — how do chunked provider events become one ChatMessage with tool calls and token totals?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What are the accumulation rules in `agglomerate_stream_deltas` for content, index-keyed tool-call fragments, and usage, and which input shape is illegal?

## Index-keyed reassembly
**Path/Symbol:** `src/smolagents/models.py:agglomerate_stream_deltas` (:220-279); producers `LiteLLMModel.generate_stream` (:1309-1360), `InferenceClientModel.generate_stream` (:1591-1643), `OpenAIModel.generate_stream` (:1707-1759), `TransformersModel.generate_stream` (:1093-1135).
**Signature:** `agglomerate_stream_deltas(stream_deltas: list[ChatMessageStreamDelta], role=MessageRole.ASSISTANT) -> ChatMessage`.
**Data Shape:** Input deltas carry `content: str|None`, `tool_calls: list[ChatMessageToolCallStreamDelta{index,id,type,function{name,arguments}}]`, `token_usage`. Output ChatMessage has full content string, complete `ChatMessageToolCall`s (arguments as ONE concatenated string), summed TokenUsage.

### Decisive source
```python
# :236-258 — fragments accumulate per index; missing index is a hard protocol error:
if tool_call_delta.index is not None:
    if tool_call_delta.index not in accumulated_tool_calls:
        accumulated_tool_calls[tool_call_delta.index] = ChatMessageToolCallStreamDelta(
            id=tool_call_delta.id, type=tool_call_delta.type,
            function=ChatMessageToolCallFunction(name="", arguments=""))
    ...
    if tool_call_delta.function.name and len(...) > 0:
        tool_call.function.name = tool_call_delta.function.name      # name REPLACES (sent whole once)
    if tool_call_delta.function.arguments:
        tool_call.function.arguments += tool_call_delta.function.arguments  # args CONCATENATE (streamed shards)
else:
    raise ValueError(f"Tool call index is not provided in tool delta: {tool_call_delta}")
```

**Flow:** Producers yield three event kinds interleaved: usage-only deltas (`content=""`, from `stream_options={"include_usage": True}`), content deltas, and tool-call shard deltas. The agglomerator concatenates ALL non-empty contents; shards merge by `index` — id/type overwrite when present, name replaces only on a non-empty value, arguments append. TokenUsage is SUMMED across deltas because providers emit usage once at stream end while transformers' TextIteratorStreamer path instead puts the prompt count on the FIRST token's delta (:1119-1131). Downstream, `parse_tool_calls` json-parses the concatenated argument string lazily (`parse_json_if_needed`).
**Invariant:** name-replace + arguments-concatenate asymmetry mirrors how OpenAI-family streams actually fragment calls; treating the name like another append produces `"getget_weather"`-class corruption. A delta with tool_calls but no index cannot be assigned to any call slot and must fail loudly rather than guess.
**Probe:** `tests/test_models.py::TestAgglomerateStreamDeltas.test_agglomerate_stream_deltas` (:80-139, asserts exact content, first argument fragment, total_tokens==1372). Live: replay a two-shard indexed sequence → single call with concatenated args.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "agglomerate_stream_deltas accumulated_tool_calls token_usage", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the index-keyed accumulator with its strict no-index error. Adapt usage accounting to your provider (end-frame vs first-token conventions). Omit nothing from the empty-name guard or multi-call streams will misname tools.
