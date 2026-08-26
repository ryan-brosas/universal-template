<!-- capsule-v2 -->
# Auto-lock dual-timer (setTimeout + alarms) — how does a MV3 service worker enforce inactivity lock across restarts?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** Why two timer mechanisms, and which handler may NOT reset the countdown?

## Threshold split at 30 seconds
**Path/Symbol:** `apps/browser-extension/src/entrypoints/background/AutolockTimeoutHandler.ts:11-79` (`SHORT_TIMEOUT_THRESHOLD = 30`, `setAutoLockTimer`), :86-122 (`initializeAutoLockAlarm`), :167-184 (`handlePopupHeartbeat`).
**Signature:** `async setAutoLockTimer(timeoutSeconds: number)`; alarm name `'vault-auto-lock'`; unlocked-state probe `storage.getItem('session:encryptionKey')`.
**Data Shape:** `< 30s` ⇒ in-page `setTimeout` (service worker stays alive that long; alarm API minimum is 30s in packed extensions). `>= 30s` ⇒ persistent `browser.alarms` surviving worker termination.

### Decisive source
```ts
if (timeoutSeconds < SHORT_TIMEOUT_THRESHOLD) {
  // Use setTimeout for short timeouts. Service worker won't terminate before the timer fires.
  shortTimeoutTimer = setTimeout(() => { shortTimeoutTimer = null; lockVaultDueToInactivity(); }, timeoutSeconds * 1000);
} else {
  // Alarms persist across service worker restarts.
  await browser.alarms.create(AUTO_LOCK_ALARM_NAME, { delayInMinutes: delayInMinutes });
}
```
```ts
// initializeAutoLockAlarm — long timeouts must NOT restart on every worker wake:
const existingAlarm = await browser.alarms.get(AUTO_LOCK_ALARM_NAME);
if (!existingAlarm) { await setAutoLockTimer(timeout); }
```

**Flow:** every mutating handler first clears BOTH timers, then checks `timeout === 0` (disabled) and the session key (already locked) before re-arming → lock action re-verifies the session key so a manual lock racing the timer is a no-op → popup sends heartbeats to extend while open.
**Invariants:** (1) Worker restarts must not EXTEND a long countdown: init re-arms only if no alarm exists — but a dead setTimeout after restart legitimately re-arms full-duration (documented "can't restore the exact remaining time", :105-109). (2) `timeout === 0` is honored in FOUR sites — including `handlePopupHeartbeat`, which returns WITHOUT extending when auto-lock is disabled (:172-174) — omitting this check would make an open popup immortalize the vault. (3) Locking is idempotent: no encryptionKey ⇒ return early. (4) Five `session:encryptionKey` probes gate every entry point.
**Probe:** `grep -c 'SHORT_TIMEOUT_THRESHOLD = 30' apps/browser-extension/src/entrypoints/background/AutolockTimeoutHandler.ts` → `1`; `grep -c 'session:encryptionKey' apps/browser-extension/src/entrypoints/background/AutolockTimeoutHandler.ts` → `5`; `grep -c 'timeout === 0' apps/browser-extension/src/entrypoints/background/AutolockTimeoutHandler.ts` → `4`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "handlePopupHeartbeat", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-mechanism split with restart-stable long alarms; adapt thresholds to your platform's timer minimums; omit WXT/browser namespace specifics. Source confirmed at pin `95903e92`.
