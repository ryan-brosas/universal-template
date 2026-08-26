# MCP catalog — per-CLI wiring

CANONICAL SOURCE OF TRUTH: `~/.agents/mcp/servers.json` (the shared, global registry).

- read all / write one server at a time; never touch server blocks you didn't
  request.
- To wire a server, merge its block from `servers.json` into the target host
  config (per-CLI wiring notes below); never overwrite unrelated blocks.
- Prefer `--dry-run` style preview: show exactly what would be written before
  writing. Always back up a host config before its first write.

`.agents` is the global settings location for every CLI. `~/.pi/agent/mcp.json`
is pi's *derived host config* — populated from the canonical registry on request,
never authoritative on its own.

The registry itself lists only resolvable servers: stdio servers get applied when
the command resolves on PATH / exists on disk; remote servers when they carry a
URL. Servers needing secrets are declared by env var NAME (`bearerTokenEnv`) and
never by value — only suggested, never force-installed.

## Wiring notes

| CLI | Config file | Server key style |
|---|---|---|
| pi | `~/.pi/agent/mcp.json` | `mcpServers` (native; merge from canonical) |
| Claude Code | `~/.claude.json` → `mcpServers` | same shape |
| Codex | `~/.codex/config.toml` → `[mcp_servers.<name>]` | TOML; stdio only (remote shape unverified → skipped, report as "not wired") |
| OpenCode | `~/.config/opencode/opencode.json` → `mcp.<name>` | `type: local\|remote`, `enabled: true` (shape matches OpenCode `McpLocalConfig`/`McpRemoteConfig`) |

When unsure whether a CLI accepts a key format, skip that CLI (do not guess);
report it as "not wired (unsupported)".