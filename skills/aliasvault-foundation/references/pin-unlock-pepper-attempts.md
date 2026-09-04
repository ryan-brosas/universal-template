<!-- capsule-v2 -->
# PIN unlock with extension pepper + burn-after-4 — how is a low-entropy PIN made safe for protecting the vault key?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What protects a 6-8 digit PIN offline, and what exactly happens on the fourth wrong attempt?

## Composite salt + attempt ledger
**Path/Symbol:** `apps/browser-extension/src/utils/PinUnlockService.ts:157-203` (`setupPin`), :212-273 (`unlockWithPin`), :318-344 (pepper assembly), :362-387 (`derivePinKey`).
**Signature:** `setupPin(pin: string, vaultEncryptionKey: string): Promise<void>`; `unlockWithPin(pin: string): Promise<string>`; `MAX_PIN_ATTEMPTS = 4`.
**Data Shape:** Five storage keys (`local:aliasvault_pin_{enabled,encrypted_key,salt,length,failed_attempts}`); stored blob = `IV(12B) || AES-256-GCM(vaultKey)`; Argon2id params mem 65536 KiB / t 3 / p 1 / len 32; salt = `randomSalt(16B) || SHA-256(browser.runtime.id)`.

### Decisive source
```ts
// Combine: random_salt || extension_id_pepper
const combinedSalt = new Uint8Array(randomSalt.length + pepper.length);
combinedSalt.set(randomSalt, 0);
combinedSalt.set(pepper, randomSalt.length);
```
```ts
/* Increment failed attempts */
const newAttempts = currentAttempts + 1;
await storage.setItem(PIN_FAILED_ATTEMPTS_KEY, newAttempts);
if (newAttempts >= MAX_PIN_ATTEMPTS) {
  await removeAndDisablePin();   // deletes ALL five keys
  throw new PinLockedError();
}
throw new IncorrectPinError(MAX_PIN_ATTEMPTS - newAttempts);
```

**Flow:** setup validates `/^\d{6,8}$/` → derive pinKey from PIN+composite salt → encrypt vault key → persist all five keys atomically via Promise.all → unlock re-derives and decrypts; success resets the counter to 0; ANY failure path (bad format handled earlier; decrypt error) increments the counter BEFORE deciding lockout.
**Invariants:** (1) The pepper is device-bound and NOT in chrome.storage — copying the storage dir alone doesn't yield a brute-forceable blob. (2) Memory-hard 64 MiB Argon2id compensates for ~10^6..10^8 PIN space. (3) Burn-after-4 DELETES the encrypted key entirely — there is no reset-without-password; offline brute force has a hard 3-attempt horizon per stored blob. (4) Counter increments even on storage/decrypt anomalies (catch-all), so tampering with the counter can't extend attempts beyond deleting PIN data itself.
**Probe:** `grep -c 'MAX_PIN_ATTEMPTS = 4' apps/browser-extension/src/utils/PinUnlockService.ts` → `1`; `grep -c 'combinedSalt.set(pepper, randomSalt.length)' apps/browser-extension/src/utils/PinUnlockService.ts` → `1`; `grep -c 'mem: 65536' apps/browser-extension/src/utils/PinUnlockService.ts` → `1`; `grep -c 'await removeAndDisablePin();' apps/browser-extension/src/utils/PinUnlockService.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "unlockWithPin", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pepper-composited KDF salt + delete-on-exhaust attempt ledger; adapt pepper source per platform (mobile uses native keystore paths); omit wxt storage specifics. Source confirmed at pin `95903e92`.
