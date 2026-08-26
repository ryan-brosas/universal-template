<!-- capsule-v2 -->
# Exception hierarchy & context — what does RequestException carry and which multi-inheritance shapes define retry semantics?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** How do requests exceptions attach request/response context and why are ConnectTimeout/ContentDecodingError doubly-rooted?

## exceptions module
**Path/Symbol:** `src/requests/exceptions.py` full module (:1-162): RequestException (:19-35), ConnectTimeout (:91-95), ReadTimeout (:97-99), ContentDecodingError (:139-141), StreamConsumedError (:143-145), JSONDecodeError (:43-63).
**Signature:** `RequestException(*args, response=None, request=None)`.
**Data Shape:** Every exception carries `.response: Response | None` and `.request: Request | PreparedRequest | None`.

### Decisive source
```python
class RequestException(IOError):
    def __init__(self, *args, **kwargs):
        response = kwargs.pop("response", None)
        self.response = response
        self.request = kwargs.pop("request", None)
        if response is not None and not self.request and hasattr(response, "request"):
            self.request = response.request     # back-fill from response
        super().__init__(*args, **kwargs)

class ConnectTimeout(ConnectionError, Timeout):
    """Requests that produced this error are safe to retry."""
class ReadTimeout(Timeout):
    """The server did not send any data in the allotted amount of time."""
class ContentDecodingError(RequestException, BaseHTTPError): ...
class MissingSchema(RequestException, ValueError): ...
class InvalidURL(RequestException, ValueError): ...
```

**Flow:** adapter raises with `request=` kwargs → constructor pops response/request, back-fills request from response when omitted → callers catch broad (`RequestException`) or precise. Hierarchy encodes retry policy: catching Timeout catches BOTH timeouts; catching ConnectionError catches connect failures INCLUDING ConnectTimeout via MRO; ContentDecodingError also subclasses urllib3's BaseHTTPError so legacy urllib3-except code keeps working; URL-shape errors additionally subclass ValueError for input-validation catch sites.
**Invariant:** IOError base means `except OSError` catches transport failures — deliberate py3 convergence. JSONDecodeError must construct the compat error FIRST then InvalidJSONError from *self.args*, and override `__reduce__` to the compat class or pickling breaks (MRO would pick IOError's reduce). Porters who flatten the diamond lose documented `except Timeout` / `except ConnectionError` semantics.
**Probe:** Direct tests: `tests/test_requests.py::test_connect_timeout` (:2581 asserts isinstance BOTH ConnectionError and Timeout — the diamond contract), `::test_json_decode_errors_are_serializable_deserializable` (:3087 pins __reduce__ pickle round-trip); `grep -n "class ConnectTimeout" src/requests/exceptions.py` → 1 hit (:91).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "RequestException response request context", limit: 10 });
```

## Verdict
Adopt the diamond hierarchy and context back-fill exactly. Adapt names but keep the Timeout/ConnectionError split points. Omit nothing — inheritance IS the API.
