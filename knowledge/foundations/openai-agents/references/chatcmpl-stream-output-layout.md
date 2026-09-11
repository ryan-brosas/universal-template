<!-- capsule-v2 -->
# ChatCompletions stream output layout — how do chunk-stream events get stable, gap-free output_index slots when text and tool calls interleave?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** Given chat-completions chunks arriving in arbitrary order across choices, how is each item's stream `output_index` assigned once and never renumbered?

## Lazily memoized slot allocation
**Path/Symbol:** `src/agents/models/chatcmpl_stream_handler.py:` `_StreamOutputLayout` (:196–267: `assistant_message_output_index`, `function_call_output_index`, `function_calls_before_message/_after_message`), accumulation `_accumulate_tool_call_delta` (:309–339), buffering gate `_should_buffer_tool_call_delta`/`buffer_tool_call_stream` (:276–278, :391–461); usage tail `_build_response_usage` (:1353–1373).
**Signature:** `function_call_output_index(self, state, function_call_index: int) -> int`; `assistant_message_output_index(self, state) -> int`.
**Data Shape:** `assistant_message_output_idx: int | None` (None until first exposure), `function_call_output_idxs: dict[int,int]` memoization, reasoning slot count = 1 iff a reasoning-content item exists.

### Decisive source
```python
def assistant_message_output_index(self, state):
    if self.assistant_message_output_idx is None:
        output_index = self._reasoning_output_count(state)
        if self.function_call_output_idxs:
            output_index += len(state.function_calls)
        self.assistant_message_output_idx = output_index      # frozen forever after
    return self.assistant_message_output_idx

def function_call_output_index(self, state, function_call_index):
    if function_call_index in self.function_call_output_idxs:
        return self.function_call_output_idxs[function_call_index]
    function_call_offset = list(state.function_calls).index(function_call_index)  # KeyError if untracked
    output_index = self._reasoning_output_count(state)
    if self.assistant_message_output_idx is None:
        output_index += function_call_offset                  # all calls before the message
    else:
        before = self.assistant_message_output_idx - self._reasoning_output_count(state)
        output_index += function_call_offset if function_call_offset < before else function_call_offset + 1
    self.function_call_output_idxs[function_call_index] = output_index
    return output_index
```

**Flow:** reasoning content owns slot 0 when present → tool-call deltas accumulate per `delta.index` into `_BufferedToolCall` (id/name overwrite-latest, arguments string-concatenated, provider_specific_fields/extra_content deep-merged) → slots assign lazily at FIRST emission of each item: calls before the assistant message take consecutive indices, the message takes the next slot (calls-after shift +1 to leave its slot free even though it arrives earlier in choice order) → once exposed, an index is memoized and immutable for the stream's lifetime → usage builds only from the terminal chunk.
**Invariant:** consumers may key dedup/persistence on `(item_type, output_index)`: no slot ever moves, none is reused, and an unknown function-call index fails loud (`KeyError: "Function call index N has not been tracked"`). Buffer mode (`buffer_streamed_tool_calls`) withholds function deltas until the provider stream ends, then emits whole calls through the SAME layout tracker, preserving passthrough non-function deltas immediately.
**Probe:** `tests/models/test_openai_chatcompletions_stream.py::test_stream_output_layout_rejects_unknown_function_call_index` (:731), `::test_buffer_tool_call_stream_merges_provider_metadata` (:656), `::test_buffer_tool_call_stream_keeps_passthrough_index_passthrough` (:827).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", name_pattern: "function_call_output_index|OutputIndex", limit: 8 });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "...chatcmpl_stream_handler._StreamOutputLayout.function_call_output_index" });
```

## Verdict
Adopt lazy memoized slot allocation with the message-slot reservation and loud unknown-index failure; adopt index-keyed delta accumulation with metadata merging for any chunk-based provider. Adapt slot semantics to your event vocabulary. Omit thinking-block/reasoning-summary segmentation (provider-specific replay policy) unless porting those providers. Coverage: no_recorded_issue at gen 2026-08-24T14:05:06Z.
