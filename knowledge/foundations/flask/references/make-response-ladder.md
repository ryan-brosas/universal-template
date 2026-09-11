<!-- capsule-v2 -->
# make_response conversion — what return shapes are legal and who wins between body-status-headers?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** How is an arbitrary view return value converted to a Response, and in what order do tuple members override?

## Return-value ladder with tuple unpack
**Path/Symbol:** `src/flask/app.py:Flask.make_response` (1227–1367).
**Signature:** `make_response(rv: ResponseReturnValue) -> Response` (module helper `flask.helpers.make_response` :151–197 forwards 0/1/n args to this).
**Data Shape:** accepts str|bytes|bytearray, dict, list, Iterator (stream), Response subclass, other BaseResponse, WSGI callable; optional tuple `(body, status, headers)`.

### Decisive source
```python
if isinstance(rv, tuple):
    if len_rv == 2:
        if isinstance(rv[1], (Headers, dict, tuple, list)):
            rv, headers = rv          # second slot = HEADERS
        else:
            rv, status = rv           # second slot = STATUS
...
elif isinstance(rv, (dict, list)):
    rv = self.json.response(rv)
elif isinstance(rv, BaseResponse) or callable(rv):
    rv = self.response_class.force_type(rv, request.environ)
```
After conversion: explicit `status` overrides (`rv.status_code`), then `rv.headers.update(headers)`.

**Flow:** unpack tuple (3-tuple direct; 2-tuple disambiguated by second element's type; else TypeError) → None ⇒ TypeError naming the endpoint → str/bytes→Response ctor; dict/list→JSON provider response; iterator→streaming response; foreign Response/WSGI callable→force_type → apply status → extend headers.
**Invariant:** the app's `response_class` is used for EVERY conversion (substitutable); a returned Response instance of the right class passes through untouched — status/headers from the tuple only patch it. `None` is never legal.
**Probe:** `grep -Fc 'elif isinstance(rv, (dict, list)):' src/flask/app.py` = 1; `grep -Fc 'return a valid response. The function either returned' src/flask/app.py` = 1; `tests/test_basic.py::test_response_type_errors` (:1238).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "make_response tuple status headers", limit: 6 });
```

## Verdict
Adopt the full ladder incl. the 2-tuple type-disambiguation rule (porters guess wrong). Adapt JSON conversion to your provider. Omit nothing.
