<!-- capsule-v2 -->
# Entity collection twin — how does a second vector store share the provider AND the client without deadlocking embedded mode?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mem0`. **Question:** how is the entity store's backend derived from the main one, and which two provider-specific details must a porter not lose?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py` `_entity_collection_name` (:422-424), `Memory.entity_store` property (:559-580), async twin (:2218-2238); `_safe_deepcopy_config` (:285-298, config clone with dict-shape fallback); consumers: reset-teardown-ladder capsule (lazy demotion), entity-store capsule (dedup/link contract), delete-all capsule (async bulk clear).
**Signature:** `_entity_collection_name(provider: str, collection_name: str) -> str`; `entity_store` lazy property → `VectorStoreFactory.create(provider, cloned_config)`.
**Data Shape:** names: `<collection>_entities`, EXCEPT s3-providers where `-` is the legal separator → `<collection>-entities`; cloned config = same class as the original (attr-style) or plain dict fallback.

### Decisive source
```python
def _entity_collection_name(provider, collection_name):
    separator = "-" if provider == "s3_vectors" else "_"
    return f"{collection_name}{separator}entities"

entity_config = _safe_deepcopy_config(self.config.vector_store.config)
entity_collection = _entity_collection_name(self.config.vector_store.provider, self.collection_name)
if hasattr(entity_config, 'collection_name'):
    entity_config.collection_name = entity_collection
elif isinstance(entity_config, dict):
    entity_config['collection_name'] = entity_collection
# For Qdrant, share the existing client to avoid RocksDB lock contention
# when using embedded mode (path=...). QdrantConfig.client takes precedence
# over host/port/path.
if self.config.vector_store.provider == "qdrant" and hasattr(self.vector_store, "client"):
    if hasattr(entity_config, "client"):
        entity_config.client = self.vector_store.client
    elif isinstance(entity_config, dict):
        entity_config["client"] = self.vector_store.client
self._entity_store = VectorStoreFactory.create(self.config.vector_store.provider, entity_config)
```

**Flow:** first entity touch materializes the twin: deep-copy the MAIN vector-store config (never mutate it) → swap ONLY the collection name (provider-aware separator) → qdrant-specific: inject the ALREADY-OPEN client object so both stores share one local RocksDB instance → construct through the same factory as any other store → subsequent touches reuse `self._entity_store`.
**Invariant:** two collections in ONE provider instance, not two backends; the qdrant client-share exists because embedded-mode Qdrant (`path=`) takes an exclusive filesystem lock — constructing a second client deadlocks or corrupts at open; the s3_vectors separator exception encodes that AWS's naming grammar forbids `_` there; config cloning is attr-or-dict DUAL because `_safe_deepcopy_config`'s reconstruction can legitimately fall back to a bare dict — every field write must handle both shapes.
**Probe:** no dedicated unit suite for the property at this HEAD — behavior pinned indirectly by `tests/test_memory.py::test_collection_name_preserved_after_reset` (reset/rebuild cycle keeps collection naming stable) and by the entity-store test family operating over the shared-client setup. Caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_entity_collection_name entity_store QdrantConfig", limit: 10, fields: ["signature", "name", "file"] });
```
(resolved: mnt-hdd-utopia-inspo-memory-mem0.mem0.memory.main._entity_collection_name Function mem0/memory/main.py 422-424)

## Verdict
Adopt derive-the-twin-from-the-main-config + share-the-connection; adapt the separator table to your providers' name grammars; omit the dict-fallback branch only if your configs are guaranteed dataclass-shaped.
