<!-- capsule-v2 -->
# Backup-code generation & single-use consumption — how do you mint recovery codes and consume exactly one under concurrency?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are backup codes stored (hashed) and how is a code burned exactly once even if two requests race?

## backup-codes-consume
**Path/Symbol:** `src/lib/two-factor/backup-codes.ts:generateBackupCodes/verifyBackupCode :7-31`; consumption in `src/app/api/2fa/verify/route.ts:79-104`.
**Signature:** `generateBackupCodes() -> { plaintext: string[10], hashed: string[10] }` (16 random bytes hex × 2 joined by `-`, bcrypt(10)); `verifyBackupCode(input, hashes) -> index | null`.
**Data Shape:** DB stores ONLY `codeHash` + `used` flag; plaintext shown once at generation.

### Decisive source
```ts
// verify route — the two-step consume that closes the race:
const matchIndex = await verifyBackupCode(body.backupCode, hashes);
if (matchIndex === null) { ...recordFailedAttempt... }
const consumed = await prisma.client.twoFactorBackupCode.updateMany({
  where: { id: unusedCodes[matchIndex].id, used: false },   // guard INSIDE the write
  data: { used: true },
});
if (consumed.count === 0) {          // another request won the race ⇒ treat as failure
  const { lockedUntil } = await recordFailedAttempt(userId);
  return badRequest({ code: 'two-factor-error-invalid-backup-code', ... });
}
await resetRateLimit(userId);
```

**Flow:** verify against UNUSED hashed codes only → conditional `updateMany ... where used:false` → count===0 means a concurrent login already consumed it, and is handled as an INVALID attempt (counted toward lockout), not success.
**Invariant:** never mark `used:true` with an unguarded update by id; the `used: false` predicate in the WHERE is the entire concurrency story. Case-normalize input (`toUpperCase()` on both sides at compare time) but store hashes of the normalized form.
**Probe:** `grep -n "describe('verifyBackupCode'" src/lib/two-factor/backup-codes.test.ts` → :36 pins matching; consumption pins: `grep -c "used: false" src/app/api/2fa/verify/route.ts` → 2.
**Probe:** `grep -n "BCRYPT_ROUNDS\|BACKUP_CODE_COUNT" src/lib/two-factor/backup-codes.ts` → :4-5.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "generateBackupCodes verifyBackupCode consumed", limit: 10 });
```

## Verdict
Adopt hash-at-rest + conditional-update consumption for any one-time token (recovery codes, magic links, webhook secrets); adapt code shape/length; omit the specific error codes.
