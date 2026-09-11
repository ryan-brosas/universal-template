<!-- capsule-v2 -->
# Encrypted-content affinity — how do you pin follow-ups to the deployment that produced encrypted reasoning, with NO cache at all?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** stateless routing when OpenAI rejects encrypted_content produced by a different org (`invalid_encrypted_content`).

## encrypted-content-affinity
**Path/Symbol:** `litellm/router_utils/pre_call_checks/encrypted_content_affinity_check.py:EncryptedContentAffinityCheck` (`async_filter_deployments` :208-286, `_find_deployments_on_same_encryption_boundary` :178-202, `_unavailable_origin_error` :288-341).
**Signature:** `async_filter_deployments(...) -> list[dict]`; raises `BadRequestError` / `RateLimitError` (with Retry-After) / `ServiceUnavailableError` instead of returning a doomed candidate list.
**Data Shape:** model_id embedded in input items two ways: encoded item ids (`encitem_...`, decoded via `ResponsesAPIRequestUtils._decode_encrypted_item_id`) or wrapped content (`litellm_enc:{base64_metadata};{original}`, `_unwrap_encrypted_content_with_model_id`). Response-side encoding lives in `responses/utils.py` (`_update_encrypted_content_item_ids_in_response`), restore side in `get_optional_params_responses_api` — this check owns ONLY the routing decision.

### Decisive source
```python
# Follow-up switched model_name (LIT-2531): pin by Azure resource instead.
boundary_matches, originating = self._find_deployments_on_same_encryption_boundary(
    healthy_deployments=typed_healthy_deployments,
    model_id=model_id,
)
if boundary_matches:
    ...
    return boundary_matches

# Dispatching to a non-peer would guarantee an upstream
# `invalid_encrypted_content` 400, so fail fast with a clearer error.
raise await self._unavailable_origin_error(...)
```
(:264-286) with the boundary key:
```python
# Accepts any object exposing dict-style `.get(key, default)` ... A stricter
# isinstance(dict) guard would silently drop LiteLLM_Params pydantic instances
# from boundary matching and fall back to the full pool — i.e. trigger the exact
# invalid_encrypted_content failure this check exists to prevent.
getter: Final = getattr(litellm_params, "get", None)
```
(:152-176)

**Flow:** enabled globally or per-group (`encrypted_content_affinity` flag; global default True) → set `litellm_metadata["encrypted_content_affinity_enabled"]=True` ONLY when the dict already exists (setdefault would create it on chat/embeddings and hijack tag-routing's metadata-channel precedence) → decode first encoded marker in `input` → pin to originating deployment if healthy → else pin to ALL deployments sharing `(api_base, api_key)` (interchangeable Azure resource) → else fail fast mirroring the origin's cooldown status: 429-with-remaining-seconds when the cooldown cache says rate-limited, 503 otherwise, 400 when the deployment is gone entirely.
**Invariant:** (1) error messages deliberately omit model_id so a caller forging markers can't enumerate deployment ids (:295-297 comment); (2) safe to enable globally — inert without encoded markers, no quota cost for first requests, no cache/TTL anywhere; (3) the duck-typed `.get` boundary getter is load-bearing (see excerpt); (4) `_cooldown_seconds_remaining` clamps to ≥1s and reads `(timestamp + cooldown_time - now)` from CooldownCacheValue.
**Probe:** `tests/test_litellm/router_utils/pre_call_checks/test_encrypted_content_affinity_check.py::test_wrap_and_unwrap_encrypted_content` (:150) etc.; suite GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "EncryptedContentAffinityCheck async_filter_deployments", limit: 5, fields: ["signature", "name", "file"] });
```
(rank-1 = encrypted_content_affinity_check.py:208-286.)

## Verdict
Adopt the encode-in-response/decode-in-request stateless pin pattern and the encryption-boundary peer fallback; adapt marker formats to your transport; omit the cooldown-status mirroring only if clients of your API don't honor Retry-After.
