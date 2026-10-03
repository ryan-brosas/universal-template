# MCP capability registry

The canonical registry is `servers.json`; `profiles.json` defines bounded
selections. This is a declaration of capabilities, not an activation list.

Connect a server only when a task needs it, using your host's documented MCP
command or config file. Preserve unrelated settings, keep credentials in
environment variables or a private host config, and never commit secret values.
Read such a config by field name instead of printing it: a credential echoed
into a transcript or command line is exposed even though the file is private
(`knowledge/playbooks/security-and-hardening/README.md`).
The `minimal` profile enables nothing. Keep capability additions/removals in
`servers.json` and the table below consistent. Project activation belongs in
host configuration, not in this registry.

## Capabilities

| Server | Solves |
| --- | --- |
| `sourcebot` | Indexed cross-repository source retrieval |
| `context7` | Current library and framework documentation |
| `exa` | Web research when ordinary web access is insufficient |
| `beacon` | Default browser UI reading and interaction through the user's approved, connected browser session |
| `mcp-steroid` | Opt-in JetBrains semantic navigation, refactoring, inspections and debugging; disabled by default |
| `paper`, `figma-bridge`, `figma-console` | Design workflows, when relevant |
| `github` | Repository hosting and discovery: browse repositories outside the indexed corpus, inspect their source, issues, pull requests and commits, and perform GitHub operations |

Each remaining server covers a distinct problem. Do not add a second server for
a capability already listed, keep a declaration only because it was once
tried, or register an MCP server for something that is not an MCP server (a CLI
runner or transport is not a capability).

Figma appears twice because the two servers sit on different planes.
`figma-bridge` reads the document currently open in the desktop app through a
local plugin. `figma-console` owns published-library components and variables,
token import/export and console telemetry, reaching them over the Figma REST API
with its own access token; its live-document tools need the desktop plugin from
`~/.figma-console-mcp/plugin/manifest.json`. Neither replaces the other, and a
third Figma server would still need its own reason.

## Optional IDE integration

Steroid is disabled by default, including in `servers.json`. The `ide` profile
identifies the capability; it does not enable it. Keep it installed only where
useful and opt in for projects or tasks that need IDE semantics. Local source,
compiler/linter checks and tests remain the default verification path.

With Pi's MCP adapter, retain the global server definition with `disabled: true`.
From a chosen project's root, run `/mcp enable mcp-steroid`, then `/reload`. The
command writes only the project override in `.pi/mcp.json`, inheriting the global
transport without copying credentials. `/mcp disable mcp-steroid` and `/reload`
turn it off again for that project. Other hosts use their documented project
configuration. See the [Steroid procedure](../knowledge/playbooks/mcp-steroid/README.md)
for scoped use; enabling the tool does not make it a required PR check.

## Browser automation

Use the configured browser MCP, currently Beacon, for ordinary browser UI work. The
[Beacon playbook](../knowledge/playbooks/beacon/README.md) owns target verification,
batched actions, authentication boundaries and failure recovery. Discover live tool
schemas; a registry entry does not prove a connected browser or successful input.
Credentials and extension pairing remain in private host configuration.

Keep [CDP](../knowledge/playbooks/cdp/README.md) for explicit protocol work or a named
capability/approved-connection gap: screenshots, DOM/runtime inspection, tracing,
emulation, file inputs or media capture. CDP helpers are not MCP tools and must not
be mechanically renamed as such. Neither transport changes send approval or the
approved browser profile. Plain HTTP and search tools still own simpler reads.

## Sourcebot

Sourcebot is the only persistent indexed cross-repository source system used by
this architecture. Its deployment, credentials, indexes, database and repository
configuration live outside this template. This repository describes when to use
it, not how it is deployed.

Sourcebot supports direct indexed retrieval and delegated investigation through
`ask_codebase`, with no second knowledge layer in front of it. Enabled lanes and
plan/licence limits are deployment facts: report a gated capability and use only
an authorized, documented fallback. These standing
instructions and the `prompts/` adapters name the tool, so its explicit-request
gate is already satisfied. Naming it satisfies that gate without making the call
mandatory per session or phase: applicability belongs to the task. Use it for broad
unresolved codebase questions when indexed coverage can inform the decision, and
keep known local questions direct; the coding agent still owns decisions, edits and
verification against the live working tree. How to scope and bound a request,
revision caveats and fallback reporting belong to the
[cross-repository source playbook](../knowledge/playbooks/cross-repo-source/README.md).
Language-model configuration and tool-description restrictions belong to the
host/deployment.

## Repository hosting

GitHub is a separate capability from Sourcebot's index. Sourcebot answers "search
the repositories we intentionally indexed"; GitHub answers "what repository should
I look at", "what exists outside that corpus", "show me this repository's source",
"what issues, pull requests or commits are relevant" and performs repository
operations. Read GitHub evidence directly instead of ingesting repositories into
Sourcebot: admission to the corpus is a deliberate, repeated-need decision, not a
side effect of reading one repository. On this host the GitHub server
authenticates with a bearer token in the private host config (MCPorter
`bearerToken`); the declaration in this repository carries no secret.

## Profiles

`profiles.json` groups selections by capability rather than by historical
tooling: `minimal` (nothing), `cross-repo-source` (Sourcebot),
`repository-host` (GitHub), `docs` (Context7), `web-research` (Exa),
`browser` (Beacon), `ide` (local IDE/LSP), `design` (Paper/Figma).
Profiles describe useful selections; they do not install or remove anything.
