<!-- capsule-v2 -->
# Nesting-flatten migration (v2→v3) — how was unlimited depth collapsed to one level?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How do you re-parent an arbitrarily deep reply tree onto top-level roots in one migration?

## BFS flatten to depth 1
**Path/Symbol:** `isso/db/__init__.py:SQLite3.migrate` version-2 rung (lines 115–148).
**Signature:** in-runge closure; reads `parent IS NULL` ids, walks children with an explicit stack.
**Data Shape:** `flattened: dict[root_id, set[descendant_ids]]`.

### Decisive source
```python
top = first(con.execute("SELECT id FROM comments WHERE parent IS NULL").fetchall())
flattened = defaultdict(set)
for id in top:
    ids = [id]
    while ids:
        rv = first(con.execute("SELECT id FROM comments WHERE parent=?", (ids.pop(),)))
        ids.extend(rv)
        flattened[id].update(set(rv))
...
for id in flattened.keys():
    for n in flattened[id]:
        con.execute("UPDATE comments SET parent=? WHERE id=?", (id, n))
```

**Flow:** for each root, DFS/stack-walk all descendants collecting them into a per-root set → single transaction re-parents EVERY descendant directly to its thread-root → bump to version 3.
**Invariant:** After this rung the schema guarantees max nesting = 1 (`fetch`'s one-level `replies` loop and `_process_fetched_list` depend on it); the UI renders only two levels. Porters who later allow deeper trees must revisit fetch pagination AND hidden_replies arithmetic.
**Probe:** `grep -c 'PRAGMA user_version' isso/db/__init__.py` covers the ladder; direct anchor: `grep -c 'AND parent IS NULL' isso/db/spam.py` distinguishes guard SQL — the migration's own marker is `UPDATE comments SET parent=? WHERE id=?` inside db/\_\_init\_\_.py.
**Test:** `isso/tests/test_db.py:test_limit_nested_comments` (asserts exact flattened mapping).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "limiting nesting level flattened", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the collect-then-rewrite-in-one-transaction shape for any tree-depth normalization. Adapt traversal to recursive CTEs on bigger stores. Omit per-row progress logging — the summary log after COMMIT suffices.
