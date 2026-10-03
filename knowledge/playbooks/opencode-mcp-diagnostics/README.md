---
title: opencode-mcp-diagnostics
summary: "Use when an OpenCode MCP server reports failed, 'Request timed out', or needs authentication. Separates local npx cold-start delays against the default 30 s startup timeout from credential, config and remote-server failures, with a bounded probe and fix ladder."
kind: playbook
---

# OpenCode MCP connectivity diagnostics

A server marked `failed` at session start is not proof the server itself is broken.
A local stdio server runs whatever `command` names, so its startup cost belongs to
that command. For `npx` servers, npm resolution and download happen inside the
connection budget.

## Establish the failure and its owner

1. Current status: `opencode mcp list` (connected, failed, needs_auth). The shared
   service owns connections; a stale TUI card can lag a successful reconnect.
2. Configuration: global `~/.config/opencode/opencode.json(c)` plus discovered
   `opencode.json(c)` or `.opencode/opencode.json(c)` documents. V2 shape is
   `mcp.servers.<name>`, not server names directly under `mcp`.
3. Log: `grep '<name>' ~/.local/share/opencode/log/opencode.log` and compare
   `mcp connected` lines with `mcp connect failed ... status.error=`.
4. Classify before fixing:
   - `Request timed out` after roughly the startup budget: transport or initialize
     never completed.
   - `needs_auth`, 401, or OAuth messages: credentials or client registration.
   - HTTP 4xx/5xx with an endpoint error: remote server or header formatting.

## Local `npx` cold start is the common timeout

V2's default `mcp.timeout.startup` is 30 s. A cached `npx` start completes in well
under a second; a package spec absent from the npx cache must download first.
Version-pinned and unpinned specs use different cache entries, so an old warmed
version does not cover a newly pinned one.

Check the exact spec rather than assuming it is cached:

```sh
find ~/.npm/_npx -maxdepth 7 -path '*<package-name>/package.json' \
  -printf '%p -> ' -exec jq -r .version {} \; -printf '  %TY-%Tm-%Td %TH:%TM\n'
```

Then time one bounded handshake with the configured command: pipe an `initialize`
JSON-RPC line into it under `timeout 45` and treat the first stdout line as proof of
a warm start. Do not delete npm/npx caches or the OpenCode database to "test cold";
rerun instead.

Verify credential presence without reading values. `{env:NAME}` substitution needs
the variable in the service process environment:

```sh
pid=$(pgrep -f 'serve --service' | head -1)
grep -qz '^NAME=' /proc/$pid/environ && echo present || echo absent
```

## Fix ladder

1. Raise the startup budget when the command can legitimately be slow: set
   `mcp.timeout.startup` in milliseconds globally, or per server as
   `"timeout": {"startup": 60000}`.
2. Remove runtime downloads: install the server package once (`npm i -g ...`) and
   point `command` at the installed binary, or use the server's remote HTTP endpoint.
3. Pin versions deliberately and warm the new spec before relying on it. A failure
   recorded before warm-up may already be obsolete by the time it is read.
4. Re-check `opencode mcp list` and one real tool call. A component that connects
   after cache warm-up does not need credential or config changes.

Report credential state as present/absent, never values. Prefer environment
substitution over literal secrets in configuration.
