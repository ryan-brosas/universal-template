<!-- capsule-v2 -->
# Version-mismatch retry ladder — Why do reads retry on VersionMismatchError with a fixed backoff, and what does that say about read consistency?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** `_get`, `_count`, and `_query` carry identical tenacity decorators — what contract is a porter agreeing to by copying them?

## SegmentAPI retry decorators
**Path/Symbol:** `chromadb/api/segment.py:_get` (:667-673), `_count` (:921-927), `_query` (:940-953).
**Signature:** `@retry(retry=retry_if_exception(lambda e: isinstance(e, VersionMismatchError)), wait=wait_fixed(2), stop=stop_after_attempt(5), reraise=True)`.
**Data Shape:** Exactly 4 attempts spaced 2s; ONLY VersionMismatchError retries; after exhaustion the ORIGINAL error re-raises (reraise=True, not RetryError).

### Decisive source
```python
# We retry on version mismatch errors because the version of the collection
# may have changed between the time we got the version and the time we
# actually query the collection on the FE. We are fine with fixed
# wait time because the version mismatch error is not a error due to
# network issues or other transient issues. It is a result of the
# collection being updated between the time we got the version and
# the time we actually query the collection on the FE.
@retry(
    retry=retry_if_exception(lambda e: isinstance(e, VersionMismatchError)),
    wait=wait_fixed(2),
    stop=stop_after_attempt(5),
    reraise=True,
)
```

**Flow:** read path resolves collection version (Scan) → executes against segment(s) → if the underlying version advanced mid-plan, VersionMismatchError surfaces → whole read restarts at most 3 more times → final failure propagates to client as-is.
**Invariant:** Retries wrap WHOLE reads (plan+execute), not fragments — partial results never mix versions. Writes never retry here. The comment pins semantics: this is a consistency race, not transient-fault handling.
**Probe:** `/tmp/chroma-p1/probe_battery.py` api.retry_ladder anchor counting exactly 3 decorator sites (GREEN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "VersionMismatchError retry tenacity _query _get _count", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whole-read retry-on-version-race for snapshot-discovery storage engines; adapt backoff constants; omit in embedded single-node mode where scans cannot race compaction.
