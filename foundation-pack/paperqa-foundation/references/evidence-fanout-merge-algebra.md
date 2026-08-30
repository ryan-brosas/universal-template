<!-- capsule-v2 -->
# Evidence fan-out & merge algebra — how do per-chunk evidence calls merge into a session without duplicates or lost cost?

**Source:** paper-qa Apache-2.0 `main@57e89f72`; Codebase Memory `paper-qa`. **Question:** When scoring many text chunks against a question concurrently, which chunks are selected, what bounds the concurrency, and what is the merge rule into session state?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/docs.py:Docs.aget_evidence` (:492-586).
**Signature:** `async def aget_evidence(self, query: PQASession | str, settings=None, callbacks=None, embedding_model=None, summary_llm_model=None, partitioning_fn=None) -> PQASession`.
**Data Shape:** Selection gate `answer.evidence_retrieval` (True → vector top-`evidence_k` via `retrieve_texts`; False → ALL texts, uncapped). Fan-out runs through external bounded-concurrency gather (`gather_with_concurrency(max_concurrent_requests, [...])` — imported from the `lmi` package, not defined in this repo). Each job returns `(Context | None, llm_results)`.

### Decisive source
```python
matches = await self.retrieve_texts(...) if answer_config.evidence_retrieval else self.texts  # :522-530
results = await gather_with_concurrency(answer_config.max_concurrent_requests, [map_fxn_summary(...) for m in matches])
for _, llm_results in results:
    for r in llm_results:
        session.add_tokens(r)          # :573-575 EVERY result, even abandoned contexts
session.contexts += list({             # :577-585 merge algebra
    c for c, _ in results
    if c is not None and c.score > 0 and c not in session.contexts
})
```

**Flow:** empty-corpus early return (`not self.docs and len(self.texts_index) == 0`) → select candidates by the retrieval gate → per-match citation prompt data (`f"{m.name}: {m.doc.formatted_citation}"`) and JSON-vs-prose template pick → bounded concurrent context creation → token ledger over all LLMResults → filtered set-dedupe append to `session.contexts`. The dedupe relies on pydantic equality of Context objects, so an identical re-gathered context never doubles.
**Invariant:** Abandoned contexts (None) never enter `session.contexts`, but their tokens ALWAYS reach the ledger; the merge only admits strictly-positive-scored contexts (`score > 0`), making score 0 the explicit "irrelevant" sentinel that pairs with the no-model default of 5.
**Probe:** `tests/test_paperqa.py::test_evidence` (:783-839) pins uniqueness (`len({e.context}) == len(evidence)`), ≥ evidence_k yield, and source reuse across separate aget_evidence calls; `::test_too_much_evidence` (:2588-2606) stresses the knobs. Deterministic source/test-range probe (no runner provisioned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "aget_evidence gather contexts score", limit: 10 });
// trace_path --project paper-qa --function-name map_fxn_summary --direction inbound → Docs.aget_evidence (hop 1)
```

## Verdict
Adopt the merge algebra (positive-score filter + whole-object dedupe + failure-inclusive token accounting) and the retrieval gate; adapt the concurrency primitive (any semaphore-bounded gather preserving result pairing); omit lmi-specific gather semantics — record it as an external dependency if you port verbatim. Coverage: docs.py no_recorded_issue + metadata_match @ gen 2026-08-25T19:57:59Z.
