<!-- capsule-v2 -->
# Provider tool-call normalization — how do five LLM provider shapes collapse into one (call_id, name, args) tuple?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** How is a raw tool call recognized and decoded regardless of provider, and which id/args fields must be preferred to keep results correlatable?

## extract_tool_call_info / is_tool_call_list / parse_tool_call_args
**Path/Symbol:** `lib/crewai/src/crewai/utilities/agent_utils.py:1366-1421` (`extract_tool_call_info`), `:1424-1464` (`is_tool_call_list`), `:1882-1918` (`parse_tool_call_args`); streaming twin `utilities/streaming.py:79-103`.
**Signature:** `def extract_tool_call_info(tool_call) -> tuple[str, str, dict | str] | None`; `def is_tool_call_list(response: list) -> bool`.
**Data Shape:** Returns `(call_id, sanitized_func_name, func_args)` or None for unrecognized shapes. Names ALWAYS pass through `sanitize_tool_name` (Unicode-normalize, camelCase split, lowercase, invalid chars → `_`, truncate 64 — OpenAI/Bedrock limits).

### Decisive source
```python
if hasattr(tool_call, "function"):            # OpenAI-style object
    ...
if hasattr(tool_call, "name") and hasattr(tool_call, "input"):  # Anthropic ToolUseBlock
    ...
if isinstance(tool_call, dict):
    # "Prefer the Responses API 'call_id', then OpenAI 'id', then Bedrock
    #  'toolUseId', else generate one. A raw Responses function_call item carries
    #  BOTH 'id' (fc_...) and 'call_id' (call_...) with different values, and the
    #  matching function_call_output must reference 'call_id' -- reading 'id'
    #  would produce a tool result that can't be correlated to its invocation."
    call_id = (tool_call.get("call_id") or tool_call.get("id")
               or tool_call.get("toolUseId") or f"call_{id(tool_call)}")
    func_info = tool_call.get("function", {})
    func_name = func_info.get("name", "") or tool_call.get("name", "")
    # Responses API emits {"id","name","arguments"} with NO nested "function";
    # without the top-level fallbacks "the args silently resolved to {}"
    func_args = (func_info.get("arguments") or tool_call.get("arguments")
                 or tool_call.get("input") or {})
```

**Flow:** LLM returns either text (ReAct parse path) or a list → `is_tool_call_list` classifies by FIRST element shape across OpenAI (`function`), Anthropic (`type=="tool_use"` or `.name/.input`), Bedrock dict `{name,input}`, Responses dict `{name,arguments}` (deliberately broad — only lists reach it), Gemini (`.function_call`) → executor stores as `pending_tool_calls` → per-call extraction → JSON-string args decoded by `parse_tool_call_args`, which on failure returns a ready-to-return error dict carrying an INVALID_INPUT ToolFailure (code `json_decode_error`) instead of silently running with empty args.
**Invariant:** The id precedence order is not stylistic — swapping `call_id`/`id` breaks result correlation on OpenAI Responses API where both exist with DIFFERENT values. Gemini calls have NO stable id, hence the deterministic `call_{id(obj)}` fallback. Every branch sanitizes the name identically so schema keys, cache keys, and event names all agree.
**Probe:** `grep -c 'call_id' lib/crewai/src/crewai/utilities/agent_utils.py` → ≥10 occurrences; classification pinned indirectly via `TestNativeToolExecution` tests feeding OpenAI-style dicts. (No dedicated unit file for extract_tool_call_info at this pin — behavior verified through the native execution tests.)
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "extract_tool_call_info is_tool_call_list provider formats", limit: 5, detail: "ids" });
```

## Verdict
Adopt the union-of-shapes normalizer with documented id precedence and fail-loud arg decoding; adapt to your provider set (drop Bedrock/Gemini branches you don't serve); omit nothing else — every fallback here closes a real silent-failure bug recorded in its comment.
