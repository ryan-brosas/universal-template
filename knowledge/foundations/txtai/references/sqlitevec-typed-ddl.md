<!-- capsule-v2 -->
# sqlite-vec ANN backend — quantization-typed virtual table DDL and the temp→save connection dance

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How must a SQLite-vec-backed vector index type its embedding column and migrate from a scratch in-memory DB to its save path?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/ann/dense/sqlite.py:SQLite.tablesql` (:206-227), `.embeddingsql` (:269-289), `.searchsql` (:249-257), `.copy` (:173-204), `.save` (:75-98).
**Signature:** `tablesql()` → `CREATE VIRTUAL TABLE {table} USING vec0(indexid INTEGER PRIMARY KEY, embedding ...)`.
**Data Shape:** `setting("quantize")`: 1 → BIT, 8 → INT8, None → FLOAT32; `setting("table", "vectors")`; distance=cosine declared in DDL.

### Decisive source
```python
# Binary quantization
if self.quantize == 1:
    embedding = f"embedding BIT[{self.config['dimensions']}]"
# INT8 quantization
elif self.quantize == 8:
    embedding = f"embedding INT8[{self.config['dimensions']}] distance=cosine"
# Standard FLOAT32
else:
    embedding = f"embedding FLOAT[{self.config['dimensions']}] distance=cosine"
```
```python
def searchsql(self):
    return self.tosql(("SELECT indexid, 1 - distance FROM {table} "
                       f"WHERE embedding MATCH {self.embeddingsql()} AND k = ? ORDER BY distance"))
```
```python
if self.connection.in_transaction:
    # The backup call will hang if there are uncommitted changes, need to copy over
    # with iterdump (which is much slower)
    for sql in self.connection.iterdump():
        if self.tosql('insert into "{table}"') in sql.lower():
            connection.execute(sql)
else:
    self.connection.backup(connection)
```

**Flow:** index → initialize(recreate=True) drops+creates the vec0 virtual table → executemany inserts `(indexid, vector)` with quantize-specific bind wrapper (`vec_quantize_binary(?)` / `vec_quantize_int8(?, 'unit')` / raw) → search converts cosine DISTANCE to similarity via `1 - distance`. Save: three-way branch — temp (no path): commit, backup-copy, close old, re-point; same path: commit; different path: copy and KEEP current connection.

**Invariant:** The iterdump fallback exists because sqlite3's `Connection.backup()` HANGS when the source has uncommitted changes — this exact trap recurs in Terms.copy (scoring/terms.py:356-383) and is the reason both classes track `in_transaction` before choosing copy strategy. Third instance confirmed at pin `a10667a`: the CONTENT database `SQLite.copy` (database/sqlite.py:41-57) runs the same guard with an UNFILTERED iterdump replay (no vec-table filter — it must move every row). Quantize type must match between DDL column type and insert-time bind function or every insert fails; k = ? limit parameter is sqlite-vec's match syntax, not a plain LIMIT.

**Probe:** `test/python/testann/testdense.py:testSQLite/testSQLiteCustom` (:339-378 custom table names + quantized columns through the shared runTests matrix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "sqlite vec virtual table quantize distance copy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the typed-DDL ladder + `1 - distance` similarity projection + in_transaction/iterdump copy guard; adapt table naming; omit INT8/BIT variants if you only ship float32. Coverage caveat: exercised via testdense shared matrix.
