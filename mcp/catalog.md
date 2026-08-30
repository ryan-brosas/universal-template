# Shared MCP catalog (CLI-neutral)

CANONICAL SOURCE OF TRUTH: `~/.agents/mcp/servers.json`

`~/.agents` is the global settings area every CLI reads — skills
(`~/.agents/skills`), templates (`~/.agents/templates`), essentials
(`~/.agents/essentials`) and the MCP registry (`~/.agents/mcp/servers.json`).

## Rules

- Servers are declared ONCE, in the canonical registry; per-CLI host configs are
  derived copies written only when the user requests a specific server.
- To wire a server: copy that server's block from `servers.json` into the target
  CLI's own config (see per-CLI wiring below), one server at a time.
- Never touch servers you didn't request. Never store token **values** anywhere —
  only env var **names** (`${EXA_API_KEY}`, `${CONTEXT7_API_KEY}`, `bearerTokenEnv`).
  The actual key values live only in shell env / a daemon env file.
- Skip host shapes we haven't verified (Codex remote) instead of guessing.
- This file is a capability registry, not a mandatory "context plane": wire
  what a host actually needs; connected is not mandatory.
- **Veda is a CLI/runner, not an MCP server** — never add it to
  `servers.json`. Pi Fabric launches it via `agents.run({ runner: "veda" })`.
- **`pi-acp`** is the ACP transport into Pi — not an MCP server, and it
  carries no JetBrains PSI/Steroid semantics.
- **`mcp-steroid`** connects through `~/.mcp-steroid/bin/devrig mcp` (devrig
  launcher → JetBrains IDE; the launcher pins its own JDK).

## Current registry (`~/.agents/mcp/servers.json`)

| Server            | Kind  | Connection / command                                    | Key / env                        | Notes |
|-------------------|-------|---------------------------------------------------------|----------------------------------|-------|
| codebase-memory   | stdio | `codebase-memory-mcp` (PATH-resolved; mise shim)         | `CBM_CACHE_DIR` (machine-local)  | local graph, keep-alive |
| context7          | stdio | `npx -y @upstash/context7-mcp`               | `CONTEXT7_API_KEY`               | library docs + code examples |
| deepwiki          | stdio | `npx -y deepwiki-mcp`                        | none                             | OSS architecture pages |
| exa               | stdio | `npx -y exa-mcp-server`                      | `EXA_API_KEY`                    | live web search |
| openviking        | remote| `http://127.0.0.1:1933/mcp`                  | none (local daemon)              | mined-corpus retrieval; register only when the daemon runs |
| mcp-steroid       | stdio | `devrig mcp` (PATH-resolved)                  | none (local IDE bridge)          | JetBrains PSI/refactoring/test/debugger access via devrig |

### Deliberately not registered (researched)

| Candidate | Status | Why it is not in the registry |
|---|---|---|
| **OpenDesign** (Open Design; the local-first design app with a stdio MCP exposing tokens CSS, JSX components, entry HTML; upstream `github.com/vustudio/opendesign`, same-name mirrors/forks such as `Wallstreetrenegade/opendesign` exist) | not configured | Its documented wiring bakes machine-local absolute paths (`node` binary + daemon `cli.js`) into per-client snippets, which violates the portability rule above, and the command only resolves while the desktop app is installed. Revisit when the user runs it: add a PATH-resolvable `command` block to `servers.json`, then wire per-CLI. Role boundary: design workspace and design context; never the canonical site crawler and never raw-site ground truth. |
| **Image generation** | capability, not an MCP server | On pi hosts it is the `openai_image` extension tool (pi-better-openai): generate or edit, with project-local save. Frontend media policy: `skills/web-reference/references/media.md`. No model slug is frozen into policy. |

### Where the keys live (names only — never commit values)

These hosts already export or can export the needed vars; the `${VAR}` text in
`servers.json` is expanded by the host shell at launch:

| Var | Defined in |
|-----|------------|
| `EXA_API_KEY` | `~/.profile`, `~/.dsh/.env` |
| `CONTEXT7_API_KEY` | `~/.profile`, `~/.dsh/.env` |

## Per-CLI wiring

| CLI | Host config | Block |
|-----|-------------|-------|
| pi | `~/.pi/agent/mcp.json` | `mcpServers` (native; merge the requested server) |
| Claude Code | `~/.claude.json` | `mcpServers` (same shape) |
| Codex | `~/.codex/config.toml` | `[mcp_servers.<name>]` (stdio only) |
| OpenCode | `~/.config/opencode/opencode.json` | `mcp.<name>` (`type: local\|remote`, `enabled`) |
| DSH web profile | `~/.dsh/cordis.patch.yml` | `@monotykamary/dsh-mcp-client` inserts (codebase-memory, openviking, context7, deepwiki, exa, mcp-steroid) |

Wire the requested server into the target CLI config by merging its block from
the canonical registry; merge, don't overwrite, and never touch unrequested servers.

When unsure whether a CLI accepts a server scheme, skip that CLI (do not
write anything); report it as "not wired (unsupported)".

## Live wiring layers (machine-local)

The canonical registry fans out through per-CLI mirrors **and** machine-local
overlay files that this repo does not own — document them, never hand-edit
both sides blindly:

- `~/.pi/agent/mcp.json` — pi's mirror (all six servers; regenerate from the
  canonical registry after changes).
- `~/.mcporter/mcporter.json` — the pi-mcp-adapter layer (subset; env values
  support `${VAR}` expansion — never store literal keys there; use env vars).
- `~/.prime/agent/settings.json` — written by `mcp/sync-to-prime.py --apply`.
- The IntelliJ **built-in** MCP server (`http://localhost:64442`) is a
  separate transport from mcp-steroid; it needs `JETBRAINS_MCP_TOKEN` exported
  or it fails auth (401) — wire the token or treat the entry as dormant.

## Host notes

- **pi**: servers.json mirrors into `~/.pi/agent/mcp.json` `mcpServers`. For
  npx stdio servers the `${VAR}` placeholders are read from the shell env pi
  was launched with; ensure `EXA_API_KEY` / `CONTEXT7_API_KEY` are exported.
- **Claude Code / Codex / OpenCode**: same merge rule per host block; stdio
  entries use `command` + `args`; secrets stay env-only.
- **sonatype-guide**: intentionally uninstalled — not part of the registry; do not re-register.
- **openviking**: local streamable-HTTP daemon (port matches the running
  daemon, default `1933`). If the daemon is not running the server will fail to
  connect — treat as optional context, never a blocker.
