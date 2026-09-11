<!-- capsule-v2 -->
# Fail-closed outbound IP classification — which addresses may a server-side fetch ever target?

**Source:** Plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** how do you classify resolved addresses as "never an outbound target" so the verdict is identical across Python versions and IPv6 transition tricks can't smuggle an internal IPv4 through?

## is_blocked_ip + _BLOCKED_NETWORKS + _embedded_ipv4
**Path/Symbol:** `apps/api/plane/utils/ip_address.py`:`is_blocked_ip` (:67–95), `_BLOCKED_NETWORKS` (:16–30), `_embedded_ipv4` (:33–64).
**Signature:** `is_blocked_ip(ip: ipaddress.ip_address) -> bool`; `_embedded_ipv4(ip) -> Iterator[ip_address]`.
**Data Shape:** input is a parsed address object (zone id stripped by the caller); output boolean; recursion into embedded IPv4s. Failure posture: fail closed — anything not positively cleared is blocked.

### Decisive source
```python
# Networks ... which the stdlib ``ipaddress`` flags (is_private/is_loopback/...)
# do NOT reliably classify on every Python version. Listed explicitly so the
# verdict is identical and fail-closed across Python 3.9 – 3.14 (Plane ships on
# 3.12, where e.g. 100.64.0.0/10 is neither is_private nor is_global).
_BLOCKED_NETWORKS = [..., "100.64.0.0/10", ..., "169.254.0.0/16",  # cloud metadata
                     "::ffff:0:0/96", "64:ff9b::/96", "2002::/16", "2001::/32", ...]

def is_blocked_ip(ip):
    if (ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local
            or ip.is_multicast or ip.is_unspecified):
        return True
    if any(ip.version == net.version and ip in net for net in _BLOCKED_NETWORKS):
        return True
    for embedded in _embedded_ipv4(ip):
        if is_blocked_ip(embedded):
            return True
    return False
```

**Flow:** stdlib property check → explicit CIDR denylist for ranges the stdlib misclassifies per-version → decode IPv6 transition formats (`ipv4_mapped`, `sixtofour`, `teredo` client+server, NAT64 well-known /96 low-32 embedding) and recurse — the embedded IPv4 is what the packet ultimately reaches.
**Invariant:** `169.254.169.254`, CGNAT `100.64.0.0/10`, and every IPv6-wrapped form of them must classify blocked identically on any supported interpreter; no allow-by-default.
**Probe:** `apps/api/plane/tests/unit/bg_tasks/test_url_security.py::TestIsBlockedIp` (:45–88) parametrizes 23 blocked forms incl. `64:ff9b::7f00:1`, `2002:a00:1::`, `::ffff:169.254.169.254`, plus 5 public must-pass forms. Not executed this lane (no provisioned Django deps) — pytest.ini runner named honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "blocked private loopback embedded ipv4 transition address", limit: 10, fields: ["signature", "name", "file"] });
```
Observed live at pass 2: ranks `_embedded_ipv4` :33–64 #1 and `is_blocked_ip` :67–95 #2.

## Verdict
Adopt the explicit-CIDR-besides-stdlib + embedded-IPv4-recursion classifier verbatim as a pattern; adapt the CIDR list to your runtime's actual misclassification matrix; omit Plane's specific Python-version commentary once your floor differs.
