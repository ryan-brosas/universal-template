# Shared MCP catalog (CLI-neutral)

CANONICAL REGISTRY: `servers.json` (relative to this directory)

The registry declares capabilities. It is not a default activation list and no
host is required to connect every entry.

## Rules

- Servers are declared ONCE, in the canonical registry; per-CLI host configs are
  derived copies written only when the user requests a specific server.
- To wire a server, preview `configure.py --server NAME --target PATH`; pass
  `--apply` only after reviewing the scoped merge. `profiles.json` provides
  bounded sets, and `minimal` activates none.
- Prefer a dry-run-style preview before writing, and back up a host config
  before its first write.
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

## Current registry (`servers.json`)

| Server            | Kind  | Connection / command                                    | Key / env                        | Notes |
|-------------------|-------|---------------------------------------------------------|----------------------------------|-------|
| codebase-memory   | stdio | `codebase-memory-mcp` (PATH-resolved; mise shim)         | `CBM_CACHE_DIR` (machine-local)  | local graph, keep-alive |
| context7          | stdio | `npx -y @upstash/context7-mcp@4.0.4`               | `CONTEXT7_API_KEY`               | library docs + code examples |
| deepwiki          | stdio | `npx -y deepwiki-mcp@0.0.6`                        | none                             | OSS architecture pages |
| exa               | stdio | `npx -y exa-mcp-server@3.4.1`                      | `EXA_API_KEY`                    | live web search |
| openviking        | remote| `http://127.0.0.1:1933/mcp`                  | none (local daemon)              | optional rebuildable projection/cache over mined corpus; register only when the daemon runs; never canonical, never auto-synced, never a blocker |
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

## Scoped profiles

`profiles.json` defines `minimal` (none) and six one-server profiles:
`code-graph`, `ide`, `docs`, `repository-research`, `web-research`, and
`historical-context`. Codebase Memory and MCP Steroid are deliberately separate;
there is no ambiguous `code` compatibility alias. Profiles are explicit
selections, not always-on policy. Use `--deactivate` to remove only the selected
profile entries while preserving unrelated host configuration. Writes are atomic. Prime translation remains
available through `sync-to-prime.py`, but it also requires `--server` or
`--profile`.

Measured tool-contract costs and the 81,429-byte all-versus-minimal reduction
are recorded in `../docs/context-surfaces.md` and
`../docs/context-measurements.json`.

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

- `~/.pi/agent/mcp.json` — pi's host-owned selected subset; never regenerate
  all six by default.
- `~/.mcporter/mcporter.json` — the pi-mcp-adapter layer (subset; env values
  support `${VAR}` expansion — never store literal keys there; use env vars).
- `~/.prime/agent/settings.json` — scoped writes only through
  `mcp/sync-to-prime.py --server NAME --apply` or an explicit profile.
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
