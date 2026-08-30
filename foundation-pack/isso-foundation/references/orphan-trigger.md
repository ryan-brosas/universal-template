<!-- capsule-v2 -->
# Orphan-thread cleanup trigger — who deletes a thread when its last comment goes?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How does the threads table stay garbage-free without explicit lifecycle code in every delete path?

## DB-level orphan trigger
**Path/Symbol:** `isso/db/__init__.py:SQLite3.__init__` (lines 45–53).
**Signature:** `CREATE TRIGGER IF NOT EXISTS remove_stale_threads AFTER DELETE ON comments ...`
**Data Shape:** fires on every comments DELETE (hard deletes only — tombstones never fire it).

### Decisive source
```python
self.execute(
    [
        "CREATE TRIGGER IF NOT EXISTS remove_stale_threads",
        "AFTER DELETE ON comments",
        "BEGIN",
        "    DELETE FROM threads WHERE id NOT IN (SELECT tid FROM comments);",
        "END",
    ]
)
```

**Flow:** any hard DELETE of a comment row → trigger scans for threads with zero remaining comments → removes them. Combined with `_remove_stale`, deleting a whole thread's comments eventually removes both the comment rows AND the thread row with no application-level bookkeeping.
**Invariant:** Thread existence is DERIVED from comment presence, never maintained manually; `testDeleteCommentRemovesThread` pins this end-to-end. Porters on DBs without triggers must move this into their repository layer's delete method — the invariant, not the mechanism, is the contract.
**Probe:** `grep -c 'remove_stale_threads' isso/db/__init__.py` (exactly `1`).
**Test:** `isso/tests/test_comments.py:testDeleteCommentRemovesThread` (lines 613–617).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "remove_stale_threads trigger DELETE threads", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt derived thread lifetime (no orphan threads ever). Adapt to your DB's trigger syntax or lift into app code. Omit nothing else — the trigger is deliberately minimal.
