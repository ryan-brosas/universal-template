<!-- capsule-v2 -->
# Cross-origin auth stripping — when exactly does an Authorization header survive a redirect?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** Which host/port/scheme transitions strip the Authorization header, and where do netrc credentials get re-applied?

## SessionRedirectMixin.should_strip_auth / rebuild_auth
**Path/Symbol:** `src/requests/sessions.py:SessionRedirectMixin.should_strip_auth` (:154-184), `src/requests/sessions.py:SessionRedirectMixin.rebuild_auth` (:309-332).
**Signature:** `should_strip_auth(old_url: str, new_url: str) -> bool`; `rebuild_auth(prepared_request: PreparedRequest, response: Response) -> None`.

### Decisive source
```python
if old_parsed.hostname != new_parsed.hostname:
    return True                                   # any host change strips
# Special case: allow http -> https redirect when using the standard ports.
if (old_parsed.scheme == "http"
        and old_parsed.port in (80, None)
        and new_parsed.scheme == "https"
        and new_parsed.port in (443, None)):
    return False                                  # legacy upgrade carve-out
# Handle default port usage corresponding to scheme.
changed_port = old_parsed.port != new_parsed.port
changed_scheme = old_parsed.scheme != new_parsed.scheme
default_port = (DEFAULT_PORTS.get(old_parsed.scheme, None), None)
if (not changed_scheme
        and old_parsed.port in default_port
        and new_parsed.port in default_port):
    return False                                  # explicit==implicit default port
return changed_port or changed_scheme
```

**Flow:** hostname differs → strip → http→https on standard ports (80/None→443/None) → keep (back-compat carve-out, NOT RFC 7235) → same scheme where both ports are default-or-None → keep → otherwise strip.
**Invariant:** `rebuild_auth` runs AFTER stripping and consults `.netrc` ONLY when `trust_env` — `get_netrc_auth(url)` can re-arm credentials for the NEW host even though the header was just stripped. Porters must keep that order (strip header → maybe netrc-reapply); reversing it leaks credentials or double-applies auth. The DEFAULT_PORTS lookup uses the OLD scheme's default, so `https://host:443 → https://host` keeps auth but `http://host:8080 → https://host:443` strips (non-standard source port).
**Probe:** Direct tests: `tests/test_requests.py::TestRedirects::test_should_strip_auth_host_change` (:1940), `_http_downgrade` (:1946), `_https_upgrade` (:1950, incl. :8080/:8443 negative cases), `_port_change` (:1969), `_default_port` parametrized ×4 (:1984). All assert against `Session().should_strip_auth(...)` directly — no network needed.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "should_strip_auth", limit: 10 });
```

## Verdict
Adopt the decision table exactly (it encodes deliberate back-compat, not RFC compliance) plus the netrc re-application step. Adapt hostname parsing to host URL libs. Omit nothing — every branch here has shipped CVE-grade consequences when dropped.
