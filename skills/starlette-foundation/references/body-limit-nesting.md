<!-- capsule-v2 -->
# RequestBodyLimitMiddleware nested-responder handoff — scope-keyed limit coordination

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** When the same app nests two body limits (app-level + route-level), which responder counts bytes and how does the inner limit take over mid-request?

## RequestBodyLimitResponder.__call__ — active-responder adoption
**Path/Symbol:** `starlette/middleware/body_limit.py:RequestBodyLimitResponder.__call__` (:71-102).
**Data Shape:** two scope keys coordinate: `MAX_BODY_SIZE_SCOPE_KEY = "starlette.max_body_size"` (declared limit) and `_BODY_LIMIT_RESPONDER_SCOPE_KEY` (the counting instance). Previous limit value saved/restored in finally.

### Decisive source
```python
active_responder = scope.get(_BODY_LIMIT_RESPONDER_SCOPE_KEY)
if active_responder is not None:
    active_responder.max_body_size = self.max_body_size   # TIGHTEN the existing counter
    if active_responder.total_size > active_responder.max_body_size:
        raise _RequestBodyTooLarge
    return await self.app(scope, receive, send)           # do NOT install a second counter
self.content_length = _get_content_length(scope)
scope[_BODY_LIMIT_RESPONDER_SCOPE_KEY] = self             # first responder owns counting
```

**Flow:** the FIRST responder wraps receive/send; NESTED responders only retune `max_body_size` on the shared counter (route-level tighter-than-app works because Route wraps RequestBodyLimitMiddleware INSIDE app middleware per build_middleware_stack order). Enforcement: pre-read via Content-Length header (:104-106), cumulative via `total_size += len(body)` per http.request message.
**Invariant:** exactly ONE byte counter per request even with N limit layers — a naive port that stacks counters double-counts nothing but breaks the "innermost wins" semantics and leaks scope keys. 413 responses are sent by the OUTER owner only while `response_started` is False; after start, the raw exception propagates (:90-96, :115-122).
**Probe:** `tests/middleware/test_body_limit.py::test_existing_scope_limit_is_restored` (:220), `::test_content_length_is_checked_without_reading_body` (:39), `::test_limit_exceeded_after_response_started_is_raised` (:145).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "receive_with_limit", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "RequestBodyLimitResponder", limit: 5 });
```

## Verdict
Adopt the adopt-or-tighten pattern for ANY layered per-request quota (bytes, time, request counts). Adapt status/exception type to your error model. Omit the Content-Length fast path only if your clients chunk-encode everything anyway.
