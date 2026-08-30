<!-- capsule-v2 -->
# Handler cascade — who elects the active profile, and which reload level clears which cache?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does an agent runtime elect one active configuration profile from many, and how do top-level re-elections differ from bottom-level reloads so caches never go stale or duplicate?

## Constructor-fired election cascade with three entry levels
**Path/Symbol:** `core/config/ConfigHandler.ts` (whole file, 369 lines): `cascadeInit` (83–136), `setSelectedProfileId` (207–231), `reloadConfig` (237–283), `getWorkspaceId` (76–81), `additionalContextProviders` (354–368).
**Signature:** `cascadeInit(reason: string): Promise<void>` ; `setSelectedProfileId(profileId: string): Promise<void>` ; `reloadConfig(reason: string, injectErrors?: ConfigValidationError[]): Promise<ConfigResult<ContinueConfig>>`.
**Data Shape:** state = `profiles: ProfileLifecycleManager[]`, `currentProfile | null`, `workspaceDirs: string[] | null` (cache), `totalConfigReloads` counter; persistence key `lastSelectedProfileForWorkspace: Record<workspaceId, profileId>` where `workspaceId = workspaceDirs.join("&")`.

### Decisive source
```ts
// constructor: fire-and-forget init; awaiters gate on isInitialized, not on success
this.isInitialized = new Promise((resolve) => { this.initter.on("init", resolve); });
void this.cascadeInit("Config handler initialization");

// cascadeInit catch: error case STILL emits "init" before rethrowing
} catch (e) {
  if (signal.aborted) return;
  else { this.initter.emit("init"); throw e; } // Error case counts as init
}

// election: stored selection wins only if it still exists; fallback becomes sticky
const currentSelection = selectedProfiles[workspaceId];
const fallback = profiles.length > 0 ? profiles[0] : null;
selectedProfile = currentSelection ? (match ?? fallback) : fallback;
if (selectedProfile) this.globalContext.update("lastSelectedProfileForWorkspace",
  { ...selectedProfiles, [workspaceId]: selectedProfile.profileDescription.id });

// bottom level: drop OTHER profiles' caches, keep current's; inject errors at the head
for (const profile of this.profiles)
  if (profile.profileDescription.id !== this.currentProfile.profileDescription.id)
    profile.clearConfig();
const { config, errors = [], configLoadInterrupted } =
  await this.currentProfile.reloadConfig(this.additionalContextProviders);
if (injectErrors) errors.unshift(...injectErrors);
```

**Flow:** constructor / `refreshAll(reason)` / `updateIdeSettings` → `abortCascade()` (new AbortController per cascade) → `cascadeInit`: null the workspaceDirs cache, REBUILD `globalLocalProfileManager` fresh, loadProfiles (failure captured as fatal error + empty list, never thrown), elect profile (stored-id match else first), persist the (possibly fallback) choice, then bottom-level `reloadConfig`. `setSelectedProfileId` skips re-election: early-return when id unchanged, THROW on unknown id, persist, swap pointer, `reloadConfig("Selected profile changed")`. `registerCustomContextProvider` pushes and fire-and-forget reloads.
**Invariant:** exactly ONE elected profile owns cached config state — every reload drops all other profiles' cached results, and every load path (`reloadConfig`/`getSerializedConfig`/`loadConfig`) funnels through `currentProfile` with the same injected `additionalContextProviders`; awaiters of `isInitialized` always resolve (the failure path emits `"init"` too), so a broken startup degrades to an interrupted ConfigResult rather than a hung consumer.
**Probe:** no dedicated ConfigHandler suite exists at this pin (recorded caveat). Source-pinned observables: `setSelectedProfileId(currentId)` returns before any GlobalContext write or reload (:208–213); unknown id throws `Profile ${id} not found` (:217–218); `doLoadConfig.vitest.ts` exercises the downstream half of this contract (profile loader mocks).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "ConfigHandler reload refresh profiles", limit: 10 });
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.ConfigHandler.ConfigHandler.cascadeInit", direction: "inbound", depth: 2 });
// observed callers_total 3: constructor, refreshAll, updateIdeSettings — exactly the top-of-cascade entries
```

## Verdict
Adopt the three-level cascade (re-election vs switch vs bottom reload), the emit-init-on-error handshake, sticky-fallback election persistence, and clearing sibling-profile caches while keeping the active one; adapt the workspace identity key (dir-join `"&"`) and provider injection to your host's notion of session scope; omit the AbortController dance if your cascades cannot overlap. Trap: a mid-level switch deliberately does NOT reset the workspaceDirs cache — only full cascades do.
