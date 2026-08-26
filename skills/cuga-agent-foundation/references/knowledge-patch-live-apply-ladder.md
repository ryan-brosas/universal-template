<!-- capsule-v2 -->
# Knowledge PATCH live-apply critical section — why does a knowledge config change apply to the LIVE engine under a per-agent lock, and when does a failed preflight still save?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How must `PATCH /config/draft/knowledge` sequence read→merge→validate→live-apply→save so concurrent same-section patches can't wipe each other, and which live-apply failures block the save vs soft-fail?

## Read-merge-validate-APPLY-save inside one per-agent asyncio.Lock
**Path/Symbol:** `src/cuga/backend/server/manage_routes/knowledge_routes.py:353-760` (`patch_draft_knowledge`).
**Signature:** `async def patch_draft_knowledge(request, agent_id: Optional[str] = None) -> JSONResponse`; body `{knowledge: {...}}` or the dict itself.
**Data Shape:** merged = `{**existing_draft_knowledge, **incoming}` filtered to `dataclasses.fields(KnowledgeConfig)` names minus `persist_dir`; response carries `live_changes` flags (`embedding_changed/chunking_changed/metric_changed/reindex_recommended/dim_changed/previous_dim/new_dim/adopted_existing_collection/active_document_count`) + optional `preflight_warning` + `auto_reindex: {triggered: False, reason: "manual_required"}` on dim change.

### Decisive source
```python
# knowledge_routes.py:413-424
# The READ-MERGE-VALIDATE-APPLY-SAVE sequence below MUST run inside
# the per-agent lock -- otherwise two concurrent same-section PATCHes
# both read the pre-PATCH draft, both compute their own ``filtered``
# against stale ``existing_knowledge``, and the later writer's save
# wipes the earlier's section change (cross-section + same-section
# LMW races are both closed by this single critical section).
async with agent_draft_lock(str(agent_id)):
    existing_draft = await load_draft(agent_id) or {}
    ...
    validated = KnowledgeConfig.coerce_and_validate(filtered)
    ...
    live_apply_result = await asyncio.to_thread(live_engine.apply_knowledge_config, filtered)
    ...
    full_draft = await save_draft_section_unlocked(agent_id, "knowledge", filtered)
```
Secret preservation happens BEFORE merge: any incoming key where `is_secret_field_name(k)` and value == "" is popped, because the GET endpoint redacts secrets to "" and a naive merge would wipe the stored credential (:430-434). The live apply runs via `asyncio.to_thread` because `apply_knowledge_config` → `prepare_knowledge_update` performs a synchronous `embed_query("test")` network preflight on embedding changes; without the thread offload it stalls every other request (:455-461).

**Flow:** pop empty secret fields → merge over stored draft → filter to dataclass fields → hash pre-patch adaptation/glossary (audit) → `coerce_and_validate` (ClientAdaptationError→422 machine-readable dict; ValueError/TypeError→400) → `to_thread(apply_knowledge_config)` → ReindexInProgressError→409 structured `{error:"reindex_in_progress", collections}` → save draft POST-apply (only engine-accepted configs persist) → adopt-existing-collection check → registry reload + draft graph rebuild (best-effort, warn-only) → respond.
**Invariant:** The saved draft may never diverge from what the live engine accepted ("saved-but-not-applied was the previous bug") — EXCEPT one deliberate soft-fail branch: preflight auth failure with NO user-supplied key on a credentialed provider (openai/openrouter/litellm) whose error string looks like auth (401/Unauthorized/Invalid API/Incorrect API/AuthenticationError) returns 200 with `_preflight_warning`, because the failure is deployment env state, not user input. The classification reads the key from `filtered` (post-merge), NEVER from the raw body — a redacted "" in the PATCH means "keep stored", so reading the body would misclassify a real user key as absent (:500-508). All other live-apply failures → 400 and NO save; provider error detail stays log-only (never echoed into HTTP bodies).

**Probe:** `tests/unit/test_knowledge_patch_live_apply.py::test_patch_knowledge_applies_to_live_engine` (:48, pins that PATCH mutates `engine._config`, not just the draft) + `test_patch_knowledge_rejects_bad_config_without_partial_apply` (:102, invalid value lands nowhere); race pinning: `tests/unit/test_knowledge_draft_lmw_race.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "patch_draft_knowledge agent_draft_lock apply_knowledge_config ReindexInProgressError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-critical-section ordering (read→merge→validate→apply→save under one per-agent lock) and the post-apply save semantics with the env-key auth soft-fail carve-out. Adapt the lock primitive and config dataclass. Omit the registry-reload/draft-graph-rebuild tail if your product has no Try-It-Out draft agent. Direct tests exist for apply + reject paths.
