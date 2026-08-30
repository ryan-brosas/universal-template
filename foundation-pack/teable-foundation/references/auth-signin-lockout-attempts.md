<!-- capsule-v2 -->
# Sign-in lockout ladder — how do you throttle brute force without letting transient errors lock out legitimate users?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Where do the attempt counter, the lockout flag, and the error-masking boundaries live in a login validate?

## Config-gated lockout (`LocalStrategy.validate` catch ladder)
**Path/Symbol:** `apps/nestjs-backend/src/features/auth/strategies/local.strategy.ts` : `validate` (:29–110); service pre-gate `local-auth.service.ts` : `validateUserByEmailWithTurnstile` (:110–121), `validateTurnstileIfEnabled` (:187–241).
**Signature:** `validate(req, email, password): Promise<IUserMe>` with passport-local options `{usernameField:'email', passwordField:'password', passReqToCallback:true}`.
**Data Shape:** Cache keys `signin:attempts:{email}` (counter, 30s window) and `signin:lockout:{email}` (boolean, N minutes); config knobs `authConfig.signin.{maxLoginAttempts, accountLockoutMinutes}` — BOTH must be truthy or the whole ladder is bypassed.

### Decisive source
```ts
const { maxLoginAttempts, accountLockoutMinutes } = this.authConfig.signin;
const hasLockout = maxLoginAttempts && accountLockoutMinutes;
if (!hasLockout) { throw new CustomHttpException('Email or password is incorrect', INVALID_CREDENTIALS, ...); }
if (isLockout) { throw lockError; }                       // already locked ⇒ 429 immediately
// Use atomic increment to prevent race conditions
const attempts = await this.cacheService.incr(`signin:attempts:${email}`, 30);
if (attempts >= maxLoginAttempts) {
  await this.cacheService.set(`signin:lockout:${email}`, true, accountLockoutMinutes);
  await this.cacheService.expire(`signin:attempts:${email}`, 1);   // retire counter; lockout now owns the state
  throw lockError;
}
throw new CustomHttpException('Email or password is incorrect', INVALID_CREDENTIALS, { attempts, ... });
```

**Flow:** Turnstile pre-gate runs BEFORE credential checks when enabled (missing token ⇒ BadRequest; failure reason mapped to a user-facing message distinguishing definitive `turnstile_failed` from transient `api_error`/`internal_error`/`max_retries_exceeded`). ANY throw from validation enters the catch ladder: no config ⇒ plain invalid-credentials; locked ⇒ 429 with minutes; else atomic INCR and threshold flip. Success path refreshes `lastSignTime` and returns pickUserMe.
**Invariant:** The generic `Email or password is incorrect` masks every non-lockout cause (unregistered / password-not-set / system-user are distinguishable only BEFORE the catch, as distinct VALIDATION_ERRORs that still consume an attempt — honest caveat: even turnstile rejections consume attempts because they throw inside the same try). Counter increments are atomic; lockout replaces the counter rather than racing it.
**Probe:** `apps/nestjs-backend/src/features/auth/strategies/local.strategy.spec.ts` — five cases pin: disabled lockout ⇒ generic error; pre-locked ⇒ exact 429 message with minutes; attempt INCR called with `(key, 30)`; threshold reached ⇒ `set(lockout, true, minutes)` + `expire(attempts, 1)`; first failure carries `attempts` count.

## Get live surrounding code
**Retrieve:**
```
mcp__codebase-memory__search_graph({ project: "teable", label: "Class", name_pattern: "^(LocalStrategy|SessionStrategy|AccessTokenStrategy)$" })
→ strategy family roster w/ line ranges incl. LocalStrategy 15-111 (executed live this pass)
```

## Verdict
Adopt: dual-knob gating, atomic-INCR sliding window, threshold→lockout-flag handoff, and single generic error at the boundary. Adapt cache backend and key names. Omit turnstile specifics unless porting CAPTCHA; keep its placement lesson (pre-credential external gates share the attempt budget).
