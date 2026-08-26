<!-- capsule-v2 -->
# Multi-strategy identity chain — how does one auth guard fall back across cookie session, PAT, JWT, and anonymous?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do you authenticate browser, API-token, and service traffic with one guard while keeping DB-fresh account state on every request?

## Strategy array + per-strategy validate ladders
**Path/Symbol:** `apps/nestjs-backend/src/features/auth/guard/auth.guard.ts` : `AuthGuard` (:18–72); `strategies/session.strategy.ts` : `validate` (:23–41); `strategies/access-token.strategy.ts` : `validate` (:30–58); `strategies/session.passport.ts` : `authenticate` (:23–54); `strategies/anonymous/anonymous.strategy.ts` (:15–18).
**Signature:** `AuthGuard extends PassportAuthGuard(['session', ACCESS_TOKEN_STRATEGY_NAME, JWT_TOKEN_STRATEGY_NAME, ANONYMOUS_STRATEGY_NAME])`; each strategy `validate(payload): Promise<IUserMe | ANONYMOUS_USER>`.
**Data Shape:** Every human strategy re-loads the user by id and rejects on `!user`, `deactivatedTime`, or (session/JWT) `isSystem`; PAT additionally sets cls `accessTokenId`; all set cls `user.{id,name,email,isAdmin}` and return `pickUserMe(user)`.

### Decisive source
```ts
async validate(context: ExecutionContext) {
  const result = (await super.canActivate(context)) as boolean;   // passport tries strategies in order
  const isAllowAnonymous = this.reflector.getAllAndOverride<boolean>(IS_ALLOW_ANONYMOUS, [...]);
  if (!isAllowAnonymous && isAnonymous(this.cls.get('user.id'))) { throw new UnauthorizedException(); }
  return result;
}
...
if (ensureLogin) {
  // The redirect completes the response; returning false stops the
  // pipeline. Nest still raises ForbiddenException for a false guard,
  // which the global exception filter drops once headers are sent.
  res.redirect(`/auth/login?redirect=${encodeURIComponent(req.url)}`);
  return false;
}
```
```ts
// PassportSessionStrategy.authenticate — stale session self-heal
_deserializeUser(user, req, function (err, user) {
  if (err) { return fail(err); }
  if (!user) { delete req.session[_key].user; fail('No user session found'); }   // NOT error()
  else { req[property] = user; success(user); }
});
```

**Flow:** Public endpoints skip everything. Otherwise passport attempts `session` (cookie → custom Store) then Bearer-PAT then Bearer-JWT then `anonymous` (sets the ANONYMOUS_USER sentinel so downstream CLS reads never see undefined). The first success wins; after it, an anonymous identity on a non-allow-anonymous endpoint is re-401'd. Auth failure with `@EnsureLogin` redirects browsers to `/auth/login?redirect=…` instead of JSON-401. The access-token extractor is a hand-rolled `fromExtractors([fromAuthHeaderAsBearerToken])` loop taking the first non-null token.
**Invariant:** Identity is NEVER trusted from the token alone — deactivated/system-user state is read from the DB inside every validate; a deserialize miss downgrades to `fail()` (try next strategy / 401) while deleting the poisoned session entry rather than throwing.
**Probe:** No dedicated spec for AuthGuard itself (coverage caveat). Deterministic probes executed this pass: source pins above byte-checked at HEAD; `local.strategy.spec.ts` exercises the same CustomHttpException vocabulary; grep asserts the exact strategy-name array order in auth.guard.ts:18–23.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "teable", label: "Class", name_pattern: "^(AuthGuard|OauthStoreService|ControllerAdapter)$" })
→ AuthGuard @ .../auth/guard/auth.guard.ts lines 18-72 (5 inbound deps); executed live this pass
```

## Verdict
Adopt: ordered multi-strategy chain ending in an explicit anonymous sentinel, DB-fresh validate in every strategy, ensure-login redirect-with-false semantics, and fail-not-error stale-session healing. Adapt strategy names/extractors. Omit the teable robot-user handling (covered by the jwt-internal-token capsule).
