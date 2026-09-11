# MCP capability registry

The canonical registry is `servers.json`; `profiles.json` defines bounded
selections. This is a declaration of capabilities, not an activation list.

Connect a server only when a task needs it, using your host's documented MCP
command or config file. Preserve unrelated settings, keep credentials in
environment variables or a private host config, and never commit secret values.
Read such a config by field name instead of printing it: a credential echoed
into a transcript or command line is exposed even though the file is private
(`knowledge/playbooks/security-and-hardening/README.md`).
The `minimal` profile enables nothing. When a host enables or drops a declared
server, update `servers.json` and the table below in the same change — the host
config is private and local, this registry is not.

## Capabilities

| Server | Solves |
| --- | --- |
| `sourcebot` | Indexed cross-repository source retrieval |
| `context7` | Current library and framework documentation |
| `exa` | Web research when ordinary web access is insufficient |
| `mcp-steroid` | Language-aware local IDE integration where the host needs it |
| `paper`, `figma-bridge` | Design workflows, when relevant |
| `github` | Repository hosting and discovery: browse repositories outside the indexed corpus, inspect their source, issues, pull requests and commits, and perform GitHub operations |

Each remaining server covers a distinct problem. Do not add a second server for
a capability already listed, keep a declaration only because it was once
tried, or register an MCP server for something that is not an MCP server (a CLI
runner or transport is not a capability).

## Sourcebot

Sourcebot is the only persistent indexed cross-repository source system used by
this architecture. Its deployment, credentials, indexes, database and repository
configuration live outside this template. This repository describes when to use
it, not how it is deployed.

Sourcebot is retrieval, never reasoning: search it, read the decisive source and
tests, and let the coding agent interpret the evidence. Do not require it for
local work, and do not add a knowledge layer in front of it. No language model is
configured for it: its delegated `ask_codebase` agent duplicates the calling
agent's reasoning, so it is not part of this architecture.

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
`ide` (local IDE/LSP), `design` (Paper/Figma).
Profiles describe useful selections; they do not install or remove anything.
