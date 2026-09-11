<!-- capsule-v2 -->
# BlobStoreSupport get-retry ladder — how does a blob read tolerate transient backend failures without retrying soft-deleted blobs forever?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-blobstore/.../BlobStoreSupport.java`); Codebase Memory `nexus-public`. **Question:** How do I add bounded retries around backend reads so eventual-consistency hiccups heal, while a genuinely deleted blob fails fast?

## One retry, delete-aware skip, interrupt-honoring sleep
**Path/Symbol:** `public/common/components/nexus-blobstore/src/main/java/org/sonatype/nexus/blobstore/BlobStoreSupport.java` — constants (:111–113: `DEFAULT_MAX_RETRIES=1`, `DEFAULT_RETRY_DELAY_MS=100`), `getWithRetries` (:246–260), `shouldSkipRetries` (:262–264), `retryGetBlob` (:266–282), `sleepBetweenRetries` (:284–296), `isBlobSoftDeleted` (:298–307), `doGet` live-blob cache (:309–318).
**Signature:** `Blob get(BlobId, boolean includeDeleted)` → `getWithRetries`; `maxRetries`/`retryDelayMs` settable via `setRetryConfiguration`.
**Data Shape:** `liveBlobs` is a `LoadingCache<BlobId, BlobSupport>`; staleness (post-delete/undelete) forces `refreshBlob`; attributes carry the soft-deleted flag.

### Decisive source
```java
private Blob getWithRetries(final BlobId blobId, final boolean includeDeleted) {
  Blob blob = doGet(blobId, includeDeleted);            // cache-first read
  if (blob != null) { return blob; }
  if (shouldSkipRetries(blobId, includeDeleted)) {      // deleted => fail fast
    return null;
  }
  return retryGetBlob(blobId, includeDeleted);
}

private boolean shouldSkipRetries(final BlobId blobId, final boolean includeDeleted) {
  return !includeDeleted && isBlobSoftDeleted(blobId);
}

private boolean sleepBetweenRetries(final BlobId blobId) {
  try { Thread.sleep(this.retryDelayMs); return false; }
  catch (InterruptedException e) {
    Thread.currentThread().interrupt();                 // restore flag, stop retrying
    return true;
  }
}
```
```java
// isBlobSoftDeleted — unreadable attributes are treated as NOT just-soft-deleted
catch (IOException e) { return false; }   // so the retry ladder still runs
```

**Flow:** get ⇒ live-blob cache (stale entries refresh against attributes) ⇒ miss ⇒ if caller didn't ask for deleted blobs AND attributes say soft-deleted, return null immediately (no retry — deletion is a durable state, not a hiccup) ⇒ else one retry after a 100ms delay; an interrupted sleep re-asserts the thread's interrupt flag and abandons the ladder.
**Invariant:** retries exist ONLY for transient backend failures (S3 flake, file race), never to poll away a confirmed soft-deleted state — the attributes probe converts a "missing" answer into a classified answer first. The interrupt path preserves the interrupted status instead of swallowing it. Unreadable attributes default toward retrying (assume transient) rather than toward skipping.
**Probe:** shared-behavior pins in store suites: `S3BlobStoreTest.testSoftDeleteReturnsFalseWhenBlobDoesNotExist` (:311), `testUndeleteSuccessful` (:325); file-side ITs exercise the same ladder through `FileBlobStoreTest`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "BlobStoreSupport getWithRetries shouldSkipRetries isBlobSoftDeleted retryGetBlob", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt classify-before-retry (attributes decide deleted-vs-transient), single bounded retry with fixed delay, and interrupt-flag-preserving backoff. Adapt the LoadingCache to your object pool. Omit the metrics/performance-logger decorations. Behavior boundary stated from source with cross-store test pins.
