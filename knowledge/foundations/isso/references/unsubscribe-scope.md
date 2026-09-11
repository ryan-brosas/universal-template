<!-- capsule-v2 -->
# Reply unsubscribe scope — what does one unsubscribe link actually switch off?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** Which rows flip `notification=0` when a reader clicks the List-Unsubscribe link?

## id-OR-parent update
**Path/Symbol:** `isso/db/comments.py:Comments.unsubscribe` (lines 171–177).
**Signature:** `unsubscribe(email, id) -> None`.
**Data Shape:** single UPDATE; matches the subscriber's email against BOTH the comment with that id and every comment whose parent is that id.

### Decisive source
```python
def unsubscribe(self, email, id):
    self.db.execute(
        ["UPDATE comments SET", "    notification=0", "WHERE email=? AND (id=? OR parent=?);"], (email, id, id)
    )
```

**Flow:** the emailed link targets the PARENT comment (`/id/<parent-id>/unsubscribe/...`, minted in notifications.create_headers); the OR-parent clause clears the flag for the parent itself and all of the subscriber's direct replies under it — matching the depth-1 thread model.
**Invariant:** Email is part of the predicate: a subscriber can only mute their OWN notification flag, never someone else's row; the endpoint additionally verifies the signed `(unsubscribe, email)` token before reaching this method.
**Probe:** `grep -c 'WHERE email=? AND (id=? OR parent=?);' isso/db/comments.py` (exactly `1`).
**Test:** behavior pinned via view-level flows (`testModify` covers moderation keys; no dedicated unsubscribe unit — coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "unsubscribe notification 0 email parent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt scoped-by-owner muting (email + subtree). Adapt to your reply-depth semantics if deeper than 1. Omit nothing else — the narrowness IS the safety property.
