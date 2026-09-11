<!-- capsule-v2 -->
|# Presence-gated config override — only keys the local layer actually defines may override inheritance

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** When merging a row-local config over an inherited/integration config, how do you prevent ABSENT local keys from erasing inherited values through deepMerge?

## Path/Symbol
Generalized from `packages/nocodb/src/models/Source.ts:getConfig` (445–463) + `utils/dataUtils.ts:deepMerge` (89–112); instance evidence: nc_job_015's grandfathering decision.

**Signature:** `buildOverride(local)` = `{k: local[k] for k in OVERRIDE_KEYS if local[k] !== undefined}` then `deepMerge(parent, override)`.

**Data Shape:** override object starts EMPTY; each candidate key added only under an explicit presence test. deepMerge assigns primitives wholesale and recurses objects/arrays (fresh targets allocated).

### Decisive source
```ts
// WRONG (the historical bug): projection emits absent keys as undefined,
// deepMerge writes undefined over the parent's real value.
partialExtract(config, [['connection','database'],['searchPath']])
// RIGHT:
const sourceOverride = {};
if (config?.searchPath !== undefined)          sourceOverride.searchPath = config.searchPath;
if (config?.connection?.database !== undefined) sourceOverride.connection = { database: config.connection.database };
deepMerge(integrationConfig, sourceOverride);
```

**Flow:** decrypt/normalize both layers → build override via per-key presence tests → merge parent←override → post-merge validation of derived fields → effective config.

**Invariant:** (1) Absence is information: missing local key means "inherit", never "erase". (2) Only an ALLOWLIST of keys may override; everything else in the local blob is ignored for merging. (3) Post-merge re-validation catches composites that are individually valid but jointly invalid (empty/ill-typed searchPath stripped). (4) This mechanism is why the search-path grandfathering migration exists — see config-merge-override-discipline.md (Source funnel details) and migration-searchpath-grandfather.md (behavior-preservation backfill).

**Probe:** no unit test upstream. Source-grounded probe: Source.ts:449-455 incident comment verbatim, :456-463 correct construction, :465-472 post-merge strip, dataUtils.ts:96-108 merge semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "deepMerge partialExtract sourceOverride getConfig", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt presence-gated allowlisted overrides over extract-with-defaults; adapt key sets; omit the meta-source short-circuit. Coverage caveat: no in-repo unit tests; source-grounded.
