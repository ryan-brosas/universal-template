<!-- capsule-v2 -->
# OAuth discovery documents — how do you serve RFC 9728/8414 metadata so any web client can discover the Authorization Server?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** An MCP Resource Server must expose `/.well-known/oauth-protected-resource[/<path>]` and `/.well-known/oauth-authorization-server` — what does a correct, cache-safe, fail-scoped discovery handler look like?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/middleware/oauthMetadata.ts`: `oauthMetadataResponse` (:165-180), `buildOAuthProtectedResourceMetadata` (:70-79), `checkIssuerUrl` (:47-58), `getOAuthProtectedResourceMetadataUrl` (:91-93) + `protectedResourceMetadataPath`/`stripTrailingSlash` (:96-105), `metadataDocumentResponse` (:109-138). Graph qn `typescript-sdk.packages.server.src.server.middleware.oauthMetadata.oauthMetadataResponse`.
**Signature:** `oauthMetadataResponse(request: Request, options: AuthMetadataOptions): Response | undefined`; `buildOAuthProtectedResourceMetadata(options): OAuthProtectedResourceMetadata`; `getOAuthProtectedResourceMetadataUrl(serverUrl: URL): string`.
**Data Shape:** `AuthMetadataOptions = {oauthMetadata: OAuthMetadata; resourceServerUrl: URL; serviceDocumentationUrl?; scopesSupported?; resourceName?; dangerouslyAllowInsecureIssuerUrl?}`. PRM doc = `{resource: rsUrl.href, authorization_servers: [issuer], scopes_supported?, resource_name?, resource_documentation?: href}`.

### Decisive source
```ts
// Match before build: unmatched traffic falls through untouched even when the
// options are misconfigured — a bad issuer surfaces on the discovery routes
// (or at startup), never on the host's own traffic.
const requestPath = stripTrailingSlash(new URL(request.url).pathname);
if (requestPath === protectedResourceMetadataPath(options.resourceServerUrl)) {
    return metadataDocumentResponse(request, buildOAuthProtectedResourceMetadata(options));
}
if (requestPath === '/.well-known/oauth-authorization-server') {
    buildOAuthProtectedResourceMetadata(options); // issuer validation
    return metadataDocumentResponse(request, options.oauthMetadata);
}
return undefined;
```

**Flow:** path match (trailing slash tolerated once, like path-mounted routers) → PRM route builds the RFC 9728 document from options; AS route passes the RFC 8414 document through VERBATIM but still runs issuer validation first → both funnel into one responder: OPTIONS ⇒ `204` with reflected `Access-Control-Allow-Headers` + `Vary: Access-Control-Request-Headers` (a shared cache must not replay one preflight's allow-list against another's headers); GET/HEAD ⇒ JSON + `Access-Control-Allow-Origin: *`, HEAD = GET minus body per RFC 9110; other methods ⇒ `405` + `Allow: GET, HEAD, OPTIONS` + OAuth error body. Well-known URL derivation is path-aware: insert `/.well-known/oauth-protected-resource` ahead of the resource path (`https://api.example.com/mcp` ⇒ `…/.well-known/oauth-protected-resource/mcp`; root ⇒ bare).

**Invariant:** Fail-scope isolation: an invalid issuer throws ONLY on matched discovery routes or at startup (`buildOAuthProtectedResourceMetadata` called eagerly); unmatched host traffic NEVER throws on misconfiguration. Issuer validation: HTTPS required except localhost/127.0.0.1 (deliberate exemption of the RFC 8414 rule for local testing) unless `dangerouslyAllowInsecureIssuerUrl`; fragment or query string always rejected. Trailing-slash normalization cuts only when `path.length > 1`, so `/` stays `/` and a root resource URL keeps its bare well-known route reachable.

**Probe:** `packages/server/test/server/oauthMetadata.test.ts` — :27 full PRM shape, :38 HTTPS rejection, :44 localhost exemption + escape hatch, :57 fragment/query rejection, :74/:80 path-aware URL, :88 CORS `*`, :110 405+Allow+error body, :120 204 reflected headers, :134 undefined fall-through, :143 no-throw-on-unmatched-with-bad-issuer, :147 misconfiguration surfaces on discovery routes only, :153/:161 trailing-slash tolerance both sides, :166 HEAD body-less, :176 Vary pin.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "oauthMetadataResponse buildOAuthProtectedResourceMetadata checkIssuerUrl", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt match-before-validate fall-through, single-responder method ladder (204/405/HEAD), Vary-on-reflection, path-aware well-known insertion, and startup-eager validation. Adapt the exact well-known prefix if porting outside OAuth. Omit nothing behavioral — this file is self-contained.
