<!-- capsule-v2 -->
# Remote clock offset probe — how do you learn a storage target's clock skew when neither the device clock nor the target clock is trustworthy?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How is "remote now" actually measured, cached, and degraded — behind the `remoteDate()` primitive that lease math depends on?

## Midpoint temp-file estimator + TTL'd mutex-guarded cache + fail-soft fallback
**Path/Symbol:** `packages/lib/file-api.ts:222-244` (`fetchRemoteDateOffset_`), :248-275 (`remoteDate`); sole consumer family: LockHandler (`currentDate()` → lock TTL math, see remote-clock-discipline capsule).
**Signature:** `private async fetchRemoteDateOffset_(): Promise<number>`; `public async remoteDate(): Promise<Date>`.
**Data Shape:** state per FileApi instance: `remoteDateOffset_` (ms), `remoteDateNextCheckTime_` (epoch ms TTL deadline), `remoteDateMutex_`.

### Decisive source
```ts
const tempFile = `${this.tempDirName()}/timeCheck${Math.round(Math.random() * 1000000)}.txt`;
const startTime = Date.now();
await this.put(tempFile, 'timeCheck');
const loopStartTime = Date.now();
let stat = null;
while (Date.now() - loopStartTime < 5000) {          // stat may lag the put; poll ≤5s
    stat = await this.stat(tempFile);
    if (stat) break;
    await time.msleep(200);
}
if (!stat) throw new Error('Timed out trying to get sync target clock time');
void this.delete(tempFile);                           // fire-and-forget cleanup
const endTime = Date.now();
const expectedTime = Math.round((endTime + startTime) / 2);
return stat.updated_time - expectedTime;              // midpoint cancels one-way latency
```
```ts
if (shouldSyncTime()) {
    const release = await this.remoteDateMutex_.acquire();
    try {
        if (shouldSyncTime()) {                       // double-check AFTER acquiring
            this.remoteDateOffset_ = await this.fetchRemoteDateOffset_();
            // The sync target clock should rarely change but the device one might,
            // so we need to refresh relatively frequently.
            this.remoteDateNextCheckTime_ = Date.now() + 10 * 60 * 1000;
        }
    } catch (error) {
        logger.warn('Could not retrieve remote date - defaulting to device date:', error);
        this.remoteDateOffset_ = 0;                   // fail-soft: device clock
        this.remoteDateNextCheckTime_ = Date.now() + 60 * 1000;  // retry sooner
    } finally { release(); }
}
return new Date(Date.now() + this.remoteDateOffset_);
```

**Flow:** first lease decision of a session triggers one probe round-trip: write a uniquely-named file into the TARGET's temp dir, read its mtime back (polling because some targets make stats eventually-consistent), delete it without awaiting, and estimate skew as `target-mtime − midpoint(local start,end)`; the offset is then cached for 10 minutes so subsequent `remoteDate()` calls are pure arithmetic. A concurrent caller blocked on the mutex re-checks staleness after acquiring (double-checked locking) so N waiters cause at most ONE refresh. Any probe failure degrades gracefully: offset 0 (device clock assumed correct) with a shortened 60s retry horizon.
**Invariants:** (1) the probe needs `tempDirName()` to have been set for the current sync run (it throws 'Temp dir not set!' otherwise) — skew measurement shares the temp-dir discipline with lock/temp traffic; (2) offset estimation must use the MIDPOINT of local times around the write, not local-now, or asymmetric latency masquerades as clock skew; (3) failure never fails the sync: leases fall back to the device clock with a warning rather than aborting (correctness risk accepted over availability loss); (4) the TTL asymmetry (10 min success / 60 s failure horizon) exists because DEVICE clocks drift more often than target clocks.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/joplin && grep -cF "stat.updated_time - expectedTime;" packages/lib/file-api.ts && grep -cF "Date.now() + 10 * 60 * 1000;" packages/lib/file-api.ts && grep -cF "Could not retrieve remote date - defaulting to device date:" packages/lib/file-api.ts && grep -cF "Timed out trying to get sync target clock time" packages/lib/file-api.ts'` (anchored at repo root; expects 1 / 1 / 1 / 1). Coverage caveat: no direct unit test covers fetchRemoteDateOffset_/remoteDate at this pin (grep across packages/lib *.test.ts finds none) — source-pinned only.
**Companion capsule:** remote-clock-discipline owns WHY remote time decides liveness; this owns HOW remote time is produced.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "fetchRemoteDateOffset remoteDateOffset remoteDateNextCheckTime remoteDateMutex timeCheck", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: midpoint probe estimator, mutex with post-acquire double-check, TTL cache with shorter failure horizon, fail-soft zero-offset degradation. Adapt: TTLs to your drift tolerance. Omit: nothing portable here except joplin's logger wiring.
