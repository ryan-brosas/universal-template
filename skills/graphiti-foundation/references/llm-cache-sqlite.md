<!-- capsule-v2 -->
# LLM response cache — SQLite+JSON replacing pickle to kill a deserialization CVE

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** what does it take to cache LLM responses safely on disk when the values come from a model that can emit arbitrary bytes?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/llm_client/cache.py:LLMCache.__init__` (:28–35), `get` (:37–46), `set` (:48–60); key derivation `llm_client/client.py:_get_cache_key` (:153–157); enablement `LLMClient.__init__` (:91–92) + hit path in `generate_response` (:242–248, span attr `cache.hit`).
**Signature:** `LLMCache(directory: str)` → sqlite file `<dir>/cache.db`, table `cache(key TEXT PRIMARY KEY, value TEXT)`; `set(key, value: dict)` / `get(key) -> dict | None`.
**Data Shape:** values are JSON text only — anything non-JSON-serializable is DROPPED (warning logged, no raise); corrupted rows return None (warning logged).

### Decisive source
```python
class LLMCache:
    """Simple SQLite + JSON cache for LLM responses.

    Replaces diskcache to avoid unsafe pickle deserialization
    (CVE in diskcache <= 5.6.3). Only stores JSON-serializable data.
    """
    def set(self, key, value):
        try:
            serialized = json.dumps(value)
        except TypeError:
            logger.warning(f'Non-JSON-serializable cache value for key {key}, skipping')
            return                                   # drop, don't crash the call chain
        self._conn.execute('INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)',
                           (key, serialized))
        self._conn.commit()

    def _get_cache_key(self, messages):
        message_str = json.dumps([m.model_dump() for m in messages], sort_keys=True)
        return hashlib.md5(f'{self.model}:{message_str}'.encode()).hexdigest()
```

**Flow:** cache enabled per-client via constructor flag → key = md5(model + sort_keys-canonicalized full message dump) → hit returns before the span's retry wrapper (span records `cache.hit: true/false`) → miss stores after success.
**Invariant:** (1) NO pickle anywhere — the docstring names the CVE; a porter reintroducing pickle reintroduces RCE-on-read; (2) canonical serialization uses `sort_keys=True` so semantically identical messages hit the same key; (3) model name is part of the key so swapping providers can't serve foreign outputs; (4) connection created with `check_same_thread=False` + committed per write — safe for cross-thread async use; (5) failures degrade to a miss, never an exception.
**Probe:** `tests/llm_client/test_cache.py` pins set/get round-trip + corruption/non-serializable degradation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "LLMCache cache_key md5 sqlite json", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt JSON-only + sort-keys keys + degrade-to-miss wholesale for any LLM/response caching; adapt storage engine if already running Redis; omit md5 (not security-relevant here, but sha256 costs nothing) only with a comment explaining why.
