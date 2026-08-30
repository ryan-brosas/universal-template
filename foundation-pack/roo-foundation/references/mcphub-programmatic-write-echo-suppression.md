<!-- capsule-v2 -->
# Programmatic-write echo suppression — how do you write a server's own config file through a watched file without the watcher restarting every server?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** When your own writes to `cline_mcp_settings.json` trigger your own file watcher, how do you swallow exactly that echo — including its debounce window — and nothing else?

## Latch flag → write in try/finally → reset on a timer LONGER than the debounce
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`updateServerConfig` :1605–1618; same pattern in `updateServerToolList` :1841–1854; consumer `debounceConfigChange` :301–305; teardown clears the timer :1964–1970).
**Signature:** `this.isProgrammaticUpdate = true; try { await safeWriteJson(configPath, updatedConfig, { prettyPrint: true }) } finally { this.flagResetTimer = setTimeout(() => { this.isProgrammaticUpdate = false; this.flagResetTimer = undefined }, 600) }`.
**Data Shape:** two instance fields: boolean `isProgrammaticUpdate`, optional `NodeJS.Timeout` `flagResetTimer`; per-hub (not per-file) because the global settings file is the only programmatic write target. Debounce itself is 500 ms keyed `"${source}-${filePath}"`.

### Decisive source
```ts
// :301-305 — the watcher-side consumer: latch checked FIRST, before any debounce bookkeeping
private debounceConfigChange(filePath: string, source: "global" | "project"): void {
    if (this.isProgrammaticUpdate) { return }
```
```ts
// :319 vs :1617 — 500ms debounce < 600ms flag window (the load-bearing ordering)
}, 500) // 500ms debounce
...
}, 600)
```

**Flow:** user action → set flag (clearing any pending reset timer first, so back-to-back writes extend the window rather than racing it) → safeWriteJson inside try/finally → finally schedules flag clear at +600 ms. Watcher fires within the window → debounceConfigChange returns before allocating a timer.
**Invariant:** flag-reset delay (600 ms) must EXCEED the file-watcher debounce (500 ms); resetting them equal or inverted lets the echo land one tick late and restart all servers from a self-inflicted config change. Clearing `flagResetTimer` before re-latching makes consecutive writes safe; dispose() must clear both timer maps (:1957–1970).
**Probe:** `src/services/mcp/__tests__/McpHub.spec.ts` describe `"toggleToolAlwaysAllow"` → it `"should add tool to always allow list when enabling"` (:770–818): after `mcpHub.toggleToolAlwaysAllow(...)` the mocked `fs.writeFile` carries the updated `alwaysAllow` array while NO server-restart side effect fires — the echo path is exercised with the latch armed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "updateServerConnections debounce config file change", limit: 5 });
// CLI verified @ pin: rank#1 line-exact → McpHub.debounceConfigChange Method src/services/mcp/McpHub.ts 301-322 (total: 389)
```

## Verdict
Adopt flag + try/finally + timed-reset with the 600>500 ordering as a unit. Adapt timings to your host watcher stack (chokidar/VSCode FSWatcher differ). Omit nothing — this is the classic self-echo race and the numbers are the contract.
