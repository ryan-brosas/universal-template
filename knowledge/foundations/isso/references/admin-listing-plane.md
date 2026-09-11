<!-- capsule-v2 -->
# Admin listing plane — how does the admin UI page, sort, search, and protect itself?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What does fetchall expose to the admin, and what are the auth + enrichment rules?

## admin view + Comments.fetchall
**Path/Symbol:** `isso/views/comments.py:API.admin` (1524–1569); `isso/db/comments.py:fetchall` (208–276); login (:1476–1490).
**Signature:** `admin(env, req)` reads page/mode/order_by/asc/comment_search_url; `fetchall(mode=5, after=0, parent="any", order_by="id", limit=100, page=0, asc=1, comment_id=None, thread_uri=None) -> iterator[dict]`.
**Data Shape:** rows joined with threads (uri+title); LIMIT ?,? offset pagination; per-row `comment["hash"] = self.isso.sign(comment["id"])` (a moderation LINK token, not an identity hash).

### Decisive source
```python
try:
    data = self.isso.unsign(req.cookies.get("admin-session", ""), max_age=60 * 60 * 24)
except BadSignature:
    return render_template("login.html", ...)
if not data or not data["logged"]:
    return render_template("login.html", ...)
...
if comment_search_url:
    comment_id = get_comment_id_from_url(comment_search_url)
    uri = get_uri_from_url(comment_search_url)
    if comment_id or uri:
        comments = self.comments.fetchall(comment_id=comment_id, thread_uri=uri)
```

**Flow:** admin-session cookie (24h max-age, signed dict {"logged": True}) gates rendering; listing supports mode filter (default 2=pending queue), page×100 paging, whitelisted ordering, and URL search that splits a pasted comment URL into fragment-id (`#isso-<id>`) + path and routes to the id/uri branches of fetchall. Login is form-password against `[admin] password`, sets the same cookie factory; disabled admin renders a stub.
**Invariant:** The admin's "hash" column is deliberately a signed single-use-ish link key for moderate URLs — do NOT confuse with the public author hash. Search-by-URL tolerates thread-only paths (comment_id None) via the OR branch.
**Probe:** anchor `grep -n 'def fetchall' isso/db/comments.py | wc -l` (`1`) plus `grep -c 'comment_search_url' isso/views/comments.py` (`4`).
**Test:** exercised by testModify/testCounts indirectly; admin HTML flows untested offline (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "admin fetchall mode page comment_search_url", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt signed-link tokens in admin tables + fragment-aware URL search. Adapt auth to your SSO. Omit form-password login if you front it with real auth.
