<!-- capsule-v2 -->
# CSRF via Content-Type — how does a JSON-only body requirement defeat form-forgery?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** Why is checking `Content-Type: application/json` sufficient CSRF protection for POST/PUT/DELETE?

## xhr decorator
**Path/Symbol:** `isso/views/comments.py:xhr` (lines 58–84); applied to new/edit/delete/like/dislike.
**Signature:** `dec(self, env, req, *args, **kwargs)` raising Forbidden unless content type starts with `application/json`.
**Data Shape:** browsers can only send `application/x-www-form-urlencoded`, `multipart/form-data`, or `text/plain` from cross-site `<form>` submissions.

### Decisive source
```python
def dec(self, env, req, *args, **kwargs):
    if req.content_type and not req.content_type.startswith("application/json"):
        raise Forbidden("CSRF")
    return func(self, env, req, *args, **kwargs)
```

**Flow:** forged `<form>` POST arrives with a browser-mandated form Content-Type → rejected before handler runs; real XHR/fetch callers already send `application/json` (CORS separately constrains which origins may read responses). Note the guard passes when `content_type` is FALSY — absent header + empty body still reaches handlers like `moderate` POST (`xhr.send(null)`).
**Invariant:** Mutating endpoints must never rely on cookies alone; the Content-Type gate is the CSRF boundary. Combined with CORS middleware exposing only `X-Set-Cookie`/`Date`, cross-origin writes fail and cross-origin reads of error text are limited.
**Probe:** `grep -c 'startswith("application/json")' isso/views/comments.py` (exactly `1`).
**Test:** `isso/tests/test_comments.py:testCSRF` (form-encoded downvote → 403).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "xhr csrf forbidden content_type", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any cookie-authenticated JSON API. Adapt the allowed set if you support other safe encodings. Omit nothing — one predicate, one exception.
