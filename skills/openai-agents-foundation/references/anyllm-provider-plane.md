<!-- capsule-v2 -->
# AnyLLM provider plane — how does a third-party adapter select the API, cache/clone providers, and normalize hostile provider payloads into SDK types?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** How does `AnyLLMModel` route between Responses and Chat Completions per provider capability, and what normalization stands between any-llm's loosely-typed payloads and the SDK's strict models?

## Capability-gated API selection + two-key provider cache
**Path/Symbol:** `src/agents/extensions/models/any_llm_model.py:` `_split_model_name` (:1146–1159), `_supports_responses` (:1160–1162), `_validate_api` (:1164–1171), `_selected_api` (:1173–1181), `_get_provider` (:1183–1204), `_normalize_google_tool_result_roles` (:1208–1229), `_clone_provider_without_retries` (:1231–1239), `_normalize_response` (:1241–1265), `_normalize_chat_completion_response` (:1267–1272), `_normalize_chat_chunk` (:1290–1315).
**Signature:** `_selected_api(self) -> Literal["responses", "chat_completions"]`; `_get_provider(self) -> Any`; `_normalize_response(self, response: Any) -> Response`.
**Data Shape:** model string `provider/model[/...]` splits once on the first slash (no slash ⇒ provider `openai`); `_provider_cache: dict[bool, Any]` keyed by `disable_provider_retries`.

### Decisive source
```python
def _selected_api(self):
    if self.api is not None:
        if self.api == "responses" and not self._supports_responses():
            raise UserError(f"Provider '{self._provider_name}' does not support the Responses API.")
        return self.api
    return "responses" if self._supports_responses() else "chat_completions"

def _get_provider(self):
    disable_provider_retries = should_disable_provider_managed_retries()
    cached = self._provider_cache.get(disable_provider_retries)
    if cached is not None: return cached
    ...
    base_provider = AnyLLM.create(self._provider_name, api_key=self.api_key, api_base=self.base_url)
    if self._provider_name in {"gemini", "vertexai"}:
        self._normalize_google_tool_result_roles(base_provider)
```

**Flow:** `get_response`/`stream_response` call `_selected_api()` once per call: explicit `api=` wins but forcing `responses` on a provider without `SUPPORTS_RESPONSES` raises `UserError`; otherwise capability decides → providers are created lazily via `AnyLLM.create` and cached under two keys (retry-enabled base vs retry-disabled clone built by `client.with_options(max_retries=0)` shallow copy) so the SDK's own retry engine can take over without re-creating the provider → Google-family providers get a monkey-patched `_convert_completion_params` that rewrites `role: "function"` contents to `role: "user"` (any-llm's Gemini converter emits an unsupported role) → responses-path payloads pass through `_normalize_response`: non-`Response` payloads are `model_dump`ed and any usage dict missing `cache_write_tokens` gets it defaulted to 0 before `Response.model_validate` → chat-path chunks pass `_normalize_chat_chunk`: any-llm reasoning text (from `reasoning`/`reasoning_content` variants) is promoted into the OpenAI-style `delta.reasoning` field by round-tripping the chunk through `model_dump` → `close()` acloses each distinct cached client once (id-dedup) so both cache entries share one client safely.
**Invariant:** capability gating fails loud on impossible explicit requests; provider construction happens at most once per retry mode; normalization is total (any provider payload shape either validates into an SDK type or the adapter defaults the missing field) and never mutates the provider payload in place.
**Probe:** `tests/models/test_any_llm_model.py::test_any_llm_chat_path_is_used_when_responses_are_unsupported` (:546), `::test_any_llm_can_force_chat_completions_when_responses_are_supported` (:931), `::test_any_llm_forced_responses_errors_when_provider_does_not_support_it` (:962), `::test_any_llm_google_provider_normalizes_function_result_roles` (:473), `::test_any_llm_responses_path_defaults_missing_cache_write_tokens` (:896), `::test_any_llm_stream_flattens_reasoning_object_when_reasoning_content_is_empty` (:1543).
