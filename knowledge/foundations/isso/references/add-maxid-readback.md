<!-- capsule-v2 -->
# add() MAX(c.id) readback — how does a single-statement INSERT return the new row?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How can an INSERT be atomic with thread resolution and still return the full stored comment without `lastrowid`?

## Insert-SELECT + max-id readback
**Path/Symbol:** `isso/db/comments.py:Comments.add` (lines 106–140).
**Signature:** `add(uri, c) -> dict` (mapping of `Comments.fields` to row values).
**Data Shape:** `c` must carry `mode`, `remote_addr`, `text`; everything else optional. The voters blob is minted fresh per comment: `memoryview(Bloomfilter(iterable=[c["remote_addr"]]).array)`.

### Decisive source
```python
self.db.execute(
    ["INSERT INTO comments (",
     "    tid, parent,    created, modified, mode, remote_addr,",
     "    text, author, email, website, voters, notification)",
     "SELECT",
     "    threads.id, ?,",
     "    ?, ?, ?, ?,",
     "    ?, ?, ?, ?, ?, ?",
     "FROM threads WHERE threads.uri = ?;"],
    (...),
)
return dict(
    zip(
        Comments.fields,
        self.db.execute(
            "SELECT *, MAX(c.id) FROM comments AS c INNER JOIN threads ON threads.uri = ?", (uri,)
        ).fetchone(),
    )
)
```

**Flow:** resolve `tid` inside the INSERT itself (`SELECT threads.id ... WHERE uri=?`) so a race between thread lookup and insert cannot orphan a row → read back via `MAX(c.id)` joined on the same URI → zip against the class-level `fields` list.
**Invariant:** The readback assumes the just-inserted row has the highest id in that thread (true for single-writer SQLite AUTOINCREMENT); porters using concurrent multi-process writers must replace it with `lastrowid` or a returning clause. `modified` is always inserted as NULL (`None` at position 3).
**Probe:** `grep -c 'MAX(c.id)' isso/db/comments.py` (exactly `1`).
**Test:** `isso/tests/test_comments.py:testCreate` / `testCreateMultiple` (returned mapping carries server-assigned id).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "Comments.add INSERT SELECT threads.id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the insert-with-implicit-tid pattern (client never supplies tid). Adapt the MAX(c.id) readback to your driver's `lastrowid`/RETURNING under concurrency. Omit the `zip(Comments.fields, ...)` shape only if you keep a serializer layer — but keep the field list as the single source of truth for column order.
