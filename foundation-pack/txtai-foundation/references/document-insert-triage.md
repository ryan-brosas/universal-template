<!-- capsule-v2 -->
# Document insert triage — how do dict, list, and raw-object documents become rows, and which one silently drops data?

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** What are the exact per-type insert semantics of a content store that must keep section text, JSON attributes, and binary objects consistent?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/rdbms.py:RDBMS.insert` (:37-66), `.loaddocument` (:312-345), `.loadobject` (:360-373); DDL `schema/statement.py` (:36-74); DuckDB upsert twin `duckdb.py:insertdocument/insertobject` (:42-54).
**Signature:** `insert(documents, index=0)` over `(uid, document, tags)` tuples; `loaddocument(uid, document, tags, entry) -> section value`.
**Data Shape:** `documents(id TEXT PK, data JSON, tags, entry)`; `objects(id TEXT PK, object BLOB, ...)`; `sections(indexid INTEGER PK, id, text, tags, entry)`.

### Decisive source
```python
for uid, document, tags in documents:
    if isinstance(document, dict):
        document = self.loaddocument(uid, document, tags, entry)
    if document is not None:
        if isinstance(document, list):
            document = " ".join(document)
        elif not isinstance(document, str):
            self.loadobject(uid, document, tags, entry)
            # Clear section text for objects, even when objects aren't inserted
            document = None
        self.loadsection(index, uid, document, tags, entry)
        index += 1
```
```python
# loaddocument: copy, pop object, filter columns through store, JSON with allow_nan=False
data = {key: value for key, value in document.items() if key in self.store} if self.store is not None else document
if data:
    self.insertdocument(uid, json.dumps(data, allow_nan=False), tags, entry)
return document[self.text] if self.text in document else obj
```

**Flow:** dict → copy → pop `object` field → optional `store` allowlist → remaining keys stored as JSON (`allow_nan=False`, so NaN raises rather than emitting invalid JSON) → text+object both present stores the object too → section value = configured `text` column else the object itself. list (tokens) → joined to one string. Any other type → encoded to `objects` ONLY IF an encoder is configured; section text is forced to None either way. Only actually-saved sections advance `index`.

**Invariant:** The silent-drop branch is load-bearing knowledge: without an `objects` encoder a non-string/non-dict/non-list document produces NO row at all — no error, no section. Documents/objects upsert via `INSERT OR REPLACE`; sections cannot (indexid is positional), so re-indexing the same uid appends a new indexid. DuckDB lacks INSERT OR REPLACE: its overrides delete-then-insert per uid instead.

**Probe:** `test/python/testdatabase/testencoder.py:testDefault` (:51-73 bytearray object roundtrips as BytesIO under default encoder), `testPickle` (:105-123 list object via pickle encoder); `test/python/testdatabase/testrdbms.py:testAutoId` (:82-99 uid generation feeding these inserts).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "insert documents loaddocument loadobject loadsection", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: top hits `RDBMS.insert` (:37-66) line-exact.

## Verdict
Adopt the three-way triage + store-filtered JSON + explicit object-clearing; adapt column names (`columns.text/object/store`) to your schema; omit object support entirely only if you also reject non-text documents loudly — txtai's silence is a design choice, not an accident. Coverage: cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z.
