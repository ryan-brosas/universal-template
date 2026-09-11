<!-- capsule-v2 -->
# Limit/offset admission — where do invalid page params get silently coerced, and which caller can override the clamp?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What happens to limit=-5, limit=1e9, offset='abc', and who may bypass the 1000 cap?

## Silent-coercion funnel with a single override hatch
**Path/Symbol:** `packages/nocodb/src/helpers/extractLimitAndOffset.ts:extractLimitAndOffset` (:44–86) + `defaultLimitConfig`/`defaultGroupByLimitConfig` (:1–42); consumed by PagedResponseImpl (:62).
**Signature:** `extractLimitAndOffset(args: {limit?, offset?, l?, o?, limitOverride?, page?}): {limit?: number, offset?: number}`.
**Data Shape:** defaults env-tunable (NC_DB_QUERY_LIMIT_*, DB_QUERY_LIMIT_* legacy): default 25 / min 1 / max 1000 / ltarV3Limit 1000; group-by: group 25, records-per-group 10.

### Decisive source
```ts
const limit = +(args.limit || args.l);
obj.limit = Math.max(
  Math.min(
    limit && limit > 0 && Number.isInteger(limit)
      ? limit
      : defaultLimitConfig.limitDefault,
    defaultLimitConfig.limitMax,
  ),
  defaultLimitConfig.limitMin,
);

if (args.page) {
  obj.offset = Math.max((+args.page - 1) * obj.limit, 0);
} else {
  const offset = +(args.offset || args.o) || 0;
  obj.offset = Math.max(Number.isInteger(offset) ? offset : 0, 0);
}
// override limit if provided
if (args.limitOverride) {
  obj.limit = +args.limitOverride;
}
```
(:62–:83)

**Flow:** limit: non-positive/non-integer/NaN → DEFAULT (silent, no error), then clamp [min,max] → offset: `page` wins over raw offset ((page−1)×limit floored at 0); invalid offset strings coerce to 0; negative clamps to 0 → limitOverride is applied LAST and UNCLAMPED — the deliberate escape hatch for internal callers (LTAR nested fetches etc.).
**Invariant:** client input can never ERROR here, only degrade to defaults — validation errors would break spreadsheets that persist bad view settings. limitOverride must be reachable ONLY from trusted server-side call sites; it skips min AND max. The l/o aliases are legacy API spellings kept co-equal with limit/offset.
**Probe:** `cd packages/nocodb && grep -c "Number.isInteger" src/helpers/extractLimitAndOffset.ts` (=2: limit + offset) and `grep -c "limitOverride" src/helpers/extractLimitAndOffset.ts` (=3: type + doc-comment + apply).
**Direct test:** none upstream for this helper — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "extractLimitAndOffset limitOverride limitMax defaultLimitConfig", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt silent coercion + clamp + unclamped internal override; adapt the env names/defaults; omit if your API contract prefers 400s over silent defaults. Coverage caveat: grep-pinned only.
