<!-- capsule-v2 -->
# Validated-replay spool — how does a lazy stream get fully validated before an async submitter consumes it?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How can run() guarantee every Episode is constructor-valid before submission without materializing the list in RAM?

## _validated_replay
**Path/Symbol:** `ingestion/src/zep_ingest/pipeline.py:71-99` (`_validated_replay` contextmanager).
**Signature:** `@contextmanager def _validated_replay(episodes: Iterable[Episode]) -> Iterator[Iterator[Episode]]` using `SpooledTemporaryFile(max_size=8*1024*1024, mode="w+b")`.
**Data Shape:** Each episode pickled as a 5-tuple `(data, data_type, created_at, metadata, document)` with `pickle.HIGHEST_PROTOCOL`; replay reconstructs Episode objects (re-running `__post_init__` validation).

### Decisive source
```python
with SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as spool:
    for episode in episodes:
        record = (episode.data, episode.data_type, episode.created_at,
                  episode.metadata, episode.document)
        pickle.dump(record, spool, protocol=pickle.HIGHEST_PROTOCOL)
    spool.seek(0)
    def replay() -> Iterator[Episode]:
        while True:
            try:
                data, data_type, created_at, metadata, document = pickle.load(spool)
            except EOFError:
                return
            yield Episode(data=data, ...)
```

**Flow:** run() drains the ENTIRE user stream through the spool (constructing each Episode = eager validation; a bad episode raises HERE, before any API call) → yields `replay()` generator → submitter consumes the replayed stream once.
**Invariant:** The spool is the mechanism that lets submission stay streaming while validation stays total: episodes >8MB spill to disk instead of RAM. Reconstruction goes through the Episode constructor again, so validation cannot be bypassed by a custom loader yielding pre-baked objects. Without this, an async BatchSubmitter consuming a live generator would interleave validation failures with half-submitted batches.
**Probe:** `grep -n 'SpooledTemporaryFile' ingestion/src/zep_ingest/pipeline.py` → 2 hits (import :17, use :73); direct test coverage via `ingestion/tests/test_pipeline.py::test_run_*` family.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "_validated_replay SpooledTemporaryFile replay pickle", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt validate-then-spool-then-replay for any async bulk submission of lazily generated records; adapt the 8MB spool threshold and pickle protocol to your payload sizes; omit if your host already materializes records eagerly.
