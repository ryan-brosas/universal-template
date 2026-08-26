<!-- capsule-v2 -->
# URL scope reconstruction + _HOST_RE trust gate — building request.url from ASGI primitives

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** Which of Host header vs server scope wins when reconstructing the absolute URL, and why does the header get regex-validated?

## URL.__init__ scope branch
**Path/Symbol:** `starlette/datastructures.py:URL.__init__` (:29-66) + `_HOST_RE` (:25).
**Data Shape:** inputs `scheme`, `server=(host,port)`, `path`, `query_string`, `headers[]`; output a composed url string cached in `_url`.

### Decisive source
```python
# Rejects Host header chars (/, ?, #, @, ...) that would let urlsplit
# produce a path differing from scope["path"].          <- the comment IS the contract
_HOST_RE = re.compile(r"^([a-z0-9.-]+|\[[a-f0-9]*:[a-f0-9.:]+\])(?::[0-9]+)?$", re.IGNORECASE)

if host_header is not None and _HOST_RE.fullmatch(host_header):
    netloc = host_header                       # trusted form: use verbatim (keeps port)
elif server is not None:
    host, port = server
    default_port = {"http": 80, "https": 443, "ws": 80, "wss": 443}[scheme]
    netloc = host if port == default_port else f"{host}:{port}"   # default ports omitted
else:
    netloc = None                              # → path?query only, no authority
```

**Flow:** Host header wins when it looks like a bare host[:port]; otherwise fall back to the server tuple with default-port elision; no server info → relative URL. IPv6 hosts match via the bracketed alternative.
**Invariant:** a malicious Host header (`evil.com/#x`, `a@b`) must NOT leak into generated URLs — falling through to `server` keeps redirect/location responses honest. Porters who trust Host unconditionally reintroduce password-reset poisoning.
**Probe:** `tests/test_datastructures.py` (25 tests incl. host-header fallback cases).

## URLPath.make_absolute_url — protocol-aware joining
**Path/Symbol:** `starlette/datastructures.py:URLPath.make_absolute_url` (:189-202).
**Data Shape:** URLPath carries `(path, protocol ∈ {http, websocket, ""}, host)`; scheme picked from `{http:{True:'https',False:'http'}, websocket:{True:'wss',False:'ws'}}[protocol][base.is_secure]`; netloc = route-declared host OR base netloc; path = base.path.rstrip('/') + self.
**Flow:** this is where reverse-routing meets request context: Router.url_path_for returns URLPath; Request.url_for makes it absolute against base_url (built from app_root_path).
**Probe:** `tests/test_routing.py::test_host_reverse_urls` (:479), `::test_url_for` (:275).

## Headers/MutableHeaders raw-list semantics
**Path/Symbol:** `starlette/datastructures.py:Headers` (:500-574), `MutableHeaders.__setitem__/__delitem__/setdefault/append` (:577-661).
**Data Shape:** storage is ALWAYS `list[(bytes,bytes)]` lowercased latin-1; scope construction REPLACES `scope["headers"]` with a list in-place (:522) so later MutableHeaders edits mutate the live response message. `__setitem__` keeps first-occurrence position and deletes duplicates reversed-index; `append` never dedupes (Set-Cookie); `add_vary_header` merges comma-values.
**Invariant:** case-insensitivity comes from normalizing KEYS at every write/read boundary — a porter storing str keys breaks ASGI servers expecting bytes pairs.
**Probe:** `tests/test_datastructures.py` header block.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "_HOST_RE", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "make_absolute_url", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "getlist", limit: 10 });
```

## Verdict
Adopt the validated-Host-first ladder and the raw-bytes-pairs header store as-is. Adapt default-port elision to your schemes table. Omit username/password netloc handling if you reject userinfo URLs at the edge.
