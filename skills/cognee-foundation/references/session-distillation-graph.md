<!-- capsule-v2 -->
# Session distillation & memory — conversations become first-class graph content

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do chat sessions get persisted INTO the knowledge graph so retrieval can answer from conversation history?

## session_distillation + cognify_session
**Path/Symbol:** `cognee/modules/session_distillation/` (:524L total); session pipeline entry `cognee/api/v1/session/`; session manager consumed by retrievers via `cognee/infrastructure/session/get_session_manager.py:get_session_manager` and `generate_completion_with_session(...)` (graph_completion_retriever.py :399-412).
**Signature:** session turns are stored raw by the session manager; a distillation step converts accumulated history into DataPoints processed through the standard cognify task list.
**Data Shape:** Conversation summaries land as graph nodes with `belongs_to_set` scoping and deterministic identity so later mentions merge.

### Decisive source
```python
use_session = self._use_session_cache() and not query_batch
if use_session:
    sm = get_session_manager()
    completion = await sm.generate_completion_with_session(
        session_id=self.session_id, query=query, context=context,
        summarize_context=False,
        used_graph_element_ids=used_graph_element_ids,  # access tracking hook
        max_context_chars=getattr(self, "max_context_chars", None),
        effective_query=effective_query,
        turn_preparation=turn_preparation)
```

**Flow:** live turns go through the session manager (history + context assembly + completion in one call) → distillation pipelines re-shape stored sessions into chunk/document DataPoints → those ride the NORMAL cognify route (chunk → extract → store) so conversational knowledge is searchable by every retriever, not a special-case path. Session-scoped retrievers (`session_id` param on most) filter summaries to the conversation's scope.
**Invariant:** (1) Distilled sessions must reuse standard ingestion tasks — a parallel write path would bypass provenance, rollback, and incremental markers. (2) Batch queries never take the session path (`not query_batch` guard): multi-turn state is meaningless across an arbitrary batch. (3) `summarize_context=False` at this layer — context summarization is owned elsewhere to keep retrievers composable.
**Probe:** `cognee/tests/unit/modules/session_distillation/`; session lifecycle pins under `cognee/tests/unit/modules/session_lifecycle/`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "session_distillation generate_completion_with_session session_manager cognify_session", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt distill-into-standard-pipeline for conversational memory; adapt session storage to your infra; omit live turn-management if your host owns it.
