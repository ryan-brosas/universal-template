<!-- capsule-v2 -->
# ZepGraphiti REST adapter — per-request client, error→HTTP translation at the edge

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `graphiti`. **Question:** how do you wrap a long-lived kernel library in an HTTP service without leaking domain errors or holding DB connections between requests?

## Connected graph-selected seam
**Path/Symbol:** `server/graph_service/zep_graphiti.py` — `ZepGraphiti(Graphiti)` (:17-78), `_create_graphiti_client` (:81-103), generator dependency `get_graphiti` (:106-118) exposed as `ZepGraphitiDep = Annotated[ZepGraphiti, Depends(get_graphiti)]` (:144); projection helper `get_fact_result_from_edge` (:129-141).
**Signature:** subclass adds only REST-shaped ops (`save_entity_node`, `get_entity_edge`, `delete_group`, `delete_entity_edge`, `delete_episodic_node`); each wraps model-class statics: construct → (`generate_name_embedding`) → `save`/`delete`.
**Data Shape:** FastAPI generator dependency yields a fresh client per request; settings overrides mutate `client.llm_client.config.{base_url,api_key}` and `client.llm.model` post-construction.

### Decisive source
```python
# zep_graphiti.py :106-118 — per-request lifecycle; close() in finally:
async def get_graphiti(settings: ZepEnvDep):
    client = _create_graphiti_client(settings)
    if settings.openai_base_url is not None:
        client.llm_client.config.base_url = settings.openai_base_url
    ...
    try:
        yield client
    finally:
        await client.close()
#
# :39-44 + :46-51 — error translation lives HERE, not in core:
try:
    edge = await EntityEdge.get_by_uuid(self.driver, uuid)
    return edge
except EdgeNotFoundError as e:
    raise HTTPException(status_code=404, detail=e.message) from e
...
except GroupsEdgesNotFoundError:
    logger.warning(f'No edges found for group {group_id}')
    edges = []
```

**Flow:** boot lifespan runs `initialize_graphiti` once (build_indices_and_constraints then closes its client — main.py keeps NO app-level client: 'handled per-request') → every handler receives a freshly built ZepGraphiti via Depends → backend chosen by `db_backend`: falkordb gets silent defaults (localhost/6379/default_db) while neo4j raises ValueError unless ALL of uri/user/password are set → after the handler, finally closes driver connections.
**Invariant:** (1) translation boundary is the adapter: core raises typed GraphitiError subclasses, HTTP status mapping (404) happens only here, so graphiti_core stays transport-free; (2) delete-of-unknown-group is a WARNING-BACKED NO-OP, not an error — safe because `EntityNode.get_by_group_ids` returns [] on empty while only `EntityEdge.get_by_group_ids` raises GroupsEdgesNotFoundError (edges.py:259/:539; `GroupsNodesNotFoundError` has NO raise site at this pin — latent class); (3) asymmetric config strictness is intentional per backend: FalkorDB defaults suit local dev, Neo4j creds have no sane default so fail fast; (4) per-request construction costs a connection setup per call by design — porters who cache one client app-wide change the failure blast radius (one poisoned client kills all requests).
**Probe:** source-level greps this pass: `grep -c 'raise HTTPException' server/graph_service/zep_graphiti.py` → `3`; repo-wide `grep -rn 'raise Groups' --include='*.py' | grep -v __pycache__ | grep -v server/` shows raise sites ONLY in edges.py (:259, :539). Direct tests: none unit-level for this module (live-only int test) — coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", query: "ZepGraphiti get_graphiti _create_graphiti_client delete_group", limit: 10 });
await mcp.codebase-memory.trace_path({ project: "graphiti", function_name: "graphiti.server.graph_service.zep_graphiti.get_fact_result_from_edge" });
```

## Verdict
Adopt adapter-layer error translation and generator-dependency lifecycles when wrapping any kernel library in HTTP; keep the kernel's exception taxonomy pure and map to transport codes exactly once. Adapt backend-switch strictness to which options actually have safe defaults. Do not silently upgrade the empty-delete no-op into a 404 without deciding callers depend on idempotence.
