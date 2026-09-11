<!-- capsule-v2 -->
# exception-mapping-status-table — What class and status does every provider failure surface as, per upstream HTTP status?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** When an LLM provider returns status N, which litellm exception (with which `status_code`) must the caller observe — and where are the deviations from the OpenAI shape?

## Connected graph-selected seam
**Path/Symbol:** `litellm/litellm_core_utils/exception_mapping_utils.py:exception_type` (:2190-2548) dispatching into `_map_openai_exception` (:257), `_map_anthropic_exception` (:501), `_map_bedrock_exception` (:832), `_map_vertex_exception` (:1100), etc.
**Signature:** `exception_type(model, original_exception, custom_llm_provider, completion_kwargs={}, extra_kwargs={})`.
**Data Shape:** Raises the mapped `openai.APIError` subclass; re-raises untouched anything already in `litellm.LITELLM_EXCEPTION_TYPES` (:2198-2199). The canonical behavior table is pinned by the parametrized test matrix introduced at this very commit.

### Decisive source
```python
OPENAI_SHAPED = {
    400: (litellm.BadRequestError, 400),
    401: (litellm.AuthenticationError, 401),
    403: (litellm.APIError, 403),
    404: (litellm.NotFoundError, 404),
    408: (litellm.Timeout, 408),
    422: (litellm.BadRequestError, 422),
    429: (litellm.RateLimitError, 429),
    500: (litellm.InternalServerError, 500),
    503: (litellm.ServiceUnavailableError, 503),
}

DEVIATIONS_FROM_THE_OPENAI_SHAPE = {
    "anthropic": {403: UPSTREAM_STATUS_DISCARDED, 422: UPSTREAM_STATUS_DISCARDED},
    "azure": {500: (litellm.APIError, 500)},
    "bedrock": {403: ..., 500: (litellm.ServiceUnavailableError, 503)},
    "cohere": {401/403/404/422/429/503: UPSTREAM_STATUS_DISCARDED},   # all discarded
    "databricks": {403: (AuthenticationError, 401), 422: (BadRequestError, 400)},
    "gemini" / "vertex_ai": {403: (PermissionDeniedError, 403), 422: discarded},
    "replicate": {403: (APIError, 500), 404: (APIError, 500),
                  422: (UnprocessableEntityError, 422),
                  500: (ServiceUnavailableError, 503), 503: (APIError, 500)},
    **{"cloudflare"/"ollama"/"vllm": ALL → (APIConnectionError, 500)},
}
```
(verbatim table at `tests/test_litellm/litellm_core_utils/test_exception_mapping_utils.py:776-847`)

**Flow:** inside `exception_type`: build `extra_information` debug block (model, api_base, model_group/deployment metadata) guarded so it can never mask the real error (:2232-2264) → cross-provider timeout-string sniff FIRST ("Request timed out", "The read operation timed out", …) → Timeout regardless of provider (:2274-2287) → `litellm_proxy` special case extracts embedded error from the proxy response body (`extract_and_raise_litellm_exception`) → provider dispatch ladder to the ~17 `_map_*_exception` handlers. Each handler string/status-matches its vendor's error shapes onto the OPENAI_SHAPED classes with per-provider deviations above. Unknown exception types fall through to a final loop over `LITELLM_EXCEPTION_TYPES` matching on status (:2533).
**Invariant:** A plain upstream status N maps to exactly one class+status per provider; deviations are EXPLICIT table entries, not accidents. `ContextWindowExceededError` subclasses BadRequestError but must be checked BEFORE it wherever both are handled (the same ordering rule `_EXCEPTION_POLICY_FIELDS` documents in cooldown land). Already-litellm exceptions pass through byte-identical (test :923-935).
**Probe:** `tests/test_litellm/litellm_core_utils/test_exception_mapping_utils.py:test_an_upstream_status_maps_to_one_exception_per_provider` (:889-904, parametrized 9 statuses × 21 providers = 189 cases pinning `(type(raised.value), raised.value.status_code)`); companion `test_a_mapped_exception_keeps_the_provider_and_model_it_came_from` (:907-920) pins `llm_provider`/`model` propagation.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "exception_type custom_llm_provider mapping", limit: 10 });
```

## Verdict
Adopt the status→class table + explicit-deviation pattern for any multi-provider gateway: it converts heterogeneous vendor errors into one catchable hierarchy with honest statuses. Adapt per-vendor handler internals (string sniff lists are vendor-version-sensitive). Omit the proxy-body extraction path unless you operate a proxy. Coverage caveat: none — the table test executed green at f005afa1 via the repo venv.
