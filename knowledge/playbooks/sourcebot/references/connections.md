# Code-host connections and local Git

A connection is a named relationship to a code host, not an Ask MCP connector or
an SSO identity provider. Use the installed-version schema. Preserve the approved
corpus; adding an organization or `all` can ingest much more code than a single
repository request authorizes.

## Host-selection and credential matrix

The links in this table are the canonical host-specific setup references.
Credentials must be supplied to Sourcebot's runtime through secret references.
Scopes below concern ingestion unless explicitly identified as ACL syncing.

| Host | Discovery / addressing | Authentication and constraints |
| --- | --- | --- |
| [GitHub](https://docs.sourcebot.dev/docs/connections/github.md) | `repos` as `owner/repo`, `orgs`, `users`, topic globs; optional custom `url` | Fine-grained PAT: Contents/Metadata read for selected repos; classic PAT: `repo`. Paid GitHub App path uses an `apps` entry and installation scope, with Contents/Metadata read, organization Members read and account Email addresses read. |
| [GitLab](https://docs.sourcebot.dev/docs/connections/gitlab.md) | Fully namespaced `projects`, recursive `groups`, `users`, topics; `all` only for a self-managed custom `url`; `webUrl` may differ | Private-project PAT needs `read_api`; selectors include nested subgroups. Do not treat GitLab.com as a supported all-project crawl. |
| [Bitbucket Cloud](https://docs.sourcebot.dev/docs/connections/bitbucket-cloud.md) | `repos` as `workspace/repo`, `workspaces`, `projects`; `all` ignored | API tokens: `read:repository:bitbucket`, `read:workspace:bitbucket`; `user` is account email and `gitUser` is clone username. Repo/project/workspace access tokens are alternatives. App passwords are deprecated. |
| [Bitbucket Data Center](https://docs.sourcebot.dev/docs/connections/bitbucket-data-center.md) | Required server `url`; project/repo names, project keys, or `all` | HTTP tokens can be user-, project- or repo-scoped; user tokens also need `user`. Ordinary ingestion needs Project/Repository read. ACL-token scope conflict is discussed below. |
| [Azure DevOps Cloud](https://docs.sourcebot.dev/docs/connections/ado-cloud.md) | `deploymentType: "cloud"`; `orgs`, `projects` as `org/project`, `repos` as `org/project/repo` | Required PAT with Code/Read; token visibility bounds discovery. |
| [Azure DevOps Server](https://docs.sourcebot.dev/docs/connections/ado-server.md) | `deploymentType: "server"`, server `url`; `orgs` are collections; collection/project/repo addressing | Required PAT with Code/Read; `useTfsPath: true` accommodates legacy `/tfs` installations. |
| [Gitea](https://docs.sourcebot.dev/docs/connections/gitea.md) | `repos`, `orgs`, `users`; optional custom `url` (default `https://gitea.com`) | `read:repository`, plus `read:user` / `read:organization` for those discovery selectors. |
| [Gerrit](https://docs.sourcebot.dev/docs/connections/gerrit.md) | Host `url`, project globs; omitted projects select all | Authentication is not currently supported. Scope explicitly to avoid an accidental all-project corpus. |
| [Generic Git](https://docs.sourcebot.dev/docs/connections/generic-git-host.md) | `type: "git"`, required clone `url` | Remote-host prose supports HTTP(S). The same schema also supports local `file://`; do not infer undocumented SSH support. |
| [Local Git](https://docs.sourcebot.dev/docs/connections/local-repos.md) | `type: "git"`, `file:///absolute/container/path` or path globs | Mount read-only. Each matched directory must itself be a Git repository and have `remote.origin.url`; otherwise it is skipped. Sourcebot does not fetch or write it. |

## Narrow ingestion and revisions

Host-specific exclusion fields differ:

- GitHub: forks, archives, repository/topic globs and inclusive min/max repository
  size in bytes. GitHub's reported size need not equal the clone's disk use.
- GitLab: forks, archives, user-owned projects, project/topic globs.
- Gitea: forks, archives and repository globs.
- Bitbucket: forks, archives and repository exclusions. Some examples use globs
  where schema descriptions say specific repos; verify intended matching.
- Azure: disabled repos, repository/project globs and inclusive byte-size limits.
- Gerrit: project globs and READ_ONLY/HIDDEN projects.

Exclusion booleans default false. `revisions.branches` and `revisions.tags` accept
remote-name globs in addition to default HEAD. The docs describe 64-revision
limits inconsistently as combined and per-kind; avoid relying on the boundary
without checking the deployed version. Query filters do not add indexed branches.
See [search](search.md) for `rev:` semantics.

First discovery and subsequent connection sync queue fetch/index work; inspect
job status, then find and read a known file at the intended revision. Connection
visibility sync, code reindexing and permission syncing are distinct clocks.
For local read-only checkouts the operator must update Git history; Sourcebot
cannot make them current. If large local history needs a commit graph, an
operator can prepare `git commit-graph write --reachable` and maintain it with
`git fetch --write-commit-graph`; do not mutate a mounted checkout as a search step.

## Failures and security distinctions

A miss may mean selector exclusion, queued indexing, an unindexed revision,
limited token visibility, a skipped file or ACL enforcement. Files over 2 MB or
20,000 trigrams are skipped by default; inspect `lang:skipped`. Binary files are
not indexable. Tune limits only with a justified ingestion requirement.

For GitLab `GitbeakerTimeoutError`, investigate workload and
`GITLAB_CLIENT_QUERY_TIMEOUT_SECONDS`. GitLab/Bitbucket `TypeError: fetch failed`
can mean an untrusted CA; prefer `NODE_EXTRA_CA_CERTS`, not
`NODE_TLS_REJECT_UNAUTHORIZED=0`. Bitbucket Data Center 429 responses require
coordination with its administrator on rate limits/service-account allowances.

Connection credentials are not proof of per-user ACL enforcement. See
[identity and permissions](identity-and-permissions.md) for supported hosts and
`enforcePermissions` / `enforcePermissionsForPublicRepos` behavior.
**Bitbucket Data Center docs conflict:** the connection guide requires Repository
Admin for repo-driven ACL discovery, while the permission-sync guide says
Repository Read. Verify the relevant installed-version API requirement before
changing privileges; do not silently choose broader permissions.

Some Azure and historical migration examples contain invalid punctuation; many
other examples use comments. Validate the actual intended configuration against
the release schema instead of blindly copying snippets. The
[request-another-host entry](https://docs.sourcebot.dev/docs/connections/request-new.md)
is a feature-request issue-form redirect, not a connector or a granted write.

## Indexing source

[Connection lifecycle and complete configuration schema](https://docs.sourcebot.dev/docs/connections/indexing-your-code.md).
Operational controls live in [configuration and operations](configuration-and-operations.md),
not separate duplicated settings lists for every host.
