<!-- capsule-v2 -->
# 401 discovery chain — how do an unauthenticated client's 401, the metadata documents, and the verifier compose into hands-free OAuth discovery?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** A client that has never talked to your server must go from "401" to a working token using only standard discovery — what does each middleware contribute to that chain?

## Connected graph-selected seam
**Path/Symbol:** Composition across three files: `bearerAuth.ts` `requireBearerAuth` (:185-203) + challenge with `resourceMetadataUrl` (:136-163); `oauthMetadata.ts` `getOAuthProtectedResourceMetadataUrl` (:91-93) + `oauthMetadataResponse` (:165-180) + PRM `authorization_servers` field (:70-79). Graph qn `typescript-sdk.packages.server.src.server.middleware.oauthMetadata.getOAuthProtectedResourceMetadataUrl`.
**Signature:** Wiring: `resourceMetadataUrl = getOAuthProtectedResourceMetadataUrl(resourceServerUrl)` passed into `requireBearerAuth({…, resourceMetadataUrl})`; same URL becomes the PRM route location served by `oauthMetadataResponse`.
**Data Shape:** Chain payload: `401` + `WWW-Authenticate: Bearer …, resource_metadata="<prm-url>"` → GET prm-url → `{resource, authorization_servers:[issuer], scopes_supported,…}` → RFC 8414 AS doc at issuer's well-known.

### Decisive source
```ts
// oauthMetadata.ts — the PRM document is the pivot between the two servers:
return {
    resource: options.resourceServerUrl.href,
    authorization_servers: [options.oauthMetadata.issuer],   // ← where to get a token
    scopes_supported: options.scopesSupported,
    resource_name: options.resourceName,
    resource_documentation: options.serviceDocumentationUrl?.href
};
// getOAuthProtectedResourceMetadataUrl(new URL('https://api.example.com/mcp'))
// → 'https://api.example.com/.well-known/oauth-protected-resource/mcp'
```

**Flow:** (1) client calls the MCP endpoint bare → bearer gate answers `401` whose challenge advertises `resource_metadata` = the PRM URL (only when the option was configured) → (2) client GETs the PRM URL — which is EXACTLY the path-aware well-known route derived from the same resourceServerUrl by `getOAuthProtectedResourceMetadataUrl`, so advertised and served locations coincide BY CONSTRUCTION, not by config discipline → (3) PRM's `authorization_servers[0]` names the AS issuer → (4) client fetches the AS metadata (served verbatim at `/.well-known/oauth-authorization-server` for legacy clients probing the resource origin, or at the AS itself per RFC 8414) → `authorization_endpoint`/`token_endpoint`. Permissive CORS (`*`) on every metadata response is what makes step 2–4 work from browser-based clients.

**Invariant:** The three pieces share ONE input — `AuthMetadataOptions.resourceServerUrl`: it derives the challenge's `resource_metadata` URL, the PRM route path, and the PRM `resource` claim. Divergent sources would create a discovery loop (advertised URL ≠ served URL ⇒ client retries forever). The AS-document route exists specifically for clients that probe the RESOURCE origin first; passing the AS doc through verbatim while still running issuer validation keeps the fail-scope of the discovery capsule intact.

**Probe:** `packages/server/test/server/bearerAuth.test.ts` :147 (challenge carries `resource_metadata="https://api.example.com/…`), :98 (field order with resource_metadata last); `packages/server/test/server/oauthMetadata.test.ts` :74/:80 (path-aware derivation), :88 (PRM served at that exact path with CORS `*`), :104 (AS mirror). End-to-end shape: `test/e2e/scenarios/hosting-auth.test.ts` verifyBearer :43; conformance harness `test/conformance/src/authTestServer.ts` requireBearerAuth :158.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "getOAuthProtectedResourceMetadataUrl resource_metadata authorization_servers", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt single-source-of-truth wiring (one resourceServerUrl feeding challenge + route + claim) for any discovery protocol. Adapt the document formats to your scheme. Omit the legacy `server-legacy/auth/router.ts` variant of the URL builder — pre-GA shape.
