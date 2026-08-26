<!-- capsule-v2 -->
# Auth MFA assurance ladder — when must a valid bearer token still be rejected for step-up verification?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How does a middleware enforce per-user login-MFA and route-level MFA requirements using Supabase assurance levels — and which lookups fail open vs closed?

## requireAuth + requireMfaIfEnrolled with a bootstrap-route carve-out
**Path/Symbol:** `backend/src/middleware/auth.ts:107` (`requireAuth`), `:31` (`enforceLoginMfaIfEnabled`), `:23` (`isLoginMfaBootstrapRoute`), `:149` (`requireMfaIfEnrolled`). Direct tests: integration suites assert 401/403 shapes (`src/__tests__/integration/user.routes.test.ts`, `workflowAddons.routes.test.ts`, etc.).
**Signature:** Express middleware; stashes `res.locals.{userId, userEmail(lowercased), token}`.
**Data Shape:** decision input `mfa.getAuthenticatorAssuranceLevel(token) -> {currentLevel, nextLevel}`; step-up needed iff `nextLevel === "aal2" && currentLevel !== "aal2"` → HTTP 403 `{code:"mfa_verification_required"}`.

### Decisive source
```ts
if (error.code === "42703") return true;   // undefined_column: migration not yet applied → FAIL OPEN
sendInternalError(res, error);             // other preference-read failures → 500, not silent allow
…
if (isLoginMfaBootstrapRoute(req)) return true;  // GET/POST /user(s)/profile skips the gate so the client can enroll
```

**Flow:** Bearer parse → admin.auth.getUser (401 on miss) → locals populated → best-effort profile-email sync (failure only devLogs; never blocks) → if profile.mfa_on_login: assurance check with bootstrap-route exemption → later routes layer `requireMfaIfEnrolled` for enrolled-user-only surfaces (assurance lookup failure here is FAIL CLOSED with 401 "Unable to verify authentication").
**Invariant:** The two gates differ deliberately: the login-preference READ failing due to a missing column fails OPEN (feature not deployed yet must not lock everyone out), but an assurance LOOKUP failure fails CLOSED (can't prove level ⇒ don't serve MFA-protected surface). Email normalization happens once at the middleware boundary (`toLowerCase()`), which is why every downstream share-comparison can trust lowercase.
**Probe:** `grep -c '42703' src/middleware/auth.ts` → 1; `grep -c 'mfa_verification_required' src/middleware/auth.ts` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "requireAuth requireMfaIfEnrolled assurance aal2", limit: 10 });
```

## Verdict
Adopt assurance-level gating + asymmetric fail-open/closed rules + single-boundary email normalization; adapt to your IdP's step-up API; omit Supabase MFA factor specifics.
