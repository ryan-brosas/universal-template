<!-- capsule-v2 -->
# MCP Authorization — how does an HTTP MCP server protect its resources with OAuth 2.1, and what must a client do to get a token?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What is the exact OAuth 2.1 authorization flow an MCP server (resource server) and client must implement, and which scope/error rules keep it least-privilege and interoperable?

## Roles and scope of the auth framework
**Path/Symbol:** `docs/specification/draft/basic/authorization/index.mdx` (whole; roles :47–58; overview/requirements :60–80; scope selection :97–134; flow steps :136–188; response validation :190–213; resource parameter :215–252; access token usage :254–297; refresh :299–313; error handling :315–405; extensions :415–424).

**Data Shape:** Authorization is **OPTIONAL** and transport-scoped. HTTP-based transports SHOULD conform; stdio **SHOULD NOT** (credentials come from the environment); alternative transports MUST follow their own best practices. Roles: MCP server = OAuth 2.1 **resource server** (accepts access tokens); MCP client = OAuth 2.1 **client** (requests on behalf of a resource owner); a separate **authorization server** (AS) issues tokens. The AS may be co-hosted or separate.

### Decisive source
```md
# index.mdx:62-80 (normative requirements)
1. Authorization servers MUST implement OAuth 2.1 with appropriate security
   for both confidential and public clients.
2. AS + clients SHOULD support OAuth Client ID Metadata Documents.
3. AS + clients MAY support Dynamic Client Registration (deprecated).
4. MCP servers MUST implement OAuth 2.0 Protected Resource Metadata (RFC9728);
   MCP clients MUST use it for authorization server discovery.
5. MCP authorization servers MUST provide >=1 discovery mechanism
   (OAuth 2.0 AS Metadata RFC8414 OR OpenID Connect Discovery 1.0);
   MCP clients MUST support BOTH.
```

**Flow:** client sends an MCP request without a token → server returns `401 Unauthorized` with a `WWW-Authenticate: Bearer resource_metadata="<url>", scope="..."` header → client extracts the `resource_metadata` URL → fetches Protected Resource Metadata → picks an authorization server → does AS metadata discovery → registers (CIMD / pre-registration / dynamic) → generates PKCE, includes `resource` param, records expected issuer → opens browser to authorization URL → user authorizes → AS redirects to callback with code (+`iss`) → client validates `iss` against recorded issuer → exchanges code+verifier+resource at token endpoint → gets access token (+refresh) → sends MCP requests with `Authorization: Bearer <token>`.

**Scope selection strategy (least privilege):** on the initial 401, use the `scope` from the `WWW-Authenticate` header if present; otherwise use all `scopes_supported` from Protected Resource Metadata (omit `scope` param if undefined). The challenged scope set has **no guaranteed set relationship** to `scopes_supported` — clients MUST treat the challenge as authoritative for the current operation and MUST NOT assume subset/superset.

**Access token rules:** every client→server HTTP request carries `Authorization: Bearer <token>`; tokens MUST NOT go in the URI query string. Servers MUST validate tokens were issued specifically for them (audience per RFC8707 §2), MUST reject invalid/expired with `401`, MUST NOT accept or transit tokens for other resources, and MUST NOT pass through a client's token to upstream APIs (that's a separate token from the upstream AS).

**Refresh tokens:** clients MUST keep them confidential, SHOULD declare `refresh_token` in `grant_types`, MAY add `offline_access` scope (only if AS metadata lists it in `scopes_supported`), MUST NOT assume they'll be issued. Servers SHOULD NOT advertise `offline_access` (refresh isn't a resource requirement).

**Error codes:** `401` = auth required/token invalid; `403` = invalid scopes/insufficient permissions; `400` = malformed authorization request.

**Step-up authorization (runtime `insufficient_scope`):** server responds `403` with `WWW-Authenticate: Bearer error="insufficient_scope", scope="<required>", resource_metadata="<url>"`. Client computes the **union** of its previously-requested scope set and the challenge scopes (preserves granted permissions), re-authorizes with that union, retries the original request a bounded number of times, then treats it as permanent failure. Servers MUST account for scope hierarchies (broader implies narrower) and SHOULD emit all required scopes in a single challenge (incremental challenges force multiple round-trips).

**Invariant:** the whole flow is least-privilege + audience-bound. A porter who omits the `resource` parameter, who trusts a challenge scope without re-requesting the union, who puts a token in a query string, or who passes a client token upstream to a third-party API breaks the security model. Token passthrough is explicitly forbidden.

**Probe:** no runtime tests in the spec repo (docs + schema only). Machine-checkable anchors are the schema types and `scripts/validate-examples.ts`; coverage caveat recorded honestly. The `WWW-Authenticate`/`resource`/scope rules are prose-normative.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "Insufficient.Scope|Step-Up|Scope.Selection", limit: 10 });
```

## Verdict
Adopt the OAuth 2.1 authorization flow with RFC9728 protected-resource metadata, mandatory `resource` parameter (RFC8707), PKCE, `iss` validation, least-privilege scope selection (challenge-first, then `scopes_supported`), union-based step-up re-authorization, and strict no-token-passthrough; adapt AS endpoints, scope names, and token storage to host; omit stdio auth (env credentials), dynamic registration (deprecated), and the extension repo (`modelcontextprotocol/ext-auth`) unless building those directly.
