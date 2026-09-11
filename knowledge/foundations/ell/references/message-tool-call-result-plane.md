<!-- capsule-v2 -->
# message tool-call result plane — how do tool calls ride inside messages and get executed into follow-ups?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** What is the exact object choreography between a model's tool_call and the tool-result message I append for the next turn?

## ToolCall execution + collection
**Path/Symbol:** `src/ell/types/message.py:ToolCall` (:43-71), `Message.call_tools_and_collect_as_message` (:416-423), helpers `_content_to_text`/`_content_to_text_only` (:505-519).
**Signature:** `ToolCall.__init__(self, tool, params: Union[BaseModel, Dict[str, Any]], tool_call_id=None)`; `ToolCall.__call__(self, **kwargs)`; `call_tools_and_collect_as_message(self, parallel=False, max_workers=None) -> Message`.
**Data Shape:** ToolCall binds the invocable + a pydantic params instance (dicts coerced through `tool.__ell_params_model__`); results collect into `Message(role="user", content=[ContentBlock(tool_result=...), ...])`.

### Decisive source
```python
# message.py:53-57
def __call__(self, **kwargs):
    assert not kwargs, "Unexpected arguments provided. Calling a tool uses the params provided in the ToolCall."

    # XXX: TODO: MOVE TRACKING CODE TO _TRACK AND OUT OF HERE AND API.
    return self.tool(**self.params.model_dump())
```

**Flow:** model returns assistant Message containing tool_call blocks → caller inspects `.tool_calls`, invokes each (`call_and_collect_as_content_block` passes `_tool_call_id` so the wrapper returns a ToolResult envelope) → collected blocks become a user-role Message appended to history. Text projections: `.text` replaces non-text with reprs; `.text_only` skips them — both built by joining with an `_lstr("\n")` joiner so provenance propagates through the projection itself.
**Invariant:** call-time arguments are forbidden — parameters are frozen on the ToolCall at creation (they came from the model); this keeps replay/audit honest. Parallel mode preserves completion-order, not call-order.
**Probe:** `tests/test_message_type.py:test_content_block_coerce_tool_result` (:34-39) pins ToolResult→block coercion; `tests/test_openai_provider.py:test_translate_to_provider_with_list_tool_response` (:244-267) pins that multi-block tool results flatten to `"Banana\nApple\nOrange"` text on the wire.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "message tool calls assistant", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.types.message.Message.tool_calls @ src/ell/types/message.py:378-387
```

## Verdict
Adopt the frozen-params ToolCall + collect-as-user-message loop verbatim; it is provider-neutral. Adapt role naming if your target API differs from openai-style user/tool roles. Omit the ThreadPoolExecutor branch if your tools are strictly sequential-safe — but keep the assert, it is what prevents silent param injection.
