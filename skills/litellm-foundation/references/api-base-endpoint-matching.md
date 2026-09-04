<!-- capsule-v2 -->
# api-base-endpoint-matching — How is a caller-supplied api_base matched to a known provider endpoint without the credential-forwarding vulnerability?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** Why is endpoint matching parsed-URL segment-boundary comparison instead of substring containment, and what breaks if a porter simplifies it?

## Connected graph-selected seam
**Path/Symbol:** `litellm/litellm_core_utils/get_llm_provider_logic.py:_endpoint_matches_api_base` (:15-49).
**Signature:** `_endpoint_matches_api_base(endpoint: str, api_base: str) -> bool`.
**Data Shape:** Inputs may be bare hostname (`api.perplexity.ai`), host+path (`api.deepinfra.com/v1/openai`), or full URL (`https://api.cerebras.ai/v1`). Returns True iff hosts match exactly (case-insensitive) and, when the registered endpoint has a path, the api_base path equals it or extends it on a `/` boundary.

### Decisive source
```python
    The naive ``endpoint in api_base`` shape lets a caller pass
    ``https://attacker.com/api.groq.com/openai/v1`` to coerce the proxy
    into reading the server's GROQ_API_KEY from the environment and
    forwarding it to the attacker's host as a Bearer credential.
...
    endpoint_host: Final = (parsed_endpoint.hostname or "").lower()
    url_host: Final = (parsed_url.hostname or "").lower()
    if not endpoint_host or endpoint_host != url_host:
        return False

    endpoint_path: Final = parsed_endpoint.path.rstrip("/")
    if not endpoint_path:
        return True
    url_path: Final = parsed_url.path.rstrip("/")
    return url_path == endpoint_path or url_path.startswith(endpoint_path + "/")
```

**Flow:** normalize by injecting `https://` when no scheme (`urlparse` populates hostname only with a scheme) → compare lowered exact hostnames → empty endpoint path means host-only match → else require equality or segment-boundary extension of the caller's path. Callers loop over `litellm.openai_compatible_endpoints`; on match they set `custom_llm_provider` and pull the provider key into `dynamic_api_key` via `get_secret_str` (the groq/anyscale/deepseek/... ladder at :230-360), with a final JSON-provider fallback `JSONProviderRegistry.get_by_base_url(endpoint)`.
**Invariant:** Host must match EXACTLY — never `in`. Path matching must be anchored on `/` boundaries — `"/v1/openai".startswith("/v1/open")` style unanchored prefix tests reintroduce spoofing. The docstring's attack scenario (credential exfiltration through a lookalike api_base) is the reason this function exists; a porter who "simplifies" it reopens the hole while all tests still pass on benign inputs.
**Probe:** `tests/test_litellm/litellm_core_utils/test_get_llm_provider_endpoint_match.py` (`TestEndpointMatchesApiBase` :24-81 — dedicated direct tests incl. lookalike-host rejections); deterministic check: `grep -c "_endpoint_matches_api_base" litellm/litellm_core_utils/get_llm_provider_logic.py` → 2 (definition + single call site).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "_endpoint_matches_api_base", limit: 5 });
```

## Verdict
Adopt the parsed-URL two-stage match verbatim for any gateway that maps user-supplied base URLs onto credentialed providers. Adapt the endpoint→provider table to your fleet. Omit nothing here — the security property IS the contract. Index caveat: none; symbol resolves line-exact in `ext-litellm`.
