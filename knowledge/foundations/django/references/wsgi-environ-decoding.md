<!-- capsule-v2 -->
# WSGI environ decoding + script-name recovery — how do latin1-mangled environ values and mod_rewrite'd paths get back to real URLs?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** PEP 3333 environ strings are latin1-decoded bytes — how does Django recover UTF-8 paths, and how does it reconstruct SCRIPT_NAME when Apache rewrote the URL?

## Environ byte-recovery and script-name ladder
**Path/Symbol:** `django/core/handlers/wsgi.py` — `get_bytes_from_wsgi` (187–197), `get_str_from_wsgi` (200–207), `get_path_info` (147–151), `get_script_name` (154–184), `WSGIRequest.__init__` (57–80).
**Signature:** `get_bytes_from_wsgi(environ, key, default) -> bytes`; `get_script_name(environ) -> str`; `WSGIRequest(environ)`.
**Data Shape:** PATH_INFO/QUERY_STRING/HTTP_COOKIE round-trip through `encode("iso-8859-1")` (→ decode as needed); `repercent_broken_unicode(path_info).decode()` fixes invalid sequences; `LimitedStream(wsgi.input, content_length)` bounds the body with malformed CONTENT_LENGTH defaulting to 0.

### Decisive source
```python
def get_script_name(environ):
    if settings.FORCE_SCRIPT_NAME is not None:
        return settings.FORCE_SCRIPT_NAME
    # Apache's mod_rewrite set either SCRIPT_URL or REDIRECT_URL to the full
    # resource URL before applying any rewrites.
    script_url = get_bytes_from_wsgi(environ, "SCRIPT_URL", "") or \
                 get_bytes_from_wsgi(environ, "REDIRECT_URL", "")
    if script_url:
        if b"//" in script_url:
            # mod_wsgi squashes multiple successive slashes in PATH_INFO,
            # do the same with script_url before manipulating paths (#17133).
            script_url = _slashes_re.sub(b"/", script_url)
        path_info = get_bytes_from_wsgi(environ, "PATH_INFO", "")
        script_name = script_url.removesuffix(path_info)
    else:
        script_name = get_bytes_from_wsgi(environ, "SCRIPT_NAME", "")
    return script_name.decode()
```
and the request path assembly: `self.path = "%s/%s" % (script_name.rstrip("/"), path_info.replace("/", "", 1))` — replace only the FIRST slash because `http://test/something` vs `http://test//something` differ per RFC 3986.

**Flow:** FORCE_SCRIPT_NAME short-circuit → prefer rewrite-origins (SCRIPT_URL/REDIRECT_URL) → squash doubled slashes to match mod_wsgi's PATH_INFO mangling → subtract PATH_INFO suffix → fall back to raw SCRIPT_NAME.
**Invariant:** (1) Every environ read must go through the iso-8859-1 re-encode; reading `environ[key]` directly silently corrupts non-ASCII. (2) Empty PATH_INFO means "/" was requested (script-root without trailing slash), not an error. (3) The slash-squash applies ONLY to script_url, never to PATH_INFO itself.
**Probe:** `tests/handlers/tests.py::ScriptNameTests.test_get_script_name` (:281) and `.test_get_script_name_double_slashes` (:290); `tests/handlers/tests.py::HandlerTests.test_non_ascii_query_string` (:38) and `.test_non_ascii_cookie` (:61).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "get_script_name LimitedStream repercent_broken_unicode", limit: 10 });
```

## Verdict
Adopt the latin1 round-trip and rewrite-origin script-name recovery for any WSGI-compatible front end; adapt variable names to your server contract; omit REDIRECT_URL handling if no rewriting proxy exists upstream. Direct tests cited executed green at this pin.
