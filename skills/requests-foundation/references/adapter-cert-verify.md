<!-- capsule-v2 -->
# cert_verify file gating — why does verify=False clear CA state, and when does a missing bundle raise OSError?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** How are CA bundle paths and client certs validated on the chosen connection?

## HTTPAdapter.cert_verify
**Path/Symbol:** `src/requests/adapters.py:HTTPAdapter.cert_verify` (:307-363).
**Signature:** `cert_verify(conn, url: str, verify: VerifyType, cert: CertType) -> None`.
**Data Shape:** Mutates the urllib3 connection object in place: sets/clears `cert_reqs`, `ca_certs`, `ca_cert_dir`, `cert_file`, `key_file`.

### Decisive source
```python
if url.lower().startswith("https") and verify:
    cert_loc = None
    if verify is not True:
        cert_loc = verify                      # user-specified bundle path
    if not cert_loc:
        cert_loc = DEFAULT_CA_BUNDLE_PATH      # certifi's where()
    if not cert_loc or not os.path.exists(cert_loc):
        raise OSError(f"Could not find a suitable TLS CA certificate bundle, invalid path: {cert_loc}")
    conn.cert_reqs = "CERT_REQUIRED"
    conn.ca_certs = cert_loc if not os.path.isdir(cert_loc) else None
    if os.path.isdir(cert_loc):
        conn.ca_cert_dir = cert_loc
else:
    conn.cert_reqs = "CERT_NONE"
    conn.ca_certs = None
    conn.ca_cert_dir = None                    # explicit CLEAR even when never set
if cert:
    ...
    if conn.cert_file and not os.path.exists(conn.cert_file):
        raise OSError(f"Could not find the TLS certificate file, invalid path: {conn.cert_file}")
    if conn.key_file and not os.path.exists(conn.key_file):
        raise OSError(f"Could not find the TLS key file, invalid path: {conn.key_file}")
```

**Flow:** https AND truthy verify → resolve bundle (custom path → default certifi) → existence-checked with LOUD OSError → CERT_REQUIRED + ca file-or-dir → otherwise CERT_NONE and all three fields explicitly nulled → client cert tuple/str mapped to files with existence checks.
**Invariant:** The else-branch's triple-null is load-bearing on REUSED pooled connections: a session that verified once then flipped verify=False must scrub stale CA state from whatever connection object comes back, or urllib3 re-uses old verification material. Missing bundles fail BEFORE connecting (fail-fast OSError, not a TLS-time surprise). Note this runs per-send on the connection from get_connection_with_tls_context — pool keys were derived separately by `_urllib3_request_context`; cert_verify is the belt-and-suspenders mutation layer for subclasses that bypass pool-key derivation.
**Probe:** Direct tests: `tests/test_lowlevel.py::test_use_proxy_from_environment` (:290, env-proxy resolution through a live send); bundle-path behavior verified by reading `cert_verify` against `_urllib3_request_context` (no dedicated unit test in-suite — coverage caveat: OSError arms are source-confirmed only). `grep -c "invalid path" src/requests/adapters.py` → 3 (bundle+cert+key messages).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "cert_verify ca_certs cert_reqs", limit: 10 });
```

## Verdict
Adopt explicit-clear-on-disable plus pre-connect existence checks. Adapt attribute names to host connection type. Omit the basestring compat shim (py2 relic).
