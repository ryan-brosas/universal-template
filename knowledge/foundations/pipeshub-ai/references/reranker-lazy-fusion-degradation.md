<!-- capsule-v2 -->
|# Reranker lazy-load, fixed-weight fusion, block-aware degradation — how do you add a cross-encoder reranker that never stalls the event loop and never makes results worse when it fails?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** Where do lazy construction, blocking-inference offloading, mixed-block-type score alignment, and total failure degradation live so a reranker is safe to bolt onto an existing retriever?

## Load on first use under a lock in to_thread; skip IMAGE/empty blocks symmetrically; every failure mode returns default-scored docs
**Path/Symbol:** `backend/python/app/modules/reranker/reranker.py:RerankerService` (whole file L1–131 direct HEAD read: `__init__` L13–36, `_load_model_sync` L38–44, `_ensure_model_loaded` L46–53, `rerank` L55–131); wiring `app/containers/query.py` Singleton `"BAAI/bge-reranker-base"` L58–61; consumed via QnA ChatState (`modules/agents/qna/chat_state.py:build_initial_state` :443–546 passes `reranker_service` into state).
**Signature:** `rerank(query: str, documents: list[dict], top_k: int|None) -> list[dict]`; documents carry `{content, score?, block_type}`; outputs gain `reranker_score`, `final_score`.
**Data Shape:** TABLE blocks (GroupType.TABLE) hold `content = (summary, children)` — only `content[0]` is scored; IMAGE blocks (BlockType.IMAGE) are excluded from pairs AND from score assignment; fusion constants 0.3/0.7; device "cuda"⇒fp16 `.half()`.

### Decisive source
```python
async def _ensure_model_loaded(self):
    if self.model is not None: return self.model        # fast path, no lock
    async with self._model_lock:
        if self.model is None:                          # double-checked: concurrent
            self.model = await asyncio.to_thread(       # first callers share ONE load
                self._load_model_sync)                  # (minutes cold; would stall loop)
    return self.model

# pair-building walk and score-assignment walk MUST skip the same docs:
if block_type == GroupType.TABLE.value:
    doc_query_pairs.append((query, content[0]))         # score the summary string
elif block_type != BlockType.IMAGE.value:
    doc_query_pairs.append((query, content))
...
scores = await asyncio.to_thread(model.predict, doc_query_pairs)   # CPU/GPU-bound off-loop
except Exception:                                       # ANY model failure:
    for doc in documents:                               # default scores, original order,
        doc["reranker_score"] = 0.0                     # never raise to caller
        doc["final_score"] = doc.get("score", 0.0)
    return documents
# index-aligned assignment: score_index advances ONLY for scored docs
doc["final_score"] = 0.3 * doc["score"] + 0.7 * doc["reranker_score"]  # else reranker-only
```
(L46–53, L77–81, L92–103, L105–116.)

**Flow:** constructor stores name/device ONLY → first rerank triggers locked one-shot load (+download) in worker thread → build (query, content) pairs skipping IMAGE/empty, taking TABLE summaries → predict in thread → assign scores by walking documents again with a parallel score_index → fuse 0.3·retriever+0.7·reranker (reranker-only if no retriever score) → sort desc by final_score → optional top_k.
**Invariant:** (1) Construction must not load the model (cold load can take minutes); loading must not block the loop; concurrent first calls must share ONE load — all three are pinned by test_lazy_load_on_first_rerank :81–94 (call_count stays 1). (2) Pair-building and score-assignment walks must exclude EXACTLY the same documents or scores shift onto wrong rows — mixed-block test :182–197 pins text=0.9/table=0.3/image=0.0. (3) Degradation is TOTAL and monotone: empty docs ⇒ [], no valid pairs ⇒ defaults preserving order (:153–163), predict raising ⇒ defaults (:247–257 region) — reranking can never make output worse than retrieval order + original scores. (4) Fusion weights are fixed constants (0.3/0.7) chosen so the cross-encoder dominates without discarding retrieval signal — exact-value test :119–127. (5) fp16 conversion happens once at load on cuda only.
**Probe:** EXECUTED at pin: combined battery 124 passed rc=0 (/tmp/psh21venv, includes tests/unit/modules/reranker/test_reranker.py with real torch CPU import path). Decisive tests listed above plus test_rerank_table_block_uses_first_content_element :167–177 (asserts pair == ("q", "table summary")) and test_rerank_empty_content_skipped :201–212. Anchor greps verified pre-write: `_model_lock` :36/:50, `content[0]` :79, fusion line :113.
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` file_pattern=`*.py` query="RerankerService rerank final_score weighted combination cross encoder" → resolves `RerankerService.rerank` + weighted-combination tests.

## Verdict
Adopt verbatim for any cross-encoder post-retrieval stage: lazy locked load in to_thread, twin-walk skip discipline for non-scorable blocks, fixed-weight fusion, degrade-to-defaults on every failure. Adapt block-type vocabulary and weights to your schema; keep the degradation contract absolute — a reranker that can raise is a reranker that will take down search.
