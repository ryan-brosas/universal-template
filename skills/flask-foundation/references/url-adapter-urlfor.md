<!-- capsule-v2 -->
# URL adapter & url_for — how are trusted hosts enforced and what do the _external/_scheme defaults mean in vs out of a request?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** How is the MapAdapter bound, and how does url_for choose internal/external and handle build errors?

## create_url_adapter + Flask.url_for
**Path/Symbol:** `src/flask/app.py:Flask.create_url_adapter` (510–561), `.url_for` (1105–1225), `.inject_url_defaults` (sansio app.py:960–979), `.handle_url_build_error` (981–1013).
**Signature:** `create_url_adapter(request: Request|None) -> MapAdapter|None`; `url_for(endpoint, *, _anchor=None, _method=None, _scheme=None, _external=None, **values)`.
**Data Shape:** TRUSTED_HOSTS validated by rewriting `request.host = get_host(environ, trusted_hosts)` BEFORE bind; SERVER_NAME no longer restricts matching (3.1).

### Decisive source
```python
if request is not None:
    if (trusted_hosts := self.config["TRUSTED_HOSTS"]) is not None:
        request.trusted_hosts = trusted_hosts
    request.host = get_host(request.environ, request.trusted_hosts)
    subdomain = None; server_name = self.config["SERVER_NAME"]
    if self.url_map.host_matching:
        server_name = None                       # else actual host would be ignored
    elif not self.subdomain_matching:
        subdomain = self.url_map.default_subdomain or ""   # werkzeug has no subdomain match yet
    return self.url_map.bind_to_environ(request.environ, server_name=server_name, subdomain=subdomain)
if self.config["SERVER_NAME"] is not None:
    return self.url_map.bind(SERVER_NAME, script_name=APPLICATION_ROOT,
                             url_scheme=PREFERRED_URL_SCHEME)
return None                                       # no SERVER_NAME → no out-of-request building
```
url_for: leading "." endpoint resolves against `ctx.request.blueprint` IN a request; `_external` defaults False in-request / True outside (`_scheme` forces external); `_scheme` with `_external=False` ⇒ ValueError ("When specifying '_scheme', '_external' must be True."); BuildError funnels special values into handler chain — handlers returning None/raising BuildError are skipped, otherwise their return replaces the URL.

**Flow:** context push binds adapter (failure parked as routing_exception) → url_for injects url_default functions over `(None, *reversed(split path))` → adapter.build → anchor quoted+appended.
**Invariant:** host trust happens at BIND time via header validation, not at match time; without SERVER_NAME, out-of-request url_for raises RuntimeError; unknown `values` become query string.
**Probe:** `grep -Fc 'subdomain = self.url_map.default_subdomain or' src/flask/app.py` = 1; `grep -Fc "must be True." src/flask/app.py` = 1; tests `tests/test_request.py::test_trusted_hosts_config` (:57), `tests/test_helpers.py::test_url_for_with_scheme_not_external` (:112), `tests/test_basic.py::test_build_error_handler` (:1373).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "create_url_adapter trusted hosts url_for build error", limit: 8 });
```

## Verdict
Adopt host-validation-at-bind + in/out-of-request external defaults. Adapt scheme policy. Omit SERVER_NAME legacy semantics pre-3.1.
