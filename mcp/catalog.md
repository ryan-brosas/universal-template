# Shared MCP catalog (CLI-neutral)

CANONICAL REGISTRY: `servers.json` (relative to this directory)

The registry declares capabilities. It is not a default activation list and no
host is required to connect every entry.

## Rules

- Servers are declared ONCE, in the canonical registry; per-CLI host configs are
  derived copies written only when the user requests a specific server.
- To wire a server, use the host's own MCP command where one exists, otherwise
  edit its config file directly. `profiles.json` provides bounded selections; the
  `minimal` profile activates nothing. Back up a host config before its first
  write and preserve unrelated settings.
- Preserve unmanaged servers. Registry entries use env var **names**, never token
  values (`${EXA_API_KEY}`, `${CONTEXT7_API_KEY}`, `bearerTokenEnv`). Previews show
  names and actions, not config values. Exact local backups may contain existing
  credentials; keep them private and never publish them.
- Skip host shapes we haven't verified (Codex remote) instead of guessing.
- This file is a capability registry, not a mandatory "context plane": wire
  what a host actually needs; connected is not mandatory.
- **Veda is a CLI/runner, not an MCP server** — never add it to
  `servers.json`. Pi Fabric launches it via `agents.run({ runner: "veda" })`.
- **`pi-acp`** is the ACP transport into Pi — not an MCP server, and it
  carries no JetBrains PSI/Steroid semantics.
- **`mcp-steroid`** connects through `~/.mcp-steroid/bin/devrig mcp` (devrig
  launcher → JetBrains IDE; the launcher pins its own JDK).

## Current registry (`servers.json`)

| Server            | Kind  | Connection / command                                    | Key / env                        | Notes |
|-------------------|-------|---------------------------------------------------------|----------------------------------|-------|
| sourcebot         | remote| `http://localhost:3000/api/mcp`                    | API key in the host config (0600, machine-local, never here) | the only cross-repository code-context server; `ask_codebase` (delegated research) is model-gated and opt-in |
| context7          | stdio | `npx -y @upstash/context7-mcp@4.0.4`               | `CONTEXT7_API_KEY`               | library docs + code examples |
| exa               | stdio | `npx -y exa-mcp-server@3.4.1`                      | `EXA_API_KEY`                    | live web search |
| mcp-steroid       | stdio | `devrig mcp` (PATH-resolved)                  | none (local IDE bridge)          | JetBrains PSI/refactoring/test/debugger access via devrig |
| figma-bridge      | stdio | `npx -y @gethopp/figma-mcp-bridge@0.0.21`     | none                             | live Figma document bridge; requires the companion plugin in an open Figma file |
| paper             | remote| `http://127.0.0.1:29979/mcp`                 | none (local desktop app)         | Paper design canvas; available while Paper is running |

### Deliberately not registered (researched)

| Candidate | Status | Why it is not in the registry |
|---|---|---|
| **OpenDesign** (Open Design; the local-first design app with a stdio MCP exposing tokens CSS, JSX components, entry HTML; upstream `github.com/vustudio/opendesign`, same-name mirrors/forks such as `Wallstreetrenegade/opendesign` exist) | not configured | Its documented wiring bakes machine-local absolute paths (`node` binary + daemon `cli.js`) into per-client snippets, which violates the portability rule above, and the command only resolves while the desktop app is installed. Revisit when the user runs it: add a PATH-resolvable `command` block to `servers.json`, then wire per-CLI. Role boundary: design workspace and design context; never the canonical site crawler and never raw-site ground truth. |
| **Image generation** | capability, not an MCP server | On pi hosts it is the `openai_image` extension tool (pi-better-openai): generate or edit, with project-local save. Frontend media policy: `knowledge/playbooks/web-reference/references/media.md`. No model slug is frozen into policy. |

### Where the keys live (names only — never commit values)

These hosts already export or can export the needed vars; the `${VAR}` text in
`servers.json` is expanded by the host shell at launch:

| Var | Defined in |
|-----|------------|
| `EXA_API_KEY` | `~/.profile`, `~/.dsh/.env` |
| `CONTEXT7_API_KEY` | `~/.profile`, `~/.dsh/.env` |

## Scoped profiles

`profiles.json` defines `minimal` (none), four one-server profiles, and one
two-server design profile: `cross-repo-source`, `ide`, `docs`, `web-research`,
and `design` (selects `paper` and `figma-bridge`). The
indexed-source profile and the IDE profile are deliberately separate; there is
no ambiguous `code` compatibility alias. Profiles are explicit selections, not
always-on policy.

### Existing host configuration

