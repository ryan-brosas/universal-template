<!-- capsule-v2 -->
# S3 inverted-prefix keys + fire-and-forget deletes — lexicographic range deletion for numeric thresholds

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do you prune "all ping bodies with n ≤ threshold" from object storage when S3 has no numeric queries, without blocking the request path?

## enc / get_object / put_object / remove_objects
**Path/Symbol:** `hc/lib/s3.py:enc` (:54-75), `get_object` (:78-100), `put_object` (:103-117), `_remove_objects`/`remove_objects` (:120-158); singleton `client()` (:30-47); caller `Check.prune` (:574-604) and `Ping.get_body_bytes`.
**Signature:** `enc(n: int) -> str`; `get_object(code: str, n: int) -> bytes | None`; `put_object(code: UUID, n: int, data: bytes)`; `remove_objects(check_code: str, upto_n: int, wait: bool = False) -> None`.
**Data Shape:** Key = `f"{code}/{enc(n)}"`; enc emits `chr(122-len+1) + digitwise-inverted-digits-from-"j" + "-" + str(n)` (0→"zj", 4→"zf"); PoolManager pinned with `Retry(total=1)`.

### Decisive source
```python
# hc/lib/s3.py — the inverted sorting prefix, in full:
def enc(n):
    s = str(n)
    len_inverted = chr(ASCII_Z - len(s) + 1)
    inverted = "".join(chr(ASCII_J - int(c)) for c in s)
    return len_inverted + inverted + "-" + s
# >>> sorted([enc(i) for i in range(0, 5)])
# ['zf-4', 'zg-3', 'zh-2', 'zi-1', 'zj-0']      # smaller n sorts LAST

# Deletion is then a single start_after listing:
prefix = f"{code}/"
start_after = prefix + enc(upto_n + 1)
q = client().list_objects(settings.S3_BUCKET, prefix, start_after=start_after)

def remove_objects(check_code, upto_n, wait=False):
    """S3 API calls can take seconds... run the removal code on thread."""
    t = Thread(target=_remove_objects, args=(check_code, upto_n))
    t.start()
    if wait:
        t.join()
```

**Flow:** Write path: >100-byte bodies go to S3 under the check's key prefix; the Ping row stores only object_size. Read path: get_object maps NoSuchKey → None silently (not an error, not logged, not counted) while every OTHER failure logs and wraps as GetObjectError (feeding the token-bucket breaker). Prune path: Check.prune computes threshold = n_pings − ping_log_limit, fires threaded remove_objects (wait=True only from the slow batch command which also bumps S3_TIMEOUT to 60).
**Invariant:** The enc() grammar is load-bearing in BOTH directions: writes must use it so that "everything after enc(threshold+1)" equals "everything older than threshold"; the length-prefix char handles 9→10 rollover (fewer digits sort later). NoSuchKey must degrade to None BEFORE the generic handler or routine races (prune deleted it) page your error metrics. Deletes are best-effort by design — ReadTimeoutError during bulk delete is logged and counted, never raised; orphaned blobs are reclaimed by the separate pruneobjects sweep that diffs bucket prefixes against live check codes.
**Probe:** `hc/lib/tests/test_s3.py::test_get_object_handles_nosuchkey` (returns None AND statsd shows no error counter), `test_get_object_handles_s3error` (raises GetObjectError), `hc/api/tests/test_check_model.py::test_it_prunes_object_storage` (remove_objects called with (code, 1, wait=False)), `hc/api/tests/test_ping.py::test_it_uploads_body_to_s3`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "enc sorting prefix s3 object key", limit: 10 });
```
Resolves line-exact: hc.lib.s3.enc :54-75.

## Verdict
Adopt the inverted-digit key scheme for any threshold-range-delete need over lexicographic stores, NoSuchKey-is-None classification, retry(total=1) client discipline, and thread-offloaded deletes. Adapt key layout and the 60s slow-path timeout. Omit the orphan sweep only if you have lifecycle rules doing the same job.
