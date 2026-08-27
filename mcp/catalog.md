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

## Current registry (`~/.agents/mcp/servers.json`)

| Server            | Kind  | Connection / command                                    | Key / env                        | Notes |
|-------------------|-------|---------------------------------------------------------|----------------------------------|-------|
| codebase-memory   | stdio | `codebase-memory-mcp` (mise-managed)                    | `CBM_CACHE_DIR`                  | local graph, keep-alive |
| context7          | stdio | `npx -y @upstash/context7-mcp`               | `CONTEXT7_API_KEY`               | library docs + code examples |
| deepwiki          | stdio | `npx -y deepwiki-mcp`                        | none                             | OSS architecture pages |
| exa               | stdio | `npx -y exa-mcp-server`                      | `EXA_API_KEY`                    | live web search |
| openviking        | remote| `http://127.0.0.1:1933/mcp`                  | none (local daemon)              | mined-corpus retrieval; register only when the daemon runs |

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
| DSH web profile | `~/.dsh/cordis.patch.yml` | `@monotykamary/dsh-mcp-client` inserts (codebase-memory, openviking, context7, deepwiki, exa) |

Wire the requested server into the target CLI config by merging its block from
the canonical registry; merge, don't overwrite, and never touch unrequested servers.

When unsure whether a CLI accepts a server scheme, skip that CLI (do not
write anything); report it as "not wired (unsupported)".

## Host notes

- **pi**: servers.json mirrors into `~/.pi/agent/mcp.json` `mcpServers`. For
  npx stdio servers the `${VAR}` placeholders are read from the shell env pi
  was launched with; ensure `EXA_API_KEY` / `CONTEXT7_API_KEY` are exported.
- **Claude Code / Codex / OpenCode**: same merge rule per host block; stdio
  entries use `command` + `args`; secrets stay env-only.
- **sonatype-guide**: intentionally uninstalled — not part of the context plane; do not re-register.
- **openviking**: local streamable-HTTP daemon (port matches the running
  daemon, default `1933`). If the daemon is not running the server will fail to
  connect — treat as optional context, never a blocker.
