# Identity, membership and repository permissions

Treat these as separate layers: authentication identifies a user, membership
admits them to the workspace, roles govern administration, and permission syncing
limits repository access. Successful SSO alone does not enforce code-host ACLs.
Change these controls only within an explicitly authorized access-policy task.

## Built-in login, sessions and roles

Authentication cannot simply be disabled. Credential login is enabled by default;
an owner controls Email login and Email code in Settings → Security. Six-digit
email codes additionally require [SMTP](administration-and-licensing.md).
Set `AUTH_URL` to the deployment's public URL. For login/logout/organization
anomalies, check domain/callbacks, cookies and a full refresh before escalation.

`AUTH_SESSION_MAX_AGE_SECONDS=2592000` gives 30 days; JWT clock-skew tolerance
can admit a session briefly beyond that. `AUTH_SESSION_UPDATE_AGE_SECONDS=86400`
refreshes daily (`0` means every time). OAuth authorization codes, access tokens
and refresh tokens default to 600, 3600 and 7776000 seconds respectively through
`OAUTH_AUTHORIZATION_CODE_TTL_SECONDS`, `OAUTH_ACCESS_TOKEN_TTL_SECONDS` and
`OAUTH_REFRESH_TOKEN_TTL_SECONDS`. Stable `AUTH_SECRET` matters across restarts.

Member approval defaults on. Owners review pending registrations in Settings →
Members. An enabled invite link can admit users automatically despite approval
being required: treat it as an access-granting capability. Without approval,
new registrants enter immediately. Free-plan anonymous access, when enabled in
Settings → Access, creates a limited Guest experience; it does not disable the
account/administration boundary and is not a fix for an authorization failure.

Owner administers organization settings, members, billing and audits. Member
uses standard product features but not organization administration. Guest has
limited search/browsing, no chat history and no administrative powers. In v5,
**new free-plan users become Owners and role changes are unavailable**; the
migration guide explicitly preserves existing Members. Paid-plan new users
default to Member. Owners may promote/demote members; self-demotion or departure
requires another Owner to remain. Even Owners obey enforced repository ACLs.

## External identity providers

Paid `identityProviders` configuration is separate from ingestion `connections`.
GitHub, GitLab and Bitbucket Cloud/Server support `purpose: "sso"` (login plus
permission-sync identity) or `"account_linking"` (link an account without using
it as the login route). `accountLinkingRequired` controls mandatory linking.
`AUTH_EE_ALLOW_EMAIL_ACCOUNT_LINKING=true` automatically links same-email SSO
accounts by default; review that identity policy deliberately.

Array form defaults provider IDs to provider names and permits one of each type.
Object form supports multiple instances using unique keys and optional
`displayName`. Register `<sourcebot_url>/api/auth/callback/<id>` with each OAuth
client: object keys, not generic provider names, determine those callback IDs.
Use secret references for client credentials.

| Provider | Non-interchangeable setup requirements |
| --- | --- |
| GitHub | GitHub App preferred over OAuth App. External-identity setup alone does not require App installation. Read email; add repository metadata read for syncing and contents read only if also used for a code connection. OAuth App syncing uses `repo`. Custom-host `baseUrl` must match. |
| GitLab | `read_user`, plus `read_api` for syncing; set self-managed `baseUrl` correctly. |
| Bitbucket Cloud | Account Read, and Repositories Read for syncing; user OAuth syncing scopes are `account` / `repository`, not the ingestion API-token scope names. |
| Bitbucket Server / Data Center | Configure server `baseUrl`; user-driven syncing uses `REPO_READ`, with `PUBLIC_REPOS` also documented. Connection-token requirements are disputed; see the caveat below. |
| Google | Configure its OAuth client and exact Sourcebot callback. |
| Okta, Keycloak, Entra ID, Authentik | Configure provider-specific issuer and client credentials. Entra issuer is `https://login.microsoftonline.com/<TENANT_ID>/v2.0`. |
| JumpCloud | Issuer/client setup, `client_secret_basic` rather than default `client_secret_post`, and a stable explicit `AUTH_SECRET`. |
| Idira | Object-form provider ID, issuer, exact redirect URI and grants for intended application users. |
| GCP IAP | Protected endpoint plus signed-header JWT audience, not a normal OAuth callback flow. `AUTH_EE_GCP_IAP_ENABLED` defaults false; `AUTH_EE_GCP_IAP_AUDIENCE` is required for JIT provisioning. |

Scopes differ for identity, ingestion and write-capable review agents. Do not
merge their credentials or grant write scopes just to get login working.

