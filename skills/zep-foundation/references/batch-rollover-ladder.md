<!-- capsule-v2 -->
# Batch submitter rollover ladder — what happens when batch.create fails at page 40 of 50?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How does bulk submission keep already-submitted work recoverable while never letting a mid-run failure crash the run?

## BatchSubmitter
**Path/Symbol:** `ingestion/src/zep_ingest/submitters/batch.py:38` (`BATCH_UNAVAILABLE_STATUS_CODES = frozenset({404})`), `:41` (`require_batch_id`), `:57` (`rollover_failure_message`), `:71` (`is_batch_unavailable`), `:76` (`process_batch`), `:96-241` (`BatchSubmitter.submit/_create_batch/_add_page`).
**Signature:** `submit(episodes, destination) -> IngestResult`; pages via `islice(iterator, page_size≤350)`, rolls over at `max_items_per_batch` (default 10k, cap 50k).
**Data Shape:** Result carries `batch_ids` (the resume handles), `add_errors[index=page_index]`, `items_submitted`.

### Decisive source
```python
# _create_batch — first vs rollover failure are DIFFERENT failure classes
if error is not None:
    if result.batch_ids:
        result.add_errors.append(AddError(index=-1, item_count=0,
            error=rollover_failure_message(error, result)))
        return None                      # stop the run, KEEP submitted ids
    if isinstance(error, httpx.TransportError):
        raise InvalidBatchResponseError(... partial_result=result) from error
        # no response ⇒ the batch may exist unidentifiable; refuse to submit
    if is_batch_unavailable(error):
        raise BatchUnavailableError(partial_result=result) from error
    raise error                          # first-batch: caller may fall back
```

**Flow:** page → (if adding would exceed max_items_per_batch: process_batch + reset) → create batch if none open → map page to BatchAddItem → add_page with retries; a persistently failing PAGE records AddError and CONTINUES ("nothing that happens after the first batch opens is allowed to crash the run"); final batch processed after loop. process_batch pins a failed process attempt terminal on the result via mark_batch_failed instead of raising.
**Invariant:** Only HTTP 404 means "deployment does not serve Batch API" — every other refusal (bad key, exhausted quota) would refuse graph.add just as readily, so falling back would hide the real error behind a slow run. A transport error on create can NEVER prove availability or unavailability (no status): it raises rather than triggering sequential fallback. Rollover failure must not raise because earlier batches are still processing and their ids are the only recovery handle.
**Probe:** `grep -c 'def test' ingestion/tests/test_batch_submitter.py` → 24 incl. `test_rollover_failure_stops_the_run_without_losing_batch_ids`, `test_transport_error_on_rollover_stops_and_keeps_batch_ids`, `test_missing_batch_id_fails_before_add`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "BatchSubmitter rollover create batch_id process", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt first-create-vs-rollover asymmetry + 404-only fallback signal + page-failure record-and-continue + require_batch_id fail-fast; adapt paging limits to your API caps; omit Zep's BatchSummary pinning details.
