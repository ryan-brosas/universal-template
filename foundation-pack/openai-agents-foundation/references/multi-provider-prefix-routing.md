<!-- capsule-v2 -->
# Multi-provider prefix routing — which provider owns a model string like "openai/gpt-4.1" or "litellm/openai/gpt-4.1"?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When a model name carries a `provider/` prefix (or none), which ModelProvider resolves it and what does the resolved model string become?

## Prefix-split resolution ladder
**Path/Symbol:** `src/agents/models/multi_provider.py:` `MultiProvider.get_model` (:227–252), `_get_prefix_and_model_name` (:155–162), `_resolve_prefixed_model` (:199–225).
**Signature:** `def get_model(self, model_name: str | None) -> Model`; helper `_resolve_prefixed_model(*, original_model_name, prefix, stripped_model_name) -> tuple[ModelProvider, str | None]`.
**Data Shape:** model name split on the FIRST `"/"` only → `(prefix, stripped)`; no slash → prefix None; explicit `MultiProviderMap`, lazy `_fallback_providers` cache, and two Literal modes `openai_prefix_mode ∈ {alias, model_id}`, `unknown_prefix_mode ∈ {error, model_id}`.

### Decisive source
```python
# Explicit provider_map entries are the least surprising routing mechanism, so they always
# win over the built-in OpenAI alias and unknown-prefix fallback behavior.
if self.provider_map is not None and (provider := self.provider_map.get_provider(prefix)) is not None:
    return provider, stripped_model_name
if prefix in {"litellm", "any-llm"}:
    return self._get_fallback_provider(prefix), stripped_model_name
if prefix == "openai":
    if self._openai_prefix_mode == "alias":
        return self.openai_provider, stripped_model_name
    return self.openai_provider, original_model_name      # keep literal "openai/x" id
if self._unknown_prefix_mode == "model_id":
    return self.openai_provider, original_model_name
raise UserError(f"Unknown prefix: {prefix}")
```

**Flow:** bare/None names skip routing entirely and go straight to the built-in OpenAI provider → prefixed names resolve through the ladder above (map > litellm/any-llm lazy fallbacks > openai mode > unknown mode) → the winning provider receives either the stripped or original string.
**Invariant:** explicit map entries always beat built-ins; `openai/` under `alias` strips, under `model_id` preserves; an unknown prefix either fails loud with `UserError` or passes the full literal through — never silently re-routed to a wrong vendor. Fallback providers are created once per prefix and cached (`_fallback_providers`). `aclose()` (:254–279) closes openai + map + fallback providers deduped by `id()`, re-raises `CancelledError` immediately, keeps closing after a child failure, and raises only the FIRST captured error.
**Probe:** `tests/models/test_map.py::test_openai_prefix_can_be_preserved_as_literal_model_id` (:127) and `::test_unknown_prefix_can_be_preserved_for_openai_compatible_model_ids` (:152) pin mode preservation; `::test_multi_provider_aclose_continues_and_preserves_first_failure` (:235) pins close-all/first-error.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "MultiProvider model routing prefix", limit: 10, fields: ["signature", "name", "file"] });
// get_code_snippet("…multi_provider.MultiProvider._resolve_prefixed_model") returned the live ladder
```

## Verdict
Adopt first-slash splitting, explicit-map precedence, mode-gated openai/unknown handling, lazy per-prefix fallback caching, and best-effort aclose with first-error raise. Adapt the default provider set (litellm/any-llm) to your stack. Omit OpenAI-specific websocket/registration kwargs. Coverage: no_recorded_issue at gen 2026-08-24T14:05:06Z.
