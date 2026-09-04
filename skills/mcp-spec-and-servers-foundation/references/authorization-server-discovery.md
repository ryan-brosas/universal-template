<!-- capsule-v2 -->
# Authorization Server Discovery — how does a client find the AS for an MCP server, and how does it validate the metadata it gets?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What is the exact discovery ladder (protected-resource metadata → AS metadata) and the issuer-validation rule that prevents a client from trusting a spoofed metadata document?

## Two-stage discovery with issuer binding
**Path/Symbol:** `docs/specification/draft/basic/authorization/authorization-server-discovery.mdx` (whole; AS location :11–35; protected-resource discovery :37–53; AS metadata discovery :55–94; sequence :96–144).

**Data Shape:** Stage 1 — the MCP server (resource server) MUST implement RFC9728 Protected Resource Metadata and include `authorization_servers` (≥1). Multiple AS entries are each independent OAuth 2.0 ASes; client credentials/tokens are **per-AS** and MUST NOT be assumed portable across them. Stage 2 — the client discovers the AS's metadata via RFC8414 / OIDC Discovery.

### Decisive source
```md
# authorization-server-discovery.mdx:39-47 (protected-resource discovery)
MCP servers MUST implement one of:
1. WWW-Authenticate Header: include resource metadata URL under
   `resource_metadata` in the WWW-Authenticate header on 401 responses.
2. Well-Known URI (RFC9728), either:
   - at the MCP endpoint's path: https://example.com/public/mcp →
     https://example.com/.well-known/oauth-protected-resource/public/mcp
   - at the root: https://example.com/.well-known/oauth-protected-resource
MCP clients MUST support both; use the WWW-Authenticate URL when present,
else fall back to constructing the well-known URIs in the order above.
```

**Flow (protected-resource metadata):** client attempts unauthenticated request → gets `401` (may carry `resource_metadata` in header) → if header present, GET that URL; else probe `/.well-known/oauth-protected-resource/<mcp-path>` then `/.well-known/oauth-protected-resource` (root). If none found, abort or use pre-configured values.

**Flow (AS metadata discovery):** MCP uses the default `oauth-authorization-server` well-known suffix (RFC8414 §3.1); no MCP-specific suffix. For issuer URLs **with path components** (`https://auth.example.com/tenant1`), try in priority order:
1. `https://auth.example.com/.well-known/oauth-authorization-server/tenant1` (OAuth AS metadata, path insertion)
2. `https://auth.example.com/.well-known/openid-configuration/tenant1` (OIDC, path insertion)
3. `https://auth.example.com/tenant1/.well-known/openid-configuration` (OIDC, path appending)

For issuer URLs **without path components** (`https://auth.example.com`):
1. `https://auth.example.com/.well-known/oauth-authorization-server`
2. `https://auth.example.com/.well-known/openid-configuration`

**Invariant (critical):** after fetching an AS metadata document, the client MUST validate per RFC8414 §3.3 / OIDC Discovery §4.3 that the document's `issuer` value is **byte-identical** to the issuer identifier used to construct the well-known URL. A document fetched from `https://attacker.example/.well-known/oauth-authorization-server` containing `"issuer": "https://honest.example"` MUST be rejected. This is the anti-spoofing gate — the recorded issuer is later used to validate the authorization response's `iss` (see `authorization-overview`).

**Flow (full):** client → `401` → resource metadata URL (header or well-known probe) → resource metadata with AS URL → build AS metadata URL → try OAuth/OIDC discovery endpoints in priority order → validated AS metadata → OAuth 2.1 flow → token → MCP requests with bearer token.

**Invariant:** per-AS credential isolation + issuer-identical validation. A porter who reuses a token across two ASes listed in `authorization_servers`, or who accepts an AS metadata document whose `issuer` doesn't match the URL it was fetched from, breaks the security model.

**Probe:** no runtime tests in the spec repo; prose-normative with RFC9728/RFC8414 anchors. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "Authorization.Server|Protected.Resource", limit: 10 });
```

## Verdict
Adopt the two-stage discovery ladder (WWW-Authenticate `resource_metadata` first, then well-known URI probing in the documented order), per-AS credential isolation, and the issuer-must-match-URL validation gate; adapt your well-known path layout and metadata cache to host; omit stdio (env credentials) and the deprecated HTTP+SSE transport.
