<!-- capsule-v2 -->
# JWT cookie session — how do you make a stateless NXSESSIONID cookie that stays revocable and re-issues itself on every request?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-security/.../JwtHelper.java`, `JwtSecurityFilter.java`); Codebase Memory `nexus-public`. **Question:** How does an HMAC JWT session cookie carry identity, survive secret rotation, support server-side logout, and refresh its expiry on each use?

## Verify-and-refresh cookie with DB-backed session-id revocation
**Path/Symbol:** `public/common/components/security/nexus-security/src/main/java/org/sonatype/nexus/security/JwtHelper.java:createToken` (:179–198), `createCookie` (:200–208), `on(JwtSecretChanged)` (:173–177), `doStart` (:100–109); `security/JwtSecurityFilter.java:createSubject` (:89–164).
**Signature:** `Cookie createJwtCookie(final Subject subject, final boolean secureRequest)`; `Cookie verifyAndRefreshJwtCookie(final String jwt, final boolean secureRequest)`; claims: `user`, `realm`, `userSessionId` (UUID per login); issuer `sonatype`; expiry `nexus.jwt.expiry:1800`.
**Data Shape:** cookie `NXSESSIONID`, HttpOnly always, Secure = `cookieSecure && secureRequest` (never sets Secure on plain-HTTP requests), path = context path, maxAge = token expiry.

### Decisive source
```java
private String createToken(final String user, final String realm, final String userSessionId) {
  Date issuedAt = new Date();
  JWTCreator.Builder jwtBuilder = JWT.create()
      .withIssuer(ISSUER)
      .withClaim(USER, user)
      .withClaim(USER_SESSION_ID, userSessionId)   // revocation anchor
      .withIssuedAt(issuedAt)
      .withExpiresAt(getExpiresAt(issuedAt));
  if (realm != null) { jwtBuilder.withClaim(REALM, realm); }
  return jwtBuilder.sign(verifier.getAlgorithm());
}

@Subscribe
public void on(final JwtSecretChanged event) {     // rotation: rebuild verifier live
  verifier = new JwtVerifier(loadSecret());
}
```
Filter-side verification ladder (`JwtSecurityFilter.createSubject`):
```java
try {
  decodedJwt = jwtHelper.verifyJwt(jwt);
} catch (JwtVerificationException e) {
  cookie.setValue(""); cookie.setMaxAge(0);        // expire the bad cookie
  WebUtils.toHttp(response).addCookie(cookie);
  return super.createSubject(request, response);   // anonymous fallback
}
if (!decodedJwt.getClaim(USER_SESSION_ID).isNull()) {
  if (jwtSessionRevocationService.isRevoked(userSessionId)) {
    log.warn("SECURITY: Attempt to use revoked JWT token detected...");
    recordRevokedTokenAudit(username, userSessionId, remoteAddr, remoteHost);
    /* expire cookie, fall back to anonymous */
  }
}
```

**Flow:** login mints token with fresh random `userSessionId`; each subsequent request verifies → checks the session id against the revocation service (logout writes it there) → builds a Shiro principal from claims; `verifyAndRefreshJwtCookie` re-mints a full-validity token from the SAME claims, so active sessions roll forward indefinitely while abandoned ones die at expiry. Secret changes broadcast `JwtSecretChanged` and every node swaps its verifier without restart. Bad/expired/revoked cookies are zeroed in the response rather than erroring.
**Invariant:** verification failures degrade to anonymous with cookie-expiry side effect (never 500). Revocation is keyed on the random session-id claim — the JWT itself is stateless but logout remains instant cluster-wide via the shared store. Replay of a revoked token is audited as a security event.
**Probe:** `security/nexus-security/src/test/java/org/sonatype/nexus/security/JwtSecurityFilterTest.java` — ten cases incl. `testCreateSubject_validJwtWithRevokedSession` (:196), `_revokedSessionWithoutUserClaim` (:236), `_revokedSessionWithAuditDisabled` (:268), `_validJwtWithNullUserSessionIdClaim` (:291).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "createJwtCookie verifyAndRefreshJwtCookie JwtSecretChanged isRevoked", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt claim set + refresh-on-verify + session-id revocation anchor + degrade-don't-error handling. Adapt the auth0-jwt library calls and Shiro subject construction to your stack. Omit the audit-recorder wiring if you lack an audit bus (but keep the replay warning).
