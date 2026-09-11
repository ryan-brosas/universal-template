<!-- capsule-v2 -->
# LSP client fleet — how do you manage a fleet of per-language server processes across a workspace without double-spawning, retry storms, or orphan processes?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A coding agent wants language-server feedback for many languages at once. Servers are expensive child processes; files map to servers by extension and to a project root by marker files; config can disable, override, or add servers; and a broken spawn must not be retried forever. How is the fleet assembled, deduplicated, and torn down?

## Config ladder + per-language registry
**Path/Symbol:** `packages/opencode/src/lsp/lsp.ts` (state init :140-196, `filterExperimentalServers` :98-106) + `packages/opencode/src/lsp/server.ts` (`Info` :81-86, `NearestRoot` :32-54, `StrictNearestRoot` :56-78, `Typescript` :115-143, `JDTLS` :1147-1272).
**Signature:** `Info = {id, extensions: string[], global?: boolean, root: (file, ctx) => Promise<string|undefined>, spawn: (root, ctx, flags) => Promise<Handle|undefined>}`; `Handle = {process, initialization?}`.
**Data Shape:** state = `{clients: LSPClient.Info[], servers: Record<string, Info>, broken: Set<string>, spawning: Map<string, Promise<Info|undefined>>}` keyed by `root + server.id`.

### Decisive source
```ts
// lsp.ts:140-158 — config ladder: undefined disables all, true enables built-ins, object overrides
if (!cfg.lsp) {
  yield* Effect.logInfo("all LSPs are disabled")
} else {
  for (const server of Object.values(LSPServer)) servers[server.id] = server
  filterExperimentalServers(servers, flags)   // experimentalLspTy swaps pyright <-> ty
  if (cfg.lsp !== true) {
    for (const [name, item] of Object.entries(cfg.lsp)) {
      if (item.disabled) { delete servers[name]; continue }
      servers[name] = { ...existing, id: name, extensions: item.extensions ?? existing?.extensions ?? [],
        spawn: async (root) => ({ process: lspspawn(item.command[0], item.command.slice(1), { cwd: root, env: {...process.env, ...item.env} }), initialization: item.initialization }) }
    }
  }
}
// server.ts:32-54 — NearestRoot falls back to ctx.directory; StrictNearestRoot returns undefined instead
const first = await files.next()
if (!first.value) return ctx.directory        // NearestRoot
// if (!first.value) return undefined         // StrictNearestRoot
```

**Flow:** state init builds the server table from config; every registry `spawn` returning `undefined` (no binary on PATH, java < 21, download disabled) or throwing means "not available here". Root resolution walks UP from the file's directory to the instance directory for marker files (lockfiles, pyproject.toml, pom.xml chains); JDTLS layers four ladders (gradle-wrapper strict → settings strict → build.gradle fallback → Maven `<module>`-verified pom chain → Eclipse markers). launch.ts forces stdin/stdout/stderr pipes and throws "Process output not available" if any stream is missing — an LSP server with a dead pipe is unusable, so fail at spawn, not mid-handshake.

**Invariant:** `cfg.lsp === undefined` spawns nothing; a custom config object keeps built-ins unless explicitly disabled; exactly one client per (root, serverID) pair exists; a failed spawn is marked broken for the instance lifetime (no retry storm); scope close shuts every client down.
**Probe:** `packages/opencode/test/lsp/index.test.ts` (read whole, 231L): "does not spawn builtin LSP for files outside instance" pins the containsPath gate (spy called 0×); "does not spawn builtin LSP for files inside instance when LSP is unset" pins the undefined-config gate; "would spawn builtin LSP for files inside instance when lsp is true" pins 1×; "would spawn builtin LSP for files inside instance when config object is provided" pins built-ins surviving `{eslint:{disabled:true}}`; "uses pyright instead of ty by default" / "uses ty instead of pyright when experimentalLspTy is enabled" pin the flag swap; "passes disableLspDownload to builtin LSP spawn" pins flags reaching spawn. `packages/opencode/test/lsp/jdtls-root.test.ts` (459L, 24 tests): Maven `<module>` chain to top-level, broken-chain stop, `./`-prefix and trailing-slash normalization, commented-out `<module>` non-match, gradlew-beats-pom exclusion, no-markers → undefined. Source pin:
```bash
grep -n 'filterExperimentalServers' packages/opencode/src/lsp/lsp.ts   # expect 2
grep -n 'Process output not available' packages/opencode/src/lsp/launch.ts  # expect 1
grep -n 'const NearestRoot\|const StrictNearestRoot' packages/opencode/src/lsp/server.ts  # expect 2
```

