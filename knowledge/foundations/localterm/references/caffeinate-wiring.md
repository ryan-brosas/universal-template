<!-- capsule-v2 -->
# Caffeinate composition root — how does the daemon wire sessions, detection, and broadcast into one keep-awake decision?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do the pieces compose — who calls poke/noteOutputActivity, where do session pids/peers come from, and how does state reach every tab?

## createServer wiring: SessionManager hooks → CaffeinateManager → WS broadcast
**Path/Symbol:** `packages/server/src/index.ts` (composition root; SessionManager hooks 2194–2231, manager construction 2367–2375, payload builder `caffeinateStatePayload` 2604+, WS message handlers ~2600s) + `packages/server/src/caffeinate-manager.ts:CaffeinateManager.recompute` (245–253).
**Signature:** `recompute(): void { const wantActive = this.modeWantsActive(); this.controller.setActive(this.batteryGuard.shouldActivate(wantActive)); }`.
**Data Shape:** broadcast payload `{type:"caffeinate", supported, active, mode, activityGate, peerKeepAwake, peerActive, batteryThreshold, defaultCommands, commands, activeTrigger}` — exactly the object `tests/caffeinate.test.ts:caffeinateState()` asserts with `toEqual`.

### Decisive source
```ts
// index.ts :2201-2207 — session lifecycle events ARE the detector's event source
hooks: {
  onOutputActivity: () => caffeinateManager.noteOutputActivity(),
  onSessionActivity: () => {
    caffeinateManager.pokeAuto();
    scheduleWorkspaceSnapshot();
    refreshHerdrThemeSyncState();
  },
```
```ts
// manager :245-248 — the single decision funnel
private recompute(): void {
  const wantActive = this.modeWantsActive();   // "on" OR automatic∧detector.active
  this.controller.setActive(this.batteryGuard.shouldActivate(wantActive));
}
```

**Flow:** registry supplies live inputs (`listSessionPids: registry.pids()`, `hasRecentOutput`, `hasPeerClient`, `foregroundNames`) → session events drive the detector (`onOutputActivity` resets the silence window; attach/detach/foreground pokes re-check) → manager recomputes through the battery guard → controller spawns/kills → any `change` (mode set, trigger flip, unexpected process death — controller's own change listener is piped through at manager :127-129) re-broadcasts the full payload to EVERY connected tab. Persisted store lives at `<stateDirectory>/caffeinate.json`; tests inject a fake controller + empty snapshot so no real power assertion or `ps` ever runs.
**Invariant:** one decision funnel (`recompute`) for ALL state sources — mode, detection, and battery never write to the controller directly; and every tab must receive the AUTHORITATIVE active state after an unexpected caffeinate-process death, which only works because controller change → manager emit("change") → broadcast.
**Probe:** `packages/server/tests/caffeinate.test.ts::"broadcasts a mode change to every connected tab"` (:171 — two sockets both observe spawn+kill), `"sends the current keep-awake state on connect"` (:159 — full payload equality incl. defaults), `"reports unsupported and never spawns"` (:245); manager-side `"is always active in on mode and never in off mode"` (caffeinate-manager.test.ts:89).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "CaffeinateManager recompute", limit: 6 });
// → CaffeinateManager.recompute @ caffeinate-manager.ts:245-253
await mcp.codebase_memory.trace_path({ project: "localterm", function_name: "localterm.packages.server.src.caffeinate-manager.CaffeinateManager.recompute", direction: "inbound", depth: 1 });
```

## Verdict
Adopt the single-funnel recompute + hooks-as-event-source wiring verbatim; adapt hook names/payload fields to host transport; omit the herdr-theme refresh side-call (host-specific). Caveat: index.ts is parse_partial at :3582 (one line, far from these ranges) — ranges above verified by direct read.
