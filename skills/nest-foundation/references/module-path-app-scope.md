<!-- capsule-v2 -->
# RoutesResolver app-scoped MODULE_PATH — how do route registrations find their module prefix without leaking across apps?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** Why is MODULE_PATH metadata read with a per-application suffix, and what is the fallback order?

## getModulePathMetadata / registerRouters / getVersionMetadata
**Path/Symbol:** `packages/core/router/routes-resolver.ts:getModulePathMetadata` (:190-197), `registerRouters` (:95-153), `getVersionMetadata` (:205-215).
**Signature:** `private getModulePathMetadata(metatype): string | undefined`.
**Data Shape:** Metadata key = `MODULE_PATH + modulesContainer.applicationId` (app-scoped) vs bare `MODULE_PATH` (legacy/global); controller version falls back to `versioningConfig.defaultVersion`.

### Decisive source
```ts
const modulesContainer = this.container.getModules();
const modulePath = Reflect.getMetadata(
  MODULE_PATH + modulesContainer.applicationId,   // APP-SCOPED KEY FIRST
  metatype,
);
return modulePath ?? Reflect.getMetadata(MODULE_PATH, metatype);  // legacy fallback

// version: declared @Version() wins over configured defaultVersion:
return Reflect.getMetadata(VERSION_METADATA, metatype) ?? versioningConfig.defaultVersion;
```

**Flow:** for each controller wrapper → read app-scoped module path (written at import/registration time by THIS container instance) → fall back to the unsuffixed legacy key (multi-app interop / older tooling that stamped the shared key) → feed into RoutePathMetadata.modulePath for composition.
**Invariant:** The suffix exists because MULTIPLE Nest applications can live in one process sharing decorator metadata storage — a bare MODULE_PATH stamped by app A would corrupt app B's routing. App-scoped key first, global second, means same-process isolation with graceful degradation. Version resolution only runs when `versioning()` was configured (undefined ⇒ no version metadata consulted at all).
**Probe:** `packages/core/test/router/routes-resolver.spec.ts` (module-path metadata expectations; controller mapping messages).
**Coverage caveat:** the multi-app collision case itself has no dedicated unit spec — source-grounded from the suffix construction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RoutesResolver getModulePathMetadata MODULE_PATH applicationId", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt app-scoped metadata namespacing whenever framework state lives in a global decorator store and multiple instances may coexist; adapt the suffix token; omit the legacy fallback in greenfield ports. Porting wrong: reading only the bare key (cross-app prefix bleed), or defaulting versions when versioning is unconfigured.
