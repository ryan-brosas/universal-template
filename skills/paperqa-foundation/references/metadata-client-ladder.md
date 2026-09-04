<!-- capsule-v2 -->
# Metadata client ladder — when do you stop asking more metadata providers?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** How do multiple scholarly-metadata providers (Crossref, Semantic Scholar, OpenAlex...) run so failures degrade gracefully, results merge, and the ladder terminates as soon as hydration is complete?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/clients/__init__.py:DocMetadataClient.__init__/:query/:upgrade_doc_to_doc_details` (:84-263) over `client_models.py:MetadataProvider/DOIOrTitleBasedProvider/MetadataPostProcessor` (:91-193).
**Signature:** `async def query(self, **kwargs) -> DocDetails | None`; `metadata_clients` accepts flat collection OR nested Sequence-of-collections (nested ⇒ ORDERED task waves).
**Data Shape:** Each wave = `DocMetadataTask(providers, processors)`; providers fan out with `gather_with_concurrency(len(task.providers))` and merge by `sum()` (int-no-op route); processors get `copy.copy(doc_details)` each (idempotent, parallel-safe).

### Decisive source
```python
for ti, task in enumerate(self.tasks):
    doc_details = sum((p for p in await gather_with_concurrency(
        len(task.providers), task.provider_queries(query_args)) if p), ) or None
    if doc_details and task.processors:
        doc_details = sum(await gather_with_concurrency(len(task.processors),
            task.processor_queries(doc_details, client))) or None
    if doc_details:
        all_doc_details = doc_details + (all_doc_details or 0)
        if not all_doc_details.is_hydration_needed(inclusion=kwargs.get("fields", [])):
            break                                   # early termination
# DEFAULT_CLIENTS = (CrossrefProvider, SemanticScholarProvider, JournalQualityPostProcessor)
# ALL_CLIENTS adds OpenAlexProvider, UnpaywallProvider, RetractionDataPostProcessor
```
Graceful-degradation contract (`client_models.DOIOrTitleBasedProvider.query` :111-143): DOINotFoundError / httpx.RequestError / tenacity RetryError / TimeoutError each log-and-return-None so ONE dead provider never kills the batch.
**Flow:** Per wave: parallel provider queries → sum-merge → parallel post-processors → accumulate into `all_doc_details` → check `is_hydration_needed(inclusion=requested_fields)` → break if satisfied. Title queries enforce similarity ≥0.75 (provider-specific: S2 also requires author cross-check unless title similarity == 1.0).
**Invariant:** Providers return None on failure; they NEVER raise past this layer. Post-processors MUST be idempotent and order-independent (docstring-mandated). Early-stop only fires between waves, never mid-wave.
**Probe:** `tests/test_clients.py::test_ensure_sequential_run` (:645) + `::test_ensure_sequential_run_early_stop` (:691) pin wave ordering + early termination; `::test_ensure_robust_to_timeouts` (:626) pins graceful degradation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "DocMetadataClient is_hydration_needed DEFAULT_CLIENTS", limit: 10 });
// trace_path --function-name upgrade_doc_to_doc_details --direction inbound → Docs.aadd (hop1), agents.search.process_file (hop2)
```

## Verdict
Adopt the wave/processor split + hydration-based early stop + swallow-to-None provider contract; adapt provider set to your domain registries; omit nested-task support if one wave suffices. Runner caveat: upstream tests need network/cassettes; graph + source verified here.
