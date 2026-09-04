<!-- capsule-v2 -->
# Policy Storage — how are policies persisted, embedded, and re-hydrated without losing trigger data?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What does a porter must-know contract look like for storing typed policies over a vector backend — where do embeddings matter, where must they not, and how does stored JSON survive the round-trip?

## PolicyStorage facade over a pluggable embedding store
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/storage.py:PolicyStorage` (`_generate_policy_embedding` :121-240, `_dict_to_policy` :256-345, `search_policies` :392-413); backends `src/cuga/backend/storage/policy/{base,local,prod}.py`.
**Signature:** `PolicyStorage(collection_name="cuga_policies", backend=None, embedding_dim=None, ...)`; `await add_policy(policy: Policy)`; `await search_policies(query_embedding, limit=5, policy_type=None, enabled_only=True) -> List[tuple[Policy, float]]`; `await list_policies(...) -> List[Policy]`; `update_policy` = delete + add.
**Data Shape:** Row = `{id, policy_type, name, description, policy_json, priority, enabled, metadata_json, embedding}`. `policy_json` is the single source of truth for rehydration; columns exist only to filter/sort. Backend is a 9-method Protocol (`PolicyStoreBackend`, base.py:23-44) with two impls: `LocalPolicyStore` (sqlite-vec via LocalEmbeddingStore) and `ProdPolicyStore` (pgvector). Schema fixed by `policy_embedding_schema(dim)` (base.py:7-20): metadata cols id/tenant_id/instance_id/policy_type/enabled/priority + auxiliary `policy_json`.

### Decisive source
```python
# ToolApproval matched by tool NAME, never semantic search (:137-142)
if isinstance(policy, ToolApproval):
    logger.debug(
        f"Skipping embedding generation for ToolApproval policy '{policy.name}' (not needed for matching)"
    )
    return [0.0] * self.embedding_dim

# Priority dominates similarity in search results (:407-409)
similarity_score = 1.0 - float(distance)
policies.append((policy, similarity_score))
policies.sort(key=lambda x: (x[0].priority, x[1]), reverse=True)
```

**Flow:** lazy init (`initialize_async`: connect → init embedding fn → create schema with the RESOLVED dim) → on write: build embedding text from description + up-to-10 NL trigger strings + per-type content (Playbook markdown[:500], IntentGuard response[:300], ToolGuide guide_content[:300] + tool names, OutputFormatter keywords[:20] + format-type hints incl. JSON-schema property names) joined by `" | "` → store dict → on read: parse `policy_json`, normalize NL trigger values str→list (backward compat), strip illegal `triggers` key from ToolApproval rows, dispatch to the right subclass constructor.
**Invariant:** Embedding init FAILS LATE by design — `_initialize_embedding_function` catches its own exception, sets `_embedding_initialized = True` with `_embedding_function = None` (:105-108), so service startup succeeds; the failure surfaces only when a non-ToolApproval policy is actually written ("No embedding function available... set OPENAI_API_KEY or install fastembed"). And ToolApproval MUST get a zero-vector, never an exception. Rehydration normalizes legacy shapes before pydantic sees them.
**Probe:** `src/cuga/backend/cuga_graph/policy/tests/test_similarity_integration.py` — builds real local-embedding storage, adds policies, asserts retrieval ranking (fixture at :41-60 forces `POLICY_EMBEDDING_PROVIDER=local`, real embeddings only).
Backend asymmetry worth porting deliberately: `LocalPolicyStore.add_policy` deletes-then-adds under the tenant/instance scope (idempotent upsert, local.py:54-55); `ProdPolicyStore.add_policy` does NOT (prod.py:54) — it relies on the facade-level update_policy = delete+add. Both scope every op by `tenant_id`+`instance_id` filters; both cap count_policies via `list(filt, 10000)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_generate_policy_embedding", limit: 3 });
// → storage.py 121-240
```

## Verdict
Adopt the row shape (JSON blob + filter columns), the zero-vector-for-non-semantic-policy rule, fail-late embedding init, priority-dominant sort, and NL-trigger string→list normalization on load. Adapt sqlite-vec/pgvector to your stores; keep the tenant/instance scope discipline if multi-tenant. Omit the demo embedding-config error-message copy. Caveat: storage tests require real embedding models (no dummy vectors upstream).
