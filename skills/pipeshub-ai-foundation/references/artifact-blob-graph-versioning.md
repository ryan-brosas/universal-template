<!-- capsule-v2 -->
# Blob-then-graph versioning — in what ORDER do you write content bytes and version bookkeeping so neither store can lie?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** When a version bump spans a blob store (Mongo/Node) and a graph DB (Arango/Neo4j), what write order, failure marking, and dedupe contract keep the two consistent without distributed transactions?

## VersionManager: blob FIRST, graph second, PENDING_RECONCILE on the gap
**Path/Symbol:** `backend/python/app/services/artifact_registry/versioning.py:VersionManager.add_version/_append_version_bookkeeping/compute_content_hash/resolve_storage_version/recover_storage_version/PENDING_RECONCILE_REASON` (L52–510).
**Signature:** `add_version(*, actor, artifact_id, content: bytes, mime_type=None, expected_version=None) -> tuple[ArtifactVersion, ArtifactMetadata]`; `resolve_storage_version(current_version, versions, version) -> int | None` (pure); `recover_storage_version(current_version, storage_history_len, version) -> int | None`.
**Data Shape:** `versions` bookkeeping = list of `{registryVersion, storageVersion, contentHash?, sizeBytes?, createdAt?}` serialized as a JSON STRING on the artifacts doc (Neo4j-storable primitive shape). Registry versions are 1-based; `storageVersion` indexes the blob store's own history.

### Decisive source
```python
# Order is the invariant (module docstring): "blob-then-graph ... never the
# reverse — an orphaned blob version with no graph pointer is harmless dead
# storage; a graph version bump with no matching blob would serve WRONG or
# MISSING CONTENT."
upload_result = await blob_store.upload_artifact_version(...)   # 1. durable bytes
new_versions = self._append_version_bookkeeping(existing, upload_result=...)
try:
    await graph.update_node(artifact_id, RECORDS, {"version": new_version, ..., "reason": None})
    await graph.update_node(artifact_id, ARTIFACTS, {"contentHash": ..., "versions": serialize(...)})
except Exception:
    logger.critical("PENDING_RECONCILE: blob version write SUCCEEDED ... but graph update failed")
    try: await graph.update_node(artifact_id, RECORDS, {"reason": PENDING_RECONCILE_REASON})
    except Exception: logger.critical("Failed to even mark ...")
    raise VersionSyncError(...) from None      # NEVER reported to caller as success

# Dedupe: identical sha256 → return CURRENT version with deduplicated=True,
# zero writes — re-running the same code is idempotent instead of accumulating no-op bumps.
if artifact_doc.get("contentHash") == compute_content_hash(content):
    return ArtifactVersion(version=current_version, ..., deduplicated=True), metadata

# Optimistic concurrency WITHOUT compare-and-swap primitives:
if expected_version is not None and expected_version != current_version:
    raise VersionConflictError("... reload and retry.")
```
Storage indices come ONLY from `upload_result["storageVersion"]` / `priorStorageVersion` — never computed from `new_version`, because Node's `versionHistory` numbering isn't guaranteed to track registry versions 1:1. First-ever bump backfills version 1's mapping from `priorStorageVersion`; if Node didn't report one, log loudly ("registryVersion=%d is now unreachable") rather than invent an index.

**Flow:** authorize → read record+artifact docs → optional expected-version check → hash-dedupe short-circuit → blob upload → append bookkeeping (backfilling v1) → dual graph update → on graph failure mark `reason=PENDING_RECONCILE` (best-effort) and raise `VersionSyncError`. Reads map registry→storage via `resolve_storage_version` (`None` = current = skip `?version=` fast path; unmapped ⇒ try positional recovery before 404).
**Invariant:** (1) Blob-before-graph ALWAYS — the asymmetry makes single-sided failure benign in exactly one direction. (2) A graph-side failure must surface as `VersionSyncError`, never success-with-stale-metadata. (3) `recover_storage_version` maps positionally ONLY when `storage_history_len == current_version` proves the 1:1 layout; any other length returns None and the caller 404s rather than serves wrong bytes ("verified inference, not the guess resolve refuses to make"). (4) Recovery persistence is best-effort — a failed repair still serves THIS request, leaving the next one to recover again. (5) Bookkeeping serialization must survive BOTH stores (JSON string form accepted by `deserialize_artifact_versions` alongside native lists).
**Probe:** `tests/unit/services/artifact_registry/test_versioning.py` (346L + fakes.py): creates_record_artifact_and_owner_edge :42; raises_version_sync_error_when_no_document_id :75; serialized-string bookkeeping accepted :99; bumps_version :114; **identical_content_deduplicates_without_bumping** :134; neo4j_storable_shape :152; second_bump_reads_back_own_serialized_form :177; concurrent_writer_raises_version_conflict :196; graph_update_failure_marks_pending_reconcile :210; complete_history_maps_positionally :244; refuses_when_history_length_disproves_layout :248; repair_persists :273–293; serves_request_even_when_repair_write_fails :317.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "VersionManager add_version _append_version_bookkeeping recover_storage_version PENDING_RECONCILE" --detail ids
```

## Verdict
Adopt blob-then-graph ordering with the PENDING_RECONCILE marker + reconciler loop, hash-dedupe idempotency, expected_version optimistic conflict, storage-index-from-upload-response-only, and length-verified positional recovery. Adapt store adapters to host infra. Omit Mongo/Node blob internals.
