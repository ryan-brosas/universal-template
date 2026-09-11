<!-- capsule-v2 -->
# Entity store — dedup + link entities to memories

**Source:** mem0 MIT `<branch>@<commit>`; Codebase Memory `mem0`. **Question:** how does a memory system deduplicate entities (exact + semantic) and link each to the memories that mention it?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `_upsert_entity` (:605-651), `_existing_entities_by_text` (:586), `_normalize_entity_text` (:583), `_link_entities_for_memory` (:707), `_remove_memory_from_entity_store` (:652); `entity_store` (:559).
**Signature:** `_upsert_entity(entity_text, entity_type, memory_id, filters)` — embeds the entity, checks exact match (normalized text) then semantic match (score >= 0.95), updates `linked_memory_ids` or inserts a new entity.
**Data Shape:** entity payload `{data, entity_type, linked_memory_ids: [memory_id], ...scope filters}`; exact match via `_existing_entities_by_text`; semantic match via `entity_store.search(top_k=1)` with a 0.95 score threshold.

### Decisive source
```ts
def _upsert_entity(self, entity_text, entity_type, memory_id, filters):
    entity_embedding = self.embedding_model.embed(entity_text, "add")
    exact_match = self._existing_entities_by_text(search_filters).get(self._normalize_entity_text(entity_text))
    if exact_match is None:
        existing = self.entity_store.search(query=entity_text, vectors=entity_embedding, top_k=1, filters=search_filters)
    semantic_match = existing[0] if existing and existing[0].score >= 0.95 else None
    match = exact_match or semantic_match
    if match:
        # update existing entity's linked_memory_ids (append memory_id)
    else:
        # insert new entity with linked_memory_ids=[memory_id]
```

```

**Flow:** embed the entity → check exact match (normalized text) → if none, semantic search (top_k=1, threshold 0.95) → if a match, append `memory_id` to its `linked_memory_ids`; else insert a new entity with `linked_memory_ids=[memory_id]`. `_remove_memory_from_entity_store` strips a memory_id from every entity record on memory delete.
**Invariant:** an entity is deduped by exact OR semantic match (0.95); `linked_memory_ids` tracks which memories mention it; entity upsert failures degrade to a warning (never abort the memory write).
**Probe:** `tests/memory/` entity tests (exact match dedups; semantic match at 0.95; linked_memory_ids appended; remove on memory delete).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_upsert_entity entity_store linked_memory_ids semantic match dedup", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the entity dedup + linking model (exact + semantic match, `linked_memory_ids`, remove-on-delete); adapt the entity payload shape and score threshold to host.
