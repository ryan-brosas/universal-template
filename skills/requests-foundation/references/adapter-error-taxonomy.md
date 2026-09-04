<!-- capsule-v2 -->
# urllib3 exception taxonomy — which adapter catch arms map each urllib3 error onto which requests exception?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** In `HTTPAdapter.send`, what is the complete exception translation table including MaxRetryError reason inspection?

## HTTPAdapter.send except ladder
**Path/Symbol:** `src/requests/adapters.py:HTTPAdapter.send` (:634-748, excepts at :710-746); class hierarchy in `src/requests/exceptions.py`.
**Signature:** `send(request, stream=False, timeout=None, verify=True, cert=None, proxies=None) -> Response`.

### Decisive source
```python
except (ProtocolError, OSError) as err:
    raise ConnectionError(err, request=request)
except MaxRetryError as e:
    if isinstance(e.reason, ConnectTimeoutError):
        # TODO: Remove this in 3.0.0: see #2811
        if not isinstance(e.reason, NewConnectionError):
            raise ConnectTimeout(e, request=request)   # pure connect-timeout only
    if isinstance(e.reason, ResponseError):
        raise RetryError(e, request=request)
    if isinstance(e.reason, _ProxyError):
        raise ProxyError(e, request=request)
    if isinstance(e.reason, _SSLError):
        raise SSLError(e, request=request)
    raise ConnectionError(e, request=request)
except ClosedPoolError as e:
    raise ConnectionError(e, request=request)
except _ProxyError as e:
    raise ProxyError(e)
except (_SSLError, _HTTPError) as e:
    if isinstance(e, _SSLError):
        raise SSLError(e, request=request)     # pre-urllib3-1.22 branch
    elif isinstance(e, ReadTimeoutError):
        raise ReadTimeout(e, request=request)
    elif isinstance(e, _InvalidHeader):
        raise InvalidHeader(e, request=request)
    else:
        raise                                   # unknown HTTPError re-raised bare
```

**Flow:** ProtocolError/OSError→ConnectionError → MaxRetryError dispatches on `.reason` TYPE: ConnectTimeoutError-but-NOT-NewConnectionError→ConnectTimeout (the exclusion matters: NewConnectionError subclasses ConnectTimeoutError in urllib3, but DNS-refused must stay retryable-as-ConnectionError per issue #2811), ResponseError→RetryError, ProxyError→ProxyError, SSLError→SSLError, default→ConnectionError → ClosedPoolError→ConnectionError → raw _ProxyError→ProxyError → final arm splits legacy SSL vs ReadTimeout vs InvalidHeader vs re-raise.
**Invariant:** Every raised requests exception carries `request=` (and response when present) because `RequestException.__init__` back-fills `self.request = response.request` — callers rely on `.request` for retry logic. The exception HIERARCHY is part of the contract: ConnectTimeout(ConnectionError, Timeout) means catching Timeout catches both timeouts while catching ConnectionError catches connect failures too; ContentDecodingError also subclasses urllib3's BaseHTTPError deliberately.
**Probe:** Direct tests: `tests/test_lowlevel.py` + `tests/test_requests.py::test_connect_timeout`-family exercise arms against httpbin; hierarchy pinned by `tests/test_requests.py` timeout tests asserting isinstance. `grep -c "raise " src/requests/adapters.py` within send region: count lines 711-746 = 12 raise sites.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "MaxRetryError ConnectTimeout NewConnectionError taxonomy", limit: 10 });
```

## Verdict
Adopt the full table INCLUDING the NewConnectionError exclusion and the bare re-raise fallback. Adapt exception names to host's. Omit urllib3<1.22 compat arm only when pinning newer urllib3.
