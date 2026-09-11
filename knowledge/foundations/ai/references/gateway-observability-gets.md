<!-- capsule-v2 -->
# Gateway observability GET endpoints — why do credits/spend/generation-info hit the ORIGIN while model config rides baseURL, and why is everything a GET with query params?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How are the billing/telemetry read APIs shaped, and what does the snake_case→camelCase boundary own?

## Origin-relative GET trio + zod transform boundary
**Path/Symbol:** `packages/gateway/src/gateway-fetch-metadata.ts:getCredits` (58–82); `gateway-spend-report.ts:getSpendReport` (76–128); `gateway-generation-info.ts:getGenerationInfo` (61–87).
**Signature:** `getCredits(): Promise<{balance: string; totalUsed: string}>`; `getSpendReport(params): Promise<{results: GatewaySpendReportRow[]}>`; `getGenerationInfo({id}): Promise<GatewayGenerationInfo>`.
**Data Shape:** All three use `new URL(this.config.baseURL)` then call `${baseUrl.origin}/v1/...` (`/v1/credits`, `/v1/report?<searchParams>`, `/v1/generation?id=<encodeURIComponent>`), with `validateUrl: false`. Spend params map camelCase→snake_case (`groupBy→group_by`, `credentialType→credential_type`, `tags.join(',')`). Response schemas use zod `.transform` to rename snake_case→camelCase and to conditionally spread optional fields; generation info unwraps a `{data: …}` envelope via chained transform.

### Decisive source
```ts
const baseUrl = new URL(this.config.baseURL);
const { value } = await getFromApi({
  url: `${baseUrl.origin}/v1/credits`,
  validateUrl: false,   // deliberate: gateway origin already trusted + credentialed
  …
});
// spend report row transform (conditional spread keeps absent metrics absent):
...(cached_input_tokens !== undefined ? { cachedInputTokens: cached_input_tokens } : {}),
```
```ts
// generation info envelope unwrap:
.transform(({ data }) => data)
```

**Flow:** provider method → dedicated fetcher class → getFromApi with resolved headers → zod parse+rename → typed result; every catch funnels through `asGatewayError`.
**Invariant:** Billing/read routes live at the ORIGIN (`/v1/*`) while inference/config routes live under the `/v4/ai` baseURL prefix — porters who append `/v1/credits` to baseURL build `…/v4/ai/v1/credits` and 404. Optional numeric fields must stay ABSENT when the wire omits them (conditional spread, not `undefined` assignment) so consumers can distinguish 0 from unreported. `tags` serializes as ONE comma-joined param, not repeated params.
**Probe:** `grep -cF "params.tags.join(',')" packages/gateway/src/gateway-spend-report.ts` → `1`; `grep -cF '${baseUrl.origin}/v1/generation?id=' packages/gateway/src/gateway-generation-info.ts` → `1`; direct tests: gateway-spend-report.test.ts 'should serialize all optional query params' + 'should transform credential_type to credentialType in response'; gateway-fetch-metadata.test.ts 'should fetch credits from the correct endpoint'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "GatewaySpendReport getSpendReport searchParams group_by", limit: 10 });
```
Resolves line-exact: `getSpendReport Method gateway-spend-report.ts 76-128`.

## Verdict
Adopt origin-vs-prefix URL split for mixed-route APIs and the transform-at-boundary renaming; adapt route names; omit nothing — the conditional-spread rule is invisible until a consumer branches on `'field' in result`.
