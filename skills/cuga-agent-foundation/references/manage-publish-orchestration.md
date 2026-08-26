<!-- capsule-v2 -->
# Manage publish orchestration — how do you make a config Publish atomic against a concurrent reindex, migrate vectors on hash change, and keep the old collection active until a strict deferred flip succeeds?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** The manage UI Publish button writes a new config version and applies it live — how does the route serialize the whole critical section, reject a publish during an in-flight reindex, snapshot/strip secrets, migrate documents on a vector-hash change, and defer the active-pointer flip so an empty collection is never activated?

## Locked publish critical section + reindex guard + deferred flip
**Path/Symbol:** `src/cuga/backend/server/manage_routes/config_routes.py:64-575` (`save_manage_config_publish`), `:578-607` (history/delete), `src/cuga/backend/server/manage_routes/knowledge_reindex.py:67-188` (`deferred_reindex_complete_and_flip`), `:189-299` (`migrate_and_reindex_for_agent`), `:17-64` (`persist_active_vector_config`).
**Signature:** `async def save_manage_config_publish(request, agent_id=None) -> JSONResponse`; raises HTTP 409 `{"error":"reindex_in_progress","collections":[...]}` when a same-agent reindex is in flight; HTTP 400 for invalid knowledge config or `EmbeddingModelLoadError`; HTTP 500 on secret-strip failure (fail CLOSED).
**Data Shape:** Published config snapshot carries `knowledge._vector_config_hash`, `knowledge._adaptation_hash`, `knowledge._glossary_hash` (underscore-prefixed metadata keys, filtered out on next coerce round-trip), plus `knowledge_state` (collection, persist_dir, collection_config, documents) for import/export portability — stripped from runtime apply.

### Decisive source
```python
# config_routes.py:112-126 — lock the whole publish against concurrent PATCH/reindex, then RE-CHECK the guard
_pub_lock = agent_draft_lock(str(agent_id))
await _pub_lock.acquire()
...
_busy2 = sorted(c for c in (getattr(...engine, "_reindex_in_progress", None) or ())
                 if c == _pfx or c.startswith(f"{_pfx}_"))
if _busy2:
    raise HTTPException(status_code=409, detail={"error":"reindex_in_progress","collections":_busy2,...})
```

**Flow:** Phase A (no mutation): validate + preflight knowledge via `engine.prepare_knowledge_update` (eagerly constructs the embedder so a bad model 400s cleanly). Compute `_vec_hash` = `KnowledgeConfig.coerce_and_validate(knowledge_cfg).vector_config_hash()` and adaptation/glossary hashes; if `_prev_hash != _vec_hash`, precheck whether the target collection already has docs (skip migration) or the old collection has docs (defer hash promotion). Phase B (persist): save draft (keeps the key so the local engine survives restart), strip secrets from the PUBLISHED snapshot only (fail CLOSED — a 500 is better than leaking a key), save the published version. Commit knowledge to runtime (`engine.commit_knowledge_update`). Phase C: apply LLM/tools/policies + rebuild the production agent. Then, on hash change, migrate: flag the OLD collection busy for the whole migration+embed window (uploads/deletes can't land in it and be lost), `copy_source_files(old,new)` + `reindex(new)`. If reindex returns `started` with task_ids, spawn a background `deferred_reindex_complete_and_flip` that waits for all workers to reach terminal state, requires ALL to succeed (strict — one failure refuses), re-checks the engine still hashes to `target_hash` (user didn't change embedders mid-flight), flips `state.knowledge_config_hash` under the per-agent lock, and persists durably so it survives restart. The old collection stays active+busy until the flip succeeds.

**Invariant:** The OLD collection is the active pointer until a strict deferred flip promotes the new hash — an empty/still-filling collection is never activated. The reindex-in-progress guard is checked twice (pre-lock and post-lock) because a concurrent `reindex_for_config_change` may have acquired the lock and started workers between the two checks. Secrets never cross machines via the published snapshot store; the draft keeps them locally. The whole publish is serialized against same-agent PATCH/reindex via the non-reentrant per-agent draft lock.

**Probe:** `tests/unit/test_knowledge_reindex_in_progress_guard.py:682` (`test_publish_rejected_during_reindex`), `:489` (`test_returns_409_when_vector_change_during_reindex`), `:186` (`test_flip_promotes_hash_when_all_tasks_complete`), `:216` (`test_flip_refuses_when_all_tasks_failed`), `:242` (`test_flip_refuses_when_engine_moved_on`), `:340` (`test_flip_bails_out_after_wall_clock_deadline`), `:373` (`test_flip_persists_hash_and_embedder_fields_behaviorally`); `tests/unit/test_knowledge_publish_import_pipeline.py:81` (`test_publish_snapshot_strips_only_secret_fields`), `:96` (`test_publish_via_post_route_strips_keys_from_disk`), `:342` (`test_imported_published_snapshot_never_re_introduces_secrets`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "save_manage_config_publish deferred_reindex_complete_and_flip migrate_and_reindex_for_agent persist_active_vector_config", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the locked publish critical section with double-checked reindex guard, the snapshot-and-strip-secrets-with-fail-closed posture, the vector-hash-driven migration with old-collection-busy flag, and the strict deferred pointer flip (all-workers-success + engine-still-matches + durable persist). Adapt to your config store's versioning. Omit the FastAPI route shape if you're not building the manage UI. Direct-test coverage is strong for the guard/flip/persist; the full publish route is exercised via integration (`test_llm_config_publish.py`, `test_manager_api_integration.py`).
