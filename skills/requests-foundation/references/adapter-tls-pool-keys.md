<!-- capsule-v2 -->
# TLS pool-key derivation — how do verify/cert become urllib3 PoolKey attributes without a deprecated get_connection?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** How do verify/cert values select distinct connection pools, and what replaced `get_connection` for subclasses?

## _urllib3_request_context / build_connection_pool_key_attributes / get_connection_with_tls_context
**Path/Symbol:** `src/requests/adapters.py:_urllib3_request_context` (:85-119), `HTTPAdapter.build_connection_pool_key_attributes` (:403-453), `HTTPAdapter.get_connection_with_tls_context` (:455-510), deprecation shim `get_connection` (:512-553).
**Signature:** `build_connection_pool_key_attributes(request, verify, cert=None) -> tuple[host_params, pool_kwargs]`; `get_connection_with_tls_context(request, verify, proxies=None, cert=None) -> HTTPConnectionPool`.

### Decisive source
```python
cert_reqs = "CERT_REQUIRED"
if verify is False:
    cert_reqs = "CERT_NONE"
elif isinstance(verify, str):
    if not os.path.isdir(verify):
        pool_kwargs["ca_certs"] = verify      # file bundle
    else:
        pool_kwargs["ca_cert_dir"] = verify   # directory of CAs
pool_kwargs["cert_reqs"] = cert_reqs
if client_cert is not None:
    if isinstance(client_cert, tuple) and len(client_cert) == 2:
        pool_kwargs["cert_file"], pool_kwargs["key_file"] = client_cert
    else:
        pool_kwargs["cert_file"] = client_cert   # docs allow cert-only path
```
plus the dispatch: `select_proxy(url, proxies)` → if proxy: `prepend_scheme_if_needed(proxy,"http")`, parse, `InvalidProxyURL` when hostless, `proxy_manager.connection_from_host(**host_params, pool_kwargs=pool_kwargs)`; else same call on `self.poolmanager`.

**Flow:** derive host_params {scheme(lowercased), hostname, port} + SSL-ish pool_kwargs from verify/cert → proxy lookup with 4-key precedence (`scheme://host`, `scheme`, `all://host`, `all`) → route through ProxyManager or PoolManager using IDENTICAL host_params so pool keys stay comparable.
**Invariant:** The docstring table is the contract: verify=True ⇒ `ssl_context` set (default context); verify=False ⇒ no ssl_context but `cert_reqs="CERT_NONE"`; verify=str ⇒ `ca_certs` (file) OR `ca_cert_dir` (dir); cert always sets `cert_file` (+`key_file` only for 2-tuples). Because these land IN THE POOL KEY, changing verify/cert between requests to the same host yields DIFFERENT pooled connections — porters who stash TLS state on the adapter instead break session-level verify switching (and its security). `get_connection(url, proxies)` still exists but warns DeprecationWarning pointing at PR #6710 — custom adapters must migrate because only the tls-context path receives verify/cert.
**Probe:** Direct tests: `tests/test_requests.py::TestPreparingURLs::test_different_connection_pool_for_mtls_settings` (:3024), `_tls_settings_verify_True` (:2928), `_verify_bundle_expired_cert`/:2959, `_bundle_unexpired_cert`/:2992 — each asserts separate pools arise from differing TLS args. `grep -n "get_connection_with_tls_context" src/requests/adapters.py` → def :455 + call :662.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "get_connection_with_tls_context pool key", limit: 10 });
```

## Verdict
Adopt pool-key-affecting TLS args and the four-key proxy precedence. Adapt key names if host pool lib differs (keep them in the KEY, not adapter state). Omit the deprecated get_connection entirely for new ports.
