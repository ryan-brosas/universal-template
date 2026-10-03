# Authentication and requests

## Choose and bind the identity

Use a personal access token (PAT) for an internal/private integration with one
account at a time. Use OAuth for a public integration connecting multiple
customers. Keep credentials out of browser bundles, URLs, logs and source; bind
stored tokens to the correct customer and Calendly identity.

API v2 uses `https://api.calendly.com` and `Authorization: Bearer <token>`.
`GET /users/me` (`users:read`) returns the user URI and `current_organization`;
OAuth token responses also include `owner` and `organization`. Preserve complete
resource URIs where parameters require them; extract a UUID only for a path
parameter. API v1 is retired: migrate authentication, endpoints and payloads,
not merely the hostname.

## Scopes, roles and plans

New PATs and OAuth apps have no API access until scopes are explicitly granted.
A domain's `:write` includes its corresponding `:read`; it does not grant other
domains or bypass account roles/plans. Legacy grants retain their documented
access, and refresh migrates legacy tokens into scoped format. Do not copy an
old `scope: "default"` example as a new integration's permission model.

Map enabled features to endpoint scopes. For OAuth, request space-separated
scopes using proper URL encoding and inspect what was actually granted. For a
403, distinguish insufficient scopes (`required_scopes`), role, plan and feature
availability. Added permissions may require reauthorization, not repeated
requests with the same token. Webhook creation also needs the subscribed
family's read scope; see [webhooks](webhooks.md).

The broad scope catalog contains stale route names and an available-times scope
mismatch. Use the endpoint reference for its contract and preserve uncertainty
until an authorized request verifies the grant. Do not silently widen access to
work around a 403.

## OAuth lifecycle

The REST OAuth reference uses `https://auth.calendly.com/oauth/authorize` and
`https://auth.calendly.com/oauth/token`. Authorization is a browser redirect,
not a JSON fetch. Register the correct app type and redirect URI; bind the
callback to the initiating request using the OAuth library's CSRF/state and
PKCE protections. PKCE S256 is required for native clients and recommended for
web apps.

The token endpoint accepts form-encoded data:

- Authorization-code grant: `grant_type=authorization_code`, `code`, and the
  exact `redirect_uri` used during authorization; include `code_verifier` for
  PKCE.
- Refresh grant: `grant_type=refresh_token` and the current `refresh_token`.
- Web clients authenticate with HTTP Basic using client ID/secret. Native
  clients send `client_id` in the body; do not embed a confidential-client
  secret in a distributed app.

Access tokens are documented as two-hour tokens; calculate expiry from the
returned `expires_in`. Refresh tokens are single-use: each success immediately
invalidates the old refresh token and returns a replacement pair. The published
rotation enforcement deadline was August 31, 2026.

Serialize refresh per connection, including across workers. Atomically persist
the new access token, refresh token and expiry before releasing waiters. A stale
worker must not overwrite or erase a newer credential generation. On
`invalid_grant`, check whether another worker already rotated the token; if no
valid current generation remains, require reconnection. A timeout after refresh
may have consumed the token: do not assume replay is safe. Diagnose
`invalid_client` separately rather than making every user reconnect to a broken
app configuration.

`POST /oauth/introspect` and `POST /oauth/revoke` accept form fields `client_id`,
`client_secret`, `token` in the REST OAuth contract. Introspection reports
`active` and token metadata; revocation changes access and needs authorization.
Account email/password/login-method changes can also revoke credentials.
[MCP](mcp.md) uses separate discovery and public-client registration rules.

## Pagination and request budgets

Single-resource responses generally wrap `resource`; lists use `collection` and
`pagination`. Follow `next_page_token` with `page_token`, retaining the original
filters, until exhausted. Alternatively follow a documented next-page URL only
after validating its API origin before attaching credentials. Do not stop after
the default page. Check endpoint-specific `count` limits; most are 100, while
activity logs allow 1000. Availability/busy-time endpoints use bounded date
windows instead of ordinary keyset pagination.

Published limits are per user, including third-party integration traffic:

| Operation/account | Limit |
| --- | --- |
| General API, paid | 500 requests/minute |
| General API, Free | 50 requests/minute |
| OAuth token issuance | 8 requests/minute |
| Create invitee, trial | 5 requests/day |
| Create invitee, paid non-Enterprise | 10/minute, 50/hour and 100/day |
| Create invitee, Enterprise | 500/minute |

Use response headers as current budget evidence. `X-RateLimit-Reset` is seconds
until reset, not an epoch timestamp. Observe `X-RateLimit-Limit` and
`X-RateLimit-Remaining`; wait on 429 and bound backoff with jitter. Coordinate
workers per user rather than multiplying a limit by token count.

Handle 400 as a request/validation problem, 401 as authentication, 403 as
permissions/plan, and 404 in the authorized resource context. Some generated
error examples mislabel these as internal errors: inspect HTTP status and actual
payload. Retry safe reads selectively; timeouts and 5xx on booking or other
non-idempotent writes require reconciliation, not unconditional retries.

## Sources

- [Authentication](https://developer.calendly.com/docs/authentication/overview.md),
  [OAuth apps](https://developer.calendly.com/docs/authentication/creating-an-oauth-app.md),
  [scopes](https://developer.calendly.com/docs/authentication/scopes.md).
- [Token grants](https://developer.calendly.com/api-docs/calendly-o-auth/o-auth/post-oauth-refresh-token.md),
  [refresh rotation](https://developer.calendly.com/docs/authentication/refresh-token-rotation-guide.md),
  [introspection](https://developer.calendly.com/api-docs/calendly-o-auth/o-auth/post-oauth-introspect.md),
  [revocation](https://developer.calendly.com/api-docs/calendly-o-auth/o-auth/post-oauth-revoke.md).
- [API conventions](https://developer.calendly.com/api-docs/overview/api/api-conventions.md),
  [rate limits](https://developer.calendly.com/api-docs/overview/rate-limits.md),
  [v1 migration](https://developer.calendly.com/docs/getting-started/how-to-migrate-from-api-v1-to-api-v2.md).
