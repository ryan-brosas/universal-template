<!-- capsule-v2 -->
# CrossAppAccessProvider — how does discovery state flow into a jwt-bearer token request without a browser leg?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Which provider hooks must capture RFC 9728 discovery output, and in what order does `prepareTokenRequest` turn it into an SEP-990 assertion request?

## Discovery-state capture → async prepareTokenRequest (SEP-990 steps 2-3 client side)
**Path/Symbol:** `packages/client/src/client/authExtensions.ts` `CrossAppAccessProvider` (:602-734), hooks `saveAuthorizationServerUrl` :668 / `saveResourceUrl?` :683, `prepareTokenRequest(scope?)`: Promise\<URLSearchParams\> :694-733.
**Signature:** `new CrossAppAccessProvider(options: { assertion: AssertionCallback; clientId: string; clientSecret: string; clientName?: string; fetchFn?: FetchLike; expectedIssuer?: string })`; `AssertionCallback = (context: CrossAppAccessContext) => string | Promise<string>` (:501) with context `{ authorizationServerUrl, resourceUrl, scope?, fetchFn }`.
**Data Shape:** `_clientMetadata.grant_types: ['urn:ietf:params:oauth:grant-type:jwt-bearer']`, `token_endpoint_auth_method: 'client_secret_basic'` (:618-623); `_authorizationServerUrl`/`_resourceUrl` start undefined and are filled by `auth()`'s optional-hook calls.

### Decisive source
```ts
if (!authServerUrl) {
    throw new Error('Authorization server URL not available. Ensure auth() has been called first.');
}

if (!resourceUrl) {
    throw new Error(
        'Resource URL not available — server may not implement RFC 9728 ' +
            'Protected Resource Metadata (required for Cross-App Access), or ' +
            'auth() has not been called'
    );
}
```
(:699-709)

**Flow:** `auth()` (packages/client/src/client/auth.ts) runs discovery then calls the OPTIONAL provider hooks — `await provider.saveAuthorizationServerUrl?.(issuer)` at auth.ts:1177 (comment marks it a deprecated write-only hook the SDK never reads back; CrossAppAccessProvider reads its own copy internally) and `await provider.saveResourceUrl?.(String(resource))` at :1215 only when a resource was resolved. Later, on 401, the SDK awaits `prepareTokenRequest(scope?)`: both cached URLs are REQUIRED (throw with distinct messages otherwise), scope is stashed for the callback (:712), the user `assertion` callback produces the ID-JAG (:715-720), and params `{ grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion: <JAG>, scope? }` are returned for the RFC 7523 exchange (:723-730).
**Invariant:** This is the ONLY provider in the file whose `prepareTokenRequest` is async and state-dependent — porters who make it sync lose the discovery→assertion ordering. The grant_types entry is the full URN, not `'client_credentials'`. The two failure messages deliberately distinguish "you skipped auth()" from "the server lacks RFC 9728" — keep both.
**Probe:** `grep -n "throw new Error('Authorization server URL not available" packages/client/src/client/authExtensions.ts` → :700 only; direct tests describe `CrossAppAccessProvider` :472 incl. end-to-end :477, missing-authserver :587, missing-resource :600, metadata-shape :641.
**Caveat:** none — anchors byte-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "saveResourceUrl saveAuthorizationServerUrl provider discovery hooks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hook-capture pattern and async prepareTokenRequest ladder verbatim. Adapt the assertion callback to your IdP's ID-token source. Omit nothing from the dual error messages; they encode the RFC 9728 requirement that porters otherwise discover in production.
