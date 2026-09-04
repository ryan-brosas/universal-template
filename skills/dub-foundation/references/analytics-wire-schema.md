<!-- capsule-v2 -->
# Analytics wire schema — parse-time ParsedFilter transforms and the pipe-param twin

**Source:** dub AGPL-3.0-or-later main@29df217a29631ced4041882a28d2327cc4546f27; Codebase Memory dub. **Question:** Where exactly does a raw query string like -qr or US,CA become a structured filter, and what is the exact contract of the object handed to Tinybird pipes?

## analyticsQuerySchema (API face) vs analyticsFilterTB (pipe face)
**Path/Symbol:** apps/web/lib/zod/schemas/analytics.ts:analyticsQuerySchema (:56-391), parseAnalyticsQuery (:397-405), analyticsFilterTB (:417-512), eventsFilterTB (:514-523), eventsQuerySchema (:536-556).
**Signature:** zod v4 objects; every filter field is z.string().optional().transform(parseFilterValue); every identity field on the TB side pairs with a <field>Operator enum(["IN","NOT IN"]).optional().
**Data Shape:** API face outputs ParsedFilter {operator, sqlOperator, values} per dimension; TB face outputs comma-JOINABLE strings/arrays plus separate operator params plus ONE JSON filters param for event dims.

### Decisive source
```ts
// API face: transformation happens INSIDE the schema — handlers never see raw strings
linkId: z.string().optional().transform(parseFilterValue).describe("... exclusion (prefix with `-`) ..."),   // :75-83 pattern repeated x20
start: parseDateSchema.refine((v) => v >= DUB_FOUNDING_DATE, {...}).optional(),          // :155-162
// deprecated folds live at the schema/parser boundary:
export function parseAnalyticsQuery(searchParams) {
  const data = analyticsQuerySchema.parse(searchParams);
  if (data.tagIds && !data.tagId) data.tagId = data.tagIds;                               // :400-402
  return data;
}

// PIPE face: identity channel as split-able value + operator pair; dims ONLY via JSON filters
domain: z.union([z.string(), z.array(z.string())]).transform((v) => Array.isArray(v) ? v : v.split(",")).optional(),
domainOperator: z.enum(["IN", "NOT IN"]).optional(),
root: z.union([z.string(), z.boolean()]).transform((v) => typeof v === "boolean" ? v : v === "true" || v === "1" || v === "yes").optional(),
// All dimensional filters now go through the JSON filters parameter            // :507 comment
filters: z.string().optional().describe("JSON array of advanced filters with operators (IN, NOT IN)."),

export const eventsFilterTB = analyticsFilterTB.omit({ granularity: true, timezone: true })
  .and(z.object({ offset: z.coerce.number().default(0), limit: z.coerce.number().default(DEFAULT_PAGINATION_LIMIT), order: ..., sortBy: ... }));
```
(analytics.ts :397-414, :417-523 condensed)

**Flow:** query strings hit analyticsQuerySchema where ~20 fields transform to ParsedFilter AT PARSE TIME; device/browser/os additionally capitalize each value (iOS exempted :261); start refines against DUB_FOUNDING_DATE; booleanQuerySchema (stringbool truthy ["true"]) types root and deprecated qr (:350/:385, misc.ts :23-30); qr reaches the pipe only after prepareFiltersForPipe folds qr&&!trigger into IS_ONE_OF ["qr"] (filter-helpers.ts :37-45); eventsQuerySchema = analyticsQuerySchema minus groupBy plus page/limit(maxPageSize 1000)/sortOrder/sortBy with DEPRECATED order alias. The TB twin re-declares identity fields as split(",") unions with 8 operator pairs (:426,:434,:442,:450,:458,:466,:474,:482) and drops dimensional fields entirely.
**Invariant:** the two faces are deliberately NOT one schema: API face owns negation/negation-examples and normalization; pipe face owns Tinybird's wire constraints (IN|NOT IN only, single-valued root/saleType, no operator on customerId). The 15-field dimensional whitelist lives ONLY in buildAdvancedFilters' SUPPORTED_FIELDS (pass-11 analytics-filter-wire-format) and travels exclusively inside the JSON filters param — adding a dim means touching that whitelist, not the TB schema.
**Probe:** executed at pin: grep -c transform(parseFilterValue) -> 21; grep -n DUB_FOUNDING_DATE -> :11,:156,:157; grep -cF operator enums -> 8 (:426-482 even steps); grep -n booleanQuerySchema -> :17,:350,:385; grep -c centsSchemaWithDefault n/a here. Direct tests: no dedicated unit file for this schema module in tests/analytics (coverage caveat); behavior pinned indirectly by get-events/get-analytics integration suites + pass-11 advanced-filter-helpers unit test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", file_pattern: "zod/schemas/analytics", limit: 20 });
// observed: analyticsFilterTB Variable 417-512; eventsFilterTB 514-523; parseAnalyticsQuery 397-405; eventsQuerySchema 536-556
```

## Verdict
Adopt parse-time filter transformation, schema-level deprecation folding, and the two-face split. Adapt the operator vocabulary to your warehouse. Omit the capitalize layer if your device/browser/os values are already canonical.
