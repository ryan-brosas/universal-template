<!-- capsule-v2 -->
# Bridge startup degradation ladder — how do you make IDE-bridge startup best-effort so a broken MCP descriptor never blocks session creation?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How does an adapter layer its MCP-bridge startup failures so that every degradation level is observable (diagnostics + startup info) while session creation, restore, and forking always proceed?

## Three-layer catch ladder: start → handshake → registration
**Path/Symbol:** `src/acp/agent.ts` — `startBridge` (:171-186), `waitForBridgeReady` (:205-218); consumer sites `restoreSession` (:282,:315), `newSession` (:407,:428), `forkSession` (:1163,:1218); inner per-server layer `src/acp/mcp-bridge.ts` — `start()` (:394+, per-server try/catch with `phase='descriptor_validation'` marker). Transport internals in `references/mcp-bridge-transports.md`; IPC handshake in `references/mcp-bridge-ipc.md`.
**Signature:** `private async startBridge(mcpServers: NewSessionRequest['mcpServers'], correlationId: string, cwd: string): Promise<{ bridge: AcpMcpBridge; settings: BridgeSpawnSettings }>`; `private async waitForBridgeReady(bridge: AcpMcpBridge, settings: BridgeSpawnSettings): Promise<void>`.
**Data Shape:** the degraded return value is `{ bridge, settings: { extensionPaths: [], env: {} } }` — an EMPTY spawn-settings object that makes `PiRpcProcess.spawn` produce an ordinary pi session with no bridge extension; diagnostics accumulate on `bridge.diagnostics` (surfaced later via `buildBridgeStartupInfo` as "N registration failed" / "catalog is partial").

### Decisive source
```ts
try {
  return { bridge, settings: await bridge.start() }
} catch (error) {
  bridge.addDiagnostic(`IDE bridge startup failed: ${String((error as any)?.message ?? error)}`)
  await bridge.dispose()
  return { bridge, settings: { extensionPaths: [], env: {} } }   // degrade, never throw
}

private async waitForBridgeReady(bridge: AcpMcpBridge, settings: BridgeSpawnSettings): Promise<void> {
  if (settings.extensionPaths.length === 0) return                 // degraded → no-op
  const handshaken = await bridge.waitForHandshake()
    .then(() => true)
    .catch(error => {
      bridge.addDiagnostic(`IDE bridge handshake unavailable: ${...}`)
      return false
    })
  if (!handshaken) return                                          // skip registration wait entirely
  await bridge.waitForRegistration().catch(error => {
    bridge.addDiagnostic(`IDE bridge registration unavailable: ${...}`)
  })
}
```

**Flow:** every session-creating path calls `startBridge` first: (layer 1) `bridge.start()` throws (IPC bind failure, closed/already-started state) → diagnostic + `dispose()` + empty settings, so the pi child spawns WITHOUT the bridge extension; (layer 2) `waitForBridgeReady` no-ops when `extensionPaths` is empty (the degraded case), otherwise waits for the extension's IPC handshake — handshake failure records a diagnostic and SKIPS the registration wait (no point waiting on a socket whose peer never connected); registration failure records a diagnostic only; (layer 3, inside `start()` itself) per-server failures — `mcp/connect` returning no connectionId, invalid stdio descriptor (`phase=descriptor_validation`), discovery timeout on a silent client — set `catalogComplete=false`, push a named diagnostic, and CONTINUE to the next server. All three layers are bounded by timeouts (handshake default 20s, discovery per-server timeout), so a wedged IDE cannot hang session creation.
**Invariant:** NO bridge failure path may throw into session creation — the only values that escape are a working `{bridge, settings}` or the degraded empty-settings pair; diagnostics are append-only and survive to startup-info rendering so the user sees "catalog is partial / N registration failed" instead of a silent tool-less session; the handshake→registration wait is strictly ordered (registration is only awaited after a successful handshake); degraded sessions are indistinguishable from no-MCP sessions at the pi level (empty extensionPaths + empty env).
**Probe:** `node --import tsx --test test/unit/session-restore.test.ts test/unit/mcp-bridge.test.ts test/unit/startup-info-ide.test.ts` — "prompt auto-restores a missing session from SessionStore" pins the degraded spawn args exactly (`extensionPaths: [], env: {}` reach PiRpcProcess.spawn); "does not hang on a silent client: discovery times out and reports diagnostics" pins the bounded-wait contract; "reports registration failures separately from discovered tools" pins discovered/registered/failed counters; "buildBridgeStartupInfo distinguishes discovered and registered tools" pins the diagnostic surface ("IDE bridge registration unavailable: timeout" → "catalog is partial").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "startBridge waitForBridgeReady addDiagnostic catalogComplete", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-layer ladder (fatal-start catch → ordered handshake/registration waits → per-server continue-on-failure), the empty-settings degraded value that flows unchanged into the engine spawn args, and the append-only diagnostics that render into user-visible startup info. Adapt the diagnostic message prefixes and the 20s handshake default to your transport. Omit the fork-site reuse if you have no fork capability. Direct tests executed green at the pin.
