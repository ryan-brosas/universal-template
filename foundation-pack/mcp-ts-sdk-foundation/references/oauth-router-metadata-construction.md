<!-- capsule-v2 -->
# OAuth router metadata construction — how is AS metadata built so optional endpoints self-declare, and which issuer rules must a porter not soften?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When porting an OAuth authorization-server router, how do metadata endpoints, capability flags, and issuer validation interact so clients never see an endpoint the server won't serve?

## Metadata construction & issuer grammar
**Path/Symbol:** `packages/server-legacy/src/auth/router.ts`: `checkIssuerUrl` (:70-81), `createOAuthMetadata` (:83-128), `mcpAuthRouter` (:142-183), `mcpAuthMetadataRouter` (:213-236).
**Signature:** `createOAuthMetadata(options: { provider; issuerUrl: URL; baseUrl?; serviceDocumentationUrl?; scopesSupported? }): OAuthMetadata`; `mcpAuthMetadataRouter(options): express.Router`.
**Data Shape:** endpoints derived from PROVIDER SHAPE: `registration_endpoint = provider.clientsStore.registerClient ? '/register' : undefined`, `revocation_endpoint = provider.revokeToken ? '/revoke' : undefined` — presence in metadata ≡ handler mounted by `mcpAuthRouter` (:165-180 mount the same two conditionals).

### Decisive source
```ts
// router.ts :70-74
const checkIssuerUrl = (issuer: URL): void => {
    // RFC 8414 forbids a localhost HTTPS exemption, but testing needs it
    if (issuer.protocol !== 'https:' && issuer.hostname !== 'localhost' && issuer.hostname !== '127.0.0.1' && !allowInsecureIssuerUrl) {
        throw new Error('Issuer URL must be HTTPS');
    }
```
```ts
// :124 the RFC 9207 claim defaults TRUE because SDK code makes it true
authorization_response_iss_parameter_supported: options.provider.authorizationResponseIssParameterSupported ?? true
```

**Flow:** `checkIssuerUrl` throws on non-HTTPS (except localhost/127.0.0.1, overridable ONLY by env `MCP_DANGEROUSLY_ALLOW_INSECURE_ISSUER_URL === 'true'|'1'`, which also console.warns at module load), on any fragment (`issuer.hash`) and on any query (`issuer.search`). `createOAuthMetadata` resolves every path against `baseUrl || issuer`. `mcpAuthMetadataRouter` serves PRM at `/.well-known/oauth-protected-resource<rsPath>` where `rsPath === '/' ? '' : rsPath` (path-specific per RFC 9728) and AS metadata always at `/.well-known/oauth-authorization-server` (RFC 8414); PRM `resource` falls back resourceServerUrl → baseUrl → issuer (AS=RS back-compat).

**Invariant:** metadata is DERIVED, never hand-listed: a porter who hardcodes `/register` without gating on `registerClient` advertises an endpoint that 404s; conversely omitting the conditional mount while advertising breaks dynamic registration discovery. The insecure-issuer escape hatch must stay env-gated AND warn — silently allowing HTTP issuers is the failure mode it exists to prevent. `checkIssuerUrl` runs again inside `mcpAuthMetadataRouter` (:214), so metadata-only routers enforce the same grammar.

**Probe (direct tests):** `packages/server-legacy/test/auth/router.test.ts` — :140 'throws error for non-HTTPS issuer URL', :149 'allows localhost HTTP for development', :158 fragment / :167 query throws, :226 'derives authorization_response_iss_parameter_supported from the provider'.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "createOAuthMetadata iss parameter supported metadata", limit: 3 });
// → packages/server-legacy/src/auth/router.ts createOAuthMetadata Function 83-128 (rank #2)
```

## Verdict
Adopt shape-derived endpoint advertisement, the https/no-query/no-fragment issuer grammar, and path-aware well-known mounting; adapt route table and env-flag name to your host; omit the express Router wiring if your framework composes handlers differently.
