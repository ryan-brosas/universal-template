<!-- capsule-v2 -->
# Backend selection kernel — how does a multi-backend GUI pick ONE active backend per tab without ever stranding local-protocol callers?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** Where should backend selection, removal-fallback, tab scoping, and link-pinning live so a cloud selection never breaks local-only services and a cmd-clicked link always lands on its owning backend?

## Snapshot store with health-aware fallback ladder (`src/api/backend-registry/`)
**Path/Symbol:** `src/api/backend-registry/active-store.ts` (`computeSnapshot` :64–93, `pickFallbackBackend` :52–62, `readInitialSelection` :104–114, `getEffectiveLocalBackend` :140–144); `storage.ts` (:104–149 registry read/seeding, :205–244 selection read/write); `default-backend.ts` (:22–70); `url-selection.ts` (:25–77). Fan-in: `trace_path getActiveBackend inbound → callers_total 296` (every service/hook resolves backends through it).
**Signature:** `function computeSnapshot(backends: Backend[], selection: BackendSelection | null): Snapshot`; `getActiveBackend(): ResolvedActiveBackend`; `setActiveSelection(selection | null): void`.
**Data Shape:** Module-level `Snapshot { backends, selection, active: { backend, orgId } }` recomputed synchronously on every mutation; `NO_BACKEND` sentinel (`id:"no-backend"`) is never persisted and callers must pass `isNoBackend()` before reading `kind/host/apiKey`. Selection persists as `{backendId, orgId}` in sessionStorage (tab scope) mirrored to localStorage (new-tab fallback).

### Decisive source
```ts
function pickFallbackBackend(backends: Backend[]): Backend {
  const healthyLocalBackend = backends.find(
    (backend) =>
      backend.kind === "local" &&
      getBackendHealthEntry(backend.id)?.disabled !== true,
  );
  if (healthyLocalBackend) return healthyLocalBackend;

  const localBackend = backends.find((backend) => backend.kind === "local");
  return localBackend ?? backends[0] ?? NO_BACKEND;
}
```
```ts
// active-store.ts readInitialSelection — a URL pin wins over storage…
const fromUrl = readBackendSelectionFromUrl(backends, currentLocationSearch());
if (fromUrl) {
  writeStoredActiveBackend(fromUrl);
  return fromUrl;
}
return readStoredActiveBackend();
```

**Flow:** boot → read registry from localStorage (locked-cloud deployments REPLACE the whole registry with one cookie-auth cloud entry and force-select it; first install seeds `default-local` only when the launcher supplies host+key) → resolve initial selection: URL pin (validated against registered ids, persisted so later navigation keeps it) > sessionStorage > localStorage → `computeSnapshot`: explicit hit uses it (orgId travels only with it), removed/dangling selection falls through AND drops orgId (@spec BM-003) → fallback ladder above → context mutations (`setActive` no-ops on unchanged id+org; `updateBackend` bumps `connectionRevision` only when host/apiKey changed).
**Invariant:** A cloud active selection must NOT borrow a registered local backend: `getEffectiveLocalBackend()` returns null unless the ACTIVE backend is local (test-pinned "does not borrow"). Removal of the selected backend falls back deterministically (healthy local → any local → index 0 → sentinel), never leaving callers undefined. Tab-scoped reads mean reloading tab A never adopts tab B's backend.
**Probe:** `__tests__/api/backend-registry/active-store.test.ts` (263 L, 18 cases) — healthy-local preference over index-0 cloud (:113–118), skip-unhealthy-local (:120–126), deterministic first-local when ALL unhealthy (:128–139), effective-local cloud exclusivity (:162–167), five URL-pin cases via `bootAt(history.replaceState)+__resetActiveStoreForTests` (:212–262) incl. "URL beats sessionStorage".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "active backend store fallback selection", limit: 10 });
```

## Verdict
Adopt the snapshot-store shape (module snapshot + listeners + `useSyncExternalStore`), the four-rung fallback ladder, tab-scoped selection with mirror-write, and URL-pin-wins-then-persists. Adapt storage keys/validation (`isValidBackend` shape guard, launcher-key re-sync on loopback hosts) to your host. Omit OpenHands' locked-cloud deployment takeover if you have no managed-cloud mode. Coverage: `check_index_coverage` no_recorded_issue on all five source paths + test at gen 2026-08-24T16:13:32Z.
