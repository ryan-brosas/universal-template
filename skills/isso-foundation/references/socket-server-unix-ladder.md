<!-- capsule-v2 -->
# AF_UNIX server ladder — how does isso serve WSGI over a Unix socket without breaking remote-addr?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `isso`. **Question:** Which class flags and handler overrides make a stdlib HTTPServer usable for werkzeug on `unix://`?

## SocketHTTPServer + SocketWSGIRequestHandler + Request
**Path/Symbol:** `isso/wsgi.py:SocketHTTPServer` (:150-171), `SocketWSGIRequestHandler` (:144-147), `Request` (:137-141). Sole caller: `main()` unix:// branch (trace-verified).
**Signature:** `SocketHTTPServer(sock, app)`; handler override `run_wsgi(self)`.
**Data Shape:** `sock` is the filesystem path after stripping `unix://`; class-level flags feed werkzeug's request handler.

### Decisive source
```python
class Request(_Request):
    # Assuming UTF-8, comments with 65536 characters would consume
    # 128 kb memory. The remaining 128 kb cover additional parameters
    # and WSGI headers.
    max_content_length = 256 * 1024

class SocketWSGIRequestHandler(WSGIRequestHandler):
    def run_wsgi(self):
        self.client_address = ("<local>", 0)     # Unix sockets have NO peer address
        super(SocketWSGIRequestHandler, self).run_wsgi()

class SocketHTTPServer(HTTPServer, ThreadingMixIn):
    multithread = True
    multiprocess = False
    allow_reuse_address = 1
    try:
        address_family = socket.AF_UNIX
    except AttributeError:
        address_family = socket.AF_INET
    request_queue_size = 128

    def __init__(self, sock, app):
        HTTPServer.__init__(self, sock, SocketWSGIRequestHandler)
        self.app = app
        self.ssl_context = None
        self.shutdown_signal = False
```

**Flow:** `main()` unlinks any stale socket file → constructs the server with the path as address → stdlib bind/listen with backlog 128 → per-connection threads via ThreadingMixIn → before werkzeug builds the WSGI environ, `run_wsgi` substitutes a synthetic `("<local>", 0)` peer so `REMOTE_ADDR`-style plumbing never sees an unusable Unix-socket tuple.
**Invariant:** The client-address fake happens BEFORE `super().run_wsgi()` — afterwards is too late. Class-body `try/except AttributeError` picks AF_UNIX at import time and degrades to AF_INET where Unix sockets don't exist. `ssl_context=None`/`shutdown_signal=False` exist to satisfy attributes werkzeug's handler expects. Body cap: 256 KB total request memory budget.
**Probe:** `grep -c '("<local>", 0)' isso/wsgi.py` → `1`; `grep -c 'request_queue_size = 128' isso/wsgi.py` → `1`.
**Test:** none upstream — server classes are uncovered (`wsgi.host` is even `# pragma: no cover`) (coverage caveat; deterministic probes only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "isso", query: "SocketHTTPServer ThreadingMixIn AF_UNIX run_wsgi client_address", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the flag set + pre-dispatch peer-address fake for any Unix-socket WSGI deployment. Adapt backlog/limits to your traffic. Omit the AF_INET fallback only on platforms you've proven to expose AF_UNIX.
