<!-- capsule-v2 -->
# Lazy backend self-registration — how do backends register without a circular-import cycle?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** how can a registry construct `TmuxBackend`/`ITermBackend` classes when those same modules import the registry for registration?

## Class-slot registry + dynamic import + top-level self-registration
**Path/Symbol:** `src/utils/swarm/backends/registry.ts:ensureBackendsRegistered` (:74-79), `registerTmuxBackend` (:85-87), `registerITermBackend` (:93-100), `createTmuxBackend` (:106-113); `src/utils/swarm/backends/TmuxBackend.ts:764`; `src/utils/swarm/backends/ITermBackend.ts:370`.
**Signature:** `registerTmuxBackend(backendClass: new () => PaneBackend): void`; `ensureBackendsRegistered(): Promise<void>`.
**Data Shape:** two nullable class slots (`TmuxBackendClass`, `ITermBackendClass`) typed `new () => PaneBackend`, plus a one-shot `backendsRegistered` flag.

### Decisive source
```ts
// TmuxBackend.ts, last line of the module:
// Register the backend with the registry when this module is imported.
// This side effect is intentional - the registry needs backends to self-register to avoid circular dependencies.
// eslint-disable-next-line custom-rules/no-top-level-side-effects
registerTmuxBackend(TmuxBackend)
```
```ts
export async function ensureBackendsRegistered(): Promise<void> {
  if (backendsRegistered) return
  await import('./TmuxBackend.js')
  await import('./ITermBackend.js')
  backendsRegistered = true
}
```

**Flow:** importing either backend module runs its top-level `register*Backend(Class)` call, filling the registry's class slot WITHOUT the registry statically importing the backends → any consumer needing construction first awaits `ensureBackendsRegistered()` (dynamic imports; never spawns subprocesses, never throws) → constructors throw a named error ("not registered. Import X before using the registry") if slots are empty.
**Invariant:** the registry must stay importable from everywhere (it is the dependency-sink); heavy/OS-specific modules load only on demand; kill-by-stored-type paths (`getBackendByType(m.backendType)` in shutdown cleanup) rely on this cheap registration path rather than full detection.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'self-register' src/utils/swarm/backends/TmuxBackend.ts` (:762); `grep -n "import('./TmuxBackend.js')" src/utils/swarm/backends/registry.ts` (:76).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "ensureBackendsRegistered registerTmuxBackend registerITermBackend", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt slot-based registries fed by callee-side top-level registration plus dynamic imports when you need a stable low-level module that heavyweight implementations also depend on; adapt slot names; omit the eslint suppression by moving registration into an explicit init if your lint rules are softer.
