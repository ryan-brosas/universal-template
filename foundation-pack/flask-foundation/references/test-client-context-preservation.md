<!-- capsule-v2 -->
# Test client context preservation — how does `with client:` keep request objects usable after a request?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What environ key wires wsgi_app's finally-hook into the client, and when are preserved contexts closed?

## FlaskClient preserve_context loop
**Path/Symbol:** `src/flask/testing.py:FlaskClient.__init__` (125–133), `.open` (204–247), `__enter__/__exit__` (249–262), `._copy_environ` (185–191), `session_transaction` (135–183).
**Signature:** `open(*args, buffered=False, follow_redirects=False, **kwargs) -> TestResponse`.
**Data Shape:** `environ_base` defaults REMOTE_ADDR 127.0.0.1 + Werkzeug UA; `_new_contexts: list[context manager]`; `_context_stack: ExitStack`.

### Decisive source
```python
def _copy_environ(self, other):
    out = {**self.environ_base, **other}
    if self.preserve_context:
        out["werkzeug.debug.preserve_context"] = self._new_contexts.append
    return out
...
self._context_stack.close()        # pop PREVIOUS request's contexts first
response = super().open(request, ...)
...
for cm in self._new_contexts:      # re-enter contexts captured during THIS request
    self._context_stack.enter_context(cm)
self._new_contexts.clear()
```
wsgi_app's finally calls the environ callable with ctx (app.py:1609–1610); ctx.pop is then DEFERRED because the debugger/preserve hook holds the context (pop runs on stack close).

**Flow:** `with client:` sets flag (nesting forbidden) → each open() injects append-callback via environ → app pushes context, finally hands it to the client instead of popping → after response, previous stack entries close and new ones enter → block exit closes all. session_transaction opens/saves a session through a throwaway test_request_context without dispatching.
**Invariant:** contexts do NOT survive across requests within one with-block (stack.close() per open) — only across the END of the last request until block exit; cookies disabled ⇒ session_transaction TypeError.
**Probe:** `grep -Fc '= self._new_contexts.append' src/flask/testing.py` = 1; `grep -Fc 'self._context_stack.close()' src/flask/testing.py` = 2; `grep -Fc 'app.session_interface.' src/flask/testing.py` = 3; tests `tests/test_testing.py::test_session_transactions` (:157), `::test_session_transactions_keep_context` (:198).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "FlaskClient preserve context session transaction testing", limit: 8 });
```

## Verdict
Adopt the environ-injected callback + ExitStack per-request discipline. Adapt key name to your server contract. Omit FlaskCliRunner (thin click pass-through).
