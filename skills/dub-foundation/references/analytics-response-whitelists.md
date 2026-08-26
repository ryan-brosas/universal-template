<!-- capsule-v2 -->
# Analytics response whitelists — endpoint-keyed strict shapes as the API exit gate

**Source:** dub AGPL-3.0-or-later main@29df217a29631ced4041882a28d2327cc4546f27; Codebase Memory dub. **Question:** How do you guarantee warehouse columns and internal fields can never leak into an analytics API response, while keeping codegen-friendly defaults?

## One record keyed by VALID_ANALYTICS_ENDPOINTS; .parse as projection
**Path/Symbol:** apps/web/lib/zod/schemas/analytics-response.ts:analyticsResponse (:29-503); money type schemas/utils.ts:centsSchemaWithDefault (:15-18); partner reuse partners.ts:partnersTopLinksSchema/partnerAnalyticsResponseSchema (:853-871).
**Signature:** Record<AnalyticsGroupByOptions, z.ZodObject>; consumed as analyticsResponse[groupBy].parse(rows) at every getAnalytics return.
**Data Shape:** metric columns clicks/leads/sales .number().default(0); saleAmount = centsSchemaWithDefault (preprocess bigint|string->Number wrapping z.number().default(0)); geo rows encode drill-down depth with literal * defaults.

### Decisive source
```ts
/** Accepts number (before migration) or bigint (after), outputs number. */
const coerceToNumber = (n: unknown) => typeof n === "bigint" || typeof n === "string" ? Number(n) : n;
export const centsSchemaWithDefault = z.preprocess(coerceToNumber, z.number().default(0));
// default sits on the INNER z.number() so code generators (e.g. Speakeasy) introspect it through the preprocess layer

countries: z.object({ country: z.string(), region: z.literal("*").default("*"), city: z.literal("*").default("*"), clicks..., leads..., sales..., saleAmount }),
top_links: z.object({ link: z.string().meta({deprecated:true}), id: z.string(), domain, key, shortLink, url, title?, comments?, folderId?, partnerId?, createdAt, clicks...}),   // :251-288

// partner plane EXTENDS instead of duplicating:
const earningsSchema = z.object({ earnings: z.number().default(0) });
export const partnersTopLinksSchema = analyticsResponse["top_links"].extend(earningsSchema.shape);
export const partnerAnalyticsResponseSchema = { count: analyticsResponse["count"].extend(earningsSchema.shape)... } as const;
```
(schemas/utils.ts :7-18; analytics-response.ts :81-104, :251-288; partners.ts :849-871 condensed)

**Flow:** every getAnalytics branch ends in analyticsResponse[groupBy].parse(...) — parse IS the whitelist projection (unknown keys stripped, missing metrics defaulted to 0, bigint cents coerced). Tests pin the same shapes from the OUTSIDE with .strict() copies (get-events.test.ts :40/:56/:72, partners/analytics.test.ts :28-29), so any new column must be added deliberately to both sides. Geo drill-down is encoded structurally: countries rows carry region:* city:*, regions rows carry city:* — depth is data, not separate endpoints.
**Invariant:** the record keys ARE VALID_ANALYTICS_ENDPOINTS (as const) — a new endpoint without a whitelist entry is a compile/type error at the parse site. centsSchemaWithDefault keeps its default UNDER the preprocess so OpenAPI/codegen surfaces still show default 0. Deprecated top_links.link stays alongside id for SDK back-compat.
**Probe:** executed at pin: grep -c centsSchemaWithDefault analytics-response.ts -> 27; grep -n literal-star defaults -> :87,:88,:115; grep -n earningsSchema.shape partners.ts -> :854,:858,:863; grep -n top_links response key -> :251. Coverage caveat: no standalone unit test parses these schemas in tests/analytics — they are exercised through CI-gated integration suites listed above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", file_pattern: "zod/schemas/analytics-response", limit: 10 });
// observed: analyticsResponse Variable 29-503; analyticsTriggersResponse 8-27
```

## Verdict
Adopt the endpoint-keyed record, parse-as-projection discipline, inner-default preprocess money type, structural drill-down literals, and extend-don't-duplicate partner overlays. Adapt column names freely — the SHAPE of the guarantee is what ports.