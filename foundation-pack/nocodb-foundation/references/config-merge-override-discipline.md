<!-- capsule-v2 -->
|# Config-merge override discipline at the Source funnel — merge, post-validate, mssql-normalize

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** How does Source.getConfig orchestrate decryption → integration merge → validation → driver coercion — the funnel every connection path passes through?

## Path/Symbol
`packages/nocodb/src/models/Source.ts:getConfig` (419–475), `getSourceConfig` (477–479); helpers presence-gated-override.md + driver-coercion-funnel.md; consumer migration-searchpath-grandfather.md.

**Signature:** `getConfig(skipIntegrationConfig = false): any` — false merges integration config under source config; true returns the decrypted source config alone (this is getSourceConfig()).

**Data Shape:** integration_config and source config are encrypted-at-rest JSON. Only TWO keys may override: `searchPath` and `connection.database`. Meta sources short-circuit to the app meta db config. All three exit paths end in normalizeMssqlConfig.

### Decisive source
```ts
if (skipIntegrationConfig) return this.normalizeMssqlConfig(config);
if (!this.integration_config) return this.normalizeMssqlConfig(config);
const integrationConfig = decryptPropIfRequired({ data: this, prop: 'integration_config' });
// ... presence-gated sourceOverride build ...
let mergedConfig = deepMerge(integrationConfig, sourceOverride);
// if searchPath is not array/string or if an empty array, remove it
if ((!Array.isArray(mergedConfig.searchPath) && typeof mergedConfig.searchPath !== 'string')
    || !mergedConfig.searchPath?.length) {
  mergedConfig = { ...mergedConfig, searchPath: undefined };
}
return this.normalizeMssqlConfig(mergedConfig);
```

**Flow:** is_meta → meta db config · decrypt own · skipIntegration → normalize+return · no integration → normalize+return · else decrypt integration, presence-gated override, deepMerge, POST-MERGE searchPath shape validation → normalizeMssqlConfig.

**Invariant:** (1) Presence-gated override construction (see presence-gated-override.md) — the historical partialExtract bug erased inherited schemas via undefined keys. (2) Post-merge VALIDATION is a separate step from merging: valid inputs can compose an invalid whole. (3) The two-key override allowlist is deliberate scope-minimization: other local keys never affect the effective connection. (4) getSourceConfig(true) gives the PRE-merge view — exactly what grandfathering logic needs to ask "does this row carry its own value?" (5) Driver coercion happens once, after every branch converges.

**Probe:** no unit test upstream. Source-grounded probe: Source.ts:419-442 (branch structure), :449-455 (incident comment), :465-472 (post-merge strip), :364-366 (funnel comment).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "Source getConfig skipIntegrationConfig decryptPropIfRequired", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt decrypt→presence-gated-merge→post-validate→single-funnel-normalize as the config-resolution ladder; adapt key allowlists; omit the meta-source short-circuit unless hosting has one. Coverage caveat: no in-repo unit tests; source-grounded.
