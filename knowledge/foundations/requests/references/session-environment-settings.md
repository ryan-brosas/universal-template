<!-- capsule-v2 -->
# Environment settings merge — how do trust_env proxies, REQUESTS_CA_BUNDLE, and session defaults combine at request time?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** In `merge_environment_settings`, what wins between call-site args, environment variables, and session attributes?

## Session.merge_environment_settings
**Path/Symbol:** `src/requests/sessions.py:Session.merge_environment_settings` (:831-868).
**Signature:** `merge_environment_settings(url, proxies, stream, verify, cert) -> dict`.
**Data Shape:** Returns `{"proxies", "stream", "verify", "cert"}` ready to feed `Session.send`.

### Decisive source
```python
if self.trust_env:
    no_proxy = proxies.get("no_proxy") if proxies is not None else None
    env_proxies = get_environ_proxies(url, no_proxy=no_proxy)
    if proxies is not None:
        for k, v in env_proxies.items():
            proxies.setdefault(k, v)          # explicit call-site keys win
    if verify is True or verify is None:      # only UNSET verification is overridable
        verify = (os.environ.get("REQUESTS_CA_BUNDLE")
                  or os.environ.get("CURL_CA_BUNDLE")
                  or verify)
proxies = merge_setting(proxies, self.proxies)
stream   = merge_setting(stream,   self.stream)
verify   = merge_setting(verify,   self.verify)
cert     = merge_setting(cert,     self.cert)
```

**Flow:** when trust_env: env proxies fill gaps in the call-site map (setdefault — never overwrite), and REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE override only an explicitly-unset (`True`/`None`) verify — `verify=False` is NEVER resurrected by env vars — then all four slots pass through merge_setting against session defaults.
**Invariant:** The `verify is True or verify is None` guard means a caller who disables verification keeps that decision regardless of CA-bundle env vars (security-relevant: test suites rely on it). Env-proxy injection mutates the CALLER's dict when passed (setdefault on the same object) — deliberate, since the merged map flows onward into send/rebuild_proxies. Porters who apply env bundles over `verify=False` break offline/integration tests; porters who merge env proxies with assignment instead of setdefault silently defeat explicit per-request proxy overrides.
**Probe:** Direct tests: `tests/test_utils.py::test_set_environ*` pin the restore-on-exit helper this relies on; `tests/test_lowlevel.py::test_use_proxy_from_environment` (:290) exercises env-proxy resolution through send. `grep -n 'REQUESTS_CA_BUNDLE' src/requests/sessions.py` → 1 hit.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "merge_environment_settings verify cert proxies", limit: 10 });
```

## Verdict
Adopt precedence: call-site > env (setdefault) > session defaults; CA-bundle env only over unset verify. Adapt env var names to host conventions. Omit Windows registry proxy logic (lives in utils capsule).
