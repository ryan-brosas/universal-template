<!-- capsule-v2 -->
# SSRF-guarded egress client — opensocket-level private-IP blocking with a requests-shaped facade

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do all outbound webhook/chat integrations share one HTTP client that (a) refuses to talk to internal networks even after redirects and (b) converts every libcurl error into a human-readable message?

## hc/lib/curl.request + HttpTransport.request
**Path/Symbol:** `hc/lib/curl.py:request` (:55-206), `opensocket` closure (:128-136), `_is_private` (:51-52), error ladder (:184-201); consumer `hc/api/transports.py:HttpTransport._request` (:138-164) and retrying `request` (:166-196).
**Signature:** `request(method: str, url: str, *, params, data, json, headers, auth, timeout) -> Response`; `HttpTransport.request(method, url, *, retry: bool, ...) -> None` (3 tries or 1).
**Data Shape:** Only "get"/"post"/"put" methods; Response carries status_code+content; default UA "healthchecks.io"; json= sets Content-Type and serializes; dict data urlencodes; PROTOCOLS pinned to HTTP|HTTPS.

### Decisive source
```python
# hc/lib/curl.py — the guard is a socket-open callback, not a URL filter
opensocket_rejected_ips = []

def opensocket(purpose: int, curl_address: CurlSockAddr) -> socket.socket | int:
    family, socktype, protocol, address = curl_address
    if not settings.INTEGRATIONS_ALLOW_PRIVATE_IPS and _is_private(address[0]):
        opensocket_rejected_ips.append(address[0])
        return pycurl.SOCKET_BAD
    return socket.socket(family, socktype, socktype.protocol if False else protocol)

c.setopt(pycurl.PROTOCOLS, pycurl.PROTO_HTTP | pycurl.PROTO_HTTPS)
c.setopt(pycurl.OPENSOCKETFUNCTION, opensocket)
c.setopt(pycurl.FOLLOWLOCATION, True)
c.setopt(pycurl.MAXREDIRS, 3)
...
except pycurl.error as e:
    errcode = e.args[0]
    if errcode == pycurl.E_OPERATION_TIMEDOUT:
        raise CurlError("Connection timed out")
    elif errcode == pycurl.E_COULDNT_RESOLVE_HOST:
        raise CurlError("Could not resolve host")
    elif errcode == pycurl.E_COULDNT_CONNECT:
        if opensocket_rejected_ips:
            raise CurlError("Connections to private IP addresses are not allowed")
        raise CurlError("Connection failed")
```

**Flow:** Every integration transport funnels through HttpTransport.request → curl.request with timeout=30. Non-2xx/204 → subclass-overridable `raise_for_response` (Slack marks 404/invalid_token permanent; Pushover 400 user-invalid permanent; Telegram classifies PERMANENT_ERRORS strings and detects chat migrations). The retry loop decrements tries per TransportError UNLESS `e.permanent` (set to 0 immediately); test notifications pass retry=False so "Test!" clicks don't triple-fire.
**Invariant:** Blocking at OPEN-SOCKET time (not DNS-resolution time) is the security core: it re-checks EVERY connection attempt including redirect hops and DNS-rebinding second resolves, because it sees the actual post-connect address. The rejected-ip ledger exists solely to disambiguate E_COULDNT_CONNECT into an honest user-facing message. Error translation is a contract: transports never see raw pycurl codes; users never see stack traces; permanent-ness is how a dead webhook avoids burning retries.
**Probe:** `hc/lib/tests/test_curl.py::test_it_rejects_private_ip` (FakeCurl ip="127.0.0.1", INTEGRATIONS_ALLOW_PRIVATE_IPS=False → exact message assert), `test_it_accepts_private_ip` (True setting passes), `test_it_posts_json`, plus `hc/integrations/slack/tests/test_notify.py::test_it_handles_500` / `test_it_handles_timeout`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "curl request opensocket private ip INTEGRATIONS", limit: 10 });
```
Resolves line-exact: _is_private :51-52 and test pins test_curl.py :159-172.

## Verdict
Adopt socket-callback SSRF blocking over pre-request URL checks, the single translated-error funnel, and permanent-vs-transient retry taxonomy. Adapt to requests/httpx via their connect-hook equivalents (or resolve-then-pin, accepting the weaker guarantee); keep INTEGRATIONS_ALLOW_PRIVATE_IPS as an explicit self-hosted opt-out. Omit the UA default and latin-1 header coercion if your surface differs.
