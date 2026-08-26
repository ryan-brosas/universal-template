<!-- capsule-v2 -->
# Batch endpoint fan-out via internal Request reconstruction — how do you reuse a route handler for N payloads without HTTP self-calls?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How does `/api/batch` invoke `/api/send`'s handler in-process, and what per-item state is preserved?

## batch-request-fanout
**Path/Symbol:** `src/app/api/batch/route.ts:POST :13-56`.
**Signature:** body `z.array(anyObjectParam).max(500)`; imports `* as send from '@/app/api/send/route'` and calls `send.POST(newRequest)` directly.
**Data Shape:** response `{ size, processed, errors, details:[{index,response}], cache }` — first SUCCESSFUL item's cache token is adopted (`cache ??=`).

### Decisive source
```ts
// Recreate a fresh Request since `new Request(request)` throws:
// > Cannot read private member #state from an object whose class did not declare it
const headers = new Headers(request.headers);
headers.set('content-type', 'application/json');
headers.delete('content-length');          // body length changed ⇒ header would lie
const newRequest = new Request(request.url, { method:'POST', headers, body: JSON.stringify(data) });
const response = await send.POST(newRequest);
```

**Flow:** array in → sequential loop (NOT parallel — preserves the tracker's session-cache chaining where item N's response token feeds item N+1's header) → collect per-index failures with full response bodies → single summary response.
**Invariant:** SEQUENTIAL processing is what makes cache-token propagation work (each sub-handler sees the updated x-umami-cache); content-length MUST be deleted or undici rejects the mismatched body. Failures are data (details[]), never thrown.
**Probe:** structural pins: `grep -n "content-length" src/app/api/batch/route.ts` → :32; `grep -n "cache ??=" src/app/api/batch/route.ts` → :42.
**Probe:** `grep -cF ".max(500)" src/app/api/batch/route.ts` → 1.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "batch send.POST newRequest processed details", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt handler-level fan-out for batching onto an existing ingest route; keep the sequential/cache-chaining semantics if your protocol uses rolling tokens; adapt the size cap.
