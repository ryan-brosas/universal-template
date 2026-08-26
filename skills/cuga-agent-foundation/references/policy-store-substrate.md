<!-- capsule-v2 -->
# Policy store over the embedding substrate — how do you persist similarity-searched policies with priority/enabled filtering and an idempotent update, reusing ONE vector-store implementation?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Where do authored policies actually live (this is NOT the markdown mirror), why does add delete-then-add while prod upserts, and what does count_policies' LIMIT 10000 mean for a porter?

## Schema-pinned policy rows over Local/ProdEmbeddingStore
**Path/Symbol:** `src/cuga/backend/storage/policy/base.py` (`policy_embedding_schema` :7-20; `PolicyStoreBackend` Protocol :23-44), `local.py` (`LocalPolicyStore.add_policy` :38-55; `list_policies` :87-109; `count_policies` :111-118), `prod.py` (`ProdPolicyStore.add_policy` :38-54).
**Signature:** `add_policy(policy_data: Dict)` requires key `"embedding"` (ValueError otherwise); `search_policies(query_embedding, limit, policy_type, enabled_only) -> List[tuple]`; `list_policies(policy_type, enabled_only, limit) -> List[Dict]`; `count_policies(policy_type) -> int`.
**Data Shape:** Fixed schema: metadata `{id, tenant_id, instance_id, policy_type, enabled(boolean), priority(integer)}` + aux `policy_json(text)`. Scope (`tenant_id`, `instance_id`) comes from config getters at EVERY call, never stored on self — a tenant switch mid-process takes effect immediately.

### Decisive source
```python
# base.py:7-20 — the policy row IS an embedding-schema instance; policy storage
# has no SQL of its own on either backend
def policy_embedding_schema(embedding_dim: int) -> EmbeddingSchemaConfig:
    return EmbeddingSchemaConfig(
        embedding_dim=embedding_dim,
        id_column="id",
        metadata_columns={"id": "text", "tenant_id": "text", "instance_id": "text",
                          "policy_type": "text", "enabled": "boolean", "priority": "integer"},
        auxiliary_columns={"policy_json": "text"})

# local.py:52-55 — sqlite-vec vec0 has no unique-index upsert → explicit
# delete-then-add makes updates idempotent (same id can't duplicate)
dim = len(embedding)
store = self._get_store(dim)
await store.delete(policy_id, tenant_id=..., instance_id=...)
await store.add(policy_id, embedding, meta)

# prod.py:54 — pgvector side needs NO pre-delete: ProdEmbeddingStore.add_many
# already ON-CONFLICT-UPDATES on (scope..., id) — deleting first would be harmless
# but is skipped; DO NOT "fix" local by removing its delete (vec0 will duplicate)

# local.py:117 — counting via bounded list sweep; >10k policies silently undercounts
rows = await self._store.list(filt, 10000)
return len(rows)
```

**Flow:** create_schema(dim) lazily builds the underlying store with the pinned schema → add requires caller-computed embeddings (policy text embedded upstream; ToolApproval rows historically carry zero-vectors because they match by tool name not semantics) → search filters `{tenant, instance, policy_type?, enabled?}` and returns distance-sorted tuples whose aux slot carries `policy_json` → list dedupes ids locally (belt-and-braces vs vec0 quirks) → update = delete+add (local) / plain upsert (prod).
**Invariant:** (1) The embedding dim is frozen per collection at first write — changing the embedder model requires a NEW collection or schema migration, not in-place writes. (2) `enabled`/`priority` are FILTER COLUMNS precisely so search can push them into the WHERE clause; stuffing them into policy_json would make enabled-only scans full-table. (3) Both stores return raw tuples/dicts — deserialization of `policy_json` and NL-trigger normalization happens in `cuga_graph/policy/storage.py` ABOVE this layer; keep the split. (4) count_policies is O(n) capped at 10000 — fine for admin UIs, not for enforcement hot paths.
**Probe:** No direct unit suite for the policy stores at this HEAD (they're thin over the tested embedding stores — `tests/unit/test_knowledge_local_add_many.py` covers the shared substrate; `tests/integration/test_knowledge_pgvector_rollback.py` the prod side). Coverage caveat: the delete-then-add vs upsert asymmetry is source-read, not test-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "policy_embedding_schema LocalPolicyStore ProdPolicyStore search_policies count_policies", limit: 10 });
```

## Verdict
Adopt "domain rows as EmbeddingSchemaConfig instances" to inherit both backends for free, scope-from-config-at-call-time, and filter-column promotion for boolean/integer flags. Adapt the 10000 count cap and the aux-blob layout to your host. Port the local delete-then-add EXACTLY as-is if your vector table lacks conflict targets; use native upsert only where it exists.
