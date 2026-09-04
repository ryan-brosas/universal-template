<!-- capsule-v2 -->
# Error taxonomy raise-site census — when does a bulk group fetch throw NotFound versus return empty?

**Source:** graphiti Apache-2.0 `main@993e081a`; Codebase Memory `graphiti`. **Question:** which NotFound failures throw and which return an empty list, and how does error identity survive refactors?

## Flat GraphitiError hierarchy + its raise-site map
**Path/Symbol:** `graphiti_core/errors.py` (:18-95); decisive raise sites `edges.py:259` (EpisodicEdge.get_by_group_ids), `edges.py:539` (EntityEdge.get_by_group_ids), `search.py:414`/`:629`, `graphiti_core/helpers.py:157`/`:184`, `utils/ontology_utils/entity_types_utils.py:35`; consumer mapping `server/graph_service/zep_graphiti.py:39-78`.
**Signature:** all classes subclass `GraphitiError(Exception)` except `NodeLabelValidationError(GraphitiError, ValueError)` (:86) — dual inheritance so legacy `except ValueError` keeps working.
**Data Shape:** every error builds `self.message` FIRST and passes it to `super().__init__(self.message)` — message attribute is always populated for HTTP detail forwarding.

### Decisive source
```python
# errors.py :38-51 — sibling group classes with OPPOSITE live status:
class GroupsEdgesNotFoundError(GraphitiError):
    """Raised when no edges are found for a list of group ids."""
    def __init__(self, group_ids: list[str]):
        self.message = f'no edges found for group ids {group_ids}'
        super().__init__(self.message)

class GroupsNodesNotFoundError(GraphitiError):
    """Raised when no nodes are found for a list of group ids."""
    # LATENT at main@993e081a: defined but ZERO raise sites anywhere
    def __init__(self, group_ids: list[str]):
        self.message = f'no nodes found for group ids {group_ids}'
        super().__init__(self.message)
```

**Flow:** boundary validation raises first (GroupIdValidationError at `graphiti_core/helpers.py`:157, NodeLabelValidationError `:184`, EntityTypeValidationError `entity_types_utils.py:35`) → single-record ops raise `EdgeNotFoundError`/`NodeNotFoundError` (~30 raise sites across the four driver op-packages plus model methods) → bulk `get_by_group_ids` semantics SPLIT: `EpisodicEdge` (:259) and `EntityEdge` (:539) RAISE `GroupsEdgesNotFoundError` on zero rows while `CommunityEdge`/`HasEpisodeEdge`/`NextEpisodeEdge` and EVERY node class (`EpisodicNode` :422→466, `EntityNode` :635→684, CommunityNode, SagaNode) RETURN `[]` silently → `SearchRerankerError` guards node-distance rerankers lacking a center node (search.py:414,:629) → the Zep adapter translates per surface: Edge/NodeNotFoundError → HTTPException 404 with `.message`, GroupsEdgesNotFoundError → warn-and-continue with `edges = []` (zep_graphiti.py:46-51).
**Invariant:** an empty node list is a VALID result, not a failure — delete_group relies on it to wipe node-less groups; only Episodic/Entity edge fetches signal emptiness via exception. Do NOT normalize the asymmetry away when porting: callers already branch on it. `EpisodesNotFoundError` does not exist at this pin; `GroupsNodesNotFoundError` is latent — instantiable but nothing raises it, so except-clauses targeting it are dead code today.
**Probe:** static census re-executed pass 11 (verification pass): `grep -rn "raise GroupsEdgesNotFoundError" graphiti_core/` → exactly edges.py:259,:539; `grep -rn "raise SearchRerankerError" graphiti_core/` → exactly search.py:414,:629; `grep -rn "raise GroupsNodesNotFoundError" graphiti_core/` → 0 hits. Behavioral: `.venv/bin/python -c "assert issubclass(NodeLabelValidationError, GraphitiError) and issubclass(NodeLabelValidationError, ValueError)"` → PASS. Coverage caveat: check_index_coverage flags search.py metadata_changed + helpers.py freshness-missing → both decisive ranges read directly from source before citing; live DB paths exercised only by integration tests (lane blocker, unchanged).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", query: "GroupsEdgesNotFoundError GroupsNodesNotFoundError raise get_by_group_ids", limit: 10 });
```

## Verdict
Adopt the flat hierarchy + message-before-super convention and the documented raise-vs-empty table as a compatibility contract. Adapt: give latent classes a raise site or delete them before porting so consumers cannot depend on dead except-clauses. Omit the dual ValueError inheritance unless you also have legacy catch-sites to support.
