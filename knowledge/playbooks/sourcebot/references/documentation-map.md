# Documentation coverage map

Reviewed against the official [documentation index](https://docs.sourcebot.dev/llms.txt)
on **2026-09-27**: **79 indexed documentation entries plus one OpenAPI specification**.
Every entry is mapped below. Content was read across five disjoint topic audits;
byte-identical aliases were verified, the Helm redirect was followed to its
official chart README, and the feature-request redirect was classified as
navigation-only. Generated schemas were inspected, not copied wholesale into
this skill. The downloaded OpenAPI identifies itself as **v5.1.14**.

This is a complete accounting of that index snapshot, not a claim to have tested
every feature, deployment combination or future release. Sourcebot runtime/API,
SSO, provider, webhook and migration checks were **not** performed. Read the
linked version-matched schema for exact types/enums and fetch the index again
when updating the skill. Outbound destinations and plan limits remain deployment
facts. No remote skill or deployment was created by this documentation work.

## Product and AI features — 17 entries

| Official source | Local procedure / disposition |
| --- | --- |
| [Overview](https://docs.sourcebot.dev/docs/overview.md) | [Entry point](../README.md); product and data-flow boundaries |
| [Code Search](https://docs.sourcebot.dev/docs/features/search/code-search.md) | [Search](search.md) |
| [Writing search queries](https://docs.sourcebot.dev/docs/features/search/syntax-reference.md) | [Search](search.md) |
| [AI Search Assist](https://docs.sourcebot.dev/docs/features/search/ai-search-assist.md) | [Search](search.md) |
| [Multiple branches and tags](https://docs.sourcebot.dev/docs/features/search/multi-branch-indexing.md) | [Search](search.md); revision limits and syntax conflict |
| [Search contexts](https://docs.sourcebot.dev/docs/features/search/search-contexts.md) | [Search](search.md); repo/connection/topic grouping |
| [Ask Sourcebot](https://docs.sourcebot.dev/docs/features/ask/ask-sourcebot.md) | [Ask/models](ask-models-and-agents.md) |
| [Skills](https://docs.sourcebot.dev/docs/features/ask/skills.md) | [Native skills](native-skills.md) |
| [Connectors](https://docs.sourcebot.dev/docs/features/ask/connectors.md) | [Ask connectors](ask-models-and-agents.md) |
| [Chat Sharing](https://docs.sourcebot.dev/docs/features/ask/chat-sharing.md) | [Ask sharing](ask-models-and-agents.md) |
| [Configure Language Models](https://docs.sourcebot.dev/docs/features/ask/add-model-providers.md) | [Models](ask-models-and-agents.md); verified byte-identical alias of the configuration page below |
| [Sourcebot MCP server](https://docs.sourcebot.dev/docs/features/mcp-server.md) | [MCP](setup-and-access.md) and [native skills](native-skills.md) |
| [Code navigation](https://docs.sourcebot.dev/docs/features/code-navigation.md) | [Search](search.md); heuristic resolution |
| [Analytics](https://docs.sourcebot.dev/docs/features/analytics.md) | [Operations](configuration-and-operations.md); audit dependency |
| [Agents](https://docs.sourcebot.dev/docs/features/agents/agents.md) | [Ask/agents](ask-models-and-agents.md); experimental warning and review-agent navigation |
| [AI Code Review Agent](https://docs.sourcebot.dev/docs/features/agents/review-agent.md) | [Review agents](ask-models-and-agents.md) |
| [Language Model Providers](https://docs.sourcebot.dev/docs/configuration/language-model-providers.md) | [All 12 model variants](ask-models-and-agents.md); schema and provider-specific controls |

## Code-host connections — 12 entries

| Official source | Local procedure / disposition |
| --- | --- |
| [Indexing your code](https://docs.sourcebot.dev/docs/connections/indexing-your-code.md) | [Connections](connections.md), [configuration](configuration-and-operations.md); lifecycle, limits and full embedded config schema |
| [GitHub](https://docs.sourcebot.dev/docs/connections/github.md) | [Connections](connections.md) |
| [GitLab](https://docs.sourcebot.dev/docs/connections/gitlab.md) | [Connections](connections.md) |
| [Bitbucket Cloud](https://docs.sourcebot.dev/docs/connections/bitbucket-cloud.md) | [Connections](connections.md) |
| [Bitbucket Data Center](https://docs.sourcebot.dev/docs/connections/bitbucket-data-center.md) | [Connections](connections.md); ACL scope conflict |
| [Azure DevOps Cloud](https://docs.sourcebot.dev/docs/connections/ado-cloud.md) | [Connections](connections.md) |
| [Azure DevOps Server](https://docs.sourcebot.dev/docs/connections/ado-server.md) | [Connections](connections.md) |
| [Gitea](https://docs.sourcebot.dev/docs/connections/gitea.md) | [Connections](connections.md) |
| [Gerrit](https://docs.sourcebot.dev/docs/connections/gerrit.md) | [Connections](connections.md) |
| [Other Git hosts](https://docs.sourcebot.dev/docs/connections/generic-git-host.md) | [Connections](connections.md); remote/local protocol distinction |
| [Local Git repositories](https://docs.sourcebot.dev/docs/connections/local-repos.md) | [Connections](connections.md); read-only mounts and operator-owned freshness |
| [Request another code host](https://docs.sourcebot.dev/docs/connections/request-new.md) | Navigation-only redirect to GitHub's feature-request issue form, login-gated; no hidden setup content or authorized form submission |

## Deployment, configuration and operations — 16 entries

| Official source | Local procedure / disposition |
| --- | --- |
| [Deploy Sourcebot](https://docs.sourcebot.dev/docs/deployment/deploy-sourcebot.md) | [Deployment](deployment-and-upgrades.md); options navigation |
| [Docker Compose](https://docs.sourcebot.dev/docs/deployment/docker-compose.md) | [Deployment](deployment-and-upgrades.md) |
| [Kubernetes / Helm](https://docs.sourcebot.dev/docs/deployment/k8s.md) | Redirect resolved through the [official chart README](https://github.com/sourcebot-dev/sourcebot-helm-chart); [deployment](deployment-and-upgrades.md). GitHub navigation HTML is not documentation content. |
| [Config File](https://docs.sourcebot.dev/docs/configuration/config-file.md) | [Configuration](configuration-and-operations.md) |
| [Environment variables](https://docs.sourcebot.dev/docs/configuration/environment-variables.md) | [Operations](configuration-and-operations.md), [identity](identity-and-permissions.md), [administration](administration-and-licensing.md), [review agents](ask-models-and-agents.md) |
| [Structured Logging](https://docs.sourcebot.dev/docs/configuration/structured-logging.md) | [Operations](configuration-and-operations.md) |
| [Architecture](https://docs.sourcebot.dev/docs/misc/architecture.md) | [Deployment](deployment-and-upgrades.md); verified byte-identical alias of infrastructure architecture |
| [Scalability](https://docs.sourcebot.dev/docs/misc/scalability.md) | [Deployment](deployment-and-upgrades.md); vertical scaling |
| [Telemetry](https://docs.sourcebot.dev/docs/misc/telemetry.md) | [Operations](configuration-and-operations.md) |
| [Service Ping](https://docs.sourcebot.dev/docs/misc/service-ping.md) | [Operations](configuration-and-operations.md), [licensing](administration-and-licensing.md) |
| [Sizing Guide](https://docs.sourcebot.dev/docs/deployment/sizing-guide.md) | [Deployment](deployment-and-upgrades.md), [audit storage](administration-and-licensing.md) |
| [Architecture Overview](https://docs.sourcebot.dev/docs/deployment/infrastructure/architecture.md) | [Deployment](deployment-and-upgrades.md); qualify embedded-service language for v5 |
| [Redis](https://docs.sourcebot.dev/docs/deployment/infrastructure/redis.md) | [Operations](configuration-and-operations.md); queues and TLS |
| [V4 to V5 Guide](https://docs.sourcebot.dev/docs/upgrade/v4-to-v5-guide.md) | [Upgrades](deployment-and-upgrades.md); role, license, database, secret and SSO changes |
| [V3 to V4 Guide](https://docs.sourcebot.dev/docs/upgrade/v3-to-v4-guide.md) | [Upgrades](deployment-and-upgrades.md); authentication/tenancy |
| [V2 to V3 Guide](https://docs.sourcebot.dev/docs/upgrade/v2-to-v3-guide.md) | [Upgrades](deployment-and-upgrades.md); historical config/reindex boundary |

## Identity and administration — 13 entries

| Official source | Local procedure / disposition |
| --- | --- |
| [Permission syncing](https://docs.sourcebot.dev/docs/features/permission-syncing.md) | [Identity](identity-and-permissions.md); scope, partial coverage, revocation and sync timing |
| [External Identity Providers](https://docs.sourcebot.dev/docs/configuration/idp.md) | [Identity](identity-and-permissions.md); all provider variants and callback IDs |
| [Authentication](https://docs.sourcebot.dev/docs/configuration/auth/authentication.md) | [Identity](identity-and-permissions.md) |
| [Providers](https://docs.sourcebot.dev/docs/configuration/auth/providers.md) | [Identity](identity-and-permissions.md) |
| [SCIM](https://docs.sourcebot.dev/docs/configuration/auth/scim.md) | [Identity](identity-and-permissions.md) |
| [Access Settings](https://docs.sourcebot.dev/docs/configuration/auth/access-settings.md) | [Identity](identity-and-permissions.md) |
| [Members and roles](https://docs.sourcebot.dev/docs/configuration/auth/roles-and-permissions.md) | [Identity](identity-and-permissions.md); v5 migration qualification |
| [FAQ](https://docs.sourcebot.dev/docs/configuration/auth/faq.md) | [Identity](identity-and-permissions.md); auth/anonymous and proxy distinctions |
| [Transactional Email](https://docs.sourcebot.dev/docs/configuration/transactional-emails.md) | [Administration](administration-and-licensing.md) |
| [Audit Logs](https://docs.sourcebot.dev/docs/configuration/audit-logs.md) | [Administration](administration-and-licensing.md); records, actions, retention |
| [Activating a Subscription](https://docs.sourcebot.dev/docs/activating-a-subscription.md) | [Licensing](administration-and-licensing.md) |
| [Seat Reconciliation](https://docs.sourcebot.dev/docs/seat-reconciliation.md) | [Licensing](administration-and-licensing.md) |
| [Free Trial](https://docs.sourcebot.dev/docs/free-trial.md) | [Licensing](administration-and-licensing.md) |

## REST API and OpenAPI

All 22 entries below map to [the REST procedure](api.md), with search syntax in
[Search](search.md). They comprise authentication, 20 operation pages and the
complete OpenAPI contract. The published specification is not a live-server test.

| Official source | Distinct contract |
| --- | --- |
| [Authentication](https://docs.sourcebot.dev/docs/api-reference/authentication.md) | Keys, scopes and one-time credentials |
| [Search code](https://docs.sourcebot.dev/api-reference/search-&-navigation/search-code.md) | Blocking search, limits and exhaustive-result flag |
| [Find symbol definitions](https://docs.sourcebot.dev/api-reference/search-&-navigation/find-symbol-definitions.md) | Definition request and ranges |
| [Find symbol references](https://docs.sourcebot.dev/api-reference/search-&-navigation/find-symbol-references.md) | Reference request and ranges |
| [List repositories](https://docs.sourcebot.dev/api-reference/repositories/list-repositories.md) | Visibility, filters, pagination and `repoId` |
| [List connections](https://docs.sourcebot.dev/api-reference/connections/list-connections.md) | Visible connection metadata, no secrets |
| [Create a scoped access token](https://docs.sourcebot.dev/api-reference/scoped-access-tokens/create-a-scoped-access-token.md) | Custom entitlement, exact one-hour lifecycle |
| [Revoke a scoped access token](https://docs.sourcebot.dev/api-reference/scoped-access-tokens/revoke-a-scoped-access-token.md) | Creator-only revocation |
| [Get commit details](https://docs.sourcebot.dev/api-reference/git/get-commit-details.md) | Commit and parents |
| [Get diff between two commits](https://docs.sourcebot.dev/api-reference/git/get-diff-between-two-commits.md) | Two-dot structured diff |
| [List commits](https://docs.sourcebot.dev/api-reference/git/list-commits.md) | History filters, BRE semantics and pagination |
| [List commit authors](https://docs.sourcebot.dev/api-reference/git/list-commit-authors.md) | Author counts and pagination |
| [Get file contents](https://docs.sourcebot.dev/api-reference/git/get-file-contents.md) | Raw source and optional ref |
| [Get file blame](https://docs.sourcebot.dev/api-reference/git/get-file-blame.md) | Ordered line ranges, rename/history limits |
| [Get a file tree](https://docs.sourcebot.dev/api-reference/git/get-a-file-tree.md) | Required revision and path list |
| [Get a user](https://docs.sourcebot.dev/api-reference/enterprise-ee/get-a-user.md) | Owner-only membership lookup |
| [Remove a user](https://docs.sourcebot.dev/api-reference/enterprise-ee/remove-a-user-from-the-organization.md) | Access/session revocation, last-owner/SCIM restrictions |
| [List users](https://docs.sourcebot.dev/api-reference/enterprise-ee/list-users.md) | Owner-only membership inventory |
| [List audit records](https://docs.sourcebot.dev/api-reference/enterprise-ee/list-audit-records.md) | Owner-only time/pagination filters |
| [Get Sourcebot version](https://docs.sourcebot.dev/api-reference/system/get-sourcebot-version.md) | Running-version evidence |
| [Health check](https://docs.sourcebot.dev/api-reference/system/health-check.md) | Service health, not integration proof |
| [OpenAPI specification](https://docs.sourcebot.dev/api-reference/sourcebot-public.openapi.json) | All 20 operations; request/response/error schemas and security alternatives |

## Optional index destinations

The [changelog](https://sourcebot.dev/changelog) and
[roadmap](https://github.com/sourcebot-dev/sourcebot/issues/459) were inspected as
release/planning context. They are not substitutes for current feature docs:
roadmap items can remain listed after implementation, and historical plan labels
can differ. The [support link](https://github.com/sourcebot-dev/sourcebot/issues/new?template=get_help.md)
opens a login-gated issue form; it is a navigation destination, not another
hidden feature guide. No issue was submitted.

## Source conflicts retained rather than guessed away

The owning references identify query `rev:` semantics and revision-limit wording;
`context` versus `contexts` and paid/Enterprise labels; Bitbucket Data Center ACL
scopes; free-plan roles versus migrated Members; embedded services versus v5;
remote HTTP(S) versus local Git; deprecated settings still in prose tables;
review-agent App/client IDs, model configuration and logging defaults; REST `id`
versus `repoId`; malformed illustrative JSON and audit-example/schema differences.
Use the installed release, exact schema and focused runtime evidence to resolve
a task-critical conflict. This skill does not manufacture certainty where the
documentation disagrees.
