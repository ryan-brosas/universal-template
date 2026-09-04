<!-- capsule-v2 -->
# Mistral prefix-continuation shim — how does an assistant-prefix message become a single user turn?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** How does the agent satisfy Mistral's constraint that a conversation cannot END on an assistant message?

## Pre-call merge of trailing assistant content into the last user turn
**Path/Symbol:** `os_computer_use/llm_provider.py:237-246` (`MistralBaseProvider.call`), `:230-235` (`create_function_def` dict-description unwrap).
**Signature:** `call(messages, functions)` — MUTATES the caller's list (`messages.pop()`).
**Data Shape:** Input history may end `[…, user, assistant(prefix)]`; after the shim it ends `[…, user(prefix + "\n" + text)]` — or gains a NEW user turn if no prior user message exists.

### Decisive source
```python
def call(self, messages, functions=None):
    if messages and messages[-1].get("role") == "assistant":
        prefix = messages.pop()["content"]
        if messages and messages[-1].get("role") == "user":
            messages[-1]["content"] = prefix + "\n" + messages[-1].get("content", "")
        else:
            messages.append({"role": "user", "content": prefix})
    return super().call(messages, functions)
```

**Flow:** detect trailing assistant turn → pop it → if a user turn precedes, PREPEND the prefix onto it (thought-before-instruction ordering) → else synthesize a user turn → delegate to OpenAI-compatible call path.
**Invariant:** This is why the agent loop can append `THOUGHT:` as an assistant message universally: Mistral-family vendors reject trailing-assistant payloads and this subclass is the ONLY place that repairs them. The mutation is destructive — the caller's history object loses its final assistant entry (safe here because run() rebuilds the thought each turn; a porter who reuses histories across providers must copy first). The sibling `create_function_def` override also unwraps `{"description": {...}}` dicts to inner strings before schema-building.
**Probe:** `cd /mnt/hdd/utopia/inspo/external/open-computer-use && sed -n '237,246p' os_computer_use/llm_provider.py && grep -n 'messages.pop()' os_computer_use/llm_provider.py` (pins the pop-mutation at :239).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "MistralBaseProvider call prefix assistant pop", limit: 5, fields: ["signature", "name", "file"] });
// expect MistralBaseProvider.call (llm_provider.py 237-246)
```

## Verdict
Adopt the trailing-assistant repair for any vendor with continuation-style chat APIs (Mistral, some OSS servers); adapt to non-destructive copying if your history objects are shared across providers; omit when all vendors accept trailing assistant turns.
