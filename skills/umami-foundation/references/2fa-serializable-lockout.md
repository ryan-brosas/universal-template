<!-- capsule-v2 -->
# Serializable attempt-counter lockout — how do you rate-limit 2FA guesses without a race letting guess #6 through?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How is a fail counter incremented and a lockout set atomically under concurrent attempts?

## 2fa-serializable-lockout
**Path/Symbol:** `src/lib/two-factor/rate-limit.ts:recordFailedAttempt :19-53` (+ `checkRateLimit :8-17`, `resetRateLimit :55-57`).
**Signature:** `recordFailedAttempt(userId) -> { lockedUntil?: Date }`; `prisma.transaction(cb, { isolationLevel: Prisma.TransactionIsolationLevel.Serializable })`.
**Data Shape:** row `(userId, attempts, lockedUntil)`; MAX_ATTEMPTS=5, LOCKOUT_MINUTES=15, MAX_RETRIES=3.

### Decisive source
```ts
return await (prisma.transaction(
  async (tx: Prisma.TransactionClient): Promise<{ lockedUntil?: Date }> => {
    const record = await tx.twoFactorRateLimit.upsert({
      where: { userId },
      update: { attempts: { increment: 1 } },   // atomic INCREMENT, not read-modify-write
      create: { userId, attempts: 1 },
    });
    if (record.attempts >= MAX_ATTEMPTS) {
      const lockedUntil = new Date(Date.now() + LOCKOUT_MINUTES * 60 * 1000);
      await tx.twoFactorRateLimit.update({ where: { userId }, data: { lockedUntil } });
      return { lockedUntil };
    }
    return {};
  },
  { isolationLevel: Prisma.TransactionIsolationLevel.Serializable },
) as Promise<{ lockedUntil?: Date }>);
// catch (err): if (err.code === 'P2034') { retries++; continue; }   // serialization failure ⇒ retry
```

**Flow:** each failed verify → increment inside SERIALIZABLE tx; crossing the threshold sets lockout in the SAME transaction. Success path calls `resetRateLimit` (deleteMany) which clears both counter and lock.
**Invariant:** the serializable level + retry-on-P2034 loop is what closes the lost-update race (two concurrent 5th attempts must not both see 5 and only one lock). The cast-comment in-source documents WHY the `as Promise<...>` is needed (Prisma's batch/callback overload union) — keep it or your types lie.
**Probe:** no direct unit test ships for this file (coverage caveat: exercised via route tests); structural pins: `grep -c "Serializable" src/lib/two-factor/rate-limit.ts` → ≥1; `grep -n "P2034" src/lib/two-factor/rate-limit.ts` → :47.
**Probe:** `grep -n "MAX_ATTEMPTS\|LOCKOUT_MINUTES\|MAX_RETRIES" src/lib/two-factor/rate-limit.ts | head -3` → :5-7.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "checkRateLimit recordFailedAttempt lockedUntil", limit: 10 });
```

## Verdict
Adopt serializable increment-and-lock for security-sensitive counters; adapt thresholds/TTLs; for non-security counters prefer plain optimistic retry instead of paying serializable cost.
