<!-- capsule-v2 -->
# Dormant lock kernel — what ships but never runs, and how do you port that honestly?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** Are the file-based sync locks live in this build, and what must a porter know before enabling them?

## The enabled flag
**Path/Symbol:** `packages/lib/services/synchronizer/LockHandler.ts` :152 (`private enabled_ = false`) + 7 short-circuits; consumer `packages/lib/Synchronizer.ts` :154-158 (construction), :356 (only reader of `.enabled`).
**Signature:** `public set enabled(v: boolean)` — exists, and NOTHING in production assigns it.
**Data Shape:** boolean instance field defaulting `false`; every mutating method opens with `if (!this.enabled) return <null-ish>`.

### Decisive source
```ts
public async locks(lockType: LockType = null): Promise<Lock[]> {
    if (!this.enabled) return [];          // reads: no locks exist
    if (this.enabled) throw new Error('Lock handler is enabled');   // ← dead arm
    ...
}
// Synchronizer.lockHandler():  new LockHandler(this.api())   ← no options, enabled stays false
```
The 7 guards (locks :205, saveLock :230, acquireExclusiveLock :290, startAutoLockRefresh :381, stopAutoLockRefresh :442, acquireLock :459, releaseLock :478) each pair a benign disabled-return with an UNREACHABLE throw on the opposite polarity. `acquireSyncLock` has no guard at all — it is only reachable through the guarded `acquireLock`.

**Flow:** Synchronizer.start calls acquireLock(Sync) → nullLock sentinel returned → startAutoLockRefresh returns `''` without starting any timer → lockErrorStatus_ skips the syncLockGone check behind `if (this.lockHandler().enabled)` (:356). Sync proceeds entirely unlocked.
**Invariants for a porter:** (1) treat the whole kernel as dormant scaffolding at this pin — multi-client mutual exclusion is NOT enforced by joplin clients today against plain targets; (2) if you enable it, you must also create the `locks/` + `temp/` dirs first (MigrationHandler.upgrade does exactly this for v0/v1 targets because remoteDate() needs temp files); (3) keep the null-object return contract — callers expect a `Lock` back even when disabled; (4) the dead `if (this.enabled) throw` arms are anti-pattern noise, not semantics — do not "fix" them into the port.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/joplin && grep -cF "if (!this.enabled)" packages/lib/services/synchronizer/LockHandler.ts && grep -c "enabled_ = false" packages/lib/services/synchronizer/LockHandler.ts && grep -c "\.enabled = true" packages/lib/Synchronizer.ts'` (anchored at repo root; expects 7 / 1 / 0).
**Coverage caveat:** suite stub only (`synchronizer_LockHandler.test.ts`: one always-true test; real cases commented).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "LockHandler enabled nullLock lockErrorStatus_", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the dormancy FACT (porters assume locks are active — they are not), the null-Lock contract, dir-bootstrap-before-enable ordering from MigrationHandler. Adapt: your own enable switch. Omit: the unreachable throw arms.
