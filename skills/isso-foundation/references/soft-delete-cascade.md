<!-- capsule-v2 -->
# Soft-delete with stale sweep — how do you delete a comment that has replies?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How can a referenced comment be "deleted" without losing its children, and when does a row actually leave the table?

## Tombstone + iterative GC
**Path/Symbol:** `isso/db/comments.py:Comments.delete` + `Comments._remove_stale` (lines 317–357).
**Signature:** `delete(id) -> None | dict`; `_remove_stale() -> None`.
**Data Shape:** mode 4 = soft-deleted tombstone (text emptied, author/website nulled, email and remote_addr deliberately RETAINED so the author hash still resolves).

### Decisive source
```python
def _remove_stale(self):
    sql = (
        "DELETE FROM",
        "    comments",
        "WHERE",
        "    mode=4 AND id NOT IN (",
        "        SELECT",
        "            parent",
        "        FROM",
        "            comments",
        "        WHERE parent IS NOT NULL)",
    )
    while self.db.execute(sql).rowcount:
        continue

def delete(self, id):
    refs = self.db.execute("SELECT * FROM comments WHERE parent=?", (id,)).fetchone()
    if refs is None:
        self.db.execute("DELETE FROM comments WHERE id=?", (id,))
        self._remove_stale()
        return None
    self.db.execute("UPDATE comments SET text=? WHERE id=?", ("", id))
    self.db.execute("UPDATE comments SET mode=? WHERE id=?", (4, id))
    for field in ("author", "website"):
        self.db.execute("UPDATE comments SET %s=? WHERE id=?" % field, (None, id))
    self._remove_stale()
    return self.get(id)
```

**Flow:** leaf rows hard-DELETE; referenced rows become mode-4 tombstones; `_remove_stale` then repeatedly deletes unreferenced tombstones until the DELETE's rowcount hits 0 — cascading GC up the tree as chains of dead replies collapse.
**Invariant:** A comment that is anyone's parent NEVER disappears while the child exists; tombstone content must be blanked but the row must survive. The `while ... rowcount` loop is required because one pass can free parents whose own children were removed in the same pass.
**Probe:** `grep -c 'while self.db.execute(sql).rowcount:' isso/db/comments.py` (exactly `1`) and `grep -c 'mode=4 AND id NOT IN' isso/db/comments.py` (exactly `1`).
**Test:** `isso/tests/test_comments.py:testDeleteWithReference` / `testDeleteWithMultipleReferences`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "Comments.delete _remove_stale mode 4", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier delete (tombstone vs hard delete) and the fixpoint sweep — it composes with any parent-referencing schema. Adapt which fields you null on tombstoning (isso keeps email/remote_addr for hash stability). Omit the string-tuple SQL assembly style; it's an isso idiom, not the contract.
