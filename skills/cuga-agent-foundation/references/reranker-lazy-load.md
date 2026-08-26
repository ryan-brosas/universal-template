<!-- capsule-v2 -->
# Cross-encoder reranker with never-block lazy load — how do you add a heavy rerank model without ever letting a user query wait on a model download?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You want to rescore retrieval candidates with a cross-encoder (~1.1GB model), but a user query must NEVER block on a model download — what does the load lifecycle look like?

## UX contract first: search serves fusion-ranked results while the model loads in background
**Path/Symbol:** `src/cuga/backend/knowledge/reranker.py` — module docstring :1-20 (the contract), `_ENCODERS/_LOADING/_RETRY_AFTER/_LOCK` :64-67, `is_ready` :70-72, `_build_encoder` :75-87, `prewarm` :90-115, `ensure_loading` :118-144, `rerank` :147-173.
**Signature:** `prewarm(model_name) -> None` (blocking, idempotent, raises `RerankerUnavailableError`); `ensure_loading(model_name) -> None` (non-blocking, spawns one daemon thread); `rerank(query, candidates: list[RerankedCandidate], limit, model_name) -> list[RerankedCandidate]`; engine gates on `is_ready()` and only calls `rerank` when True.
**Data Shape:** `RerankedCandidate(text, score, metadata, original_score)` — after reranking, `score` becomes the cross-encoder score (ordering only) while `original_score` keeps the fusion score so callers never see suddenly-different score units in display.

### Decisive source
```python
# :96-112 prewarm — _LOCK guards ONLY fast dict/set ops, NEVER the download
with _LOCK:
    if model_name in _ENCODERS: return
    already = model_name in _LOADING
    if not already: _LOADING.add(model_name)
if already: return          # another thread owns the load
try:
    enc = _build_encoder(model_name)   # the slow part — OUTSIDE _LOCK
    ...
except Exception:
    with _LOCK: _RETRY_AFTER[model_name] = time.monotonic() + _RETRY_COOLDOWN_S  # 30s
    raise
```
```python
# :147-163 rerank refuses when not loaded — caller degrades to fusion ranking
encoder = _ENCODERS.get(model_name)
if encoder is None:
    raise RerankerUnavailableError(f"reranker model {model_name!r} is not loaded yet")
```
**Flow:** engine checks `is_ready()` → loaded? rerank : else serve fusion + `ensure_loading()` kicks background fetch → loader thread runs `prewarm` (double-checked under lock, download outside lock) → success publishes encoder + clears retry; failure records `time.monotonic() + 30s` cooldown so airgapped deploys don't hammer the network or spam logs → next queries rerank automatically once ready.
**Invariant:** (1) The lock must NEVER cover the download — holding it would block `is_ready` checks and searches for other models. (2) `rerank` raises rather than downloading when unloaded — a caller that skipped the gate degrades instead of blocking. (3) Failed loads back off 30s before any re-trigger. (4) Default model MUST be `BAAI/bge-reranker-base` (fastembed-servable); the popular `bge-reranker-v2-m3` is NOT fastembed-servable. (5) Mirror embedder offline-cache env (`FASTEMBED_CACHE_PATH`, `HF_HUB_OFFLINE`) so pre-baked containers stay offline.

**Probe:** `tests/unit/test_knowledge_reranker.py` — `test_rerank_sorts_trims_and_preserves_fusion_score` (:44), `test_rerank_refuses_when_not_loaded` (:59), `test_ensure_loading_populates_in_background` (:68), `test_ensure_loading_backs_off_after_failure` (:80).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "rerank RerankedCandidate prewarm ensure_loading RETRY_COOLDOWN", limit: 8 });
```
## Verdict
Adopt the three-function split (is_ready / ensure_loading / blocking prewarm) + refusal-on-unloaded for ANY optional heavy model behind a request path. Adapt the cooldown duration. Omit nothing — the original-score preservation is what keeps UI/eval stable across the flip.
