<!-- capsule-v2 -->
# GraphitiClients — one typed bundle replacing five parallel params

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `graphiti`. **Question:** how does a pipeline of ~10 free functions receive its infrastructure without threading five loose arguments everywhere or reaching for a service locator?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/graphiti_types.py` — `GraphitiClients(BaseModel)` (:26-33); constructed once in `graphiti.py:235` (`self.clients = GraphitiClients(...)`); consumed as a single `clients:` parameter by `search/search.py:99`, `utils/maintenance/{node_operations.py×6,edge_operations.py×2,combined_extraction.py}`, and `utils/bulk_utils.py×5` call sites.
**Signature:** five fields typed by ABC: `driver: GraphDriver`, `llm_client: LLMClient`, `embedder: EmbedderClient`, `cross_encoder: CrossEncoderClient`, `tracer: Tracer`.
**Data Shape:** `model_config = ConfigDict(arbitrary_types_allowed=True)` — required because the clients are plain ABCs, not pydantic models; pydantic would reject them otherwise.

### Decisive source
```python
# graphiti_types.py :26-33 (complete class):
class GraphitiClients(BaseModel):
    driver: GraphDriver
    llm_client: LLMClient
    embedder: EmbedderClient
    cross_encoder: CrossEncoderClient
    tracer: Tracer

    model_config = ConfigDict(arbitrary_types_allowed=True)
#
# tests/utils/maintenance/test_bulk_utils.py :33 — test doubles bypass
# validation on purpose (heavyweight/networked real clients):
clients = GraphitiClients.model_construct(  # bypass validation to allow test doubles
```

**Flow:** Graphiti.__init__ assembles the five implementations (provider factories / composition root) → bundles them ONCE into `self.clients` → every pipeline entry point that used to take `(driver, llm_client, embedder, cross_encoder)` now takes one `clients` argument, so adding a sixth infrastructure concern (tracer was the latest) touches signatures in exactly one place per function rather than every caller → search and maintenance helpers destructure only the fields they use.
**Invariant:** (1) this is a VALUE object, not a locator: no function reaches back into Graphiti; the bundle is passed explicitly, keeping pipeline functions pure-ish and directly testable; (2) signature stability is the payoff — the param list of `bulk_add_episodes`-family functions stops growing with each new client; (3) tests rely on `model_construct` (validation SKIPPED) so doubles need not satisfy isinstance checks — meaning the type hints are documentation-grade at test time but enforced at production construction; (4) arbitrary_types_allowed is safe here because instances are constructed by code, never parsed from untrusted input.
**Probe:** repo-wide grep this pass: `grep -rn 'GraphitiClients' --include='*.py' | grep -v __pycache__ | grep -v graphiti_types.py` → 27 usage lines across graphiti.py, search.py, bulk_utils.py, maintenance/*, and three test files using model_construct. Direct tests: `tests/utils/maintenance/test_bulk_utils.py`, `test_node_operations.py`, `test_entity_extraction.py` all construct the bundle (run green in this pass's battery). MCP snippet retrieval for the full class executed this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", query: "GraphitiClients arbitrary_types_allowed", limit: 5 });
await mcp.codebase-memory.get_code_snippet({ project: "graphiti", qualified_name: "graphiti.graphiti_core.graphiti_types.GraphitiClients" });
```

## Verdict
Adopt a typed client bundle when a multi-service pipeline would otherwise thread ≥3 parallel dependencies through free functions; keep it explicit (parameter), not ambient. Use pydantic only as a field-checked struct with arbitrary_types_allowed, and reach for model_construct in tests. Omit if your language has cheap structural DI — the pattern ports, the pydantic specifics don't have to.
