<!-- capsule-v2 -->
# Provider profiles in secrets — how do you store multi-config API settings safely and migrate them without data loss?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Where do named provider profiles live, how do reads survive corrupt/retired entries, and what does the migration-flag ledger guarantee?

## Promise-chain lock; secrets-backed JSON; per-entry sanitize with retired passthrough
**Path/Symbol:** `src/core/config/ProviderSettingsManager.ts` (class :44-662; `SCOPE_PREFIX = "roo_cline_config_"` :45; promise-chain `lock` :86-92; `initialize()` migration ladder :95-170; `load()` :573-628; per-mode map seeding :108-122; `listConfig`/`saveConfig`/`deleteConfig` :326-500).
**Signature:** `load(): Promise<ProviderProfiles>`; `saveConfig(name, config): Promise<string>`; schema = `{currentApiConfigName, apiConfigs: Record<name, ProviderSettingsWithId>, modeApiConfigs?, migrations?: {...five flags}}`.
**Data Shape:** Whole profile document stored under ONE secrets key (`roo_cline_config_api_config`); each config carries a generated id (`Math.random().toString(36)` 13 chars); `modeApiConfigs: Record<modeSlug, configId>`.

### Decisive source
```ts
// Synchronize readConfig/writeConfig operations to avoid data loss:
private _lock = Promise.resolve()
private lock<T>(cb: () => Promise<T>) {
    const next = this._lock.then(cb)
    this._lock = next.catch(() => {}) as Promise<void>   // chain NEVER rejects
    return next
}
// load(): outer schema extended to z.any() per-config, THEN per-entry:
const sanitizedConfig = this.sanitizeProviderConfig(apiConfig)     // unknown provider → drop entry
const schema = isRetiredProvider(providerValue)
    ? providerSettingsWithIdSchema.passthrough()                   // KEEP legacy fields
    : providerSettingsWithIdSchema                                 // strict parse strips extras
const result = schema.safeParse(sanitizedConfig)
return result.success ? {...acc, [key]: result.data} : acc          // failed entry skipped, not fatal
```
`initialize()` runs INSIDE the lock: missing doc → write defaults; missing `modeApiConfigs` → seed ALL modes with current config's id (fallback first-any, then default); id-less configs get ids; missing `migrations` ledger initialized all-false; each un-migrated flag runs its migration then flips true — fresh installs start all-true so they never re-run.
**Flow:** constructor fire-and-forget initialize → every read/write serialized through the promise-chain lock → load sanitizes + parses per entry → migrations mutate + mark dirty → single store() persists.
**Invariant:** The lock chain never breaks on error; one poisoned config cannot fail the whole profile load (skip-not-crash) yet retired providers keep their vendor fields via passthrough; migration flags make every data move exactly-once even across crash-retries; ids are assigned before anything references them.
**Probe:** `src/core/config/__tests__/ProviderSettingsManager.spec.ts` (:42 no write when storage empty, :78 generates ids for id-less configs, :107/:146/:186 individual migration flags, :227 throws when storage fails, :458 retired-provider legacy keys preserved).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "ProviderSettingsManager providerProfilesSchema migrate lock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt secrets-backed single-document profiles, the rejecting-immune promise-chain lock, skip-poisoned-entry loads, and the boolean migration ledger. Adapt key names/schema. Do not replace the ledger with schema-version ints — independent flags let migrations ship independently without a big-bang version bump.
