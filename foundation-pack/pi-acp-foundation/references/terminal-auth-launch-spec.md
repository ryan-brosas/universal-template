<!-- capsule-v2 -->
# Terminal-auth launch spec — how does an auth method relaunch the adapter itself in a terminal, correctly in both dev and installed layouts?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you build the terminal-auth launch spec so the client's "Authenticate" banner relaunches THIS adapter — without hardcoding an install path?

## getAuthMethods + terminalAuthLaunchSpec
**Path/Symbol:** `src/acp/auth.ts` (whole, 59L) — `PI_SETUP_METHOD_ID` :4, `getAuthMethods` :16-44, `terminalAuthLaunchSpec` :46-58. Direct test: `test/unit/auth-methods-terminal-auth-meta.test.ts` (2 tests).
**Signature:** `getAuthMethods(opts?: { supportsTerminalAuthMeta?: boolean }): AuthMethod[]`; `terminalAuthLaunchSpec(): { command: string; args: string[] }`.
**Data Shape:** ONE method carrying BOTH wire shapes: registry-required `{id, name, description, type: 'terminal', args: ['--terminal-login'], env: {}}` AND Zed-style `_meta['terminal-auth'] = {command, args, label: 'Launch pi'}` (gated by `supportsTerminalAuthMeta`, default true).

### Decisive source
```ts
function terminalAuthLaunchSpec(): { command: string; args: string[] } {
  // If we were launched as `node /path/to/dist/index.js`, reuse that.
  // This is the most reliable in local dev and custom Zed configurations.
  const argv0 = process.argv[0] || 'node'
  const argv1 = process.argv[1]
  if (argv1 && argv0) {
    const isNode = argv0.includes('node')
    const isJs = argv1.endsWith('.js')
    if (isNode && isJs) {
      return { command: argv0, args: [argv1, '--terminal-login'] }
    }
  }
  // Fallback: assume `pi-acp` is on PATH.
  return { command: 'pi-acp', args: ['--terminal-login'] }
}
```

**Flow:** `initialize` probes client capabilities → `getAuthMethods({supportsTerminalAuthMeta})` embeds the launch spec in `_meta['terminal-auth']` when the client supports it → the client renders its terminal-auth banner → on click the client spawns `{command, args}` in a terminal, which relaunches the adapter with `--terminal-login` → the user completes login; the next newSession model probe then succeeds. The spec derivation: when the adapter itself was launched as `node <path>/dist/index.js` (argv0 includes 'node' AND argv1 ends '.js'), reuse that exact pair plus the flag — this survives dev checkouts, custom Zed configs, and non-PATH installs; otherwise assume a PATH-installed `pi-acp` binary.
**Invariant:** the launch spec is derived from the RUNNING process, never from a configured install path — whatever layout launched the adapter, the same layout relaunches it; the registry shape (`type/args/env`) is always present so spec-compliant clients work even when `_meta` is omitted; the method id is a single stable constant (`pi_terminal_login`).
**Probe:** `node --import tsx --test test/unit/auth-methods-terminal-auth-meta.test.ts` (meta present with string command + exact args + label when enabled; meta['terminal-auth'] absent when disabled) — executed GREEN at pin (pass 4).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "getAuthMethods terminalAuthLaunchSpec terminal-auth PI_SETUP_METHOD_ID", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt argv-derived launch specs for terminal-auth relaunch (reuse the running node+script pair; PATH fallback) and the dual-shape auth method (registry fields + client-extension `_meta`). Adapt the flag, method id, and PATH binary name to your agent. Omit the `_meta` shape if your client population is purely spec-compliant. Coverage caveat: the argv-reuse branch itself is not unit-pinned (tests pin the meta on/off gating only) — the heuristic is source-read.