## SCIM membership lifecycle

Paid SCIM 2.0 is enabled in Settings → Security; give the IdP the displayed base
URL and generated bearer token securely. SCIM controls membership, not SSO or
Owner promotion. While enabled, local membership administration is disabled;
role management remains in Sourcebot.

- New users are Members in Pending state. First sign-in/organization access
  activates membership and consumes a seat, subject to a hard seat cap.
- `active: false` suspends membership and revokes sessions, API keys and OAuth
  tokens. `active: true` returns it to Pending, not immediately Active.
- Supported attributes: email from `userName` or primary `emails`, name from
  `name.formatted` or fallback `displayName`, `active`, and `externalId`.
  Other attributes are ignored.
- The docs report testing with Okta, not every nominally compatible IdP.
  Okta OIDC SSO needs a separate provisioning-only SAML application for SCIM.
  Use `userName`, HTTP Header authentication, and the documented create/update/
  deactivate provisioning options; test lifecycle transitions with authorized
  test users before rollout.

## Repository ACL syncing

`PERMISSION_SYNC_ENABLED` defaults false and requires paid access, a code-host
connection and its corresponding external identity provider. Enforcement covers
search, navigation, file browsing, MCP and Ask/LLM context, including for Owners.

| Host | Documented coverage |
| --- | --- |
| GitHub Cloud / Enterprise Server | Read-or-higher direct, team, default-organization, outside-collaborator and owner access |
| GitLab Cloud / self-managed | Guest-or-higher direct/indirect membership; private-project enforcement; internal projects remain visible to all users |
| Bitbucket Cloud / Data Center | Partial repo-driven discovery: inherited group/project grants require user-driven syncing |
| Azure DevOps Cloud/Server, Gitea, Gerrit, generic Git | Not documented as supported for permission syncing |

User- and repo-driven intervals default to 24 hours. Repo-driven syncing can be
separately disabled with `PERMISSION_SYNC_REPO_DRIVEN_ENABLED=false`. Inherited
Bitbucket grants can lag until user-driven sync; assess a shorter
`userDrivenPermissionSyncIntervalMs` when required. Bitbucket Cloud account
deletion also has an upstream grace-period caveat. Refresh permissions through
Settings → Linked Accounts → Connected → Refresh Permissions when appropriate.
Existing users missing an OAuth access token after enabling syncing may need to
sign out/in or unlink/relink with the necessary scopes.

Provider authentication errors (including 401/403/410 or refresh failure) revoke
affected host access; rate limits and 5xx retain existing permissions. Distinguish
this sync behavior from a user-facing MCP license denial.

Per-connection `enforcePermissions` defaults to the global flag; global false
wins. `enforcePermissionsForPublicRepos=false` leaves public repositories visible
to all users; true, with enforcement active, requires a linked account for that
host. Public/private classification updates on **connection sync**, not ACL sync;
a visibility change may retain its prior treatment until that cycle completes.

The Bitbucket Data Center connection page asks for Repository Admin to discover
repo-level permissions; the ACL page says Repository Read. This is an unresolved
upstream conflict: verify the installed-version requirement before expanding
privileges. Validate allowed and denied repository access across actual consumer
surfaces; configuration and an Owner-only happy path do not prove enforcement.

## API-key restrictions

Both controls default false:
`DISABLE_API_KEY_CREATION_FOR_NON_OWNER_USERS` blocks creation only;
`DISABLE_API_KEY_USAGE_FOR_NON_OWNER_USERS` blocks both creation and use with 403.
See [REST](api.md) for separately entitled, one-hour repository-scoped tokens.

## Official sources

- [Authentication](https://docs.sourcebot.dev/docs/configuration/auth/authentication.md), [providers](https://docs.sourcebot.dev/docs/configuration/auth/providers.md), [FAQ](https://docs.sourcebot.dev/docs/configuration/auth/faq.md)
- [Access settings](https://docs.sourcebot.dev/docs/configuration/auth/access-settings.md), [roles](https://docs.sourcebot.dev/docs/configuration/auth/roles-and-permissions.md), [v5 role migration](https://docs.sourcebot.dev/docs/upgrade/v4-to-v5-guide.md)
- [External providers and schema](https://docs.sourcebot.dev/docs/configuration/idp.md), [SCIM](https://docs.sourcebot.dev/docs/configuration/auth/scim.md)
- [Permission syncing](https://docs.sourcebot.dev/docs/features/permission-syncing.md), [environment controls](https://docs.sourcebot.dev/docs/configuration/environment-variables.md)
