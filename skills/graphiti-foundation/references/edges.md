<!-- capsule-v2 -->
# Edges — the bi-temporal fact-edge model

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how do fact-edges carry bi-temporal validity and survive save/delete/embedding?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/edges.py`: `Edge` (:49), `EpisodicEdge` (:143), `EntityEdge` (:263) — `save` (:144), `get_by_uuid` (:165), `get_by_uuids` (:191), `get_by_group_ids` (:218), `generate_embedding` (:287), `load_fact_embedding` (:300); `delete_by_uuids` (:93).
**Signature:** `EntityEdge.save(driver)` persists the edge; `generate_embedding(embedder)` computes the fact embedding; `load_fact_embedding(driver)` loads it.
**Data Shape:** each fact-edge carries FOUR timestamps (`valid_at` — when the fact became true in the world; plus the bi-temporal pair); `__hash__`/`__eq__` for dedup.

### Decisive source
```ts
class EntityEdge(Edge):
    async def save(self, driver): ...
    async def generate_embedding(self, embedder): ...
    async def load_fact_embedding(self, driver): ...
    # four timestamps: valid_at (event time) + bi-temporal pair
```

**Flow:** edges are extracted from episodes, resolved (deduped via `__hash__`/`__eq__`), then saved to the driver. EntityEdges generate + load fact embeddings. `get_by_uuid(s)`/`get_by_group_ids` retrieve edges for search/contradiction resolution.
**Invariant:** a fact-edge carries bi-temporal validity (event time + ingestion time); edges dedup by hash/eq; embeddings are generated and loaded for semantic search.
**Probe:** `tests/` edge tests (save persists; get_by_uuid retrieves; generate_embedding; bi-temporal timestamps preserved).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "EntityEdge save generate_embedding valid_at bi-temporal edges", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bi-temporal fact-edge model (four timestamps, dedup by hash/eq, embedding generation); adapt the timestamp semantics and driver calls to host.
