<!-- capsule-v2 -->
# Host validation ladder — how does get_host defend against host-header spoofing through proxies?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** Which headers may supply the host, in what precedence, and what grammar must a host satisfy before ALLOWED_HOSTS is even consulted?

## Host extraction + validation funnel
**Path/Symbol:** `django/http/request.py` — `_get_raw_host` (172–188), `get_host` (190–210), `split_domain_port` (849–860), `validate_host` (863–880); `host_validation_re` (:35).
**Signature:** `get_host(self) -> str` raising `DisallowedHost`; `split_domain_port(host) -> tuple[str, str]`.
**Data Shape:** precedence `X-Forwarded-Host` (only when USE_X_FORWARDED_HOST) → `HTTP_HOST` → PEP 333 SERVER_NAME+port reconstruction; DEBUG + empty ALLOWED_HOSTS permits `.localhost, 127.0.0.1, [::1]`.

### Decisive source
```python
host_validation_re = _lazy_re_compile(
    r"^([a-z0-9.-]+|\[[a-f0-9]*:[a-f0-9.:]+\])(?::([0-9]+))?$")

def split_domain_port(host):
    if match := host_validation_re.fullmatch(host.lower()):
        domain, port = match.groups(default="")
        return domain.removesuffix("."), port   # strip one trailing dot
    return "", ""                                # invalid ⇒ empty domain

def validate_host(host, allowed_hosts):
    return any(pattern == "*" or is_same_domain(host, pattern)
               for pattern in allowed_hosts)
```
`get_host` raises `DisallowedHost("Invalid HTTP_HOST header: %r. You may need to add %r to ALLOWED_HOSTS.")` when the domain fails either the regex or list check.

**Flow:** pick raw host by precedence → lowercase + fullmatch against the strict grammar (domains or bracketed IPv6, optional numeric port; anything else ⇒ domain="") → strip single trailing dot → validate against ALLOWED_HOSTS patterns (`*`, leading-dot subdomain match via `is_same_domain`, exact) → mismatch raises DisallowedHost.
**Invariant:** (1) Grammar validation happens BEFORE allowlist matching — a syntactically invalid host never reaches pattern comparison and cannot smuggle characters into log files or cache keys. (2) X-Forwarded-* headers are trusted only behind explicit settings; default Django ignores them entirely, which IS the anti-spoofing posture. (3) The trailing-dot tolerance mirrors DNS FQDN semantics — exactly one dot removed.
**Probe:** `tests/requests_tests/tests.py::HostValidationTests` (:1306) — direct suite pining every DisallowedHost case, IPv6 hosts, ports, and trailing-dot behavior at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "get_host split_domain_port validate_host DisallowedHost", limit: 10 });
```

## Verdict
Adopt grammar-first-then-allowlist ordering for any host-aware virtual hosting; adapt the regex to your platform's hostname rules; omit X-Forwarded support unless your deployment actually sits behind a trusted proxy. Direct suite cited executed green at this pin.
