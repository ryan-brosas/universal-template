<!-- capsule-v2 -->
# Mobile unlock method ladder — in what order do biometric and PIN unlock attempt, and when must the user be redirected?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What is the fallback chain when FaceID fails or is cancelled, and what distinguishes "retry here" from "send to unlock screen"?

## Biometric→PIN→manual ladder
**Path/Symbol:** `apps/mobile-app/utils/VaultUnlockHelper.ts:24-72` (`attemptAutomaticUnlock`), :78-104 (`attemptPinUnlock`), :117-131 (`authenticateForAction`).
**Signature:** `static async attemptAutomaticUnlock(params: { enabledAuthMethods: AuthMethod[]; unlockVault: () => Promise<boolean> }): Promise<UnlockResult>` where `UnlockResult = { success, error?, redirectToUnlock? }`.
**Data Shape:** Methods: `'faceid' | 'password'`; PIN availability probed via native `NativeVaultManager.isPinEnabled()`; every failure path returns `redirectToUnlock: true` (4 sites).

### Decisive source
```ts
if (isFaceIDEnabled) {
  try {
    const isUnlocked = await unlockVault();
    if (isUnlocked) { return { success: true }; }
    // Biometric failed - fall through to PIN fallback below
  } catch (error) {
    // Biometric error - fall through to PIN fallback below
  }
  if (isPinEnabled) { return this.attemptPinUnlock(); }
  return { success: false, error: 'Biometric unlock failed', redirectToUnlock: true };
}
```
```ts
// PIN cancel vs real failure discrimination:
if (!errorMessage.includes('cancelled') && !errorMessage.includes('canceled')) {
  console.error('PIN unlock error:', error);
}
```

**Flow:** faceid-enabled ⇒ try biometric; success returns immediately; failure/cancellation falls THROUGH to PIN when enabled ⇒ native `showPinUnlock()` then re-probe `isVaultUnlocked()` (native side owns retries/lockout) ⇒ no PIN ⇒ redirect. No biometric ⇒ direct PIN path. Neither ⇒ redirect.
**Invariants:** (1) Cancellation of biometric is a FALLBACK trigger, not an abort — users cancelling FaceID land on PIN silently. (2) The helper never verifies PIN itself; it delegates to native and confirms via a second `isVaultUnlocked()` probe. (3) User-cancellation noise is suppressed from logs by matching BOTH British/American spellings ('cancelled'/'canceled'). (4) `authenticateForAction` adds a grace parameter (`recentUnlockGraceSeconds`) so step-up prompts can be skipped within a fresh-unlock window — returned boolean only, never throws.
**Probe:** `grep -c "includes('faceid')" apps/mobile-app/utils/VaultUnlockHelper.ts` → `2`; `grep -c 'redirectToUnlock: true' apps/mobile-app/utils/VaultUnlockHelper.ts` → `4`; `grep -c "includes('cancelled') && !errorMessage.includes('canceled')" apps/mobile-app/utils/VaultUnlockHelper.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "attemptAutomaticUnlock", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the biometric→PIN→redirect ladder with native-delegated verification; adapt method names/native bridge; omit React Native specifics. Source confirmed at pin `95903e92`.
