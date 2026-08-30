<!-- capsule-v2 -->
# Mode-mask fetch (bitwise OR) — how does mode filtering admit multiple visibility states?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** Why is the mode predicate `(? | comments.mode) = ?` and why do the two call sites differ in parenthesization?

## Bitwise visibility mask
**Path/Symbol:** `isso/db/comments.py:Comments.fetch` (lines 278–288) vs `Comments.reply_count` (lines 400–413).
**Signature:** `fetch(uri, mode=5, after=0, parent="any", order_by="id", asc=1, limit=None, offset=0) -> iterator[dict]`.
**Data Shape:** `mode` is a bitmask: 1 = published, 2 = pending, 4 = deleted-tombstone; default `5` = 1|4 (published + tombstones).

### Decisive source
```python
# fetch — mask form, paren OUTSIDE:
"SELECT comments.*, likes - dislikes AS karma FROM comments INNER JOIN threads ON",
"    threads.uri=? AND comments.tid=threads.id AND (? | comments.mode) = ?",
...
# reply_count — paren INSIDE the comparison's right operand slot:
sql = [
    "SELECT comments.parent,count(*)",
    "FROM comments INNER JOIN threads ON",
    "   threads.uri=? AND comments.tid=threads.id AND",
    "   (? | comments.mode = ?)",
    "GROUP BY comments.parent",
]
```

**Flow:** `(mode | row.mode) == mode` is true iff the row's mode bits are a SUBSET of requested modes — one parameter pair replaces an IN-list. `reply_count` groups by parent to power `total_replies`/`hidden_replies` in the view.
**Invariant / TRAP:** The `fetch` spelling is correct SQL; the `reply_count` spelling binds fine on SQLite but evaluates as `(mode|comments.mode)=?` grouped oddly — porters must NOT "normalize" one into the other without re-testing counts; the asymmetry is load-bearing legacy. `karma` exists only in `fetch`'s projection and only its whitelist (`["id","created","modified","likes","dislikes","karma"]`) accepts it as an order_by.
**Probe:** `grep -c 'likes - dislikes AS karma' isso/db/comments.py` (`1`); `grep -c '(? | comments.mode) = ?' isso/db/comments.py` (`1`); `grep -c '(? | comments.mode = ?)' isso/db/comments.py` (`1`).
**Test:** `isso/tests/test_comments.py:testGetSortedByUpvotes` (karma ordering), `testFetchEmpty`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "fetch karma mode bitwise threads.uri", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt subset-mask visibility if your modes are bit flags; otherwise translate to an explicit IN-list but keep BOTH count paths on one predicate. Adapt default mask per surface (public 5, admin any). Omit the reply_count paren quirk — document it, don't copy it.
