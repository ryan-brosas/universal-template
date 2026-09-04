<!-- capsule-v2 -->
# Proxy selection & NO_PROXY bypass — how is a proxy picked for a URL and when does no_proxy/CIDR/registry logic veto it?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What key precedence selects a proxy from the map, and what is should_bypass_proxies' full decision ladder?

## utils.select_proxy / resolve_proxies / should_bypass_proxies
**Path/Symbol:** `src/requests/utils.py:select_proxy` (:885-908), `.resolve_proxies` (:911-939), `.should_bypass_proxies` (:810-870), CIDR helpers `address_in_network` (:726-738) / `is_valid_cidr` (:763-784), `get_environ_proxies` (:873-882).
**Signature:** `select_proxy(url, proxies) -> str | None`; `should_bypass_proxies(url, no_proxy: str | None) -> bool`.

### Decisive source
```python
proxy_keys = [
    urlparts.scheme + "://" + urlparts.hostname,   # most specific
    urlparts.scheme,
    "all://" + urlparts.hostname,
    "all",                                         # least specific
]
for proxy_key in proxy_keys:
    if proxy_key in proxies:
        return proxies[proxy_key]                  # first match wins
```
```python
# should_bypass_proxies ladder:
no_proxy = no_proxy or get_proxy("no_proxy")       # lowercase env beats uppercase
if hostname is None: return True                   # file:/// etc.
if no_proxy:
    for proxy_ip in no_proxy_hosts:
        if is_ipv4_address(hostname):
            if is_valid_cidr(proxy_ip) and address_in_network(hostname, proxy_ip): return True
            elif hostname == proxy_ip: return True  # plain IP entry
        else:
            host = host.lstrip(".")                 # leading-dot entries match subdomains
            if hostname == host or host_with_port == host: return True
            host = "." + host
            if hostname.endswith(host) or host_with_port.endswith(host): return True
with set_environ("no_proxy", no_proxy_arg):         # platform bypass w/o DNS surprises
    bypass = proxy_bypass(hostname)
```

**Flow:** four-key specificity order (host-pinned scheme → bare scheme → host-pinned all → all); scheme-less/hostless URLs degrade to `proxies.get(scheme, proxies.get("all"))`. Bypass ladder: explicit arg → env (lowercase preferred for curl/wget parity) → IP-hostname matched by CIDR containment OR literal equality; hostname matched exactly, with-port variant, or dot-anchored suffix (`lstrip(".")` then re-anchor with leading dot so `prelocalhost` does NOT match `localhost` — CPython bpo-39057 boundary rule) → platform `proxy_bypass` under a scoped env override.
**Invariant:** The lstrip-then-redot anchoring is what makes `.d.o.t` match subdomains but NOT strings merely ENDING in the label — dropping the redot step reintroduces the greedy-suffix bug. `resolve_proxies` layers env proxies via setdefault ONLY (request-level keys always win) and consults this bypass BEFORE adding anything.
**Probe:** Direct tests: `tests/test_utils.py::test_should_bypass_proxies_no_proxy` ×10 (:838), `_domain_boundary` ×9 incl. `prelocalhost` negative (:861), `test_bypass_no_proxy_keyword`/:263 & `_not_bypass`/:277 pairs, TestIsIPv4Address/TestIsValidCIDR. `grep -n 'lstrip("\\.")' src/requests/utils.py` → 1 hit (:854).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "should_bypass_proxies", limit: 10 });
```

## Verdict
Adopt four-key precedence + anchored suffix matching + CIDR arm verbatim. Adapt env var names/platform bypass to host OS layering. Omit winreg details unless porting to Windows.
