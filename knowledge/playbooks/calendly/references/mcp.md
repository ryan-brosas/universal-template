# Calendly MCP

## Two different servers

- `https://developer.calendly.com/_mcp/server` searches developer documentation.
  It does not establish access to a Calendly account or permission to book.
- `https://mcp.calendly.com` is Calendly's hosted account-action MCP server.
  Self-hosting is not supported. Connection requires user consent and a
  compatible OAuth client; a configured URL alone proves neither.

Do not install, register or authorize either service just to read this playbook.
When setup is requested, use the host's actual configuration contract and keep
credentials host-side.

## Compatibility and authentication

The account server requires OAuth 2.1 Authorization Code with PKCE S256,
protected-resource/authorization-server discovery, and Dynamic Client
Registration (DCR). PATs and statically provisioned developer-console
client ID/secret flows are not supported for this MCP connection. A client that
only asks for those static credentials is incompatible; do not work around it
by pasting a REST token.

For a client implementation:

1. Follow the resource metadata advertised by the 401 challenge. The documented
   resource metadata URL is
   `https://mcp.calendly.com/.well-known/oauth-protected-resource`.
2. Discover the authorization server from that document; current public metadata
   points to `https://calendly.com/`, with metadata at
   `https://calendly.com/.well-known/oauth-authorization-server`.
3. Use the discovered authorization, token and registration endpoints. Do not
   replace them with the REST OAuth reference's `auth.calendly.com` host.
4. Register a public client with `client_name`, exact `redirect_uris`,
   `grant_types: ["authorization_code"]`, `response_types: ["code"]`, and
   `token_endpoint_auth_method: "none"`. Include `refresh_token` in grant types
   if the client uses refresh tokens. Production redirects require HTTPS and
   reject wildcards, userinfo and malformed URIs; local HTTP is environment-policy
   dependent, not a universal exception.
5. Complete browser consent and PKCE. Persist the returned client identity and
   tokens securely; DCR clients do not receive a client secret. Apply the
   single-use rotation protections in [authentication](authentication-and-requests.md).

The current resource metadata advertises `mcp:scheduling:read` and
`mcp:scheduling:write`; the DCR guide says these are assigned server-side and
need not be included in registration. Use live metadata as the authority for
resource and scopes. Do not substitute REST domain scopes because the overview
loosely describes “same scopes and permissions.” Account role/plan restrictions
still apply; a write grant is not user authorization for every available action.

## Tool discovery and verification

Discover live tools and inspect their schemas before calling them. The published
list covers scheduling, availability, locations, users, organization invitations,
routing forms and no-shows, plus `list_calendly_skills`/`load_calendly_skill`.
Do not assume every new REST family is exposed through MCP or reconstruct a tool
name from a REST path. The documentation's tool names and equivalent-endpoint
table are navigation aids, not proof of runtime availability or argument shape.

Several REST equivalents in that table are stale, including availability,
locations, shares and routing submissions. Use the discovered MCP schema for
MCP calls and the endpoint/OpenAPI contract for REST calls. A tool annotation
such as `readOnlyHint` or `idempotentHint` is a hint, not a permission boundary.

After authorized setup, verify consent and a harmless identity/event-type read
first. For writes, apply the same confirmation, timezone, ambiguous-result
recovery and read-back checks as [REST scheduling](scheduling.md). Report missing
DCR support, authentication failures, missing tools and account-plan errors as
separate blockers; do not claim a successful integration from public discovery
metadata alone.

## Sources

- [MCP overview/DCR](https://developer.calendly.com/docs/mcp/calendly-mcp-server.md),
  [published tools](https://developer.calendly.com/docs/mcp/supported-tools.md).
- [Resource metadata](https://mcp.calendly.com/.well-known/oauth-protected-resource),
  [authorization-server metadata](https://calendly.com/.well-known/oauth-authorization-server).
