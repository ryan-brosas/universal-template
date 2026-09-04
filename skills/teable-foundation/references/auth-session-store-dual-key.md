<!-- capsule-v2 -->
# Session store dual-key revocation — how does a custom express-session Store support user-wide logout over a dumb shared cache?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do you revoke every session of a user on password change when your cache (Redis) has no secondary index?

## Dual-key store (`SessionStoreService extends Store`)
**Path/Symbol:** `apps/nestjs-backend/src/features/auth/session/session-store.service.ts` : `setCache` (:27–42), `getCache` (:44–73), `clearByUserId` (:124–132).
**Signature:** `get(sid, callback)` / `set(sid, session, callback?)` / `destroy(sid, callback?)` / `touch(sid, session, callback?)` / `clearByUserId(userId): Promise<void>`.
**Data Shape:** Stored payload is `pick(session, ['passport','cookie'])` — only auth-relevant keys survive. Two cache families: `auth:session-store:{sid}` = session payload with TTL = configured session expiry; `auth:session-user:{userId}` = map `{sid → epochSecondsExpiry}` with the SAME TTL; plus transient tombstones `auth:session-expire:{sid}` (60s).

### Decisive source
```ts
this.ttl = second(this.authConfig.session.expiresIn);
this.userSessionExpire = this.ttl + 60 * 2;   // index must outlive its sessions
...
userSessions[sid] = nowSec + this.userSessionExpire;
for (const [key, value] of Object.entries(userSessions)) {
  if (value < nowSec) { delete userSessions[key]; }   // prune expired sids on write
}
await this.cacheService.set(`auth:session-user:${userId}`, userSessions, this.ttl);
await this.cacheService.set(`auth:session-store:${sid}`, session, this.ttl);
```
```ts
async clearByUserId(userId: string) {
  const userSessions = (await this.cacheService.get(`auth:session-user:${userId}`)) ?? {};
  for (const sid of Object.keys(userSessions)) {
    // Preventing competition
    await this.cacheService.set(`auth:session-expire:${sid}`, true, 60);
    await this.cacheService.del(`auth:session-store:${sid}`);
  }
  await this.cacheService.del(`auth:session-user:${userId}`);
}
```

**Flow:** GET checks three gates in order — tombstone present ⇒ expired; store entry missing ⇒ miss; sid absent from the user's index map ⇒ orphan, self-heal by deleting the store key; index expiry past ⇒ delete store + rewrite pruned index. SET writes the index first (pruning dead sids) then the store. TOUCH re-runs full get→set so a touch cannot resurrect a revoked session (it errors 'Session not found'). Credential-changing flows (`changePassword`, `resetPassword`, `addPassword`, `changeEmail` in local-auth.service.ts :379/:455/:478/:517) all call `clearByUserId`.
**Invariant:** The user-index expiry always exceeds the session TTL (+120s) so an alive session can never outlive its index; revocation sets a tombstone BEFORE deleting so a concurrent touch/recreate racing the revoke still observes death; reads self-heal orphans instead of trusting stale indexes.
**Probe:** `apps/nestjs-backend/src/features/auth/session/session-store.service.spec.ts` — pins index write shape (`{[sid]: now+userSessionExpire}`), expired-sid pruning on set, all four getCache gates, and clearByUserId's exact cache calls `set('auth:session-expire:session-id', true, 60)` → `del('auth:session-store:session-id')` → `del('auth:session-user:user-id')`.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "teable", label: "Class", name_pattern: "^(SessionStoreService)$" })
→ SessionStoreService @ apps/nestjs-backend/src/features/auth/session/session-store.service.ts lines 13-133 (executed live this pass)
```

## Verdict
Adopt the dual-key scheme, +margin index TTL, tombstone-before-delete, and orphan self-heal as a complete portable unit. Adapt key prefixes/TTL config to host. Omit express-session `Store` subclassing if the host framework has its own store interface — port the invariants, not the base class.
