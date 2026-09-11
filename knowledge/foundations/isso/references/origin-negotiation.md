<!-- capsule-v2 -->
# Origin negotiation — how does Isso decide which Origin/Referer to trust and echo?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How are configured hosts matched against the request, and what is the fallback?

## origin(hosts) closure
**Path/Symbol:** `isso/wsgi.py:origin` (66–89) with `urlsplit`/`urljoin` (38–63); consumed by CORSMiddleware and `local("origin")`.
**Signature:** `origin(hosts) -> func(environ) -> str`; hosts pre-split to `(netloc, port, ssl)` triples.
**Data Shape:** match key = EXACT triple equality of the incoming Origin or Referer (parsed via the same urlsplit) against each configured `[general] host`.

### Decisive source
```python
def origin(hosts):
    hosts = [urlsplit(h) for h in hosts]
    def func(environ):
        if not hosts:
            return "http://invalid.local"
        loc = environ.get("HTTP_ORIGIN", environ.get("HTTP_REFERER", None))
        if loc is None:
            return urljoin(*hosts[0])
        for split in hosts:
            if urlsplit(loc) == split:
                return urljoin(*split)
        else:
            return urljoin(*hosts[0])
    return func
```

**Flow:** prefer Origin header, else Referer; exact-triple match → reflect THAT host canonically; no header or no match → FIRST configured host. CORS middleware emits this value per-request as Access-Control-Allow-Origin WITH credentials=true — so untrusted origins never get echoed.
**Invariant:** The allowlist is closed: output is always one of the CONFIGURED canonical forms (`urljoin` re-adds default ports only when nonstandard), never the raw client string. Empty host list yields a dead sentinel origin rather than an open relay.
**Probe:** `grep -cF 'urljoin(*hosts[0])' isso/wsgi.py` (exactly `2`: no-header + no-match fallbacks).
**Test:** `isso/tests/test_wsgi.py:test_origin`, `test_urlsplit`, `test_urljoin`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "origin HTTP_ORIGIN referer urlsplit hosts", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt allowlist-reflect-or-default origin resolution wherever CORS-credentials endpoints exist. Adapt header precedence to your threat model. Omit wildcard echoes entirely.
