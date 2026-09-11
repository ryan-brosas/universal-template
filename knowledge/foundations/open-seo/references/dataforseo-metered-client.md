<!-- capsule-v2 -->
# DataForSEO metered client — how do you wrap a paid third-party SDK so every call is charged exactly once and the 3MB SDK never enters eager startup?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** What is the single metering point's control flow, including the charged-but-failed case?

## meter() proxy + meterDataforseoCall seam
**Path/Symbol:** `src/server/lib/dataforseo/client.ts:meter` (:48-61), `meterDataforseoCall` (:154-205), `createDataforseoClient` (:63-152), `loadDataforseoSections` (:27-31).
**Signature:** `function meter<I, T>(customer: BillingCustomerContext, pick: (sections: DataforseoSections) => (input: I) => Promise<DataforseoApiResponse<T>>, defaultFeature?: CreditFeature): (input: I & { creditFeature?: CreditFeature }) => Promise<T>`.
**Data Shape:** Every section fetcher returns `DataforseoApiResponse<T> = { data: T; billing: { path: string[]; costUsd: number } }`; callers can override the credit feature per call via `input.creditFeature`.

### Decisive source
```ts
const result = await execute();            // inside meterDataforseoCall
} catch (error) {
  if (error instanceof DataforseoChargedTaskError) {
    // A malformed request … that DataForSEO did not bill returns no value to the
    // customer, so don't charge — … If DataForSEO still billed us
    // (costUsd > 0), fall through to the normal charge + capture path so the
    // spend stays metered and visible instead of silently eaten.
    if (error.isInvalidField && error.billing.costUsd <= 0) {
      throw new AppError("VALIDATION_ERROR", error.message);
    }
    await trackDataforseoCost({ /* charge the failed-but-billed task */ });
  }
  throw error;
}
await trackDataforseoCost({ /* normal success path */ });
```

**Flow:** self-hosted mode ⇒ bare execute, no metering → hosted: resolve org customer, assert credits available (balance snapshot taken BEFORE execution), execute, track spend on success AND on charged-task failure, rethrow. The client is a hand-built facade of `meter()` entries grouped by section (serp/backlinks/keywords/domain/labs/lighthouse/business/aiSearch); each entry passes a PICKER `(s) => s.fetchX` so the section module — and its ~3MB statically-imported SDK — loads only on first API call via a lazily-cached dynamic import (`sectionsPromise ??= import(...)`). Type-only namespace import keeps sections out of the compile-time graph.
**Invariant:** ONE metering point per call — fetchers themselves never bill. Charged failures must still meter (vendor billed us even though the task failed); unbilled invalid-field rejections surface as non-reportable VALIDATION_ERROR without charging. Balance check happens before execution; spend recorded after.
**Probe:** `src/server/lib/dataforseo/client.test.ts` (metering on success/charged-failure/unbilled-rejection triad).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "meterDataforseoCall DataforseoChargedTaskError loadDataforseoSections", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: single metering seam, charged-vs-unbilled failure split, picker-based lazy section loading for heavyweight SDKs in serverless isolates. Adapt the billing backend (Autumn here) and feature-attribution taxonomy. Omit the specific section catalog.
