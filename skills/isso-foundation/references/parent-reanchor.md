<!-- capsule-v2 -->
# Parent re-anchoring on reply — how is a comment's parent validated against the thread?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** When storing a reply, how does Isso guarantee the parent exists AND belongs to the same thread, and what happens to grandchildren posted against deep nests?

## Parent re-anchor recursion
**Path/Symbol:** `isso/db/comments.py:Comments.add` (`_find`, lines 83–104).
**Signature:** `_find(uri, parent) -> int | None` (closure inside `add(uri, c)`).
**Data Shape:** `uri` is the thread URI string; incoming `c["parent"]` may be `"0"`, `0`, `None`, a stale id, or an id from another thread. Output is a re-anchored parent id or `None`.

### Decisive source
```python
def _find(uri, parent):
    if parent in ["0", 0, None]:
        return None
    obj = self.get(parent)
    if obj is None:  # parent does not exist
        return None
    rv = self.db.execute(
        ["SELECT CASE WHEN EXISTS(",
         "   SELECT comments.id FROM comments INNER JOIN threads",
         "       ON comments.tid=threads.id WHERE threads.uri=?",
         "       AND comments.id=?)",
         "   THEN 1 ELSE 0 END;"],
        (uri, parent),
    ).fetchone()
    if rv[0] == 0:  # parent is not in current thread
        return None
    return _find(uri, obj.get("parent")) or parent
```

**Flow:** sentinel parents (`"0"`, `0`, `None`) → `None`; missing parent → `None`; EXISTS-check `(threads.uri=? AND comments.id=?)` fails → `None`; otherwise recurse toward the root and anchor at the highest ancestor that still resolves (`_find(...) or parent`). A reply to a deleted/deep comment silently lands top-level or on the nearest valid ancestor instead of erroring.
**Invariant:** A stored `comments.parent` ALWAYS references an existing comment in the SAME thread (`tid` derived from `uri`, never from client input); nesting depth is bounded to 1 by construction after the v2→v3 migration flattened all deeper trees.
**Probe:** `grep -c 'return _find(uri, obj.get("parent")) or parent' isso/db/comments.py` (exactly `1`).
**Test:** `isso/tests/test_comments.py:testCreateInvalidParent` + `testCreateInvalidThreadForParent` (cross-thread parent rejected).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "Comments.add parent thread uri", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the re-anchor-or-null recursion and the EXISTS-based cross-thread check (portable to any SQL store). Adapt `"0"` sentinel handling to your API's nullability conventions. Omit the SQLite-flavored `CASE WHEN EXISTS` spelling only if your ORM offers an equivalent existence probe — the semantic (check before trust, never raise) is the contract.
