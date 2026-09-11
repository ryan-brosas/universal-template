<!-- capsule-v2 -->
# Storage-version upgrade policy — how do you migrate every segment to a new on-disk format without overwhelming the cluster or downgrading LOB capability?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** How does a background policy rewrite segments from storage V2→V3 (and normalize column-group formats) under a token-bucket rate limit and a version-compatibility gate?

## Rate-limited upgrade with semver floor + TEXT-field refusal
**Path/Symbol:** `internal/datacoord/compaction_policy_storage_version.go` (policy 34–52, targetVersion 63–69, Trigger 93–135, triggerOneCollection 137–215).
**Signature:** `func (policy *storageVersionUpgradePolicy) Trigger(ctx) (map[CompactionTriggerType][]CompactionView, error)`; `func segmentColumnGroupFormatsAllEqual(segment *SegmentInfo, targetFormat string) bool`.
**Data Shape:** Non-thread-safe rate state (`lastPeriod time.Time; currentCount int`) — deliberately single-goroutine. Config: StorageVersionCompactionEnabled, StorageFormatCompactionEnabled, SessionVersionRequirement (semver string), RateLimitInterval, RateLimitTokens, DataNodecfg.StorageFormat.

### Decisive source
```go
minVersion := policy.versionManager.GetMinimalSessionVer()
if minVersion.LT(versionRequirement) {
    mlog.Info(ctx, "storage version upgrade policy skipped due to minimal querynode version does not satisfy requirement", ...)
    return map[CompactionTriggerType][]CompactionView{}, nil
}
...
// TEXT fields require V3 manifest storage for LOB support and cannot be
// downgraded ... skip this collection entirely instead of silently bumping
if targetVersion < storage.StorageV3 {
    for _, field := range collection.Schema.GetFields() {
        if field.GetDataType() == schemapb.DataType_Text { return nil, nil }
    }
}
```

**Flow:** Enable = either version- or format-compaction flag. Each tick: parse required semver; if the MINIMAL connected QueryNode session version is below it, skip everything — upgraded data must never land where old nodes cannot read it. Token bucket: reset count when interval elapsed; each emitted view consumes one token up to maxCount; collections processed in meta order until tokens exhaust. Per collection: TTL fetch, triggerID, target resolution (V2 default; V3 when UseLoonFFI), TEXT-field downgrade refusal, then segment filter: healthy+flushed+not-compacting+not-importing+not-L0+not-snapshot-protected AND (versionEnabled ∧ version≠target ∨ formatEnabled ∧ already-V3 ∧ mixed column-group formats). Views are single-segment MixSegmentViews (rewrite via mix machinery), counted against the shared token bucket.
**Invariant:** The compatibility gate reads the MINIMUM session version across the fleet, not any node's — one stale QueryNode freezes migration entirely (safe-side). Rate limiting lives in policy state, valid only because Trigger runs on exactly one goroutine; moving it requires a mutex. Format-normalization applies ONLY to segments already on V3 (it rewrites column-group encodings, not the container version).
**Probe:** Direct-source pins: min-version gate :101–105; TEXT refusal comment :167–179; dual-flag filter :185–197; token loop :118–120/:201–213. Upstream suite `internal/datacoord/compaction_policy_storage_version_test.go` (1,213L) exercises these branches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "storageVersionUpgradePolicy targetVersion segmentColumnGroupFormatsAllEqual", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI rank-1: `...targetVersion Method internal/datacoord/compaction_policy_storage_version.go 63-69`.)

## Verdict
Adopt min-version gating + token-bucket + capability-refusal triad for any rolling storage-format migration. Adapt semver source to your service registry. Omit LoonFFI specifics. Caveat: cgo-blocked runner; direct source + upstream suite read at pin.
