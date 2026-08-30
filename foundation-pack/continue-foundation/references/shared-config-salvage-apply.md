<!-- capsule-v2 -->
# Shared-config salvage & four-shape apply — how does org policy reach every config shape without crashing on damaged files?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How do you apply one organization-level settings object to FOUR structurally different config representations, salvaging what you can when the shared file itself is corrupt?

## Salvage-then-apply over a flat partial schema
**Path/Symbol:** `core/config/sharedConfig.ts:sharedConfigSchema` (10–43), `salvageSharedConfig` (48–77), `modifyAnyConfigWithSharedConfig` (91–201).
**Signature:** `salvageSharedConfig(sharedConfig: object): SharedConfigSchema` ; `modifyAnyConfigWithSharedConfig<T extends ContinueConfig | BrowserSerializedContinueConfig | Config | SerializedContinueConfig>(continueConfig: T, sharedConfig: SharedConfigSchema): T`.
**Data Shape:** one flat zod `.partial()` object whose comment groups map each field to its target subobject (top-level booleans / `experimental` / `ui` / `tabAutocompleteOptions`). Apply RENAMES three fields on the way in: `useAutocompleteCache→useCache`, `useAutocompleteMultilineCompletions→multilineCompletions`, `disableAutocompleteInFiles→disableInFiles`.

### Decisive source
```ts
// For security in case of damaged config file, try to salvage any security-related values
export function salvageSharedConfig(sharedConfig: object): SharedConfigSchema {
  const salvagedConfig: SharedConfigSchema = {};
  if ("allowAnonymousTelemetry" in sharedConfig) {
    const val = z.boolean().safeParse(sharedConfig.allowAnonymousTelemetry);
    if (val.success) salvagedConfig.allowAnonymousTelemetry = val.data;   // never throws
  }
  // ...same pattern for disableIndexing, disableSessionTitles, disableAutocompleteInFiles
  return salvagedConfig;
}

export function modifyAnyConfigWithSharedConfig<T extends /* 4 shapes */>(continueConfig: T, sharedConfig: SharedConfigSchema): T {
  const configCopy = { ...continueConfig };
  configCopy.tabAutocompleteOptions = { ...configCopy.tabAutocompleteOptions };   // clone BEFORE field writes
  if (sharedConfig.useAutocompleteCache !== undefined) {
    configCopy.tabAutocompleteOptions.useCache = sharedConfig.useAutocompleteCache;   // undefined-gated write
  }
  // ...ui/experimental cloned likewise; top-level booleans written directly
  return configCopy;
}
```

**Flow:** read shared config → salvage security-relevant fields with per-field `safeParse` (damaged file yields partial object, not an exception) → for each of the four shapes, clone nested objects then copy every defined field into its renamed slot.
**Invariant:** salvage NEVER throws and returns only validated fields; apply is total across all four shapes because it is generic over their union; an `undefined` org value can never erase a local value (every write is gated on `!== undefined`). The source comment records the two-step split rationale: security flags must be applied BEFORE remote-config merge on the JSON plane, while role selections are added after, since serialized shapes lack them.
**Probe:** no direct suite at this pin (runner block recorded); source-pinned observable: `salvageSharedConfig({ allowAnonymousTelemetry: "yes", disableIndexing: true })` returns exactly `{ disableIndexing: true }`. Call-site evidence: applied LAST on the YAML plane via GlobalContext inside `loadContinueConfigFromYaml`, deliberately NOT try/caught ("has security implications and failure should be fatal" — see yaml-compile-ladder.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "salvageSharedConfig modifyAnyConfigWithSharedConfig", limit: 5 });
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.sharedConfig.modifyAnyConfigWithSharedConfig", direction: "inbound", depth: 2 });
// observed inbound: yaml plane applies it last; migrateJsonSharedConfig handles legacy JSON one-shot migration
```

## Verdict
Adopt per-field `safeParse` salvage for untrusted/partial policy files and undefined-gated rename-mapped application generic over your config shapes; adapt the field table to your domain; omit the four-shape union if you have one canonical shape. Coverage caveat: behavior verified by direct source read + call-site inspection only (no installed runner).
