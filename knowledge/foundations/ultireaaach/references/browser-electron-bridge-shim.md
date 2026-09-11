<!-- capsule-v2 -->
# Browser-side Electron-bridge shim — how do you run an Electron-renderer webapp in a plain browser against local mocks?

**Source:** Ultireaaach `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory `ultireaaach`. **Question:** the SPA is a webpack build written for an Electron renderer (`window.require('electron')`, `@electron/remote`, `electron-store`) and hardcodes cloud hosts — how does it boot in a plain browser with zero code changes to the bundle?

## Connected graph-selected seam
**Path/Symbol:** `packages/front/build/electron-bridge.js` (409 lines, HAND-WRITTEN repo code — header comment "Electron Bridge v4"; NOT minified vendor output; loaded as the FIRST script so shims exist before webpack bundles run). Graph evidence: search_graph "createPasServer PAS launcher rpc shim" surfaced `front.build.electron-bridge.launcherRpcCall` (91-98) as an indexed symbol.
**Signature:** IIFE installing globals: `window.require/__bridgeRequire(mod)`, `window.electron`, `window.remote`, `window.process`, `window.frontendMode`, `window.openLinkedIn/liProxy`.
**Data Shape:** `requestActionAtLauncher*` client contract `{responseEncoded: JSON-string|null, error: string|null}` (twin of pas-server's server-side wrap); fake JWT payload `{sub, iat, exp(ms), userId, role, aclScopes, email}`.

### Decisive source
```js
function noopMainWindow() {
  return new Proxy(getCurrentWindow(), {
    get: function (target, prop, receiver) {
      if (prop in target) { /* bind real fixture methods */ }
      if (prop === 'requestActionAtLauncher' || prop === '...Read' || prop === '...Write') {
        return function (arg) {
          var parsed = typeof arg === 'string' ? JSON.parse(arg) : arg;
          return launcherRpcCall((parsed && parsed.name) || '', parsed && parsed.payloadJsonable);
        };
      }
      // Direct dispatch: callRead("getSimpleMachineToken") → this.mainWindow[Q](...)
      return function () { var r = launcherResponse(String(prop));
        return r !== null && r !== undefined ? r : undefined; };
    },
  });
}
var CLOUD_RX = /^https?:\/\/[a-z0-9.-]*linkedhelper\.com\//i;
var V2_RX   = /^https?:\/\/[a-z0-9.-]*linkedhelper\.com\/v2\//i;
var LI_RX   = /^https?:\/\/(www\.)?linkedin\.com\//i;
// fetch + XMLHttpRequest.open rewrite: V2 -> '/lh-backend/v2/', cloud -> '/lh-backend/',
// linkedin -> '/li-proxy?url=' + encodeURIComponent(url)
```
**Flow:** install `window.require` dispatch table (electron, @electron/remote, electron-store -> localStorage-backed MemoryStore mirroring `lhBackendTokens`, sqlite/source-manager stubs, stream/fs/os/path/util shims) -> `remote.getGlobal` overrides incl. `localPASServerURL http://localhost:4000` (:141 — this is what wires the dashboard onto the PAS shim port), `frontendMode 'support'` (:139) while `window.frontendMode = 'electron'` (:264, comment: envService checks platform === "electron" in ~143 places) -> `seedLocalTokens()` writes a decodable fake JWT (role:'user', exp = now + 6h **ms**) into localStorage `lhBackendTokens` BEFORE bundles read it -> fetch/XHR rewrites keep every request same-origin -> hidden 1px iframe loads linkedin.com/feed/ through /li-proxy -> autoLogin polls every 300 ms up to 80 tries, fills email/password via the native value setter + input/change events, clicks submit after a 300 ms validator wait.
**Invariant:** the bundle never learns it isn't in Electron: EVERY property access on mainWindow must resolve (Proxy get trap returns a callable for unknown names — avoids "this.mainWindow[Q] is not a function"), and NO request may escape to the real internet (`CLOUD_RX` catches any subdomain of linkedhelper.com with or without `/v2/`). Client-side `launcherResponse` table (~17 cases, default null) deliberately mirrors the server's `specificResult` fixtures. Caveat: this file lives under `front/build/`; a dashboard rebuild would clobber it — verify the hand-written header survives after any rebuild.
**Probe:** no upstream test exists (coverage caveat). Deterministic evidence executed this pass: whole-file checkout read (409 lines) matched the graph-indexed symbols (`launcherRpcCall` 91-98); coverage check `no_recorded_issue/metadata_match/generation_matches` @ gen 2026-08-23T00:33:18Z; `pnpm test` exit 0 exercises the served stack this file bootstraps against.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ultireaaach",
  qualified_name: "ultireaaach.packages.front.build.electron-bridge.launcherRpcCall" });
// observed this pass: electron-bridge.js 91-98 — try { launcherResponse(name) } ->
// { responseEncoded: JSON.stringify(result)|null, error:null }, catch -> {responseEncoded:null,error}
```

## Verdict
Adopt the three-layer recipe — require-dispatch table, Proxy-everything main window, network-layer host rewriting — for running any Electron-renderer or cloud-dependent SPA fully locally without forking the bundle. Adapt module names, host regexes, and the seeded-token payload to your app. Omit the LinkedIn iframe/auto-login conveniences unless your flow needs live-page previews.
