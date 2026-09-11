<!-- capsule-v2 -->
# Trusted-proxy remote address — how is the client IP recovered behind a reverse proxy?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How should X-Forwarded-For be walked, and where is anonymization applied?

## Reverse walk to first non-proxy
**Path/Symbol:** `isso/views/comments.py:API._remote_addr` (lines 466–478); `isso/utils/__init__.py:anonymize` (lines 21–39).
**Signature:** `_remote_addr(request) -> str` (already anonymized).
**Data Shape:** `[server] trusted-proxies` = list of proxy IPs; `access_route` = XFF chain + socket peer.

### Decisive source
```python
remote_addr = request.remote_addr
if self.trusted_proxies:
    route = request.access_route + [remote_addr]
    remote_addr = next((addr for addr in reversed(route) if addr not in self.trusted_proxies), remote_addr)
return utils.anonymize(str(remote_addr))

def anonymize(remote_addr):
    ipv4 = ipaddress.IPv4Address(remote_addr)
    return "".join(ipv4.exploded.rsplit(".", 1)[0]) + "." + "0"   # /24
    # IPv6: /48 via exploded.rsplit(":", 5)[0] + ":" + "0000"*5 ; mapped-v4 unwrapped first
```

**Flow:** walk the hop chain RIGHT-TO-LEFT and take the FIRST address that is not a trusted proxy (closest hop appended by the last trusted proxy wins; untrusted spoofed prefixes are skipped past) → immediately zero out host bits (/24 v4, /48 v6) before anything touches storage or guard queries. Unparseable input falls back to `0.0.0.0`.
**Invariant:** Trust decisions use ONLY configured proxies — never blanket-trust XFF; anonymization happens at acquisition so every downstream consumer (guard rate limits, vote blobs, hash keys, migrate imports) sees only truncated addresses.
**Probe:** `grep -cF 'reversed(route) if addr not in self.trusted_proxies' isso/views/comments.py` (`1`); `grep -c 'ipv6.ipv4_mapped' isso/utils/__init__.py` (`2`).
**Test:** `isso/tests/test_utils.py:test_anonymize`; FakeIP harness in `test_vote.py`/`test_guard.py` drives distinct IPs through the full stack.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "_remote_addr access_route trusted proxies anonymize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt right-to-left walk with explicit trust list + anonymize-at-ingestion. Adapt truncation lengths to your privacy policy. Omit direct XFF trust without configuration.
