<!-- capsule-v2 -->
# Client Authorization & SEP-2352 Issuer Isolation

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How does an MCP client isolate OAuth credentials per authorization server (SEP-2352) and prevent token cross-posting?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/auth.ts`: `auth` (:1014), `discardIfIssuerMismatch` (:128-145), `adaptOAuthProvider` (:210-221), `determineScope` (:1043-1072); refresh persistence boundary (:1326-1373, see refresh-persistence-boundary.md).
**Signature:** `discardIfIssuerMismatch(credential: StoredCredential, expectedIssuer: string): StoredCredential | undefined`
**Data Shape:** `StoredCredential` carries `{ token: string, issuer: string, scope?: string, expiresAt?: number }`.

### Decisive source
```ts
// SEP-2352: Every stored credential carries an issuer stamp.
// Mismatched stamps read back as undefined, forcing clean re-authentication.
export function discardIfIssuerMismatch(credential: StoredCredential | undefined, expectedIssuer: string): StoredCredential | undefined {
  if (!credential) return undefined;
  if (!credential.issuer) {
    console.warn("SEP-2352 isolation inactive: unstamped credential back-stamped on first use");
    credential.issuer = expectedIssuer;
    return credential;
  }
  if (credential.issuer !== expectedIssuer) {
    return undefined; // Fail-closed: do not return tokens belonging to another AS
  }
  return credential;
}
```

**Flow:**
1. Stored tokens and client registrations carry an `issuer` stamp written on every save.
2. Reads verify the stamp matches the expected AS URL; mismatches return `undefined` (fail-closed).
3. On 401 Unauthorized, the transport triggers `onUnauthorized()` once to refresh/re-auth before failing.
4. Scope widening on 403 bypasses refresh grants (`forceReauthorization`) and directs the user to the authorization endpoint.
5. (New at pin `3924de9`) Refresh-branch persistence sits OUTSIDE the refresh try/catch: `saveTokens` failures after a successful refresh PROPAGATE — silently dropping rotated tokens would leave already-invalid credentials in storage (refresh-persistence-boundary.md). Credential invalidation on invalid_client/invalid_grant now warns via `warnCredentialInvalidation` (:994-1006), JSON-stringifying AS-supplied values so control characters cannot forge log lines.

**Invariant:**
- Tokens stamped with Issuer A are never sent to Issuer B's token endpoint.
- If discovery resolves a different AS during a redirect callback, in-flight authorization codes fail closed immediately.
- Scope unions are computed mechanically without semantic deduplication.

**Probe:** `packages/client/test/client/auth.test.ts` — :4978 `discardIfIssuerMismatch: returns undefined only on a different stamp; warns on unstamped` (stamped→stamped, cross-stamp→undefined, unstamped→as-is, undefined-in→undefined-out); refresh persistence propagation :3080.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "discardIfIssuerMismatch adaptOAuthProvider auth determineScope", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt SEP-2352 issuer-stamped isolation and fail-closed callback gates; adapt OAuth provider interfaces to the host token store.
