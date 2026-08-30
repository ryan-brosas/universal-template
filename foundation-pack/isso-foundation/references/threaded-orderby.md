<!-- capsule-v2 -->
# Parents-first threaded ordering — how do replies always sort under their parent?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How does a single ORDER BY keep every reply immediately after its parent regardless of user-chosen sort?

## CASE-wrapped ORDER BY
**Path/Symbol:** `isso/db/comments.py:Comments.fetch` (lines 297–303) and `Comments.fetchall` (lines 256–267).
**Signature:** shared suffix: `ORDER BY CASE WHEN comments.parent IS NOT NULL THEN comments.created END, <order_by> [DESC][, comments.created]`.
**Data Shape:** `order_by` whitelisted against `[id, created, modified, likes, dislikes, karma]` (fetch) / `[..., tid]` (fetchall); anything else falls back to `created` — the "custom sanitization".

### Decisive source
```python
# custom sanitization
if order_by not in ["id", "created", "modified", "likes", "dislikes", "karma"]:
    order_by = "created"
sql.append("ORDER BY CASE WHEN comments.parent IS NOT NULL THEN comments.created END, ")
sql.append(order_by)
if not asc:
    sql.append(" DESC")
```

**Flow:** the CASE emits NULL for top-level rows and their created-timestamp for replies; in SQLite ASC ordering NULLs come first → all roots first (in chosen sort), then ALL replies grouped after them by the secondary key. Descending sorts flip only the second term.
**Invariant:** The whitelist-before-interpolation is what makes dynamic ORDER BY injection-safe; the CASE prefix is what keeps threads visually coherent. Dropping either breaks the API contract pinned by the sorted-fetch tests.
**Probe:** `grep -c 'ORDER BY CASE WHEN comments.parent IS NOT NULL THEN comments.created END' isso/db/comments.py` (exactly `3`).
**Test:** `isso/tests/test_comments.py:testGetSortedByNewest` / `testGetSortedByUpvotes` / `testGetSortedByNewestWithNested`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "ORDER BY CASE parent created fetch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whitelist + parents-first CASE for any flat-storage thread renderer. Adapt the fallback column. Omit string-appended SQL if you use a query builder, but preserve both semantics.
