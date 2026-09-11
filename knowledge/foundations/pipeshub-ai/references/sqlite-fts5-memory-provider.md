<!-- capsule-v2 -->
# SQLite+FTS5 memory provider — can you get ranked agent memory without a vector database?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do you build a durable, relevance-ranked MemoryProvider from stdlib-only pieces (sqlite3 + FTS5) without an embedding API, and which async/locking traps must a porter not fall into?

## One sqlite3.Connection on a worker thread behind one asyncio.Lock; BM25 inverted at the boundary
**Path/Symbol:** `backend/python/app/agent_loop_lib/modules/providers/memory/sqlite.py:SQLiteMemoryProvider/_fts_query/_scope_matches` (L31–246); backend selection `control_plane/control_plane.py` (`memory="sqlite"` branch); interface `modules/providers/memory/base.py:MemoryProvider/MemoryResult/MemoryScope`.
**Signature:** `_fts_query(raw: str) -> str | None`; `SQLiteMemoryProvider(path=":memory:")`; `async add(content, metadata=None, scope=None) -> str`; `async search(query, top_k=10, scope=None) -> list[MemoryResult]`; `get/delete/clear/close`.
**Data Shape:** Table `memories(id PK, content, metadata JSON-text, agent_id, user_id, session_id, team_id, created_at)` + virtual `memories_fts(memory_id UNINDEXED, content)` kept in the SAME commit as the row table (dual-write). `MemoryResult{id, content, metadata, score}` with score = **negated** bm25 rank.

### Decisive source
```python
def _fts_query(raw):  # arbitrary user text → safe MATCH expression
    words = _WORD_RE.findall(raw)
    if not words: return None            # nothing searchable ⇒ [] not error
    escaped = [w.replace('"', '""')]     # quote-doubling sidesteps FTS5 operator
    return " OR ".join(f'"{w}"' for w in escaped)  # syntax (-,:,unbalanced ")
# search():
"WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?", (fts_query, top_k * 5)
# Over-fetch 5x BEFORE Python-side scope filtering — scope cols are NOT in
# the FTS index. bm25() is lower-is-better ⇒ invert once at the boundary:
results.append(MemoryResult(..., score=-float(rank)))
except sqlite3.OperationalError: return []   # malformed MATCH ⇒ [], never raise

# Every op: async with self._lock: conn = await self._connect()
#           await asyncio.to_thread(_sync_fn)   # stdlib driver is sync
```

**Flow:** lazy connect (`check_same_thread=False`) + idempotent CREATE TABLE/FTS init → add() inserts row + FTS entry in one transaction under lock → search(): user text → `_fts_query` quoted-phrase OR-chain → BM25-ranked join over-fetch ×5 → Python-side `_scope_matches` filter (None query-field = wildcard) → collect until top_k → scores already sign-inverted for callers.
**Invariant:** (1) ONE connection + ONE asyncio.Lock + to_thread serialization — the stdlib sqlite3 driver is synchronous and NOT thread-safe per-connection by default; naive per-call connections or unlocked threads corrupt state. (2) Dual-write row+FTS tables inside one commit; deleting only the row leaves phantom FTS hits forever (delete/clear both touch both tables). (3) Scope filtering happens AFTER rank ordering via over-fetch — putting scope columns into the FTS index or WHERE would wreck BM25 ranking; over-fetch factor is the tuning knob. (4) `_fts_query` returns None for wordless input ⇒ empty result, never a raised error. (5) Score sign convention flipped ONCE at the boundary so callers never learn FTS5's lower-is-better. (6) `path=":memory:"` default = private test DB; real path = durability across restarts.
**Probe:** Backend selection pinned: `tests/unit/agent_loop_lib/control_plane/test_control_plane_coverage.py:61–68` (`test_sqlite_memory_backend` asserts instance type; unknown-backend ValueError). Search/add/delete internals have NO direct unit suite upstream — caveat recorded; deterministic probe = graph resolution of `_fts_query` @ sqlite.py:31–41.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "SQLiteMemoryProvider fts_query bm25 memories_fts scope_matches" --detail ids
```

## Verdict
Adopt the stdlib-only FTS5 memory pattern (single serialized connection, dual-table same-commit writes, over-fetch-then-filter scoping, boundary score inversion, tolerant phrase-OR query builder); adapt schema/scope fields and the over-fetch factor to host load. Omit the sibling InMemory substring provider (strictly weaker recall). Coverage caveat: selection wired+tested; internals untested upstream at pin.
