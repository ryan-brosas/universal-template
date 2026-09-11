<!-- capsule-v2 -->
# SSRF pinned-fetch transport — how do you fetch a user-supplied URL without a DNS-rebinding TOCTOU?

**Source:** Plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** validating a hostname and then letting your HTTP client resolve it again reopens the rebinding window — how does Plane guarantee the validated IP is exactly the reached IP?

## PinnedIPAdapter + _request_to_ip
**Path/Symbol:** `apps/api/plane/utils/url_security.py`:`PinnedIPAdapter` (:46–76) + `_request_to_ip` (:103–157).
**Signature:** `PinnedIPAdapter(server_hostname, *args, **kwargs)`; `_request_to_ip(method, scheme, hostname, ip, port, path, *, headers, timeout, auth=None, **kwargs) -> requests.Response`.
**Data Shape:** caller passes an already-validated IP string; adapter is mounted per-request on a throwaway `requests.Session`, holds no global state (safe under any Celery pool). Failure shape: `requests.RequestException` on transport errors; session closed on any exception.

### Decisive source
```python
def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
    # requests >= 2.32 calls this (it replaced get_connection() as part of
    # the CVE-2024-35195 fix).
    host_params, pool_kwargs = self.build_connection_pool_key_attributes(request, verify, cert)
    # server_hostname is a recognised urllib3 SSL pool-key field, so pools
    # for different hostnames don't collide.
    pool_kwargs["server_hostname"] = self._server_hostname
    return self.poolmanager.connection_from_host(**host_params, pool_kwargs=pool_kwargs)
```
and in `_request_to_ip`:
```python
url = f"{scheme}://{host_for_url}:{port}{path}"          # IP literal — no DNS lookup
request_headers["Host"] = host_label if port == default_port else f"{host_label}:{port}"
session.trust_env = False  # ignore ambient proxy / netrc / env
if scheme == "https":
    session.mount("https://", PinnedIPAdapter(server_hostname=hostname))
...
response = session.request(method, url, headers=request_headers, timeout=timeout,
                           allow_redirects=False, verify=True,
                           proxies=_NO_PROXIES, auth=auth, **kwargs)
```

**Flow:** resolve+validate once upstream (`resolve_and_validate`) → rewrite URL to the validated IP literal → socket connects with zero second DNS lookup → `server_hostname` keeps TLS SNI/cert verification against the real name → manual `Host` header carries the original hostname (IPv6 bracketed, port appended only when non-default) → ambient proxy/netrc/env disabled because a CONNECT tunnel would bypass pinning entirely.
**Invariant:** the address that was checked is exactly the address that is reached; identity of the real hostname survives in Host/SNI/verification. Never honor `trust_env` or configured proxies on this path.
**Probe:** `apps/api/plane/tests/unit/bg_tasks/test_url_security.py::TestPinnedFetch::test_connects_to_validated_ip_not_hostname` (:138–159) asserts `session.request` URL == `https://93.184.216.34:443/hook`, `headers["Host"]=="example.com"`, `allow_redirects False`, `verify True`, `trust_env False`, `proxies {"http": None, "https": None}`. Not executed this lane (no Django deps provisioned); pytest.ini runner named honestly.
**Coverage caveat:** url_security.py indexed `no_recorded_issue` @ gen 2026-08-25T19:59:48Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "pinned fetch SSRF pin connection validated IP", limit: 10, fields: ["signature", "name", "file"] });
```
Observed live at pass 2: ranks `pinned_fetch` :198–222, `_fetch_validated_hop` :160–195, and the pinning tests top-of-list.

## Verdict
Adopt the validate-once/connect-to-literal pattern plus per-request throwaway sessions and proxy isolation as a portable contract; adapt the requests/urllib3 hook to your client library's equivalent connection-pool customization; omit Plane's settings wiring (`WEBHOOK_ALLOWED_IPS/HOSTS`) and Celery integration specifics.
