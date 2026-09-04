<!-- capsule-v2 -->
# Optimizer disk-fit preflight — how do you gate background compaction on disk space without deadlocking a full disk?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** Before an optimization builds its output segment, how is "is there room on disk" decided — and why must that decision ignore the storage quota and tolerate unmeasurable filesystems?

## 2× occupied, physical free space only, fail-open on unknown
**Path/Symbol:** `lib/shard/src/optimize.rs`: `check_segments_size` (:658-743), called from `execute_optimization` at :792 — after input validation (race-lost inputs already returned a no-op) and before `on_successful_start`. Verdict source: `lib/shard/src/quota/manager/measure.rs`: `QuotaManager::fits_on_disk` (:62-75), `DiskFit` (:18-26), `available_bytes` (:43-46), per-path `disk_usage` cache (:105-121).
**Signature:** `fn check_segments_size(optimizer_name: &str, optimizing_segments: &[LockedSegment], temp_path: &Path) -> OperationResult<()>`; `pub fn fits_on_disk(&self, path: &Path, required_bytes: u64) -> DiskFit`.
**Data Shape:** input = the ORIGINAL segments being optimized (a `LockedSegment::Proxy` input is a service error — proxies are not sized); `space_occupied` is the sum of `dir_disk_size` over their data paths, collapsing to `None` on ANY read error; `space_needed = 2 × occupied` (old bytes still live while the new segment is built); verdict is `DiskFit::{Fits{available}, TooLarge{available, required}, Unknown}`.

### Decisive source
```rust
// measure.rs :57-61 — the quota-blindness is load-bearing
/// Blind to the configured limits by design: an optimization is what *frees*
/// a disk the quota has declared full, so only not fitting may stop one.
pub fn fits_on_disk(&self, path: &Path, required_bytes: u64) -> DiskFit {
    let Some(available) = self.available_bytes(path, required_bytes) else {
        return DiskFit::Unknown;
    };
    if available < required_bytes { DiskFit::TooLarge { available, required: required_bytes } }
    else { DiskFit::Fits { available } }
}
// DiskFit :23-25 — Unknown is a proceed, not a refusal
/// Free space could not be measured. Callers proceed: refusing work over a
/// stat we cannot take would stall any filesystem that does not report one.
Unknown,
// check_segments_size :695 — 2× occupied (source bytes stay live until post-flush retirement)
let space_needed = space_occupied.map(|x| 2 * x);
// :708-713 — estimation failure also proceeds
let Some(space_needed) = space_needed else {
    log::warn!("Could not estimate the space needed by `{optimizer_name}`; will try optimizing anyway");
    return Ok(());
};
// :726-735 — only TooLarge refuses, carrying both numbers for the error message
DiskFit::TooLarge { available, required } => Err(OperationError::service_error(format!(
    "Not enough space available for optimization, needed: {}, available: {}", ...))),
```

**Flow:** sum on-disk size of every original input (any stat error ⇒ give up estimating) → compute 2× → create temp_path if missing → ask the quota manager's free-space meter (served from the same per-path cache as quota checks, but with `watch_below = required`: a cached reading below the requirement is never reused, so a nearly-full disk is re-measured call by call) → Fits ⇒ proceed; TooLarge ⇒ service error with both byte counts; Unknown ⇒ warn + proceed.
**Invariant:** (1) the gate measures PHYSICAL free space, never the configured quota — gating optimization on the quota would remove the very mechanism that frees a quota-full disk; (2) both failure-to-measure paths (size estimation error, unmeasurable free space) are FAIL-OPEN — refusing work over an unreadable stat would stall any filesystem that does not report one; (3) the requirement is 2× occupied because source bytes stay live until the swap retires them post-flush.
**Probe:** `lib/shard/src/quota/manager/measure.rs::fits_on_disk_answers_from_free_space_not_the_quota` (:130-161) pins the quota-blindness directly: with the strictest possible quota (`max_disk_usage_percent: Some(1)`), a 0-byte need still returns `Fits`, and a `u64::MAX` need returns `TooLarge` carrying `required == u64::MAX` and the real `available`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "check_segments_size fits_on_disk DiskFit TooLarge available_bytes watch_below", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way verdict (Fits / TooLarge-with-both-numbers / Unknown-proceed), the 2× occupied sizing, the fail-open policy on any measurement failure, and the watch-below freshness rule (never trust a cached reading tighter than your requirement). Adapt the per-path statvfs cache to your host's fs API. Omit the quota-manager integration itself — the contract is just "give me physical free space on this path".
