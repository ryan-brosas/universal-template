<!-- capsule-v2 -->
# Sync-target version gate & migration ladder — when may a client sync, and what runs under the exclusive lock first?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How does an old client refuse a new target (and vice versa), and how are format upgrades made crash-safe?

## MigrationHandler
**Path/Symbol:** `packages/lib/services/synchronizer/MigrationHandler.ts` :70-81 (`checkCanSync`), :83-157 (`upgrade`); registry `:21-26 migrations[] = [null, migration1, migration2, migration3]`; consumer `packages/lib/Synchronizer.ts` :498-517.
**Signature:** `checkCanSync(remoteInfo?: SyncInfo): Promise<void>`; `upgrade(targetVersion = 0): Promise<void>`.
**Data Shape:** target version read from `info.json` (`version: 0` = brand-new target; legacy `.sync/version.txt` ⇒ version 1).

### Decisive source
```ts
if (remoteInfo.version > supportedSyncTargetVersion) throw new JoplinError('...Please upgrade your app.', 'outdatedClient');
else if (remoteInfo.version < supportedSyncTargetVersion) throw new JoplinError('...Please upgrade the sync target.', 'outdatedSyncTarget');
...
if (autoLockError) throw autoLockError;
await migration(this.api_, this.db_);
if (autoLockError) throw autoLockError;   // abort AFTER the step too, before info.json rewrite
```
Version bootstrap in Synchronizer.start:
```ts
let remoteInfo = await fetchSyncInfo(this.api());
if (!remoteInfo.version) { await this.migrationHandler().upgrade(Setting.value('syncVersion')); ... }
await this.migrationHandler().checkCanSync(remoteInfo);
if (appVersion !== 'unknown') checkIfCanSync(remoteInfo, appVersion);   // app floor from info.json
```

**Flow:** fetch info.json → version 0 ⇒ upgrade() to current → checkCanSync both directions → per-app floor `checkIfCanSync` throws `'MustUpgradeApp'` dispatched as MUST_UPGRADE_APP. upgrade(): pre-create `.lock/` + `.tmp/` dirs for v0/v1 (locks + remoteDate need them), acquire EXCLUSIVE lock with `timeoutMs: 30_000` + `clearExistingSyncLocksFromTheSameClient`, start auto-refresh capturing errors into `autoLockError`, run each migration step with the double abort-check, rewrite legacy `{version}` into info.json ONLY for versions 1 and 2 ("New migrations should set the sync target info directly"), finally stop refresh + release lock.
**Invariants:** (1) `'outdatedSyncTarget'` is caught upstream and flips `sync.upgradeState = SHOULD_DO` — it is a user-flow signal, not a crash (:572-574); (2) auto-lock errors abort the ladder BOTH before and after each step so a lost lease can never leave a half-upgraded target; (3) version writes are idempotent per step and only v1/v2 get the legacy rewrite; (4) fetchSyncInfo failsafe: missing info.json AND missing .sync/version.txt on a non-initial target ⇒ `'failSafe'` error (wipe protection) unless zero synced items.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/joplin && grep -cF "if (autoLockError) throw autoLockError;" packages/lib/services/synchronizer/MigrationHandler.ts && grep -cF "[1, 2].includes(newVersion)" packages/lib/services/synchronizer/MigrationHandler.ts && grep -cF "outdatedSyncTarget" packages/lib/Synchronizer.ts'` (anchored at repo root; expects 2 / 1 / ≥1). Direct test: `packages/lib/services/synchronizer/synchronizer_MigrationHandler.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "MigrationHandler checkCanSync upgrade outdatedClient outdatedSyncTarget migrations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: bidirectional version gates with distinct error codes, exclusive-locked migration ladder with double lease-abort checks, dir bootstrap before locking, initial-sync detection before wipe-failsafe. Adapt: your version registry shape. Omit: the specific v1→v3 data rewrites.
