<!-- capsule-v2 -->
# ChatMessage value plane — what does the message dataclass guarantee on construction and round-trip?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `smolagents`. **Question:** How do tool calls from heterogeneous providers become one shape at construction, how do string roles re-type on `from_dict`, and which serialization drops `raw`?

## Coerce-on-construct, re-type-on-load, strip-raw-on-wire
**Path/Symbol:** `src/smolagents/models.py` — `ChatMessage` (:123-169), `_coerce_tool_call` (:172-190), `MessageRole` (:111-120), `ChatMessageToolCall(Function)` (:95-108); helper `get_dict_from_nested_dataclasses` (:70-76).
**Signature:** `from_dict(cls, data: dict, raw=None, token_usage=None) -> ChatMessage`; `model_dump_json(self) -> str`; `render_as_markdown(self) -> str`.
**Data Shape:** role: MessageRole (str-Enum; internal values include "tool-call"/"tool-response"); content: str | list[dict]; tool_calls: list[ChatMessageToolCall] | None.

### Decisive source
```python
# :131-134 + :176-190 — construction-time normalization:
def __post_init__(self):
    if self.tool_calls is None: return
    self.tool_calls = [_coerce_tool_call(tc) for tc in self.tool_calls]
# _coerce ladder: ChatMessageToolCall passthrough → dict → .model_dump() → .dict() → rebuild
return ChatMessageToolCall(
    function=ChatMessageToolCallFunction(arguments=d["function"]["arguments"], name=d["function"]["name"]),
    id=d["id"], type=d["type"])
# :137 — wire JSON drops raw:
def model_dump_json(self): return json.dumps(get_dict_from_nested_dataclasses(self, ignore_key="raw"))
```

**Flow:** Any provider payload (OpenAI dict, pydantic object, dataclass) assigned as tool_calls is normalized in `__post_init__` before anyone reads it. `from_dict` accepts a plain dict from disk/network, re-types `data["role"]` through `MessageRole(...)` (works for both `"user"` strings and enum instances because it's a str-Enum), rebuilds tool-call dataclasses, and reattaches raw/token_usage out-of-band. `dict()` (step-dict path) keeps raw; `model_dump_json()` (wire path) removes it. `render_as_markdown` appends each tool call as one JSON line.
**Invariant:** After construction, `message.tool_calls[i]` is ALWAYS a ChatMessageToolCall dataclass — consumers never defend against foreign shapes. Round-trip asymmetry is deliberate: raw stays in memory/step dicts for debugging but never crosses the wire where arbitrary SDK objects can't serialize.
**Probe:** `tests/test_models.py::test_chatmessage_has_model_dumps_json` (:225-228, content round-trips through model_dump_json); `::test_chatmessage_from_dict_role_conversion` (:230-244, str→enum AND enum→enum role inputs both yield MessageRole members). Live: `ChatMessage(role=..., tool_calls=[{"id":"1","type":"function","function":{"name":"f","arguments":{}}}])` → isinstance check passes without manual conversion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "smolagents", query: "ChatMessage from_dict model_dump_json coerce tool call MessageRole render markdown", limit: 8, fields: ["signature", "lines"] });
```
Executed at pin: render_as_markdown :160-169, _coerce_tool_call :172-190, model_dump_json :136-137, test_chatmessage_from_dict_role_conversion :230-244, from_dict :140-155 all top-5.

## Verdict
Adopt normalize-at-the-door (constructor coercion) + re-type-at-load (`from_dict`) so every downstream consumer sees canonical shapes. Adapt the role vocabulary to your provider via conversions (see model-message-cleaning). Omit `raw` from any serialized payload you hand to another process — keep it memory-side only.
