<!-- capsule-v2 -->
# WSGI pipeline — where exactly do push, dispatch, error handling, and pop happen relative to the response?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What is the exact ordering contract of `wsgi_app` that a WSGI-compatible reimplementation must not break?

## wsgi_app try/except/finally ladder
**Path/Symbol:** `src/flask/app.py:Flask.wsgi_app` (1569–1619) + `__call__` (1621–1628).
**Signature:** `wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> Iterable[bytes]`.
**Data Shape:** environ dict in; iterable of bytes out; `error: BaseException|None` captured across two nested try blocks; debugger preserve-context hook read from environ in finally.

### Decisive source
```python
ctx = self.request_context(environ)
error: BaseException | None = None
try:
    try:
        ctx.push()
        response = self.full_dispatch_request(ctx)
    except Exception as e:
        error = e
        response = self.handle_exception(ctx, e)
    except:                                # BaseException: mark error, RE-RAISE
        error = sys.exc_info()[1]
        raise
    return response(environ, start_response)   # response sent INSIDE try
finally:
    if "werkzeug.debug.preserve_context" in environ:
        environ["werkzeug.debug.preserve_context"](ctx)
    ...
    ctx.pop(error)                          # teardown AFTER response bytes flow
```

**Flow:** build context → push (routing+session) → full_dispatch → on Exception convert to 500/error response; on BaseException re-raise but still remember error → send response via `response(environ, start_response)` → finally: hand ctx to debugger if asked → pop with the original error so every teardown func receives it.
**Invariant:** `ctx.pop()` always runs, even for GeneratorExit/KeyboardInterrupt, and receives the ORIGINAL exception (`error`), not the 500 conversion; middleware must wrap `app.wsgi_app`, not `__call__`, or they lose this contract.
**Probe:** `grep -Fc 'ctx.pop(error)' src/flask/app.py` = 1 and `grep -Fc 'error = sys.exc_info()[1]' src/flask/app.py` = 1; `tests/test_basic.py::test_baseexception_error_handling` (:948) pins the BaseException boundary.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "wsgi_app full dispatch request error handling", limit: 8 });
```

## Verdict
Adopt the push→dispatch→send→pop-in-finally shape with error passthrough. Adapt the environ key name for context preservation to your debugger's convention. Omit the FLASK_RUN_FROM_CLI guard in `run()` (dev-server product behavior).
