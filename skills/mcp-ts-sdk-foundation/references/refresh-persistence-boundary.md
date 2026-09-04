<!-- capsule-v2 -->
# Refresh persistence boundary — why saveTokens failures after a successful refresh must propagate instead of falling through?

**Source:** typescript-sdk MIT `main@3924de9` (commit 3924de99 #2053); Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Where is the exact try/catch boundary around OAuth token refresh, and what happens when persisting freshly minted tokens fails?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/auth.ts`: `authInternal` refresh branch (:1326-1373) — `let newTokens` hoisted OUT of the try (:1329), assignment inside (:1332), persistence AFTER the catch (:1368-1371); credential-invalidation warning helper `warnCredentialInvalidation` (:994-1006) called from `auth` (:1021 InvalidClient/UnauthorizedClient, :1029 InvalidGrant).
**Signature:** `async function authInternal(provider, options, { issuer, metadata, clientInformation }, infoCtx): Promise<AuthResult>`; `function warnCredentialInvalidation(provider: OAuthClientProvider, error: OAuthError, invalidated: string): void`.
**Data Shape:** `newTokens: OAuthTokens | undefined` — undefined means nothing was minted (refresh threw); non-undefined tokens are persisted with `{ ...newTokens, issuer }` so every saved value carries the SEP-2352 stamp.

### Decisive source
```ts
// auth.ts :1346-1373 — persistence moved OUTSIDE the refresh try/catch
        // Persist any newly minted tokens. Persistence failures must always
        // propagate: the authorization server may have rotated the refresh
        // token, so silently dropping the new tokens would leave the client
        // with credentials that are already invalid server-side.
        if (newTokens) {
            await provider.saveTokens({ ...newTokens, issuer }, infoCtx);
            return 'AUTHORIZED';
        }
```

**Flow:** stored refresh token + !forceReauthorization → `refreshAuthorization(...)` inside try → SUCCESS assigns `newTokens` and falls out of the try; saveTokens now happens AFTER the catch block, so its failure REJECTS the caller (pre-fix behavior: the same catch swallowed any non-OAuthError from saveTokens and silently fell through to a brand-new authorization request — fatal under rotating refresh tokens, where the old token was already consumed server-side) → refresh throws ServerError or non-OAuth error → log-and-fall-through to fresh authorization (now WITH a console.warn naming the cause, JSON-stringified so attacker-controlled response bodies cannot forge log lines) → other OAuth errors rethrow.

**Invariant:** Only the REFRESH call is guarded by the try/catch; token PERSISTENCE sits outside it because dropping rotated credentials leaves the client permanently logged out while appearing healthy. Recovery paths that invalidate credentials (invalid_client / unauthorized_client / invalid_grant) announce themselves via `warnCredentialInvalidation`, whose wording distinguishes a provider that implements `invalidateCredentials()` (credential actually discarded) from one that omits it (stale credential STILL IN STORAGE and replayed next call — the operator-facing truth).

**Probe (direct tests):** `sed -n '3080,3090p' packages/client/test/client/auth.test.ts` → `it('propagates saveTokens errors after a successful refresh (#2034)', …)` mocking `saveTokens.mockRejectedValueOnce(persistError)`; `grep -n "propagates through auth() on the refresh branch" packages/client/test/client/auth.test.ts` → :2492; `grep -c "warnCredentialInvalidation" packages/client/src/client/auth.ts` → 3.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "warnCredentialInvalidation", limit: 3 });
// → warnCredentialInvalidation Function packages/client/src/client/auth.ts 994-1006
```

**Verdict:** Adopt the outside-the-catch persistence boundary + JSON-stringified cause logging; adapt invalidation wording to your host's observability; omit the fall-through branch entirely if your host treats any refresh failure as terminal.
