<!-- capsule-v2 -->
# Graph-backed skill store — how does one store implementation stay correct on BOTH ArangoDB and Neo4j?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do you implement a SkillStore/SkillHistoryReader/SkillCandidateStore triple on a graph DB without forking per backend — and which backend differences will silently corrupt data if ignored?

## Generic-interface-only access + tenant scoping at construction + Python-side filtering beyond flat equality
**Path/Symbol:** `backend/python/app/agents/agent_loop/skills/graph_store.py` — module docstring (:1-45), `GraphSkillStore` (:168-626), `_key` (:192), `_is_visible` (:195-200), `_get_org_doc` (:302-308), `list_skills` (:312-318), `get_provenance` (:333-348).
**Signature:** `GraphSkillStore(graph_provider: IGraphDBProvider, org_id: str, user_id: str, *, validator=None, visibility_scope: str | None = None)`; methods take NO org/user args — tenancy binds at construction.
**Data Shape:** Collections: `agentSkills` (full rendered SKILL.md in `content` + every frontmatter field denormalized), `agentSkillVersions` (append-only full snapshots, id `{skillKey}_v{version}`), `agentSkillCandidates`, `agentSkillRelation` edges. Only the backend-agnostic `IGraphDBProvider` surface is called (`get_document`, `batch_upsert_nodes`, `update_node`, `delete_nodes`/`delete_nodes_and_edges`, `batch_create_edges`, `delete_edges_from`, `get_nodes_by_filters`) — NEVER `execute_query` (AQL vs Cypher would break the undeployed backend).

### Decisive source
```python
# The backend divergence that shapes every read:
#   Arango get_nodes_by_filters w/o return_fields → raw document (_key/_id);
#   Neo4j → node properties (which already include an `id` property).
# Store never passes return_fields; identifier read is:
def _doc_id(doc): return doc.get("id") or doc.get("_key")
# ...and anything beyond flat equality is filtered IN PYTHON after fetch —
# get_nodes_by_filters does plain equality only, and the catalog is hundreds
# of docs per org, not millions, so post-fetch filtering stays cheap.
docs = [d for d in docs if self._is_visible(d)]
metadatas = [self._doc_to_metadata(d) for d in docs]
if filter is not None:
    metadatas = [m for m in metadatas if matches_filter(m, filter)]
```

**Flow:** construct with `(provider, org_id, user_id)` per request → reads apply hard `orgId` equality (+ visibility scope) → writes stamp `orgId`/`createdBy` AND create a USER→skill OWNER `permission` edge so finer user/team visibility can layer on later WITHOUT migration → create/update re-syncs `related/requires/replaced_by` frontmatter into real skill-to-skill relation edges by drop-and-recreate (no diffing at this catalog size).
**Invariant:** (1) `execute_query` is forbidden here by design — using it "works" until you deploy the other backend. (2) Tenant boundary = `orgId` equality on EVERY read + stamp on every write; visibility_scope narrows to `createdBy` EXCEPT `source=="builtin"` skills, which stay org-visible regardless (REST API passes the caller's id; agent runtime passes None). (3) `_key(name) = f"{org_id}_{name}"` — same skill name can exist independently per org. (4) Neo4j node properties allow only primitives/primitive arrays: any map-shaped value MUST be index-aligned parallel string arrays (`resourcePaths`+`resourceContents`; audit trail as four parallel arrays). (5) Listing uses denormalized fields with no SKILL.md parse; full-body path parses `content` — both kept consistent because content is ALWAYS re-rendered from the domain model at write time (see usage-carry-forward capsule). (6) Provenance (`created_by/updated_by/pack_*`) deliberately lives OUTSIDE the portable domain model — it's a storage concern read raw off the doc (used by BuiltinSkillSeeder to detect edited builtins).
**Probe:** `backend/python/tests/unit/agents/adapter/test_skills_graph_store.py` — `TestOrgIsolation.test_second_org_cannot_see_or_load_first_orgs_skill` (:296), `test_second_org_can_create_a_same_named_skill_independently` (:312), `TestCreatorScoping.test_builtin_skill_stays_visible_regardless_of_scope` (:374).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "GraphSkillStore get_nodes_by_filters batch_upsert_nodes IGraphDBProvider agentSkills", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt generic-interface-only persistence, construction-bound tenancy, owner-edge-on-write, and python-side non-equality filtering; adapt collection names, key scheme, and visibility rules to host; omit the builtin-source carve-out unless you seed shared builtin skills. Direct tests cover org isolation, creator scoping, and candidate delegation (473-line suite); Neo4j-vs-Arango return-shape divergence is source-documented but exercised only through the fake provider in tests (caveat noted in TestNeo4jSafeEncoding's design).
