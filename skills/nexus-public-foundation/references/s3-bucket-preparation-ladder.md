<!-- capsule-v2 -->
# S3 bucket preparation ladder — how do you validate/create a bucket at blobstore start with ownership checks and permission-specific errors?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-blobstore-s3/.../BucketManager.java`, `BucketValidationCacheService`); Codebase Memory `nexus-public`. **Question:** How do I make "ensure bucket exists" idempotent, cluster-cheap, and diagnostic — distinguishing access-denied from ownership violations?

## Cached validation + create-on-missing + typed errors
**Path/Symbol:** `public/common/components/nexus-blobstore-s3/src/main/java/org/sonatype/nexus/blobstore/s3/internal/BucketManager.java:prepareStorageLocation` (:70–86), `createBucketAndInvalidateCache` (:88–105); validation cache in `BucketValidationCacheService.validate`.
**Signature:** `void prepareStorageLocation(BlobStoreConfiguration config)` (implements `StorageLocationManager`); error factory methods on `S3BlobStoreException`: `bucketOwnershipError()`, `insufficientCreatePermissionsError()`, `unexpectedError(op)`.
**Data Shape:** `BucketValidationResult = {exists, ownershipValid}` memoized per bucket by the cache service (so N nodes / repeated starts don't each hit ListObjects); AWS error code string compared against `ACCESS_DENIED_CODE`.

### Decisive source
```java
public void prepareStorageLocation(final BlobStoreConfiguration blobStoreConfiguration) {
  String bucket = getConfiguredBucket(blobStoreConfiguration);
  try {
    BucketValidationResult result = cacheService.validate(bucket);
    if (!result.exists()) {
      createBucketAndInvalidateCache(bucket);
    }
    else if (!result.ownershipValid()) {
      throw bucketOwnershipError();        // exists but NOT ours => refuse loudly
    }
  }
  catch (ExecutionException e) {
    throw new BlobStoreException("Failed to validate bucket: " + bucket, e.getCause(), null);
  }
}

private void createBucketAndInvalidateCache(final String bucket) {
  try {
    s3.createBucket(bucket);
    cacheService.invalidate(bucket);       // next validation re-checks for real
  }
  catch (S3Exception e) {
    if (ACCESS_DENIED_CODE.equals(e.awsErrorDetails().errorCode())) {
      log.error("Error creating bucket {}", bucket, e);
      throw insufficientCreatePermissionsError();   // actionable: fix IAM
    }
    throw unexpectedError("creating bucket");
  }
}
```

**Flow:** start/prepare ⇒ cached validate (exists + owner tag check) ⇒ missing ⇒ create then invalidate cache entry ⇒ AccessDenied on create ⇒ dedicated "insufficient permissions" exception; exists-but-foreign-owned ⇒ dedicated ownership error (prevents silently writing into someone else's bucket); any other failure ⇒ generic unexpected.
**Invariant:** creation success INVALIDATES the cache rather than priming it — the next validation must observe real state (another node may have raced). Ownership is checked even when the bucket exists so misconfiguration cannot poison another account's data. Error types are chosen to be actionable: IAM problem ≠ ownership problem ≠ unknown.
**Probe:** `nexus-blobstore-s3/src/test/java/.../BucketManagerTest.java` and `BucketValidationCacheServiceTest.java` pin the validate/create/invalidate branches and the access-denied mapping.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "BucketManager prepareStorageLocation BucketValidationCacheService createBucketAndInvalidateCache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt cache-validate → create-on-missing → invalidate-after-create, the exists-but-not-owned refusal, and access-denied-specific error typing. Adapt AWS SDK v2 specifics and the feature-flagged ownership check to your cloud layer. Omit the encryption-client wrapper plane. Branch tests verified on-disk at the pinned commit.
