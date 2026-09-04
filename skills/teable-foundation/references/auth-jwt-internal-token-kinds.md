<!-- capsule-v2 -->
# JWT internal token kinds — how do server-to-service calls carry a base-scoped robot identity without a real login?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How should internal automation/app traffic authenticate as a non-human principal scoped to one base?

## Internal-token discriminator (`JwtStrategy.validateInternalToken`)
**Path/Symbol:** `apps/nestjs-backend/src/features/auth/strategies/jwt.strategy.ts` : `validate` (:32–37), `validateInternalToken` (:39–77), `setAppIdFromToken` (:79–82).
**Signature:** `validate(req, payload: IJwtAuthInfo | IJwtAuthInternalInfo)` — discriminated by `'baseId' in payload`.
**Data Shape:** Internal payloads are `{baseId, type: JwtAuthInternalType.User|App|Automation, userId?, context?, allowSystemUser?}`; User kind resolves a REAL user; App/Automation map to the shared constants `APP_ROBOT_USER` / `AUTOMATION_ROBOT_USER` from `@teable/core`.

### Decisive source
```ts
private async validateInternalToken(payload: IJwtAuthInternalInfo, req: Request) {
  this.cls.set('tempAuthBaseId', payload.baseId);
  if (payload.type === JwtAuthInternalType.User) {
    if (!payload.userId) { throw new UnauthorizedException('User ID is required for User type tokens'); }
    const user = await this.userService.getUserById(payload.userId);
    if (!user) { throw new UnauthorizedException(); }
    ... // deactivatedTime / isSystem gates identical to user tokens
  }
  // Handle App and Automation type tokens - use robot users
  const user = payload.type === JwtAuthInternalType.App ? APP_ROBOT_USER : AUTOMATION_ROBOT_USER;
  this.cls.set('user', user);
  this.cls.set('tempAuthBaseId', payload.baseId);
  if (payload.type === JwtAuthInternalType.App) { await this.setAppIdFromToken(payload.baseId, req); }
  if (payload.type === JwtAuthInternalType.Automation) { this.cls.set('workflowContext', payload.context); }
  return user;
}

protected async setAppIdFromToken(_baseId: string, _req: Request) {
  // This method is overridden in enterprise edition to support app authentication
  // Community edition does not have app model, so this is a no-op
}
```

**Flow:** Bearer JWT → payload with `baseId` routes to the internal branch which FIRST pins `tempAuthBaseId` in CLS (this key later unlocks TemplatePermissions/owner fallback inside `PermissionService.getPermissionByBaseId`). User-kind behaves like a normal login. App/Automation kinds become robot users — no DB lookup exists for them — while Automation additionally parks its execution context under cls `workflowContext`. The permission plane treats `tempAuthBaseId`-scoped requests as template-preview identities rather than role-less outsiders.
**Invariant:** Robot identities never bypass the guard chain (they ride the same strategy order and anonymous re-check); base scoping travels in the token and lands in CLS before any permission resolution reads it.
**Probe:** No dedicated upstream spec (coverage caveat). Deterministic probe executed this pass: byte-check of :32–82 at HEAD plus grep confirming `'baseId' in payload` as the only discriminator between `validateUserToken` and `validateInternalToken`.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "teable", label: "Class", name_pattern: "^(JwtStrategy)$" })
→ teable.apps.nestjs-backend.src.features.auth.strategies.jwt.strategy → JwtStrategy lines 18-103 (executed live this pass)
```

## Verdict
Adopt: token-discriminated internal identity kinds, dedicated robot principals, CLS-scoped base binding ahead of authorization, and an overridable enterprise hook stubbed honestly in community code. Adapt constant names and CLS keys. Omit workflowContext semantics unless porting teable's own automation runner.
