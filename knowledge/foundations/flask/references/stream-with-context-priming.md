<!-- capsule-v2 -->
# stream_with_context — how can a generator keep using `request` after the request context would normally be gone?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What is the push/prime/finally choreography that keeps the context alive during response streaming?

## Generator priming trick
**Path/Symbol:** `src/flask/helpers.py:stream_with_context` (63–148).
**Signature:** accepts an iterator OR a generator function (decorator form via TypeError fallback); returns a wrapped iterator.
**Data Shape:** inner `generator()` re-pushes the CAPTURED AppContext; the outer wrapper is advanced exactly once BEFORE returning.

### Decisive source
```python
def generator():
    if (ctx := _cv_app.get(None)) is None:
        raise RuntimeError("'stream_with_context' can only be used ...")
    with ctx:                       # re-pushes the SAME context object
        yield None                  # prime point
        try:
            yield from gen
        finally:
            if hasattr(gen, "close"):
                gen.close()         # clean up user WSGI iterators too

wrapped_g = generator()
next(wrapped_g)                     # execute TO the sentinel NOW, while ctx active
return wrapped_g
```

**Flow:** called inside view → capture ctx → create wrapper → advance to first yield immediately (this is what captures the context and pushes it) → Response iterates later; every subsequent `next()` resumes INSIDE `with ctx` → on exhaustion/abort, user generator closed.
**Invariant:** the context is captured at CALL time (inside the request), not at iteration time; headers must be finalized before streaming starts (no Set-Cookie from the generator — session writes there are lost); double-use of `ctx` here is why `_push_count` exists.
**Probe:** `grep -Fc 'wrapped_g = generator()' src/flask/helpers.py` = 1 (assignment; next line advances); `grep -Fc 'hasattr(gen, "close")' src/flask/helpers.py` = 1; tests `tests/test_helpers.py::test_streaming_with_context` (:229), `::test_streaming_with_context_and_custom_close` (:256), `::test_stream_keeps_session` (:287).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "stream_with_context generator request context", limit: 6 });
```

## Verdict
Adopt prime-then-return + finally-close. Adapt the RuntimeError wording/guard to your framework's context check. Omit the decorator-form overload plumbing if your API takes iterators only.
