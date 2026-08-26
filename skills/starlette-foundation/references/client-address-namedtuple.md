<!-- capsule-v2 -->
# client Address NamedTuple — how do I expose the peer address when the server may not provide one?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** What should `request.client` return when `scope["client"]` is absent or None, and what type makes both tuple-code and attribute-code work?

## client property + Address
**Path/Symbol:** `starlette/requests.py:HTTPConnection.client` (:161-167); `starlette/datastructures.py:Address` (:13-15).
**Signature:** `@property def client(self) -> Address | None`; `class Address(NamedTuple): host: str; port: int`.
**Data Shape:** scope["client"] is a `(host, port)` 2-tuple per ASGI spec, or missing/None.

### Decisive source
```python
class Address(NamedTuple):
    host: str
    port: int

@property
def client(self) -> Address | None:
    # client is a 2 item tuple of (host, port), None if missing
    host_port = self.scope.get("client")
    if host_port is not None:
        return Address(*host_port)
    return None
```

**Flow:** property reads the scope leniently (`get`, tolerating absent AND explicit None) → wraps the raw pair in Address so callers get BOTH tuple unpacking (`host, port = request.client`) and attribute access (`request.client.host`) → None propagates untouched for test scopes and non-network transports.
**Invariant:** absence is a valid steady state, not an error — every consumer must branch on None (e.g. rate limiters fall back to a sentinel key). Returning a NamedTuple (not a plain tuple) keeps full backward compat with tuple-expecting code while upgrading attribute ergonomics and typing.
**Probe:** `tests/test_requests.py::test_request_client` (:68-79 — parametrized over present pair, explicit None, and missing key).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", namePattern: "^Address$", limit: 5 });
await mcp.codebase_memory.trace_path({ project: "starlette", function_name: "client", direction: "inbound", depth: 2 });
```

## Verdict
Adopt the get-lenient/None-preserving wrapper for any optional scope datum. Adapt Address into a frozen dataclass if you need methods, but keep NamedTuple-compatible construction. Omit proxy-header resolution (X-Forwarded-For) from this layer — upstream keeps it out of the core property on purpose; that belongs in your deployment middleware.
