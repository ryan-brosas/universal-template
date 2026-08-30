<!-- capsule-v2 -->
# Response cache-key derivation — which request fields may influence the cache key, and what exactly is stored?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `litellm`. **Question:** How is the cache key built from completion kwargs so identical requests collide and litellm-internal params never leak into it?

## `Cache.get_cache_key`
**Path/Symbol:** `litellm/caching/caching.py:Cache.get_cache_key` (:325-375) inside `class Cache` (:55-919); hashing helper `_get_hashed_cache_key` (:454-471); namespace prefixer (:473-490); semantic tenant scope (:304-323).
**Signature:** `def get_cache_key(self, **kwargs) -> str`.
**Data Shape:** input = full completion kwargs (incl. `litellm_params`); output = `<namespace>:<sha256-hex>` string; intermediate key material is an ordered string concat `f"{param}: {value}"` of contributing params.

### Decisive source
```python
        preset_cache_key: Final = self._get_preset_cache_key_from_kwargs(**kwargs)
        if preset_cache_key is not None:
            return preset_cache_key
        combined_kwargs: Final = ModelParamHelper._get_all_llm_api_params()
        litellm_param_kwargs: Final = all_litellm_params
        is_semantic_cache: Final = self._is_semantic_cache()
        scope_excluded_params: Final = self._SEMANTIC_CACHE_SCOPE_EXCLUDED_PARAMS if is_semantic_cache else frozenset()
        for param in kwargs:
            if param in scope_excluded_params:
                continue
            if param in combined_kwargs:
                param_value = self._get_param_value(param, kwargs)
                if param_value is not None:
                    cache_key += f"{param}: {param_value}"
            elif param not in litellm_param_kwargs:  # user optional param e.g. top_k
                if litellm.enable_caching_on_provider_specific_optional_params is True:  # feature flagged
                    ...
        if is_semantic_cache:
            cache_key += self._get_semantic_cache_tenant_scope(kwargs)
        hashed_cache_key = Cache._get_hashed_cache_key(cache_key)   # hashlib.sha256(...).hexdigest()
        hashed_cache_key = self._add_namespace_to_cache_key(hashed_cache_key, **kwargs)
```
(:338-365, condensed) — namespace precedence: `cache["namespace"] > metadata["redis_namespace"] > self.namespace` (:484-488).

**Flow:** preset short-circuit (caller-supplied key wins, then written back into `litellm_params.preset_cache_key`) → include only LLM-API params with non-None values → provider-specific extras only behind the feature flag → semantic caches append tenant scope from api-key/team/org metadata → sha256 hex → namespace prefix.
**Invariant:** `all_litellm_params` never contribute key material; identical logical requests produce identical keys regardless of kwargs iteration order effects being limited to concatenation layout (hash input is deterministic per same kwarg set observed live).
**Probe:** executed live at the pin: `Cache._get_hashed_cache_key(s)` twice → equal 64-char hex; different message content → different hex. Direct tests: `tests/test_litellm/caching/test_redis_semantic_cache.py` (mocks `get_cache_key` for handler flow), `tests/local_testing/test_caching.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm", qn_pattern: "caching\\.caching", name_pattern: "get_cache_key" });
// rank-1 group → Cache.get_cache_key Method caching.py :325-375 (verified at pin).
// Adversarial note: semantic_query ["cache key","hash","preset"] lands on minified proxy UI bundles — use this BM25/name needle instead.
```

## Verdict
Adopt: preset-key short-circuit, allow-list-driven key material (API params only), sha256-hex storage keys with optional namespace prefixing, tenant-scope exclusion list for shared semantic caches. Adapt the allow-list to your request surface and the flag default if you want provider-specific params to split cache entries. Omit the minified-bundle search surface entirely; it is product UI, not kernel.
