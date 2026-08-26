<!-- capsule-v2 -->
# Blob store group fill policies — how do writes land on one member while reads/deletes fan out across all of them, and where is the membership remembered?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-blobstore/.../group/BlobStoreGroup.java` + `FillPolicy` implementations); Codebase Memory `nexus-public`. **Question:** How do I implement a storage group that spreads or concentrates writes by policy while remaining able to FIND any previously written blob?

## Fill-policy write routing + locatedBlobs cache + search fallback
**Path/Symbol:** `public/common/components/nexus-blobstore/src/main/java/org/sonatype/nexus/blobstore/group/BlobStoreGroup.java` — `create(headers, fn)` (:226–236), `locatedBlobs` cache (:127–128), `locate(BlobId)` (:550–566), `get(includeDeleted)` fan-out (:296–311), `delete` all-match (:313–330); `RoundRobinFillPolicy.nextMember` (rotating index + writability/quota filters); `WriteToFirstMemberFillPolicy.chooseBlobStore` (:50–60).
**Signature:** `@Nullable BlobStore chooseBlobStore(BlobStoreGroup group, Map<String,String> headers)`; group create ⇒ `fillPolicy.chooseBlobStore(this, headers)` then `locatedBlobs.put(blob.getId(), result.getName())`.
**Data Shape:** `locatedBlobs` is a distributed `Cache<BlobId,String>` (blob id → member NAME) populated only for WRITABLE members; fill policies are named Spring components (`writeToFirst`, round-robin) selected per group configuration.

### Decisive source
```java
private Blob create(final Map<String, String> headers, final CreateBlobFunction createBlobFunction) {
  BlobStore result = fillPolicy.chooseBlobStore(this, headers);
  if (result == null) {
    throw new BlobStoreException("Unable to find a member Blob Store of '" + this + "' for create", null);
  }
  Blob blob = createBlobFunction.create(result);
  locatedBlobs.put(blob.getId(), result.getBlobStoreConfiguration().getName()); // REMEMBER the member
  return blob;
}

Optional<BlobStore> locate(final BlobId blobId) {
  String blobStoreName = locatedBlobs.get(blobId);       // fast path: cached member
  if (blobStoreName != null) {
    return Optional.ofNullable(blobStoreManager.get(blobStoreName));
  }
  BlobStore blobStore = search(blobId);                  // slow path: ask every member
  if (blobStore != null && blobStore.isWritable()) {
    locatedBlobs.put(blobId, blobStore.getBlobStoreConfiguration().getName());
  }
  return Optional.ofNullable(blobStore);
}
```
```java
// RoundRobinFillPolicy: rotate start index, then first PASSING member wins
final int index = nextIndex() % members.size();
ArrayList<BlobStore> rotatedMembers = new ArrayList<>(members);
rotate(rotatedMembers, index);
return rotatedMembers.stream()
    .filter(BlobStore::isWritable)
    .filter(BlobStore::isStorageAvailable)
    .filter(skipOnSoftQuotaViolation ? this::hasNoQuotaViolation : s -> true)
    .findFirst().orElse(null);
```

**Flow:** WRITE — policy picks one passing member (round-robin rotates the START of the candidate list so full/quota-violating early members are skipped rather than blocking), blob written there, id→member recorded in `locatedBlobs`. READ — cache hit ⇒ single-member get; miss ⇒ `search` probes every member; includeDeleted reads bypass the cache entirely and scan members for existence. DELETE — remove from cache FIRST, then soft-delete on EVERY member where the blob exists, requiring ALL to succeed.
**Invariant:** a blob lives on exactly ONE member but the group must find it without a global index — hence the write-time memo plus exhaustive-search fallback; deleting from every existing location keeps replicas consistent if a future policy ever duplicates. Policies filter on writability AND storage availability AND (optionally) quota at SELECTION time, never after.
**Probe:** `nexus-blobstore/src/test/java/org/sonatype/nexus/blobstore/group/internal/RoundRobinFillPolicyTest.java`, `WriteToFirstMemberFillPolicyTest.java`, `BlobStoreGroupTest.java` pin selection order, rotation, and quota-skip behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "BlobStoreGroup chooseBlobStore locate RoundRobinFillPolicy locatedBlobs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt policy-selected single-member writes with write-time member memoization and search-on-miss, plus delete-fanout-with-all-match. Adapt the distributed-cache helper to your clustering story (a local map works single-node). Omit the metrics-service aggregation surface. Selection tests verified on-disk at the pinned commit.
