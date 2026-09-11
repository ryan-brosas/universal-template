# MCP capability registry

The canonical registry is `servers.json`; `profiles.json` defines bounded
selections. This is a declaration of capabilities, not an activation list.

Connect a server only when a task needs it, using your host's documented MCP
command or config file. Preserve unrelated settings, keep credentials in
environment variables or a private host config, and never commit secret values.
Read such a config by field name instead of printing it: a credential echoed
into a transcript or command line is exposed even though the file is private
(`knowledge/playbooks/security-and-hardening/README.md`).
The `minimal` profile enables nothing.

## Capabilities

| Server | Solves |
| --- | --- |
| `sourcebot` | Indexed cross-repository source retrieval |
| `context7` | Current library and framework documentation |
| `exa` | Web research when ordinary web access is insufficient |
| `mcp-steroid` | Language-aware local IDE integration where the host needs it |
| `paper`, `figma-bridge` | Design workflows, when relevant |
| `github` | Repository hosting: code browsing, issues and pull requests |

Each remaining server covers a distinct problem. Do not add a second server for
a capability already listed, keep a declaration only because it was once
tried, or register an MCP server for something that is not an MCP server (a CLI
runner or transport is not a capability).

## Sourcebot

Sourcebot is the only persistent indexed cross-repository source system used by
this architecture. Its deployment, credentials, indexes, database and repository
configuration live outside this template. This repository describes when to use
it, not how it is deployed.

Sourcebot is retrieval first: search it, read the decisive source and tests, and
let the coding agent reason. Do not require it for local work, and do not add a
knowledge layer in front of it.

The deployment configures one language model — the OmniRoute `top-tool` combo —
for delegated research only. `ask_codebase` is opt-in and runs only when the
user's prompt asks for it by name, since retrieval and reasoning otherwise stay
with the calling agent. Assignment and evidence contract:
`knowledge/playbooks/cross-repo-source/references/research-brief.md`.

## Profiles

`profiles.json` groups selections by capability rather than by historical
tooling: `minimal`, `cross-repo-source`, `ide`, `docs`, `web-research`, `design`.
Profiles describe useful selections; they do not install or remove anything.
