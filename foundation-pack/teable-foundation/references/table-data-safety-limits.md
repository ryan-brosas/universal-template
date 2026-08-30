<!-- capsule-v2 -->
# Table data-safety limits — how does teable derive a multi-section resource-limit config from environment variables with aliased fallbacks?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does teable build a typed, nested resource-limit configuration from env vars, tolerating aliases and invalid values, so a porter gets a safe defaults-and-overrides resolver?

## Env-driven nested config with alias fallback
**Path/Symbol:** `packages/v2/container-node/src/tableDataSafetyLimits.ts` — `resolveTableDataSafetyLimitsFromEnv` (17–63), helpers `parsePositiveInteger` (3–7), `firstPositiveInteger` (9–15).
**Signature:** `resolveTableDataSafetyLimitsFromEnv(): TableDataSafetyLimitConfig`.
**Data Shape:** returns `{fieldOptions, recordValues, computed, tableSchema, viewConfig, displayText}` — each a nested object of `number|undefined` limits. Every limit reads one or more env vars (aliases) and takes the first positive integer found; invalid/non-integer/≤0 values silently become `undefined` (unset limit).

### Decisive source
```ts
const parsePositiveInteger = (value) => {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
};
const firstPositiveInteger = (...values) => {
  for (const value of values) { const parsed = parsePositiveInteger(value); if (parsed != null) return parsed; }
  return undefined;
};
export const resolveTableDataSafetyLimitsFromEnv = () => ({
  fieldOptions: { maxBytes: firstPositiveInteger(process.env.TABLE_LIMIT_FIELD_OPTIONS_MAX_BYTES),
    maxSelectChoices: firstPositiveInteger(process.env.TABLE_LIMIT_SELECT_CHOICES_MAX, process.env.MAX_SELECT_FIELD_OPTIONS_PER_FIELD), ... },
  ...
});
```
**Flow:** for each limit, `firstPositiveInteger` scans its env aliases in order and returns the first that parses to a positive integer; otherwise `undefined`. Aliases let legacy env names (e.g. `MAX_SELECT_FIELD_OPTIONS_PER_FIELD`, `MAX_TABLE_FIELDS_PER_TABLE`) keep working alongside the canonical `TABLE_LIMIT_*` names. The result is a fully-typed nested config consumed by the v2-core safety-limit checks.
**Invariant:** a limit is only ever a positive integer or `undefined` (never zero/negative/NaN); alias precedence is left-to-right; an unset or invalid limit means "no limit enforced" rather than a crash or a wrong value.
**Probe:** no direct unit spec exists for `resolveTableDataSafetyLimitsFromEnv`; it is pure and unit-testable by setting `process.env` before calling. The benchmark harness `packages/v2/benchmark-node/src/benchmarkTableDataSafetyLimits.ts` exercises the config, and v2-core consumers enforce the limits. Coverage caveat: no direct test file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "resolveTableDataSafetyLimitsFromEnv firstPositiveInteger", limit: 10,, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the env-driven nested config resolver with `firstPositiveInteger` alias fallback and undefined-as-unset semantics. Adapt the limit keys and env names to your domain. Omit teable's specific limit values and the enforcement checks (those live in v2-core consumers).
