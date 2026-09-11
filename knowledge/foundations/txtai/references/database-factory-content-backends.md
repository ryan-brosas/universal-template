<!-- capsule-v2 -->
# Content database factory + dialect adapters — how `content` config selects a backend and where dialect quirks hide

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** How is a content backend chosen from config, and which backend quirks are patched inside narrow overrides rather than the shared SQL machinery?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/factory.py:DatabaseFactory.create` (:21-60), `.resolve` (:62-78); `duckdb.py:formatargs` (:126-156), `.insertdocument/insertobject` (:42-54), `.copy` (:86-124), `.rows` (:75-81).
**Signature:** `create(config) -> Database | None`; `formatargs(args) -> (query, positional_list)`.
**Data Shape:** `config["content"]`: `True`→sqlite, `"duckdb"`, `"client"` or any URL-scheme string→Client, other truthy string→Resolver custom backend, absent/None→no content store. Factory writes the standardized name back into `config["content"]`.

### Decisive source
```python
if content == "duckdb":
    database = DuckDB(config)
elif content == "sqlite":
    database = SQLite(config)
elif content:
    url = urlparse(content)
    if content == "client" or url.scheme:
        database = Client(config)
    else:
        database = DatabaseFactory.resolve(content, config)
```
```python
# DuckDB doesn't support named parameters — rewrite :name to ?, order by match position
pattern = rf"\:{key}(?=\s|$)"
match = re.search(pattern, query)
if match:
    query = re.sub(pattern, "?", query, count=1)
    params.append((match.start(), value))
args = (query, [value for _, value in sorted(params, key=lambda x: x[0])])
```

**Flow:** factory normalizes `True`→"sqlite", instantiates, stores the name back so `setting()` can find backend-specific config (`{"sqlite": {...}}`). Custom backends resolve through Resolver with ImportError wrapping naming the backend string. DuckDB patches live in OVERRIDES, never in RDBMS: INSERT OR REPLACE unsupported → delete-then-insert per uid; named binds → regex-rewritten positional ?'s sorted by first occurrence; cursor IS the connection; rows() fetchmany(256) generator (its cursors are not directly iterable); copy() exports documents/objects/sections to parquet in a temp dir, re-imports, replays indexes from duckdb_indexes(), CHECKPOINT, then re-begins a transaction (DuckDB connections start in one).

**Invariant:** The shared RDBMS code stays dialect-free by contract: every quirk must be an override of a named hook (`connect/getcursor/rows/addfunctions/jsonprefix/jsoncolumn/copy/formatargs/insertdocument/insertobject`). A port adding backend behavior inline in rdbms.py breaks every other backend. The factory's write-back of the normalized `content` name is what keeps `Database.setting()` lookups working after `True` was normalized.

**Probe:** `test/python/testdatabase/testrdbms.py` — Common.TestRDBMS is subclassed per backend (SQLite/DuckDB categories share the whole suite matrix via `cls.backend`); testencoder.py:testDefault iterates `for content in ["duckdb", "sqlite"]` (:61).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "DatabaseFactory create content duckdb sqlite client resolver formatargs", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: `DatabaseFactory.create` (:21-60), `DuckDB.formatargs` (:126-156) line-exact.

## Verdict
Adopt the normalize-in-factory / patch-in-overrides split + write-back of the canonical backend name; adapt the URL/client branch to your remote protocol; omit parquet-copy in favor of your backend's native dump only if you keep the uncommitted-changes caveat in mind (see sqlitevec-typed-ddl for the SQLite twin trap). Coverage: cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z.
