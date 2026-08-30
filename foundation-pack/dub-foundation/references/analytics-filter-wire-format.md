<!-- capsule-v2 -->
# ParsedFilter wire algebra — comma/negation syntax to SQL-safe structured filters

**Source:** dub AGPL-3.0-or-later `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** How does a raw query value like `-US,CA` become a typed, injection-safe filter object shared by API, dashboard, and warehouse?

## parseFilterValue + the web-side helper quartet
**Path/Symbol:** `packages/utils/src/functions/parse-filter-value.ts:parseFilterValue` (:25-55) + `buildFilterValue` (:63-66) + `FilterOperator` type (:1); `apps/web/lib/analytics/filter-helpers.ts`: `ensureParsedFilter` (:69-81), `prepareFiltersForPipe` (:30-60), `extractWorkspaceLinkFilters` (:90-134), `buildAdvancedFilters` (:161-178).
**Signature:** `parseFilterValue(value: string | string[] | undefined): ParsedFilter | undefined`.
**Data Shape:** `{ operator: "IS"|"IS_NOT"|"IS_ONE_OF"|"IS_NOT_ONE_OF" (display), sqlOperator: "IN"|"NOT IN" (SQL), values: string[] }` — display and SQL operators are deliberately SEPARATE fields.

### Decisive source
```ts
const isNegated = value.startsWith("-");
const cleanValue = isNegated ? value.slice(1) : value;
const values = cleanValue.split(",").filter(Boolean);

if (values.length === 0) return undefined;

const operator: FilterOperator = isNegated
  ? values.length > 1 ? "IS_NOT_ONE_OF" : "IS_NOT"
  : values.length > 1 ? "IS_ONE_OF" : "IS";

const sqlOperator: SQLOperator = isNegated ? "NOT IN" : "IN";
```
(parse-filter-value.ts :37-48)

```ts
const extractFilter = (filter?: ParsedFilter) => ({
  values: filter?.values,
  operator: (filter?.sqlOperator === "NOT IN" ? "NOT IN" : "IN"),
});
```
(filter-helpers.ts :100-105)

**Flow:** leading `-` negates the WHOLE list (never per-item); empty/all-comma input → undefined; array input keeps order and picks IS vs IS_ONE_OF by length. Web side: `ensureParsedFilter` lifts bare strings to `{IS, IN, [v]}`; `prepareFiltersForPipe` folds deprecated boolean `qr` into `trigger:["qr"]` and splits `"US-CA"` regions into country=US filter + region=CA param; `extractWorkspaceLinkFilters` collapses display operators to pure SQL operators for pipes; `buildAdvancedFilters` walks the closed 15-entry `SUPPORTED_FIELDS` table emitting `{field, operator, values}` triples for the JSON channel.
**Invariant:** values are data, never spliced into SQL — every consumer binds them as parameters (MySQL placeholders or Tinybird JSON filters), so commas/negations cannot smuggle syntax.

**Probe:** executed: `grep -n 'IS_NOT_ONE_OF' packages/utils/src/functions/parse-filter-value.ts` → :1 (type); `grep -n 'isNegated ? value.slice(1)' ...` → :39; `grep -n '"qr"' apps/web/lib/analytics/filter-helpers.ts` → :42; `grep -n 'sqlOperator === "NOT IN"' ...` → :102. Direct test `tests/analytics/advanced-filter-helpers.test.ts` (:1-660, pure unit) pins exact shapes — single :13-20, negated :22-29, multi :32-58, empty-inputs :61-91 — runner offline-blocked, anchors line-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", name_pattern: "^(parseFilterValue|buildFilterValue)$", limit: 5, fields: ["signature"] });
```
(observed: parseFilterValue 25-55, buildFilterValue 63-66.)

## Verdict
Adopt the dual-operator ParsedFilter algebra and whole-list negation prefix. Adapt the operator vocabulary to your SQL dialect. Omit nothing; keep the closed field whitelist when porting buildAdvancedFilters.
