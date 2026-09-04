<!-- capsule-v2 -->
# ChatCompletions param gating & header override — which request params default ON only for the official endpoint, and how does a global header override beat per-call settings?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When one ChatCompletions adapter serves both api.openai.com and arbitrary third-party backends, how do you default provider-specific params (`store`, `stream_options.include_usage`) without breaking non-OpenAI backends, and how do you give a process-wide header escape hatch that still loses to nothing but stays async-safe?

## is_openai base_url gate + explicit→default param ladders + ContextVar header precedence
**Path/Symbol:** `src/agents/models/chatcmpl_helpers.py:` `HEADERS` (:35), `HEADERS_OVERRIDE` (:37–38), `ChatCmplHelpers.is_openai` (:43–46), `get_store_param` (:48–51), `get_stream_options_param` (:54–67); `src/agents/models/openai_client_utils.py:` `is_official_openai_base_url` (:8–13), `is_official_openai_client` (:14–20); consumers `src/agents/models/openai_chatcompletions.py` call sites (:703–706) + `create_kwargs` Omit mapping (:710–735) + `_merge_headers` (:804–809); twin merges `src/agents/extensions/models/litellm_model.py:_merge_headers` (:890–891), `src/agents/extensions/models/any_llm_model.py:_merge_headers` (:1507–1513).
**Signature:** `get_store_param(client, model_settings) -> bool | None`; `get_stream_options_param(client, model_settings, stream: bool) -> dict[str, bool] | None`; `is_official_openai_base_url(base_url, *, websocket: bool = False) -> bool`.
**Data Shape:** `None` return means "omit the key entirely" (mapped through `_non_null_or_omit` into `Omit` in `create_kwargs`); `HEADERS_OVERRIDE` is a `ContextVar[dict[str, str] | None]` defaulting to None; base_url gate = scheme `https` (or `wss` for websocket) AND hostname exactly `api.openai.com`.

### Decisive source
```python
# get_store_param: explicit setting wins; default True ONLY for the official endpoint
default_store = True if cls.is_openai(client) else None
return model_settings.store if model_settings.store is not None else default_store

# openai_chatcompletions._merge_headers: override merged LAST = highest precedence
return {
    **HEADERS,                                  # User-Agent: Agents/Python <version>
    **(model_settings.extra_headers or {}),
    **(HEADERS_OVERRIDE.get() or {}),
}
```

**Flow:** every request builds `create_kwargs` where each nullable param passes through `_non_null_or_omit` → `store` resolves explicit `ModelSettings.store`, else True for an official-OpenAI client, else None (omitted); `stream_options` is None unless streaming, and inside it `include_usage` follows the same explicit→(True if OpenAI else None) ladder, producing `{"include_usage": bool}` only when resolved non-None → headers merge in fixed order across all three adapters (openai_chatcompletions, litellm, any_llm): static `HEADERS` first, per-call `model_settings.extra_headers` second, `HEADERS_OVERRIDE.get()` last so the contextvar wins every key collision (any_llm additionally drops non-string values while merging).
**Invariant:** third-party backends never receive params they may reject — the default is omission (None→Omit), never `False`; the official-endpoint detection is hostname-exact (a proxy at another host gets no OpenAI-only defaults even if it forwards to OpenAI); header precedence is total and identical across adapters: override > extra_headers > SDK User-Agent.
**Probe:** `tests/models/test_openai_chatcompletions.py::test_store_param` (:1450 — default True for `AsyncOpenAI()`, explicit False/True respected); non-OpenAI default None asserted at the tail of `::test_user_agent_header_chat_completions` (:1589; `AsyncOpenAI(base_url="http://www.notopenai.com")` → `get_store_param(...) is None`, :1638–1651); same test's `HEADERS_OVERRIDE.set({"User-Agent": ...})` block (:1616) reaches `extra_headers["User-Agent"]` on the wire and resets via token; `tests/models/test_litellm_user_agent.py::test_user_agent_header_litellm` (same contract through the litellm adapter).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "chatcmpl_helpers.py", query: "store stream_options is_openai", limit: 20 });
await mcp.codebase_memory.trace_path({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.models.chatcmpl_helpers.ChatCmplHelpers.get_store_param", direction: "inbound" });
```

## Verdict
Adopt the explicit→endpoint-default→omit ladder for any adapter that serves one official endpoint plus arbitrary third-party backends, and the ContextVar last-wins header merge for a process-wide, async-task-scoped header escape hatch shared by all sibling adapters. Adapt the endpoint predicate (scheme+hostname) and the default-on param set per API. Omit the override var if your host has no multi-adapter plane — per-call extra_headers alone then suffice. Coverage: direct source+test reading fallback this pass (Codebase Memory MCP not connected); all cited ranges read from checkout at fe45b415.
