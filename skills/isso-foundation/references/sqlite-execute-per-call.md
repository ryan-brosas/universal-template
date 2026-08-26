<!-- capsule-v2 -->
# SQLite execute-per-call — what does the DB wrapper guarantee about connections?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** Why is every query its own connection, and what must a porter add for multi-statement atomicity?

## Connection-per-execute
**Path/Symbol:** `isso/db/__init__.py:SQLite3.execute` (lines 55–60).
**Signature:** `execute(sql: str | list[str], args=()) -> Cursor`.
**Data Shape:** `sql` may be a list/tuple of line fragments — joined with single spaces first (the repo's house style for readable SQL).

### Decisive source
```python
def execute(self, sql, args=()):
    if isinstance(sql, (list, tuple)):
        sql = " ".join(sql)
    with sqlite3.connect(self.path) as con:
        return con.execute(sql, args)
```

**Flow:** join fragment list → open a FRESH connection per call → execute → close on context exit. Migrations bypass this helper (`with sqlite3.connect(self.path)` directly, 6 total sites in this file) because they need explicit BEGIN/COMMIT/ROLLBACK around multiple statements.
**Invariant:** No long-lived connection and no cross-call transaction state; each call autocommits on clean exit. Anything needing multi-statement atomicity (all five migration rungs) opens its own connection and manages the transaction by hand.
**Probe:** `grep -c 'with sqlite3.connect(self.path) as con:' isso/db/__init__.py` (exactly `6`: one in `execute`, five migration bodies).
**Test:** `isso/tests/test_db.py:test_defaults` (whole ladder exercised via constructor).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "SQLite3 execute connect path", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt stateless-per-call execution for simple CRUD (crash-safe, no leaked locks). Adapt to a pooled engine by wrapping multi-statement work in explicit transactions. Omit the list-of-strings SQL style only if you keep readability another way.