## Spawn dedupe kernel
**Path/Symbol:** `packages/opencode/src/lsp/lsp.ts` (`getClients` :208-297, inner `schedule` :217-249, finalizer :198-202).
**Signature:** `getClients(file) → Effect<LSPClient.Info[]>`; `touchFile(input, diagnostics?)`, `hasClients(file)`, `status()`.
**Data Shape:** in-flight entry = the actual spawn task promise; deleted only if still current (`s.spawning.get(key) === task`).

### Decisive source
```ts
// lsp.ts:217-249 — schedule: broken-set marks on ANY failure path, reuse stops the duplicate
const handle = await server.spawn(root, ctx, flags)
  .then((value) => { if (!value) s.broken.add(key); return value })
  .catch(() => { s.broken.add(key); return undefined })
if (!handle) return undefined
const client = await LSPClient.create({...}).catch(async () => {
  s.broken.add(key); await Process.stop(handle.process); return undefined   // handshake failure kills the child
})
const existing = s.clients.find((x) => x.root === root && x.serverID === server.id)
if (existing) { await Process.stop(handle.process); return existing }      // never two clients per key
// lsp.ts:255-272 — concurrent callers share one in-flight task
const inflight = s.spawning.get(root + server.id)
if (inflight) { const client = await inflight; if (!client) continue; result.push(client); continue }
const task = schedule(server, root, root + server.id)
s.spawning.set(root + server.id, task)
task.finally(() => { if (s.spawning.get(root + server.id) === task) s.spawning.delete(root + server.id) })
```

**Flow:** getClients gates on containsPath (outside-instance files never spawn), matches extensions, resolves the root, then: existing client → reuse; broken key → skip; in-flight task → await it; else schedule. Every newly added client publishes `Event.Updated` (one event per new client, test pins the event after a custom-server init). The InstanceState finalizer shutdown()s all clients when the instance scope closes — no orphaned language servers.

**Invariant:** at most one live client per (root, serverID); N concurrent first-touches of the same file produce ONE spawn; a spawn that wins a race against an existing client has its child stopped; handshake failure stops the child before marking broken; teardown is total on scope close.
**Probe:** index.test.ts "publishes lsp.updated after custom LSP initialization" pins the Updated event via a real fake server (fixture/lsp/fake-lsp-server.js). lifecycle.test.ts (160L whole): init() idempotent ×3, status()/diagnostics() empty initially, hasClients false outside instance / true for `.ts` with `lsp:true`, Diagnostic.pretty severity formatting (ERROR/WARN/[line:col], default ERROR). Source pin:
```bash
grep -c 's.broken' packages/opencode/src/lsp/lsp.ts    # expect 5
grep -c 's.spawning' packages/opencode/src/lsp/lsp.ts  # expect 4
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "LSP service getClients schedule broken spawning NearestRoot StrictNearestRoot spawn Handle", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-state fleet kernel (reuse / broken-no-retry / in-flight-share / fresh-spawn) as the general pattern for any per-project external-process fleet: one Set for permanent failures, one Map of live tasks for dedupe, and a scope finalizer for total teardown. Adopt the `spawn → Handle|undefined` contract — availability checks belong in spawn and return absence, not errors, so the caller can distinguish "not here" from "crashed". Adopt NearestRoot-vs-StrictNearestRoot as two explicit policies (fall back to workspace root vs refuse) instead of one ambiguous walker. Adapt the marker-file tables to your project shapes; omit the experimental-flag swap if you have no A/B server pairs. Direct tests read whole (index.test.ts 231L, lifecycle.test.ts 160L, jdtls-root.test.ts 459L, launch.test.ts 22L); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
