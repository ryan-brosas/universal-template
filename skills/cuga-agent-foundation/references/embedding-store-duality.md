<!-- capsule-v2 -->
# LocalEmbeddingStore / ProdEmbeddingStore duality — how do you serve the SAME schema-driven vector contract over sqlite-vec AND pgvector without letting either dialect leak into callers?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A porter wants one vector store behind policy and knowledge that runs zero-infra locally and pgvector in prod — where does dialect translation live, what does each side do about upserts/dim-mismatch, and what breaks if you "simplify" it?

## Schema-configured dual backends
**Path/Symbol:** `src/cuga/backend/storage/embedding/base.py` (`EmbeddingSchemaConfig` :6-10; `EmbeddingStoreBackend` Protocol :13-20), `local.py` (`LocalEmbeddingStore` :21-228), `prod.py` (`ProdEmbeddingStore` :19-244).
**Signature:** `EmbeddingSchemaConfig(embedding_dim: int, id_column: str, metadata_columns: Dict[str,str], auxiliary_columns: Dict[str,str])`; both stores expose `add(id, embedding, metadata)`, `add_many(items) -> None`, `search(query_embedding, limit, metadata_filter) -> List[tuple]`, `get(id, tenant_id="", instance_id="")`, `delete(id, tenant_id="", instance_id="")`, `list(metadata_filter, limit)`.
**Data Shape:** metadata_columns are filterable/scope columns; auxiliary_columns ride along unfilterable (e.g. `policy_json`, `chunk_text`). Factory `embedding/__init__.py get_embedding_store(collection, schema, mode, local_db_path, postgres_url)` picks prod only when `mode=="prod"` (ValueError if no postgres_url), else local — there is no third mode.

### Decisive source
```python
# base.py:6-10 — the whole port is this dataclass; both stores are generic over it
@dataclass
class EmbeddingSchemaConfig:
    embedding_dim: int
    id_column: str
    metadata_columns: Dict[str, str]
    auxiliary_columns: Dict[str, str]

# local.py:41-55 — sqlite-vec vec0 table: aux columns prefixed '+' (unindexed),
# type map defaults unknown names to TEXT
parts = [f"embedding float[{dim}]"]
for k, v in meta.items(): parts.append(f"{k} {_VEC0_TYPE.get(v.lower(), 'TEXT')}")
for k, v in aux.items(): parts.append(f"+{k} {typ}")
sql = f"CREATE VIRTUAL TABLE IF NOT EXISTS {name} USING vec0({cols})"

# local.py:133-150 — KNN search: MATCH + k + ORDER BY distance; filter ONLY on
# declared metadata keys (unknown filter keys are silently DROPPED)
where_parts = ["embedding MATCH ?", "k = ?"]
for k, v in metadata_filter.items():
    if k in self._schema.metadata_columns: where_parts.append(f"{k} = ?")
sql = f"... WHERE {' AND '.join(where_parts)} ORDER BY distance"

# prod.py:162-168 — pgvector cosine: query embedding passed THREE times,
# distance aliased so the tuple shape matches the sqlite side
params.extend([query_embedding, query_embedding, limit])
i1, i2, i3 = len(params)-2, len(params)-1, len(params)
f"SELECT {id_col}, {aux}, (embedding <=> ${i1}) AS distance ... ORDER BY embedding <=> ${i2} LIMIT ${i3}"
```

**Flow:** caller builds a schema config once (`policy_embedding_schema` / `knowledge_embedding_schema`) → factory picks store by mode → local lazily opens sqlite3 with `check_same_thread=False`, loads the `sqlite_vec` extension, creates the vec0 table; prod lazily creates an asyncpg pool (min 1/max 4, command_timeout=60), runs `CREATE EXTENSION IF NOT EXISTS vector` inside try (InsufficientPrivilege → warn-and-assume-preinstalled), registers `pgvector.asyncpg.register_vector`, creates a plain table + HNSW cosine index. All blocking sqlite work goes through `asyncio.to_thread`; prod is async-native.
**Invariant:** (1) `search` returns `(id, *aux_cols, distance)` tuples on BOTH sides — knowledge reads `chunk_text/meta_json` positionally from aux slots, policy reads `policy_json`; changing column order breaks both consumers. (2) Filter keys not present in `metadata_columns` are silently ignored (never an error) — scoping must use declared scope cols. (3) The dim is fixed at first store creation (`_get_store(dim)` memoizes on first add); a later different-dim embedding hits a table built for the old dim — callers must re-create collection, never mix dims. (4) `_serialize_float32` falls back to raw `struct.pack` when `sqlite_vec.serialize_float32` import fails but the extension itself still loads — don't remove the fallback. (5) Prod `add_many` wraps `executemany` in ONE explicit `conn.transaction()` because bulk path lost the implicit per-row transaction safety; keep it.
**Probe:** `tests/unit/test_knowledge_local_add_many.py` — `test_add_many_inserts_all_items` (:35), `test_add_many_round_trips_metadata` (:45), `test_add_many_empty_is_noop` (:59), and the fallback probe `test_add_many_fallback_loop_when_executemany_unavailable` (:66) which swaps `store._conn` for a wrapped connection raising `OperationalError` on executemany and asserts fast-path tried exactly once, 4 per-row inserts, ONE commit. Prod side has NO direct unit test (needs live pgvector) — see `tests/integration/test_knowledge_pgvector_rollback.py` for the integration harness; coverage caveat stands.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "LocalEmbeddingStore search add_many _serialize_float32 ProdEmbeddingStore register_vector", limit: 10 });
```

## Verdict
Adopt the schema-dataclass-over-two-backends pattern, the `(id, *aux, distance)` return-shape parity, silent-drop metadata filtering, lazy connection/pool init, and the executemany-with-single-commit (+fallback loop) batch path. Adapt the concrete type maps (`_VEC0_TYPE` vs `_pg_type`: integer→BIGINT, boolean→BOOLEAN, float→DOUBLE PRECISION), pool sizing, and HNSW index choice to your host. Omit nothing structural — the aux-column prefix trick and triple-parameter cosine ordering are load-bearing.
