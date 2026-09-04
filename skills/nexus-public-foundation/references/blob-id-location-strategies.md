<!-- capsule-v2 -->
# Blob ID location strategies — how are blob IDs mapped to physical paths across file, S3, and group stores without a central index?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-blobstore/.../DefaultBlobIdLocationResolver.java` + strategy family); Codebase Memory `nexus-public`. **Question:** How do I derive a stable on-disk/object-store path from just a blob ID — including temporary and user-chosen direct-path blobs — so any store implementation finds the same object?

## Prefix-tagged ID grammar → four strategies
**Path/Symbol:** `public/common/components/nexus-blobstore/src/main/java/org/sonatype/nexus/blobstore/DefaultBlobIdLocationResolver.java` — prefixes (:44, :48), `getLocation` (:66–79), `getBlobIdLocation` (:81–89), `fromHeaders` (:96–105); `VolumeChapterLocationStrategy.java:location` (:35–42); `DateBasedLocationStrategy.java` (:23–33); `DirectPathLocationStrategy.java` (:29–38); `TemporaryLocationStrategy.java`; filename escaping in `LocationStrategySupport.escapeFilename` (:25–29).
**Signature:** `String getLocation(BlobId id)`; `BlobId fromHeaders(Map<String,String> headers)`; `tier = Math.abs(blobId.hashCode() % modulo) + 1`; constants `TIER_1_MODULO=43`, `TIER_2_MODULO=47`; `UNSAFE_TOKENS = [.\\:/]`.
**Data Shape:** ID grammar: plain UUID ⇒ volume/chapter; `tmp$<uuid>` ⇒ temp; `path$<name>` ⇒ direct-path (user-visible name embedded IN the id); IDs created after the datastore migration carry a `blobCreatedRef` timestamp ⇒ date-based layout.

### Decisive source
```java
public String getLocation(final BlobId id) {
  if (id.asUniqueString().startsWith(TEMPORARY_BLOB_ID_PREFIX)) {   // tmp$
    return temporaryLocationStrategy.location(id);                  // tmp/<escaped>
  }
  else if (id.asUniqueString().startsWith(DIRECT_PATH_BLOB_ID_PREFIX)) { // path$
    return directLocationStrategy.location(id);                     // directpath/<name>
  }
  return getBlobIdLocation(id);
}

private String getBlobIdLocation(final BlobId blobId) {
  if (blobId.getBlobCreatedRef() != null) {
    return dateBasedLocationStrategy.location(blobId);   // yyyy/MM/dd/<id>
  }
  return volumeChapterLocationStrategy.location(blobId);
}

// VolumeChapterLocationStrategy — two-tier hash fan-out
return String.format("vol-%02d/chap-%02d/%s",
    tier(blobId, TIER_1_MODULO), tier(blobId, TIER_2_MODULO), escapeFilename(blobId.asUniqueString()));
```
```java
// DirectPathLocationStrategy — traversal guard is load-bearing
String realBlobIdPath = blobId.asUniqueString().replace(DIRECT_PATH_PREFIX, "");
checkArgument(!realBlobIdPath.contains(".."), "Traversal not allowed with direct blobs");
```

**Flow:** `create` asks `fromHeaders`: TEMPORARY_BLOB_HEADER ⇒ mint `tmp$<uuid>`, DIRECT_PATH header ⇒ mint `path$<blobName>`, else plain uuid — the ID ITSELF encodes its layout class → every later read/compact/delete re-derives the location from the ID with no lookup table → two-tier vol/chap hashing spreads ~1M+ files evenly enough for filesystem comfort (43×47 ≈ 2k dirs at tier 2).
**Invariant:** path derivation is a PURE FUNCTION of the ID — any store implementation (file, S3) resolves identical IDs to identical relative paths, which is what makes attribute files, soft-delete relocation, and metrics all work unchanged across backends. The direct-path traversal check must run BEFORE formatting or `path$../../etc` escapes the content dir; filename escaping (`.` `\` `:` `/` → `-`) protects Windows and nested-path schemes.
**Probe:** `nexus-blobstore/src/test/java/org/sonatype/nexus/blobstore/DirectPathLocationStrategyTest.java` pins the traversal rejection; date-based streaming pinned in S3-side `S3BlobStoreTest.testGetBlobIdUpdatedSinceStream_dateBased` (:226).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "DefaultBlobIdLocationResolver VolumeChapterLocationStrategy DirectPathLocationStrategy getLocation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the encode-the-layout-in-the-ID grammar (plain/tmp$/path$ + created-ref timestamp) and pure-function path resolution with the two-tier hash fan-out. Adapt modulo counts to your expected file population. Omit the legacy migration branch if you start fresh with date-based IDs only. Traversal-guard test verified on-disk at the pinned commit.
