<!-- capsule-v2 -->
# Anthropic system-role extraction — what differs in calling Anthropic beyond the image block?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** How are system prompts and tool definitions shaped for the Anthropic Messages API inside the same agent loop?

## System join + tool_use block scan + max_tokens injection
**Path/Symbol:** `os_computer_use/llm_provider.py:201-227` (`AnthropicBaseProvider.call`), `:180-189` (`create_function_def` → `input_schema`).
**Signature:** `call(messages, functions) -> (text, [tool_call]) | text`.
**Data Shape:** System roles are JOINED with `"\n"` into one top-level `system` string; tool defs use `input_schema` (NOT OpenAI's nested `function.parameters`); every call injects `max_tokens=4096` because Anthropic requires it.

### Decisive source
```python
system = "\n".join(msg.get("content") for msg in messages if msg.get("role") == "system")
messages = [msg for msg in messages if msg.get("role") != "system"]
completion = self.completion(messages, system=system, tools=tools, max_tokens=4096)
text = "".join(getattr(block, "text", "") for block in completion.content)
if functions:
    tool_calls = [self.create_tool_call(block.name, block.input)
                  for block in completion.content
                  if block.type == "tool_use"]
    return text, tool_calls
```

**Flow:** hoist ALL system messages out of the array (joined, not first-wins) → strip them from messages → completion with `system=` kwarg + mandatory max_tokens → response scanned once: text blocks concatenated via `getattr(block,"text","")`, tool_use blocks mapped to canonical `{type:"function", name, parameters}` shape.
**Invariant:** The canonical internal tool-call shape (`create_tool_call`) is produced identically by both provider families, so `sandbox_agent.run()` never branches on vendor; text extraction tolerates mixed content arrays by ignoring non-text blocks rather than raising.
**Probe:** `cd $REFERENCE_ROOT/external/open-computer-use && grep -n 'max_tokens=4096' os_computer_use/llm_provider.py && grep -n 'input_schema' os_computer_use/llm_provider.py` (pins the mandatory kwarg at :212 and schema key at :184).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "AnthropicBaseProvider system tool_use input_schema max_tokens", limit: 6, fields: ["signature", "name", "file"] });
// expect AnthropicBaseProvider.call + create_function_def
```

## Verdict
Adopt system-hoisting + canonical-tool-call normalization for dual-vendor loops; adapt max_tokens to your model limits (hardcoded here); omit the getattr-join only if you need ordered multi-block text fidelity.
