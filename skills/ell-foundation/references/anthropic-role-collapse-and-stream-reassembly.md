<!-- capsule-v2 -->
# anthropic role collapse and stream reassembly — how are alternating roles collapsed and streamed blocks reassembled?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I map openai-style free-role message lists onto an API that requires strict alternation and a top-level system param?

## role merge + block reassembly
**Path/Symbol:** `src/ell/providers/anthropic.py:AnthropicProvider.translate_to_provider` (:28-66) + `translate_from_provider` (:69-155).
**Signature:** `translate_to_provider(self, ell_call: EllCallParams) -> MessageCreateParamsStreaming`.
**Data Shape:** wire form is `{role: "user"|"assistant", content: [blocks...]}` with system extracted; stream state is `current_blocks: Dict[int, Dict[str, Any]]`.

### Decisive source
```python
# anthropic.py:38-48
role_correct_msgs   : List[MessageParam] = []
for msg in dirty_msgs:
    if (not len(role_correct_msgs) or role_correct_msgs[-1]['role'] != msg['role']):
        role_correct_msgs.append(msg)
    else: cast(List, role_correct_msgs[-1]['content']).extend(msg['content'])

system_message = None
if role_correct_msgs and role_correct_msgs[0]["role"] == "system":
    system_message = role_correct_msgs.pop(0)

if system_message:
    final_call_params["system"] = system_message["content"][0]["text"]
```

```python
# anthropic.py:96-99 — partial JSON tool args accumulate as strings
elif chunk.type == "content_block_delta":
    if chunk.index in current_blocks:
        block = current_blocks[chunk.index]
        if (delta := chunk.delta).type == "text_delta":
            block["text"] += delta.text
        if delta.type == "input_json_delta":
            block["input"] += delta.partial_json
```

**Flow:** consecutive same-role messages merge by extending content (never creating new entries); only a leading system message is popped into the `system` param. Streaming walks typed events: `message_start` snapshots metadata (minus content), `content_block_start` registers blocks by index (tool_use inputs initialized to `""`), deltas append text/partial-json, `content_block_stop` finalizes — text becomes `_lstr(..., origin_trace=origin_id)`, tool_use resolves the named tool and `json.loads` the accumulated input, with JSONDecodeError swallowed behind an optional logger (partial args → tool dropped, not crash). Usage normalization maps anthropic `input_tokens/output_tokens` onto ell's `prompt_tokens/completion_tokens`.
**Invariant:** strict alternation must be achieved by merging, never by dropping messages; and every emitted text/tool id carries the origin trace or the provider-lifecycle assert fires.
**Probe:** `tests/test_openai_provider.py` covers the shared lifecycle; for this capsule's translation logic there is no direct test at pin — coverage caveat recorded honestly (anthropic module guarded by ImportError, exercised only via integration). Deterministic anchor: `grep -c 'content_block_stop\|content_block_start\|input_json_delta' src/ell/providers/anthropic.py` == 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "system prompt docstring", limit: 5, fields: ["signature", "name", "file"] });
// adjacent seam; the anthropic translator itself is best reached via:
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "disallowed api params", limit: 5, fields: ["signature", "name", "file"] });
// rank-2 shows the google twin overriding the same contract @ src/ell/providers/google.py:36-37
```

## Verdict
Adopt role-collapse-by-extension and index-keyed stream reassembly for any alternating-turn API. Adapt event type names to your vendor's protocol. Omit the swallow-on-bad-JSON only if you can fail loudly instead — ell chose resilience because a mid-stream parse failure should not destroy the whole conversation.
