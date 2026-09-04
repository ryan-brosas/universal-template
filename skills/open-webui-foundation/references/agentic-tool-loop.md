<!-- capsule-v2 -->
# Agentic tool-call loop — how do streamed tool calls become a bounded agent loop whose display state stays aligned with the provider stream?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition; citations-only) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When the model streams tool calls, how do I execute them, feed results back for another completion round, and cap the loop without corrupting the OR-style output list shown to users?

## Agentic while-loop over queued tool-call batches
**Path/Symbol:** `backend/open_webui/utils/middleware.py:streaming_chat_response_handler` (loop body 4891-5323; argument hygiene `_split_tool_calls` 230-283).
**Signature:** `while tool_calls and (max_tool_call_iterations is None or tool_call_iterations < max_tool_call_iterations): ...` inside `async def streaming_chat_response_handler(response, ctx)`.
**Data Shape:** `tool_calls: list[list[dict]]` FIFO of batches (one per streamed response); each call `{id, function:{name, arguments:str}}`. Display state is an OR-style `output` list of items (`message` | `reasoning` | `function_call` | `function_call_output` | `open_webui:code_interpreter`) plus `prior_output` prefix and `full_output() = prior_output + output`.

### Decisive source
```python
res = await generate_chat_completion(
    request,
    new_form_data,
    user,
    bypass_system_prompt=True,
)

if isinstance(res, StreamingResponse):
    # Save accumulated output and start fresh.
    # Responses API output_index values are relative
    # to the current response — a clean output list
    # keeps indices aligned. The display prefix
    # ensures the UI shows tool history during
    # streaming.
    prior_output = list(output)
    # Trim the trailing empty placeholder message
    # so it doesn't persist as a ghost item once
    # the new stream produces real content.
    ...
    output = []
    await stream_body_handler(res, new_form_data)
    output[:0] = prior_output
    prior_output = []
else:
    break
```
(middleware.py 5278-5309)

**Flow:** stream → collect delta tool_calls by index (arguments string-concatenated) → `_split_tool_calls` expands concatenated JSON objects (`'{"query":"A"}{"query":"B"}'` via `json.JSONDecoder().raw_decode` position walk; decode failure returns `[raw]`; clones get fresh `call_<uuid4 hex>` ids) → queue batch → while-loop iteration: append `function_call` items for unseen call_ids → `parse_tool_params` (JSONCodec.loads → `ast.literal_eval` fallback → `None` sentinel ⇒ explicit malformed-JSON error string returned to the model) → execute (`params` filtered to spec `parameters.properties` keys; direct tools via `event_caller({'type':'execute:tool',...})` to the browser session, server tools via `get_updated_tool_function(...)`) → `process_tool_result` normalizes result/files/embeds → mark `function_call` completed, append `function_call_output` items (`input_text` parts; data-URI images become LLM-only `input_image` parts stripped from the frontend copy), append fresh empty `message` item → restore pre-RAG original user/system messages before re-applying accumulated citation sources (prevents RAG-template duplication) → continuation request above → next `stream_body_handler` pass reuses the same SSE consumer. Iteration cap from `request.state.max_tool_call_iterations` else env default (env.py 1009-1024: `CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS` default 256, legacy fallback name `CHAT_RESPONSE_MAX_TOOL_CALL_RETRIES` accepted at 1011, `''`→256, int-parse failure→256, `-1`→None/unlimited); exceeding it emits `'Tool-call limit reached (N iterations).'`.
**Invariant:** Ordinary tool calls run sequentially in model order; only `delegate_task` calls fan out concurrently (`await asyncio.gather(*(...))`, middleware.py 5009-5023). Tool exceptions never escape `execute_tool_call` — they become `str(e)` results. After every iteration `output` ends with exactly one in-progress placeholder message; before resplicing, a trailing empty placeholder is trimmed so no ghost item persists. On continuation failure: `emit_message_error(error_content)` then `break` — the loop never half-executes silently.
**Probe:** no upstream tests exist at this pin (zero test files repo-wide — recorded block). Deterministic anchors: `grep -n "output\[:0\] = prior_output" backend/open_webui/utils/middleware.py` → line 5306; `grep -n "delegate_calls = \[" backend/open_webui/utils/middleware.py` → line 5009; `sed -n '1014,1015p' backend/open_webui/env.py` prints `CHAT_RESPONSE_MAX_TOOL_CALL_ITERATIONS = 256`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "_split_tool_calls expand concatenated JSON arguments", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the batch-FIFO loop shape: parse→execute→OR-item bookkeeping→continuation with `prior_output` splice and per-response index reset, plus the None-sentinel malformed-args feedback instead of raising. Adopt sequential-except-delegate execution and spec-key param filtering. Adapt `generate_chat_completion`/`event_caller` to your host transport (they are open-webui's router dispatcher and socket RPC). Omit product specifics (builtin citation-source name list, `ENABLE_RESPONSES_API_STATEFUL` branch keeping only `[system] + converted output` when stateful). Coverage caveat: middleware.py is graph-clean but this ~1900-line handler has no upstream test; claims are pinned by direct source reads at lines cited above.
