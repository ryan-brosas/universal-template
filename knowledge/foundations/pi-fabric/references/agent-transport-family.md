<!-- capsule-v2 -->
# Transport adapter family + auto ladder — how do you launch the same worker across tmux/screen/localterm/herdr/bare-process behind one interface?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** what contract must every launch backend satisfy, and in what order is "auto" resolved?

## One adapter interface, five backends, availability-probed ladder
**Path/Symbol:** `src/agents/transports/process-transport.ts` (:8-28), `tmux-transport.ts:15-53`, `screen-transport.ts:11-45`, `localterm-transport.ts:19-64`, `herdr-transport.ts:44-170`; selection `src/agents/manager.ts:#resolveTransport` (:1323-1336); registry :417-424.
**Signature:** `interface AgentTransportAdapter { kind; available(): Promise<boolean>; launch(request): Promise<AgentTransportHandle> }`; handle = `{kind, sessionId?, attachCommand?, livenessPollIntervalMs?, isAlive(), stop()}`.
**Data Shape:** launch request `{id, name, cwd, workerPath, workerArguments}`; process transport reuses pid as sessionId with instant `isAlive`; external transports advertise a slower poll interval (2s) because liveness costs a CLI/API call.

### Decisive source
```ts
async #resolveTransport(requested: FabricAgentTransport) {
  if (requested !== "auto") {
    const adapter = this.#transports.get(requested);
    if (!adapter || !(await adapter.available()))
      throw new Error(`Fabric agent transport is unavailable: ${requested}`);
    return adapter;
  }
  for (const kind of ["herdr", "localterm", "tmux", "screen", "process"] as const) {
    const adapter = this.#transports.get(kind);
    if (adapter && (await adapter.available())) return adapter;
  }
  throw new Error("No Fabric agent transport is available");
}
```

**Flow:** explicit choice fails LOUD when unavailable (never silently downgrades) → auto walks richest-to-poorest (in-pane visibility first, bare detached process last) probing `available()` → each backend implements the same three verbs differently: tmux `has-session`, screen `-ls` string scan, localterm/herdr **pid / API-poll** instead of CLI re-invocation → herdr speaks newline-delimited JSON over a Unix socket/Windows named pipe with 3s timeout and 1MB response cap, deriving `attachCommand` from an optional second `pane.get` whose failure is tolerated ("very short runs can exit before the optional attach metadata is read").
**Invariant:** `available()` must be cheap AND side-effect-free enough to run on every auto resolution, but herdr's probe legitimately pings the socket once — availability is allowed to be a live check; `isAlive()` semantics differ per backend and consumers only trust the advertised `livenessPollIntervalMs`. A porter who makes explicit-mode fall back silently turns a config error into a wrong-surface launch.
**Probe:** `tests/script-runtime.test.ts:18-67` pins runtime resolution feeding spawn argv; `tests/herdr-transport.test.ts:85,96` pin availability gating + pane-id control; `tests/localterm-transport.test.ts:43` pins pid-based liveness without repeated CLI calls.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "AgentTransportAdapter available launch isAlive tmux screen herdr", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the adapter interface + loud-explicit/auto-ladder split for any pluggable process launcher; adapt per-backend liveness to your environment; omit herdr if you have no paned terminal host. Direct tests exist for the two nontrivial backends and the shared runtime resolver — no coverage caveat.
