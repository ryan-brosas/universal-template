# Setup, MCP access and capability diagnosis

Establish the intended deployment and installed version first. Endpoints, secrets,
repository inventory and known plan limits belong to host configuration, not this
reusable skill. For infrastructure use [deployment](deployment-and-upgrades.md);
for code hosts use [connections](connections.md); for SSO/ACLs use
[identity](identity-and-permissions.md). A working web search is not proof that
Ask has a model or MCP is entitled.

## Connect an external agent

Sourcebot MCP uses **Streamable HTTP** at `<instance>/api/mcp`. Settings → MCP
provides the URL and installation aids. In current v5 docs MCP is paid. OAuth is
preferred where supported, including dynamic client registration. API keys from
Settings → API Keys use `Authorization: Bearer <key>`. OAuth access/refresh tokens
default to one hour/90 days. Requests inherit the user's role and repository
permissions. Anonymous access is an instance policy, not a workaround to enable
when authentication fails.

The official examples cover Claude Code, Cursor, VS Code, Codex, OpenCode and
Windsurf. Their URL/header/config formats differ; use the client's current docs
and approved credential handling rather than copying another client's snippet.
Do not expose keys in shared files or tool output.

## Select a documented tool

Discover **live schemas** before use; this inventory is not an argument contract.

| Tools | Use and consequential limit |
| --- | --- |
| `list_repos` | Exact corpus discovery with a name filter; paged, documented default 30/max 100. Returned items alone do not establish total corpus size. |
| `list_branches` | Branch/ref metadata from Sourcebot's local snapshot, including `isDefault`/`isIndexed`; not a live code-host check or proof that shards match HEAD. |
| `list_tree`, `glob` | Tree orientation versus file-path glob; tree depth 1–10, default 1; entry cap default 1,000/max 10,000. |
| `grep` | Always case-sensitive regex; default 100 matching files. Scope repository, ref and include glob separately from the pattern. |
| `read_file` | Read decisive source; 1-indexed offset, maximum 500 lines per call. |
| `find_symbol_definitions`, `find_symbol_references` | Repository-scoped, search-based symbol navigation; verify semantic identity. |
| `list_commits`, `get_diff` | History filters and two-dot ref comparison, not a merge-base PR diff. |
| `list_language_models`, `ask_codebase` | Discover configured models, then delegate one bounded question. Omitted model selects the first configured model; omitted repos can expose the whole accessible corpus to the agent. |
| `create_skill`, `update_skill`, `list_skills` | [Native Ask skills](native-skills.md); authenticated user and Ask entitlement required, not anonymous or scoped-token access. |

Where a tool supports refs, pin the intended one rather than mixing defaults.
`ask_codebase` defaults to PRIVATE for authenticated users and PUBLIC for anonymous
users; explicitly preserve privacy. Its request gate, scoping, blocking-call
budget and timeout recovery belong to
[the canonical research workflow](../../cross-repo-source/README.md).

## Diagnose by boundary

| Symptom | Next distinction |
| --- | --- |
| 401 | Missing/expired/invalid authentication; inspect without printing credentials |
| 403 | Role, repository authorization, API-key policy or entitlement; read the actual error and stop blind retries |
| Repo missing | Corpus coverage, permissions, pending sync or pagination |
| Search works, Ask fails | Model/provider configuration, Ask entitlement or streaming connection |
| Stream/tool timeout | Proxy/load-balancer versus client/tool deadline; cancellation does not prove server work stopped |
| Search/read disagreement | Ref mismatch or indexing transition; prove current behavior from current source |

REST is a separate [documented API](api.md) and may remain authorized when MCP
is unavailable. Verify endpoint/version/permissions; do not invent alternate
routes to evade a paid-feature denial. Report REST retrieval as retrieval, not
an `ask_codebase` investigation.

Verify connection success with a scoped repository lookup and known-file read.
Verify Ask separately with checked citations when entitled. Tool discovery and
transport connection alone do not prove either.

## Official source

[Sourcebot MCP setup, clients, authorization and tools](https://docs.sourcebot.dev/docs/features/mcp-server.md).
