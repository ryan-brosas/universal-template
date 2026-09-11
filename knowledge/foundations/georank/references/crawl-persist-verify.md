<!-- capsule-v2 -->
# Durable crawl persistence — write-then-read-back before you commit pipeline state

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** How do you guarantee that HTML persisted by a crawler worker is actually readable by the NEXT worker in the chain before advancing the state machine?

## Put + verify-get equality gate
**Path/Symbol:** `backend/app/tasks/crawl.py` `persist_crawl_html` :296–303 (+ `StorageService` fallback memory in `app/services/storage.py`); pinned by `backend/tests/test_company_pipeline.py`.
**Signature:** `persist_crawl_html(storage_service, key: str, html: str) -> None` (raises RuntimeError on either failed put or mismatched read-back).
**Data Shape:** Object keys: `companies/{company_id}/raw.html`, `companies/{id}/{slug(role|title)}-{n}.html`, `diagnostics/{report_id}/raw.html`; `_slugify_page_key`: lowercase non-alnum→`-`, ≤40 chars, fallback "page".

### Decisive source
```python
def persist_crawl_html(storage_service, key: str, html: str) -> None:
    """Persist crawl HTML and prove that another process can read it back."""
    payload = html.encode("utf-8", errors="replace")
    if not storage_service.put(key, payload):
        raise RuntimeError(f"对象存储写入失败：{key}")
    stored = storage_service.get(key)
    if stored != payload:
        raise RuntimeError(f"对象存储回读校验失败：{key}")
```
Storage layer keeps an in-memory fallback for dev-without-MinIO — and the test pins that a SUCCESSFUL object write EVICTS the stale fallback entry (`test_successful_object_write_clears_stale_memory_fallback`).

**Flow:** encode with replacement (never throw on bad chars) → put → immediately GET and byte-compare → only then does the task write `raw_html_key` onto the company/report row and dispatch the next stage. A downstream stage re-reads from storage (`load_company_source_text`) rather than trusting the message payload.
**Invariant:** Pipeline state advances ONLY after durability is proven; the key stored in the DB is the single source of truth for later stages. Sub-page crawl failures are recorded per-page (`status:"failed"` + truncated reason) while homepage persistence remains all-or-nothing.
**Probe:** `backend/tests/test_company_pipeline.py::test_crawl_html_requires_durable_storage` (put-failure raises) + `::test_successful_object_write_clears_stale_memory_fallback`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "persist_crawl_html", limit: 5 });
// verified line-exact: crawl.py :296–303
```

## Verdict
Adopt write-read-back verification ahead of any state transition keyed on stored artifacts; adapt to S3/GCS conditional writes; keep per-page failure records for partial crawls.
