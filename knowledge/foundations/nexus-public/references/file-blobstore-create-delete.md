<!-- capsule-v2 -->
# FileBlobStore create/delete — how do you get crash-safe blob writes and two-phase soft delete on a plain filesystem?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-blobstore-file/.../FileBlobStore.java`); Codebase Memory `nexus-public`. **Question:** How do I implement content+attributes storage on a filesystem so partial writes never become visible, ID collisions self-heal, and deletion is recoverable until compaction?

## Temp-write → atomic move, per-blob lock, soft-delete index
**Path/Symbol:** `public/common/components/nexus-blobstore-file/src/main/java/org/sonatype/nexus/blobstore/file/FileBlobStore.java` — `create` retry loop (:400–421), `tryCreate` (:424–492), collision constants (:160–164), `doDelete` (:535–588), `doDeleteHard` (:590–630), hard-link copy with fallback (:493–518).
**Signature:** `private Blob tryCreate(Map headers, BlobIngester ingester, @Nullable BlobId reusedBlobId)`; `RETRY_ON_COLLISION = nexus.blobstore.retryOnCollision (default true)`, `MAX_COLLISION_RETRIES = 8`; per-blob mutual exclusion via `liveBlobs.getUnchecked(blobId).lock()`.
**Data Shape:** each blob = content file + `.properties` attributes file at the location-strategy path; temp siblings carry a random UUID suffix; metrics (`contentSize`) drive the running store size; soft delete stamps `deletedDateTime`, `softDeletedLocation`, `deletedReason` into attributes.

### Decisive source
```java
final Path temporaryBlobPath = temporaryContentPath(blobId, uuidSuffix);
...
Lock lock = blob.lock();
try {
  final boolean wouldCollide = fileOperations.exists(blobPath);
  if (reusedBlobId == null && RETRY_ON_COLLISION && wouldCollide && !isDirectPath) {
    throw new BlobCollisionException(blobId);          // caller retries with a NEW id
  }
  final StreamMetrics streamMetrics = ingester.ingestTo(temporaryBlobPath); // write tmp
  ...
  FileBlobAttributes blobAttributes = new FileBlobAttributes(temporaryAttributePath, headers, metrics);
  blobAttributes.store();                              // attrs to tmp too
  move(temporaryBlobPath, blobPath);                   // THEN atomic moves
  move(temporaryAttributePath, attributePath);
  return blob;
}
catch (Exception e) {
  // Something went wrong, clean up the files we created
  fileOperations.deleteQuietly(temporaryAttributePath);
  fileOperations.deleteQuietly(temporaryBlobPath);
  fileOperations.deleteQuietly(attributePath);
  fileOperations.deleteQuietly(blobPath);
  throw new BlobStoreException(e, blobId);
}
finally { lock.unlock(); }
```
```java
// doDelete: soft delete = relocate attributes copy + mark + index for compaction
blobAttributes.setDeletedDateTime(deletedDateTime);
blobAttributes.setSoftDeletedLocation(softDeletedPrefixLocation);
if (!originalPrefixLocation.equals(softDeletedPrefixLocation)) {
  ... newBlobAttributes.setOriginalLocation(getLocationPrefix(blobId));
  newBlobAttributes.store();                          // recovery copy under date-based prefix
}
blobAttributes.setDeleted(true);
blobAttributes.store();
blobDeletionIndex.createRecord(blobId);               // compact task consumes later
blob.markStale();
```

**Flow:** CREATE — resolve id from headers → per-blob lock → collision check (re-mint up to 8 times) → stream into `tmp/` sibling while hashing → attributes written next to it → BOTH moved into place atomically (`supportsAtomicMove`) → any failure deletes everything it touched. DELETE — missing attrs ⇒ fall back to hard delete; already-deleted ⇒ false; otherwise stamp deletion metadata, park a recovery copy of the attributes at a fresh date-based prefix, flip `deleted`, record in the deletion index, mark the live cache entry stale. Hard delete removes both files plus the parked copy and invalidates the cache entry.
**Invariant:** the content path never contains a partially-written file — readers only ever see complete files because publication is the rename. Deletion is two-phase BY CONSTRUCTION: soft-deleted blobs stay physically present (recoverable via the parked attribute copy's `originalLocation`) until the compact task hard-deletes from the index; metrics are only adjusted once, guarded by the existing-size/direct-path branch.
**Probe:** `nexus-blobstore-file/src/test/java/org/sonatype/nexus/blobstore/file/FileBlobStoreTest.java` plus concurrency ITs `FileBlobStoreConcurrencyIT.java`; undelete behavior pinned S3-side in `S3BlobStoreTest.testUndeleteSuccessful` (:325) against the shared `BlobStoreSupport` ladder.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "FileBlobStore tryCreate BlobCollisionException doDelete softDeletedLocation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt temp-sibling + atomic-move publication, the per-blob lock keyed off a live-blob cache, bounded collision re-minting, and soft-delete-with-parked-attributes before compaction. Adapt `FileOperations` (hard-link copy with automatic fallback when links fail) to your FS abstraction. Omit the datastore-backed deletion-index variant if you keep the index on-disk. Tests verified on-disk at the pinned commit.
