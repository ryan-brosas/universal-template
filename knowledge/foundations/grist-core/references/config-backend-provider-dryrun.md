<!-- capsule-v2 -->
# ConfigBackendAPI provider dry-run — how do you validate a login-provider config against the POST-RESTART environment without restarting, and which boolean flags describe the active→next transition?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does the admin config API decide "configured / canBeActivated / willBeActive / willBeDisabled" by dry-running readers over a hypothetical future settings object?

## Dry-run every provider reader against a fresh AppSettings carrying candidate env vars
**Path/Symbol:** `app/server/lib/ConfigBackendAPI.ts` — `ConfigBackendAPI.addEndpoints()` (:23–106), `_buildProviderList()` (:111–139), exported-for-tests `_fillProviderInfo()` (:146–205).
**Signature:** `_fillProviderInfo({ currentSettings: AppSettings, newSettings: AppSettings, providers: AuthProvider[] }): AuthProvider[]`.
**Data Shape:** `AuthProvider = { name, key, metadata?, isConfigured?, configError?, isActive?, activeError?, isSelectedByEnv?, willBeActive?, willBeDisabled?, canBeActivated? }`. Candidate env comes from `ActivationsManager.current().prefs?.envVars` (DB-persisted env overlay). `NotConfiguredError` = "reader ran fine but nothing configured"; any OTHER throw becomes `configError`.

### Decisive source
```ts
// ConfigBackendAPI.ts:113-135 — the dry-run loop
const newSettings = new AppSettings("grist");
newSettings.setEnvVars((await this._activations.current()).prefs?.envVars || {});
const providers: AuthProvider[] = [];
for (const { key, name, reader: configuredCheck, metadataReader } of LOGIN_SYSTEMS) {
  const record: AuthProvider = { name, key };
  try {
    configuredCheck(newSettings);                       // may THROW NotConfiguredError or real errors
    record.metadata = metadataReader?.(newSettings) ?? {};
    record.isConfigured = true;
  } catch (e) {
    if (e instanceof NotConfiguredError) { record.isConfigured = false; }
    else { record.configError = (e as Error).message; }
  }
  providers.push(record);
}
```

**Flow:** set-active route validates `providerKey` against the built list OR `FALLBACK_PROVIDER_KEY` → writes `GRIST_LOGIN_SYSTEM_TYPE` into DB env via `updateEnvVars` (:48) → sets `onRestartClearSessions: true` (:50) → takes effect only after restart. The transition matrix in `_fillProviderInfo`: `next = newFromConfig || first(isConfigured||configError) || active`; `isActive = key===active && key===next`; `willBeActive = key===next && key!==active`; `willBeDisabled = key===active && key!==next`; `canBeActivated = isConfigured && key!==next && !isNewFixedByEnv`; duplicate-error clearing when `activeError === configError` (:179); final pass deletes all `undefined`/`false` fields for clean test snapshots (:194–202).
**Invariant:** The SAME reader functions serve runtime boot AND admin-UI status — a provider is "configured" iff its reader does not throw `NotConfiguredError`, so adding a login system requires only a `LOGIN_SYSTEMS` entry with a throwing-or-not reader; there is no separate validation schema to drift. Env-selected providers are LOCKED: `isNewFixedByEnv` suppresses every `canBeActivated` (:191).
**Probe:** `test/server/lib/ConfigBackendAPI.ts` (`fillProviderInfo` suite :40–207: empty list, active-configured mark, change-by-configuration, selection-by-database, selection-by-env-variable "not offer to change", config-error-prevents-activation, runtime-error-on-active). Source pins: `grep -c 'onRestartClearSessions' app/server/lib/ConfigBackendAPI.ts` = 2 (:50/:81); transition-field count `grep -c 'willBeDisabled\|willBeActive\|canBeActivated\|isSelectedByEnv' app/server/lib/ConfigBackendAPI.ts` = 4.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"ConfigBackendAPI addEndpoints _fillProviderInfo auth-providers","limit":10,"detail":"ids"}'
```

## Verdict
Adopt the dry-run-against-future-env pattern and the full transition-flag matrix (it is directly tested); adapt ActivationsManager persistence to any durable env-overlay store; omit getgrist.com-specific PATCH secret handling unless porting that SaaS surface. Direct mocha coverage at this pin; runner-blocked locally — probes recorded as source-pinned assertions.
