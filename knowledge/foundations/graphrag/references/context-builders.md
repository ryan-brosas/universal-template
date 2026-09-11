<!-- capsule-v2 -->
# Query context builders + dynamic community selection

**Source:** graphrag MIT `<branch>@<commit>`; Codebase Memory `graphrag`. **Question:** how do RAG search modes assemble LLM context from a knowledge graph, and how does the system pick WHICH communities to read at query time instead of all of them?

## Connected graph-selected seam
**Path/Symbol:** `graphrag/query/context_builder/`: `local_context.py` — `build_entity_context` (:30), `build_relationship_context` (:158), `get_candidate_context` (:320), `_filter_relationships` (:232); `community_context.py`, `conversation_history.py`, `source_context.py`, `rate_relevancy.py`; `dynamic_community_selection.py`: `DynamicCommunitySelection` (:26) — `select(query) -> (list[CommunityReport], dict)` (:73). Search modes in `query/structured_search/`: `local_search/`, `global_search/`, `basic_search/`, `drift_search/` sharing `base.py`.
**Signature:** context builders are pure functions `(entity/corpus, params) -> str context blocks`; `DynamicCommunitySelection.select(query)` asks an LLM which community reports are relevant, then only those feed the global-search prompt.
**Data Shape:** entity context = name/description/claims/rank blocks; relationship context = weighted, rank-filtered tuples; conversation history kept as alternating turns with token budget.

### Decisive source
```ts
class DynamicCommunitySelection:
    async def select(self, query) -> tuple[list[CommunityReport], dict]:
        # rate each community report's relevancy to the query (LLM judge),
        # keep reports above threshold -> far fewer tokens than map-reduce over ALL reports
def get_candidate_context(...):   # local search: entities -> their relationships,
    ...                           # claims, and source text units, rank-ordered
```

**Flow:** a query enters one of four modes → local search builds entity-centered context via `get_candidate_context` (entities matched from the query → relationships filtered by rank → covariates → text units); global search either maps/reduces over community reports or uses `DynamicCommunitySelection` to pick relevant ones first; DRIFT mixes both. Context builders enforce token budgets per block.
**Invariant:** context assembly is separated from prompting (builders produce strings; prompts template them); every builder is budget-bounded; dynamic selection trades one cheap LLM rating pass for a much smaller map-reduce.
**Probe:** `tests/` query tests (context contains ranked relationships within budget; dynamic selection returns subset + metadata; four modes share base interface).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "build_entity_context get_candidate_context DynamicCommunitySelection select", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pure budget-bounded context builders per block type plus LLM-rated community preselection for global queries; adapt budgets and rating thresholds to host.
