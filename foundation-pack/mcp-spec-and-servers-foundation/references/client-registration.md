<!-- capsule-v2 -->
# Client Registration — how does an MCP client obtain a client ID before the authorization flow, and which mechanism wins?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What are the three client-registration mechanisms, their selection priority, and the exact Client ID Metadata Document contract (the modern default)?

## Three mechanisms, one priority order
**Path/Symbol:** `docs/specification/draft/basic/authorization/client-registration.mdx` (whole; overview/priority :7–18; CIMD :20–126; pre-registration :128–136; dynamic :138–179; AS binding :181–202).

**Data Shape:** Clients supporting all options SHOULD use priority order:
1. **Pre-registered** client info for the server (if the client has it).
2. **Client ID Metadata Documents** (CIMD) — if AS advertises `client_id_metadata_document_supported: true`.
3. **Dynamic Client Registration** (RFC7591) — fallback if AS advertises `registration_endpoint` (deprecated).
4. Prompt the user to enter client info if no other option is available.

### Decisive source
```md
# client-registration.mdx:36-51 (CIMD requirements)
For MCP Clients:
- MUST host metadata at an HTTPS URL; client_id URL MUST use "https"
  scheme and contain a path component (e.g. https://example.com/client.json)
- metadata MUST include at least: client_id, client_name, redirect_uris
- MUST ensure client_id value matches the document URL exactly
- MAY use private_key_jwt for client auth with appropriate JWKS
For Authorization Servers:
- SHOULD fetch metadata when encountering URL-formatted client_ids
- MUST validate fetched document's client_id matches the URL exactly
- SHOULD cache metadata respecting HTTP cache headers
- MUST validate redirect URIs in the auth request against the document
- MUST validate the document is valid JSON with required fields
```

**Flow (CIMD):** client hosts a JSON doc at an HTTPS URL; uses that URL as `client_id`. Client sends authorization request with `client_id=<url>` + `redirect_uri`. AS detects the URL-formatted `client_id`, fetches the document, validates (client_id matches URL, redirect_uri in allowed list, structure valid, optional domain trust policy), shows consent page with `client_name`, then issues the code via redirect. AS caches the doc respecting HTTP cache headers.

**Example CIMD doc:** `{ "client_id": "https://app.example.com/oauth/client-metadata.json", "client_name": "Example MCP Client", "redirect_uris": ["http://127.0.0.1:3000/callback", "http://localhost:3000/callback"], "grant_types": ["authorization_code"], "response_types": ["code"], "token_endpoint_auth_method": "none" }`. Note `localhost` redirect URIs are allowed (loopback).

**Dynamic Client Registration (deprecated):** RFC7591 `POST /register` → client credentials. When the AS supports OIDC + dynamic registration, the client MUST specify an appropriate `application_type` — omitting it defaults to `"web"` under OIDC, which conflicts with native-style redirect URIs. Native apps (desktop/mobile/CLI/localhost web) SHOULD use `"native"`; web apps (remote browser-based) SHOULD use `"web"`. Clients MUST handle registration failures from redirect-URI constraints and MAY retry with an adjusted `application_type` or conforming redirect URIs.

**Authorization Server Binding (critical):** clients using pre-registered or dynamically-registered credentials MUST associate them with the specific AS that issued them, keyed by the AS's `issuer` identifier. When the AS changes (detected via updated protected resource metadata), clients MUST NOT reuse credentials from a different AS and MUST re-register. Pre-registered credentials are inherently AS-specific — if the indicated AS no longer matches, surface an error rather than silently using mismatched credentials. **CIMD client IDs are portable across ASes** (self-hosted HTTPS URLs resolved on demand — no re-registration needed when the AS changes).

**Invariant:** client_id↔URL identity + per-AS credential binding. A porter who lets a client_id drift from its document URL, who reuses dynamic/pre-registered credentials across ASes, or who omits `application_type` on an OIDC dynamic registration breaks interoperability or security.

**Probe:** no runtime tests in the spec repo; prose-normative with RFC7591 / draft-ietf-oauth-client-id-metadata-document anchors. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "CIMD|ClientRegistration|Authorization-Server-Binding", limit: 10 });
```

## Verdict
Adopt the priority order (pre-registered → CIMD → dynamic → user prompt), the CIMD HTTPS-URL-as-client_id contract with exact URL↔client_id match, per-AS credential binding keyed by issuer, and `application_type` on dynamic registration; adapt your metadata document URL, redirect URIs, and trust policy to host; omit dynamic registration for new implementations (deprecated in favor of CIMD).
