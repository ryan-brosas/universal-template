<!-- capsule-v2 -->
# Auto-dispatch probe — how do you choose batch vs sequential without losing the first item or misreading a blip?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How does method="auto" detect Batch-API availability while preserving the stream it peeked?

## submit_episodes auto path
**Path/Symbol:** `ingestion/src/zep_ingest/submitters/__init__.py:30-118` (`submit_episodes`), `Method = Literal["auto","batch","sequential"]` at `:25`.
**Signature:** `submit_episodes(client, episodes, destination, *, method="auto", page_size=350, max_items_per_batch=10_000, batch_metadata=None, max_add_retries=3, max_retries=5, min_interval=0.0) -> IngestResult`.
**Data Shape:** Empty stream short-circuits to `IngestResult(method="sequential")` with zero calls; the peeked first episode is re-attached via `chain([first], iterator)`.

### Decisive source
```python
iterator = iter(episodes)
try:
    first = next(iterator)
except StopIteration:
    return IngestResult(method="sequential", client=client)
stream = chain([first], iterator)

summary, error = call_with_retries(create_probe_batch, max_retries=max_add_retries)
if error is not None:
    if is_batch_unavailable(error):
        result = SequentialSubmitter(...).submit(stream, destination)
        result.warnings.insert(0, notice)
        return result
    raise error
batch_id = require_batch_id(getattr(summary, "batch_id", None))
return BatchSubmitter(client, initial_batch_id=batch_id, **batch_kwargs).submit(
    stream, destination)
```

**Flow:** validate all numeric config → sequential? direct → auto: probe availability with the REAL batch.create (retried on transient errors so "a momentary blip can't crash the run or wrongly trip the sequential fallback — only a deployment that does not serve the endpoint does that") → hand the untouched stream to the chosen submitter, seeding BatchSubmitter with the probe's already-created batch_id.
**Invariant:** The probe consumes one real item and MUST be threaded back (`chain`) or that episode is silently dropped. Only 404 trips fallback; every other error is re-raised "rather than silently downgraded to sequential, which would hit the same wall one item at a time". A custom Pipeline submitter + method/batch_metadata args is a ConfigurationError, never ignored.
**Probe:** `grep -c 'def test' ingestion/tests/test_dispatch.py ingestion/tests/test_pipeline.py | awk -F: '{s+=$2} END{print s}'` → ≥30; see also `tests/test_threads.py::test_auto_falls_back_to_sequential_when_endpoint_not_found`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "submit_episodes auto probe batch create fallback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt probe-with-real-call + chain-back-the-peeked-item + 404-only fallback; adapt probe call and notice wording to your API; omit the Zep client typing.
