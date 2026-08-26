<!-- capsule-v2 -->
# Guarded graph writes — how do you let an LLM populate a Neo4j knowledge graph without polluting it?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** What validation boundary and write choreography keep LLM-extracted entities/relationships inside a fixed ontology, per-company scoped?

## Closed-vocabulary validation + company-scoped MERGE
**Path/Symbol:** `backend/app/services/graph_store.py` whole (140L): `_ALLOWED_ENTITY_LABELS` :15, `_ALLOWED_RELATIONSHIP_TYPES` :16–19, `_validate_graph_payload` :21–39, `create_company_node` :41–56 (clears prior links), `add_entities_and_relations` :58–91.
**Signature:** `add_entities_and_relations(company_id: str, entities: list[dict], relations: list[dict]) -> None` (raises ValueError pre-write).
**Data Shape:** Entity labels closed set {Person, Product, Technology, Company}; relation types {FOUNDED_BY, HAS_PRODUCT, USES_TECH, COMPETES_WITH}; entity `{name unique non-empty, type, props}`; relation `{from, to, type}`.

### Decisive source
```python
# create_company_node clears the previous graph FIRST — re-runs are idempotent:
MERGE (c:Company {id: $id})
SET c += $props
WITH c
OPTIONAL MATCH (c)-[link:HAS_ENTITY]->(old)
DELETE link
```
Every node is namespaced by company so identically-named entities never collide across tenants:
```cypher
MERGE (e:{entity_type} {{company_id: $company_id, name: $name}})
SET e += $props
MERGE (c:Company {{id: $company_id}})
MERGE (c)-[:HAS_ENTITY]->(e)
```
Relation endpoints are matched INSIDE the same company scope before MERGE, so a hallucinated name silently no-ops instead of cross-linking companies.

**Flow:** validate payload BEFORE any Cypher (unknown label/type ⇒ ValueError; empty/duplicate names rejected) → wipe old HAS_ENTITY links → upsert Company node → per-entity MERGE → per-relation endpoint-match+MERGE. Caller (`tasks/process.py:_run_graph`) additionally guarantees the Company self-entity exists in the entity list even when the LLM omitted it.
**Invariant:** The ontology is a CLOSED vocabulary — new types require code change, not model creativity. Graph state per company is fully derived from the LATEST extraction run (delete-before-insert), never an accretion of partial runs. All reads (`get_company_graph`) LIMIT results (100 nodes/200 rels).
**Probe:** `backend/tests/test_graph_store.py::test_validate_graph_payload*` (label/type/name assertions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "_validate_graph_payload", limit: 5 });
// verified line-exact: graph_store.py :21–39
```

## Verdict
Adopt closed-ontology validation + tenant-scoped MERGE for any LLM→graph pipeline; adapt vocabularies to your domain; omit Neo4j driver details if using another graph store (contract ports directly).
