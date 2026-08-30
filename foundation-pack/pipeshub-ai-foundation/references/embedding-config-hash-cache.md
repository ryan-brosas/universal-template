<!-- capsule-v2 -->
|# Embedding-instance config-hash cache — how do you make admin model changes take effect on the next query without paying model-construction cost when nothing changed?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** Where do you re-read mutable AI-provider config (so a UI change is live immediately) while still caching the expensive constructed object across queries?

## Re-read config every call; rebuild the instance only when its hash moves
**Path/Symbol:** `backend/python/app/modules/retrieval/retrieval_service.py:RetrievalService._embedding_config_hash` (L170–185) + `get_embedding_model_instance` (L187–234) + `_ensure_sparse_embedder` (L120–131); state seeded in `__init__` L104–111.
**Signature:** `_embedding_config_hash(embedding_configs: list[dict]|None) -> str` (static); `get_embedding_model_instance(use_cache: bool = False) -> Embeddings|None`.
**Data Shape:** cache pair `(_cached_dense_embeddings, _cached_embedding_config_hash)` guarded by `_embedding_model_lock: asyncio.Lock`; hash input per config = `{provider, isDefault, model, endpoint}` serialized with `json.dumps(..., sort_keys=True)`, sha256 truncated to 16 hex chars; empty config list hashes to literal `"default"`.

### Decisive source
```python
ai_models = await self.config_service.get_config(AI_MODELS, use_cache=use_cache)
config_hash = self._embedding_config_hash((ai_models or {}).get("embedding"))
if self._cached_dense_embeddings is not None \
        and self._cached_embedding_config_hash == config_hash:
    return self._cached_dense_embeddings          # fast path OUTSIDE the lock
async with self._embedding_model_lock:            # double-checked
    if ...hash unchanged...: return self._cached_dense_embeddings
    selected = next((c for c in embedding_configs if c.get("isDefault", False)),
                    embedding_configs[0])            # isDefault-first, [0] fallback
    dense_embeddings = await asyncio.to_thread(get_embedding_model,
                                               selected["provider"], selected)
self._cached_dense_embeddings = dense_embeddings   # stamp AFTER successful build
self._cached_embedding_config_hash = config_hash
```
(L195–231; error tail L232–234 logs and returns None — never raises to the caller.)

**Flow:** every query → read current AI_MODELS config → hash it → unchanged ⇒ reuse instance (no lock taken) → changed/first call ⇒ double-checked rebuild under lock in `asyncio.to_thread` (heavy SDK construction off the loop) → stamp instance+hash together. SparseEmbedder follows the same shape but capability-gated (`supports_sparse_vectors`) with its own `_sparse_embedder_lock`.
**Invariant:** (1) Config freshness is PER-CALL, instance construction is PER-HASH — you get both immediate provider swaps and zero steady-state cost. (2) The hash covers exactly the fields that change model behavior ({provider,isDefault,model,endpoint}); unrelated config churn must not evict. (3) Cache stamping happens only after a successful build — a failing provider swap leaves the old working instance + old hash intact. (4) Errors degrade to None (caller raises "No dense embeddings found"), never propagate config exceptions into search results. (5) The fast path checks BEFORE taking the lock — hot queries pay one dict compare.
**Probe:** EXECUTED at pin: combined battery 124 passed rc=0 via /tmp/psh21venv. Decisive tests: TestGetEmbeddingModelInstance test_caches_model_when_config_unchanged :323–338 ("config read twice, model built once", `first is second`, get_config.await_count >= 2), test_rebuilds_model_when_config_changes :341–364 (openai→cohere swap builds model_b), test_prefers_is_default_config :367–384 (second-listed isDefault wins), test_uses_default_when_no_embedding_config :313–320, test_returns_none_on_error :387–390. Anchor greps verified pre-write: `supports_sparse_vectors` :122/:815.
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` file_pattern=`*modules/retrieval/*` query="get_embedding_model_instance embedding config hash cache" → resolves `_embedding_config_hash` + `get_embedding_model_instance` (graph offsets :166–180/:182–229 vs HEAD :170–185/:187–234 — source wins).

## Verdict
Adopt whenever a long-lived service consumes user-mutable provider/model config: re-read + hash every call, double-checked rebuild, stamp-after-success, None-on-error. Adapt the hashed-field set to what your constructors actually consume. Omit the to_thread only if your builder is already async-cheap; never omit the outside-lock fast path or every query serializes on the lock.
