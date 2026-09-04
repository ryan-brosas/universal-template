<!-- capsule-v2 -->
# S3 multipart upload/copy — how do you stream unknown-length uploads and server-side copies to S3 with abort-on-failure and parallel part copying?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-blobstore-s3/.../MultipartUploader.java`, `ParallelRequester.java`, `ParallelCopier.java`); Codebase Memory `nexus-public`. **Question:** How do I implement S3 upload/copy that picks single-part vs multipart by size, aborts cleanly on any failure, and parallelizes large copies?

## Size-adaptive uploader + parallel copy requester
**Path/Symbol:** `public/common/components/nexus-blobstore-s3/src/main/java/org/sonatype/nexus/blobstore/s3/internal/MultipartUploader.java` — `upload` (:70–84: read first chunk, decide), `readChunk` boundary, `finally`-abort (:150+); `ParallelRequester.java` — thread pool (:43–53), `parallelRequests` (:64–110); `ParallelCopier.java` — `copy` (:48–68) + `copyParts` offset loop.
**Signature:** `void upload(EncryptingS3Client s3, String bucket, String key, InputStream contents)`; chunk size `nexus.s3.multipartupload.chunksize` (default 5,242,880 = S3's 5MB minimum part); copier parallelism `nexus.s3.parallelRequests.parallelism` (0 ⇒ `availableProcessors`).
**Data Shape:** uploader selected by Spring `@ConditionalOnProperty(nexus.s3.uploaderName)`; copier likewise (`parallelCopier` is matchIfMissing default); completed parts collected as `(partNumber, eTag)` pairs.

### Decisive source
```java
public void upload(final EncryptingS3Client s3, final String bucket, final String key, final InputStream contents) {
  try (InputStream input = contents) {
    InputStream chunkOne = readChunk(input);
    if (chunkOne.available() < chunkSize) {
      uploadSinglePart(s3, bucket, key, chunkOne);      // small => plain PutObject
    }
    else {
      uploadMultiPart(s3, bucket, key, chunkOne, contents);
    }
  }
  ...
  finally {
    if (uploadId != null) {                             // only set when multi started
      try { s3.abortMultipartUpload(...); } catch (...) { log.warn(...); }
    }
  }
}
```
```java
// ParallelRequester.parallelRequests — fixed pool + ExecutorCompletionService
final String uploadId = s3.createMultipartUpload(bucket, key).uploadId();
CompletionService<List<CompletedPart>> completionService = new ExecutorCompletionService<>(executorService);
for (int i = 0; i < parallelism; i++) {
  completionService.submit(() -> operations.get().apply(uploadId));   // workers pull offsets
}
List<CompletedPart> completedParts = new ArrayList<>();
for (int i = 0; i < parallelism; i++) {
  completedParts.addAll(completionService.take().get());              // all must succeed
}
// AWS S3 requires parts to be in ascending order by part number
completedParts.sort(Comparator.comparingInt(CompletedPart::partNumber));
s3.completeMultipartUpload(...);
```

**Flow:** UPLOAD — peek one chunk: under 5MB ⇒ PutObject; else initiate multipart, loop readChunk→uploadPart collecting eTags, complete; ANY exception after initiation runs `abortMultipartUpload` in `finally` so orphaned parts never bill forever. COPY — object smaller than chunk ⇒ single CopyObject; else multipart-copy where N workers pull `(partNumber = offset.getAndIncrement())` from a shared AtomicInteger, each computing byte ranges until exhausted, results gathered via completion service, SORTED BY PART NUMBER before Complete.
**Invariant:** the sort-before-complete step is mandatory — workers finish out of order and S3 rejects an unsorted part list. The abort-in-finally uses the null-until-initiated `uploadId` sentinel so single-part paths never attempt an abort. Workers share ONE uploadId but claim disjoint part numbers atomically; `take()` as many times as submitted makes failure of any worker propagate instead of hanging.
**Probe:** `nexus-blobstore-s3/src/test/java/.../MultipartUploaderTest.java` — `testUploadWithMultipartApi` (:57), `testUploadAbortsMultipartUploadsOnError` (:71), `testReadChunkReadsStreamsInChunks` (:84), `testUploadUsesPutObjectForSmallUploads` (:118); `ParallelCopierTest.java` — `testCopySplitsParts` (:100), `testCopyAbortsMultipartOnError` (:85), `testCalcFirstAndLastBytesProperly` (:53).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "MultipartUploader ParallelCopier parallelRequests abortMultipartUpload", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt first-chunk size probing, abort-on-any-failure via the initiated-uploadId sentinel, and the shared-offset worker pool with sort-before-complete. Adapt AWS SDK v2 client types and the property-driven strategy selection to your stack. Omit the alternate uploader/copier implementations (TransferManager, ProducerConsumer) unless you need their throughput profiles. Ten direct tests verified on-disk at the pinned commit.