Profiles describe useful selections; they do not manage installed servers or
remove anything. Selecting `minimal` does not clear an existing host config.
Inspect the host's current configuration before adding, changing, or removing
servers, and preserve unrelated entries.

### Write safety and recovery

This repository ships declarations and verified host shapes. It does not write
host configuration. Apply the selection yourself with the host's documented MCP
command where one exists, otherwise edit its config file directly: preview the
change, preserve unrelated settings and unmanaged servers, and back up the file
before its first write. A config, backup, or sidecar that may contain existing
credentials stays private and is never published.

Tool schemas add task context when activated. Measure the current host and
selected servers rather than treating historical schema sizes as a budget.

## Per-CLI wiring

| CLI | Host config | Block |
|-----|-------------|-------|
| pi | `~/.pi/agent/mcporter.json` | `mcpServers` (native; merge the requested server) |
| Claude Code | `~/.claude.json` | `mcpServers` (same shape) |
| Codex | `~/.codex/config.toml` | `[mcp_servers.<name>]` (stdio only) |
| OpenCode | `~/.config/opencode/opencode.json` | `mcp.<name>` (`type: local\|remote`, `enabled`) |
| DSH web profile | `~/.dsh/cordis.patch.yml` | `@monotykamary/dsh-mcp-client` inserts (sourcebot, context7, exa, mcp-steroid) |

Wire the requested selection using the host’s verified format; preserve unrelated
settings and unmanaged servers. A host config path names only where that CLI
reads servers: the canonical definitions stay in this repository’s
`servers.json` and `profiles.json`, and each host file is a local mirror or
overlay of the requested subset, never the registry itself. Each host has its own MCP command or config file;
this repository supplies no shared writer.

When unsure whether a CLI accepts a server scheme, skip that CLI (do not
write anything); report it as "not wired (unsupported)".

## Live wiring layers (machine-local)

The canonical registry fans out through per-CLI mirrors **and** machine-local
overlay files that this repo does not own — document them, never hand-edit
both sides blindly:

- `~/.pi/agent/mcporter.json` — pi's live native MCP config; `~/.pi/agent/fabric.json`
  sets `mcp.configPath` to it explicitly, so it is the only layer pi-fabric loads.
  Never regenerate the full registry by default.
- `~/.mcporter/mcporter.json` — MCPorter CLI layer, consulted only when no explicit
  `configPath`/`MCPORTER_CONFIG` is set (`$XDG_CONFIG_HOME/mcporter/mcporter.json[.jsonc]`
  first, then this path), followed by a project `<root>/config/mcporter.json`.
  Env values support `${VAR}` expansion — never store literal keys there; use env vars.
- `~/.prime/agent/settings.json` — scoped writes only: add one server or an
  explicit profile, never by regenerating the full registry.
- The IntelliJ **built-in** MCP server (`http://localhost:64442`) is a
  separate transport from mcp-steroid; it needs `JETBRAINS_MCP_TOKEN` exported
  or it fails auth (401) — wire the token or treat the entry as dormant.

## Host notes

- **pi**: servers.json mirrors into `~/.pi/agent/mcporter.json` `mcpServers`. For
  npx stdio servers the `${VAR}` placeholders are read from the shell env pi
  was launched with; ensure `EXA_API_KEY` / `CONTEXT7_API_KEY` are exported.
- **Claude Code / Codex / OpenCode**: same merge rule per host block; stdio
  entries use `command` + `args`; secrets stay env-only.
- **sourcebot**: remote MCP at the local Sourcebot deployment
  (`http://localhost:3000/api/mcp`, bound to loopback). It is the primary
  capability for cross-repository code questions
  (`knowledge/playbooks/cross-repo-source/README.md`); no second code-graph
  server belongs in the registry.
  Deployment and corpus live outside this repository (on this machine:
  `~/sourcebot/` — `compose.yaml`, `config.json`, `.env`); the
  index, cloned repositories and database are Docker volumes there. The corpus is
  a deliberate explicit repository list in that `config.json`; the connection is
  GitHub public read-only, so it can only ever read public repositories. MCP
  authentication uses a Sourcebot API key held in the machine-local host config
  (0600), never here; the deployment's `.env` is the only other place a secret
  may live. No language model is configured, so ask-style summarization stays
  unavailable on purpose: the agent retrieves evidence and reasons itself.
  If the deployment is not running the entry is dormant; treat indexed source as
  optional context, never a blocker.
- **figma-bridge**: run the companion Figma plugin in each file the agent should
  access; the stdio server brokers those live plugin connections.
- **paper**: Paper exposes its local Streamable HTTP endpoint while the desktop
  app is running; a stopped app makes the registry entry dormant.
