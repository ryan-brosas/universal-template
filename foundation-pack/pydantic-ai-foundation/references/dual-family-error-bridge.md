<!-- capsule-v2 -->
# Dual-family HTTP error bridge — how do you migrate HTTP stacks while old `except` clauses keep firing?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you swap `httpx`→`httpx2` underneath users without breaking their existing exception handlers?

## dual-family-error-bridge
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_ssrf.py:` `_compatible_request_error_init` (:136–139), `_compatible_http_status_error_init` (:141–147), `_Compatible*Error = type(...)` factories (:150–170), `_send_request` (:177–181), `_read_body` (:184–189), `_aiter_raw` (:748–757); consumer `safe_download` (:663–669).
**Signature:** `_CompatibleRequestError = type('_CompatibleRequestError', (httpx2.RequestError, legacy_httpx.RequestError), {'__init__': _compatible_request_error_init})` — dynamic dual-inheritance classes built ONLY when legacy `httpx` is installed; otherwise plain `httpx2` errors are used directly.
**Data Shape:** bridge init writes `self.__dict__['_request']` (the private backing field of the `request` property in BOTH libraries) and `__dict__['response']`, calling `Exception.__init__` directly.

### Decisive source
```python
# These initialize classes inheriting from both HTTPX families, so they call `Exception.__init__`
# directly: `super().__init__` would walk a diamond MRO spanning two libraries and run only the
# first family's initializer.
def _compatible_request_error_init(self, message, *, request=None):
    Exception.__init__(self, message)
    self.__dict__['_request'] = request

async def _aiter_raw(response):
    try:
        async for raw in response.aiter_raw():
            yield raw
    except httpx2.RequestError as e:
        raise _compatible_request_error(e) from e
```

**Flow:** `safe_download` sends/reads through helpers that catch `httpx2.RequestError` and re-raise the dual-family type → `raise_for_status` failures are re-wrapped into `_CompatibleHTTPStatusError(str(e), request=…, response=…)` (:668–669) → user code written against either library's exception hierarchy matches.
**Invariant:** four rules:
1. Diamond-MRO trap: `super().__init__` on a class inheriting both families' errors runs only the FIRST family's `__init__` — call `Exception.__init__` explicitly and poke the `_request` backing field yourself. An upstream rename of `_request` breaks this silently (their comment says exactly that).
2. Translation must live INSIDE the streaming generator (`_aiter_raw`), not around the consuming loop — errors the loop body raises itself (size cap, malformed gzip) must keep their own types.
3. Subclass identity is deliberately NOT preserved across the bridge: `RequestError`s are re-raised "at family level", so handlers must catch `httpx2.RequestError` itself, not `ConnectError` etc. (documented in `safe_download`'s Raises block :583–589).
4. Every escape point needs bridging: send (:177), body read (:184), raw-stream iteration (:748), status raise (:668), AND the zlib gzip-decode errors, which construct `_CompatibleDecodingError` directly instead of `httpx.DecodingError`.
**Probe:** `tests/test_httpx2_sdk_readiness.py` (294 lines, whole-file new) pins family-level behavior across SDK surfaces; `tests/models/test_instrumented.py` covers stream-cancel error tuples including both families.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "safe_download RequestError DecodingError dual family", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bridge whenever you replace an HTTP library under public APIs mid-era: dual-inheritance + explicit `Exception.__init__` + private-backing-field pokes + generator-scoped translation; adapt the specific exception pairs to your libraries; omit the bridge entirely once the migration window closes (pydantic-ai marks it TODO(v3)).
