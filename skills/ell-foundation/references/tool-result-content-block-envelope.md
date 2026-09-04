<!-- capsule-v2 -->
# tool result content block envelope — what exact shape does an invoked tool return, per result type?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** What must a tool wrapper return so the framework can both track plain calls and feed vendor APIs?

## dual-mode wrapper return
**Path/Symbol:** `src/ell/lmp/tool.py:wrapper` (:23-78).
**Signature:** `wrapper(*fn_args, _invocation_origin: str = None, _tool_call_id: str = None, **fn_kwargs) -> Tuple[Any, Dict, Dict] | Tuple[ToolResult, Dict, Dict]`.
**Data Shape:** always a 3-tuple `(result, {"tool_kwargs": tool_kwargs}, {})`; the result half is either the raw return or a `ToolResult(tool_call_id, result=[ContentBlock...])`.

### Decisive source
```python
# tool.py:43-58
if isinstance(result, str) and _invocation_origin:
    result = _lstr(result,origin_trace=_invocation_origin)

if _tool_call_id:
    try:
        if isinstance(result, ContentBlock):
            content_results = [result]
        elif isinstance(result, list) and all(isinstance(c, ContentBlock) for c in result):
            content_results = result
        else:
            content_results = [ContentBlock(text=_lstr(json.dumps(result, ensure_ascii=False),origin_trace=_invocation_origin))]
    except TypeError as e:
        raise TypeError(f"Failed to convert tool use result to ContentBlock: {e}. Tools must return json serializable objects. or a list of ContentBlocks.")
    ...
    return ToolResult(tool_call_id=_tool_call_id, result=content_results), _invocation_api_params, {}
else:
    return result, _invocation_api_params, {}
```

**Flow:** string results gain an origin trace only when invoked through an LMP (origin present). With `_tool_call_id`: ContentBlock/list-of-blocks pass through; everything else is JSON-dumped into a text block; `parsed` blocks are downgraded to text with a printed warning (`c.parsed` → `c.text` JSON); `tool_call` inside a result asserts ("Tool call in tool result"), audio asserts. Without `_tool_call_id` (plain Python call) the raw value flows back untouched.
**Invariant:** non-JSON-serializable returns raise TypeError with guidance rather than corrupting the conversation; the 3-tuple shape is unconditional so tracking code can treat tools and LMPs identically.
**Probe:** `tests/test_tools.py:test_tool_json_dumping_behavior` (:7-52) pins all three branches: dict → `[ContentBlock(text='{"key": "value"}')]`, bare string → `json.dumps("Simple string result")`, ContentBlock list passes through unchanged.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "write_lmp IntegrityError", limit: 5, fields: ["signature", "name", "file"] });
// sibling store seam; tool-envelope test anchors resolve via:
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "tool json dumping behavior", limit: 3, fields: ["name", "file"] });
```

## Verdict
Adopt the dual-mode envelope and the parsed→text downgrade warning. Adapt the serialization fallback (JSON dump) to your message format if it is not JSON-wire-based. Omit the `_invocation_origin` trace on direct calls — it exists solely so tracked conversations link tool outputs to their invocation.
