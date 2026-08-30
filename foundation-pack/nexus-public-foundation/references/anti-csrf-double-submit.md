<!-- capsule-v2 -->
# Anti-CSRF double-submit — when is a request CSRF-checked, and which requests escape the token requirement?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-security/.../authc/AntiCsrfHelper.java`, `AntiCsrfFilter.java`); Codebase Memory `nexus-public`. **Question:** How does a cookie-to-header CSRF check avoid blocking API clients and CLI tools while still stopping forged browser posts?

## Session-gated double-submit with Sec-Fetch-Site pre-filter
**Path/Symbol:** `public/common/components/security/nexus-security/src/main/java/org/sonatype/nexus/security/authc/AntiCsrfHelper.java:isAccessAllowed` (:76–94), `isCrossSiteRequest` (:113–127), `requireValidToken` (:102–110), `isAntiCsrfTokenValid` (:168–172).
**Signature:** `boolean isAccessAllowed(final HttpServletRequest httpRequest)`; `void requireValidToken(final HttpServletRequest httpRequest, @Nullable final String token)` (throws Shiro `UnauthorizedException`); token name `NX-ANTI-CSRF-TOKEN` used as BOTH cookie and header.
**Data Shape:** safe methods = GET/HEAD; multipart POSTs defer validation to the upload path (`requireValidToken` after field extraction); non-session-authenticated requests are exempt.

### Decisive source
```java
public boolean isAccessAllowed(final HttpServletRequest httpRequest) {
  if (!enabled) return true;
  boolean safeHttpMethod = isSafeHttpMethod(httpRequest);
  if (!safeHttpMethod && isCrossSiteRequest(httpRequest)) {   // Sec-Fetch-Site metadata
    log.debug("Blocking cross-site request header Sec-Fetch-Site:{}",
        httpRequest.getHeader(HttpHeaders.SEC_FETCH_SITE));
    return false;
  }
  return safeHttpMethod
      || isMultiPartFormDataPost(httpRequest)
      || !isSessionAuthentication()                            // API-key/basic clients exempt
      || isExemptRequest(httpRequest)                          // CsrfExemption contributors
      || isAntiCsrfTokenValid(httpRequest,
            Optional.ofNullable(httpRequest.getHeader(ANTI_CSRF_TOKEN_NAME)));
}

private static boolean isAntiCsrfTokenValid(final HttpServletRequest request, Optional<String> token) {
  Optional<String> cookie = getAntiCsrfTokenCookie(request);
  return token.isPresent() && token.equals(cookie);            // exact equality vs cookie
}
```

**Flow:** unsafe method + `Sec-Fetch-Site` header present and not `same-origin`/`none` ⇒ hard block regardless of tokens. Otherwise allow if: safe method, multipart post (validated later at the handler), no session auth (non-browser client), path contributed as exempt, or header token exactly equals the cookie value. Filter maps denial to 401 with a plain-text token-mismatch message.
**Invariant:** the check applies ONLY to session-cookie authentication — basic/API-key requests have no ambient credential to forge, so they bypass entirely. The Sec-Fetch-Site pre-filter blocks cross-site browser traffic BEFORE token comparison, closing the gap where a forged page omits the header. Multipart forms can't carry custom headers, so their token rides as a form field validated downstream.
**Probe:** `security/nexus-security/src/test/java/org/sonatype/nexus/security/authc/AntiCsrfHelperTest.java` — 18 cases incl. `testIsAccessAllowed_NotBrowser` (:186), `_PowerShell` (:199), `_MissingCsrfCookie_ExemptTelemetryPath` (:285), `testIsCrossSite` matrix (:322).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "AntiCsrfHelper NX-ANTI-CSRF-TOKEN Sec-Fetch-Site requireValidToken", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exemption ladder ordering (metadata-block → safe-method → multipart-defer → non-session → explicit-exempt → double-submit compare). Adapt token name, header transport, and exemption contribution to your framework. Omit the DirectJS-specific multipart comment context.
