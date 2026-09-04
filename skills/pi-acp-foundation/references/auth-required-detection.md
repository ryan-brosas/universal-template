<!-- capsule-v2 -->
# Auth-required detection — best-effort credential detection → ACP authRequired

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter detect a missing-credentials / not-configured pi error and surface it as an ACP `authRequired` error with terminal-auth methods?

## Auth-required detection
**Path/Symbol:** `src/acp/auth-required.ts` (whole, 37L) + `src/acp/auth.ts` (whole, 96L).
**Signature:** `maybeAuthRequiredError(err: unknown): RequestError | null`; `getAuthMethods(opts?: { supportsTerminalAuthMeta?: boolean }): AuthMethod[]`.
**Data Shape:** The error message is lowercased and matched against a substring list. `getAuthMethods` returns one terminal-auth method with BOTH the registry-required `type/args/env` shape AND the Zed-style `_meta['terminal-auth']` launch spec.

### Decisive source
```ts
const patterns = ['api key','apikey','missing key','no key','not configured','unauthorized','authentication','permission denied','forbidden','401','403']
const hit = patterns.some(p => s.includes(p))
if (!hit) return null
return RequestError.authRequired({ authMethods: getAuthMethods() }, 'Configure an API key or log in with an OAuth provider.')
```
```ts
// getAuthMethods: dual shape for maximum compatibility
const method: any = { id: PI_SETUP_METHOD_ID, name: 'Launch pi in the terminal', type: 'terminal', args: ['--terminal-login'], env: {} }
if (supportsTerminalAuthMeta) method._meta = { 'terminal-auth': { ...terminalAuthLaunchSpec(), label: 'Launch pi' } }
// terminalAuthLaunchSpec: reuse `node /path/to/dist/index.js` if that's how we were launched, else `pi-acp --terminal-login`
```

**Flow:** `maybeAuthRequiredError` inspects the error message substring ladder; on a hit it returns `RequestError.authRequired` carrying the terminal-auth methods. Callers (`newSession`, `session.prompt` error path) use it to fail the session with an `authRequired` error so the client can offer terminal login. `getAuthMethods` includes both the registry `type/args/env` shape and the Zed `_meta['terminal-auth']` launch spec.

**Invariant:** Detection is substring-based and best-effort (no provider-specific check); the returned error always carries the terminal-auth methods so the client can render an Authenticate action; `--terminal-login` re-launches the binary with inherited stdio (see the acp-stdio-server capsule).

**Probe:** `test/unit/auth-methods-terminal-auth-meta.test.ts` (terminal-auth meta shape) and `test/unit/new-session-auth-required-when-no-models.test.ts` (no models → authRequired).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "maybeAuthRequiredError getAuthMethods authRequired", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the substring-ladder auth detection and the dual-shape terminal-auth method. Adapt the pattern list and the launch spec to the host. Omit the `PI_SETUP_METHOD_ID`/`--terminal-login` specifics unless the target agent supports terminal login.
