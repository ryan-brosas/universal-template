<!-- capsule-v2 -->
# Gateway o11y header factory — why are deployment coordinates resolved once but the request id per call?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do ambient Vercel platform variables reach gateway requests without coupling the package to the platform?

## Two-phase Resolvable: env snapshot + async request context
**Path/Symbol:** `packages/gateway/src/gateway-provider.ts:createO11yHeaders` (389–417); `packages/gateway/src/vercel-environment.ts:getVercelRequestId` (4–6).
**Signature:** `const createO11yHeaders = (): Resolvable<Record<string, string>>` — returns an ASYNC function consumed via `await resolve(this.config.o11yHeaders)` inside every model call.
**Data Shape:** Outer phase reads `VERCEL_DEPLOYMENT_ID`, `VERCEL_ENV`, `VERCEL_REGION`, `VERCEL_PROJECT_ID` ONCE at provider creation via `loadOptionalSetting` (undefined values are omitted from the object entirely). Inner phase awaits `getContext().headers?.['x-vercel-id']` PER REQUEST. Header names: `ai-o11y-deployment-id`, `ai-o11y-environment`, `ai-o11y-region`, `ai-o11y-request-id`, `ai-o11y-project-id`.

### Decisive source
```ts
return async () => {
  const requestId = await getVercelRequestId();   // per-call: request-scoped context
  return {
    ...(deploymentId && { 'ai-o11y-deployment-id': deploymentId }),
    ...(requestId && { 'ai-o11y-request-id': requestId }),
    …
  };
};
```
```ts
// vercel-environment.ts — the ONLY import of @vercel/oidc's context API in the package:
export async function getVercelRequestId(): Promise<string | undefined> {
  return getContext().headers?.['x-vercel-id'];
}
```

**Flow:** createGateway → createO11yHeaders() captures env snapshot → each model stores the returned function → per-request combineHeaders resolves it fresh → absent values never produce `undefined`-valued headers.
**Invariant:** Static-vs-dynamic split is semantic: deployment identity is stable per instance; the request id MUST be re-read per call because it comes from AsyncLocalStorage-style request context that changes every invocation. Conditional spread (`...(x && {...})`) keeps undefined keys OUT — a literal `'ai-o11y-region': undefined` breaks some fetch/header implementations.
**Probe:** `grep -c 'ai-o11y-deployment-id' packages/gateway/src/gateway-provider.ts` → `1`; direct tests: gateway-provider.test.ts 'should pass o11y headers to GatewayLanguageModel when environment variables are set' (:758) and 'should not include undefined o11y headers' (:801).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createO11yHeaders VERCEL_DEPLOYMENT_ID ai-o11y", limit: 10 });
```
Resolves line-exact: `createO11yHeaders Function gateway-provider.ts 389-417`.

## Verdict
Adopt the snapshot-env/await-context split for any telemetry propagation through a shared client; adapt env names/context getter to your host; omit nothing — flattening the two phases either leaks one request's id into another or freezes stale ids.
