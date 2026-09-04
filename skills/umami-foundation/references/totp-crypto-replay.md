<!-- capsule-v2 -->
# TOTP secret encryption at rest + OTP replay ledger — how do you store 2FA secrets and stop code reuse within the validity window?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are TOTP secrets encrypted at rest and how is a 30-second code prevented from being used twice?

## totp-crypto-replay
**Path/Symbol:** `src/lib/two-factor/crypto.ts:encryptSecret/decryptSecret :29-49`; `src/lib/two-factor/replay-prevention.ts:markOtpUsed/isOtpReplayed :7-28`.
**Signature:** encrypt → `"${ct.hex}:${iv.hex}:${tag.hex}"` (AES-256-GCM, 12-byte IV, key from `TWO_FACTOR_ENCRYPTION_KEY` hex); replay ledger = upsert row `(userId, otp)` with `expiresAt = now+90s`.
**Data Shape:** separate dedicated key (NOT APP_SECRET) — `isTwoFactorConfigured()` validates `/^[0-9a-fA-F]{64}$/` without throwing.

### Decisive source
```ts
export async function markOtpUsed(userId: string, otp: string, tx?: TxClient): Promise<void> {
  const expiresAt = new Date(Date.now() + 90 * 1000);   // > one 30s window ± skew
  await client.twoFactorOtpUsed.upsert({
    where: { userId_otp: { userId, otp } }, update: { expiresAt }, create: { userId, otp, expiresAt },
  });
}
// isOtpReplayed: record found & unexpired ⇒ true; expired ⇒ DELETE then false.
```

**Flow:** verify route checks `isOtpReplayed` BEFORE `verifyTotp`, then `markOtpUsed` AFTER success — ordering matters: failed attempts don't poison the code, successful ones burn it for 90s.
**Invariant:** the 90s TTL must exceed the code window plus clock skew (30s step, otplib default ±1 window) or legit retries get locked out; lazy delete-on-read keeps the table tiny without a cron. GCM tag is stored alongside ciphertext — never reuse an IV with the same key.
**Probe:** `grep -n "toHaveLength(3)" src/lib/two-factor/crypto.test.ts` → :15 asserts the 3-part envelope; round-trip tests :5-53; `grep -n "90 \* 1000" src/lib/two-factor/replay-prevention.ts` → :10.
**Probe:** `grep -n "split(':')" src/lib/two-factor/crypto.test.ts | head -1` → :15 region.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "markOtpUsed isOtpReplayed encryptSecret", limit: 10 });
```

## Verdict
Adopt colon-framed GCM envelope + DB-backed replay ledger for any OTP scheme; adapt TTL to your step size (≈3× step); omit QR/URI helpers if enrollment UX differs.
