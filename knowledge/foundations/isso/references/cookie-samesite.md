<!-- capsule-v2 -->
# Cookie SameSite ladder — how are cookies made to survive cross-site embeds?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How does the Set-Cookie policy differ between https and http deployments, and why dual headers?

## create_cookie partial
**Path/Symbol:** `isso/views/comments.py:API.create_cookie` (lines 480–495); emission in `new` (:462–463), `edit` (:627–628), `delete` (:698–701).
**Signature:** `create_cookie(**kwargs) -> functools.partial(dump_cookie, secure=?, samesite=?)`.
**Data Shape:** every auth cookie is emitted TWICE — `Set-Cookie: <id>=...` and `X-Set-Cookie: isso-<id>=...` (the X- twin lets client JS read it when HttpOnly-style handling hides the first; CORS exposes `X-Set-Cookie`).

### Decisive source
```python
samesite = self.isso.conf.get("server", "samesite")
if isso_host_script.startswith("https://"):
    secure = True
    samesite = samesite or "None"
else:
    secure = False
    samesite = samesite or "Lax"
return functools.partial(dump_cookie, **kwargs, secure=secure, samesite=samesite)
```

**Flow:** public-endpoint https → `Secure; SameSite=None` (required combo — None without Secure is rejected by browsers, per the docstring's MDN link) → cookies survive third-party embed context. Plain http → `SameSite=Lax`. Deletion reuses the same factory with `expires=0, max_age=0`.
**Invariant:** The secure/samesite pairing must move together; overriding one without the other breaks either embedding or security. Admin session uses the SAME factory with an explicit expiry (`datetime.now()+timedelta(1)`).
**Probe:** `grep -cF 'samesite = samesite or "None"' isso/views/comments.py` (exactly `1`).
**Test:** exercised via create/edit/delete flows (cookie round-trip in test_comments); no isolated unit — coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "create_cookie dump_cookie samesite secure", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt scheme-derived cookie attributes for embeddable widgets. Adapt names. Omit the X-Set-Cookie twin only if your clients never need JS-visible tokens.
