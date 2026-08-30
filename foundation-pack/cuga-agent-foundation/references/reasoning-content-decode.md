<!-- capsule-v2 -->
# Reasoning-content decode — how does a porter keep `reasoning_content` from being silently dropped by LangChain's message conversion?

**Source:** cuga-agent (Apache-2.0) `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** DeepSeek-style / self-hosted reasoning models return `choices[].message.reasoning_content`, but LangChain's `_convert_dict_to_message` only forwards `function_call`/`tool_calls`/`audio` into `additional_kwargs` — so the reasoning trace is silently dropped unless the chat model rescues it. How does cuga preserve it and where is it consumed?

## Reasoning-field rescue at the decode boundary
**Path/Symbol:** `src/cuga/backend/llm/models.py` — `_get_reasoning_chat_openai()` (29-73) returning the lazily-defined inner `ReasoningChatOpenAI(ChatOpenAI)` (43-67); `_get_reasoning_chat_litellm()` (76-119) returning `ReasoningChatLiteLLM(ChatLiteLLM)` (89-108). Consumer: `src/cuga/backend/cuga_graph/nodes/cuga_lite/adapter/graph_adapter.py` `normalize_response` (167-179).
**Signature:** `def _create_chat_result(self, response: "dict | openai.BaseModel", generation_info=None) -> "ChatResult"` (overridden in both subclasses, byte-identical logic).
**Data Shape:** `response` is either a raw dict or an OpenAI BaseModel; `response["choices"][i]["message"]["reasoning_content"]` is the non-standard field. The subclass post-processes the already-built `ChatResult`, writing `reasoning_content` into `generations[i].message.additional_kwargs` via `setdefault` (never overwrites an existing value). Consumer `normalize_response` reads `(response.additional_kwargs or {}).get("reasoning_content")` and runs it through `normalize_assistant_text` alongside the content.

### Decisive source
```python
class ReasoningChatOpenAI(ChatOpenAI):
    def _create_chat_result(self, response, generation_info=None):
        result = super()._create_chat_result(response, generation_info)
        response_dict = response if isinstance(response, dict) else response.model_dump()
        choices = response_dict.get("choices") or []
        for i, res in enumerate(choices):
            if i >= len(result.generations):
                break
            raw_msg = res.get("message") or {}
            reasoning = raw_msg.get("reasoning_content")
            if reasoning and isinstance(result.generations[i].message, AIMessage):
                result.generations[i].message.additional_kwargs.setdefault(
                    "reasoning_content", reasoning)
        return result
```
Both lazy-loaders cache the class on a function attribute (`_cls`) with a double-checked read; the OpenAI variant has no lock because all callers run on the asyncio event loop (no OS threads reach `_create_llm_instance`); the LiteLLM variant additionally guards the import (`ImportError → None`) and flips a `_loaded` flag so a missing `langchain_litellm` is not re-imported every call.

**Flow:** raw response → `super()._create_chat_result` builds the `ChatResult` (dropping reasoning) → subclass re-reads the raw `choices[].message.reasoning_content` → writes into `additional_kwargs` on the matching `AIMessage` → downstream `normalize_response` extracts it (harmony-stripped) and returns `(content, reasoning)` → `on_response_processed` records it as an `Assistant_reasoning` tracker step.
**Invariant:** The rescue is a post-process on the ALREADY-built result keyed by index (`choices[i]` ↔ `generations[i]`), so a reasoning field can never corrupt the content pipeline; `setdefault` means a provider that already populated `additional_kwargs["reasoning_content"]` is never clobbered; only `AIMessage` instances receive the field (tool/function messages are skipped).
**Probe:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/tests/test_agent_graph_adapter.py:173-179` — builds a `SimpleNamespace(content="hi", additional_kwargs={"reasoning_content": "I thought about it"})` and asserts `adapter.normalize_response(response) == ("hi", "I thought about it")`, pinning the consumer contract. `tests/unit/test_llm_minimax_provider.py` confirms MiniMax (OpenAI-compatible) reuses `ReasoningChatOpenAI` with a fixed base URL + `MINIMAX_API_KEY`, but does not directly unit-test `_create_chat_result`'s rescue.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "normalize_response reasoning_content", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the subclass-rescue pattern (post-process `_create_chat_result`, index-matched `setdefault` into `additional_kwargs`) and the `normalize_response` → `(content, reasoning)` split for any reasoning-model backend whose raw completion carries `reasoning_content`; adapt the lazy-loader caching (function-attribute double-check, optional import guard) to your threading model — the lock-free assumption holds ONLY because cuga's callers are single-threaded on the asyncio loop; omit the MiniMax/OpenRouter base-URL wiring unless you mirror those providers. Coverage caveat: the two subclasses are defined INSIDE lazy-loaders, so they are not surfaced as standalone graph nodes (the file is fully indexed, but symbol-level graph search for `ReasoningChatOpenAI` returns nothing) — read `models.py` directly; the direct consumer test covers `normalize_response`, not the rescue itself.
